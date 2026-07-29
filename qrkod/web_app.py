import cv2
import sys
import math
import collections
import numpy as np
import json
import os
import logging
import threading
import time
import uuid
from flask import Flask, render_template, Response, jsonify, request

from src.config import current_config, system_state
from src.logger import logger
from src.db_manager import automations_db, save_db
from src.qr_detector import QRScanner
from src.analyzer import DoorStatusAnalyzer

# ---------------- KAMERA YÖNETİCİSİ ---------------- #
class CameraManager:
    """Kamerayı güvenli şekilde arka planda okuyan yönetici sınıf.
    Windows DirectShow thread kilitlenmelerini önler ve her zaman en güncel kareyi verir."""
    
    def __init__(self):
        self._cap = None
        self._lock = threading.Lock()
        self.frame = None
        self.is_running = False
        self.thread = None
    
    def start(self):
        with self._lock:
            if self.is_running:
                return True
            self.is_running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
            return True

    def _update(self):
        while self.is_running:
            if self._cap is None or not self._cap.isOpened():
                self._cap = cv2.VideoCapture(current_config.CAMERA_SOURCE)
                if self._cap.isOpened():
                    # Çözünürlük değiştirme (1280x720 vs) Windows kameralarını kilitlediği için tamamen kaldırıldı. 
                    # Kamera varsayılan çözünürlüğüyle (genelde 640x480) güvenli modda çalışacak.
                    logger.info("Kamera basariyla acildi.")
                else:
                    self._cap = None
                    time.sleep(1.0)
                    continue

            success, frame = self._cap.read()
            if success:
                self.frame = frame
            else:
                self.release()
                time.sleep(0.5)

    def read(self):
        return self.frame is not None, self.frame
    
    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

# ---------------- FLASK APP ---------------- #
app = Flask(__name__)
scanner = QRScanner()
analyzer = DoorStatusAnalyzer()
camera_manager = CameraManager()
camera_manager.start()

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

def draw_info(frame, qr_list):
    for qr in qr_list:
        pts = qr['points'].reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=(255, 0, 0), thickness=3)

def gen_frames():
    while True:
        # Sistem durdurulmuşsa kamerayı serbest bırak ve siyah ekran göster
        if not current_config.IS_ACTIVE:
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            black_frame[:] = (20, 15, 10)
            ret, buffer = cv2.imencode('.jpg', black_frame)
            system_state["status"] = "DURDURULDU"
            system_state["qr_count"] = 0
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.5)
            continue
        
        success, frame_ref = camera_manager.read()
        if not success or frame_ref is None:
            time.sleep(0.1)
            continue
            
        # Arka plan thread'i ile çakışmamak için karenin bir kopyasını alıyoruz
        frame = frame_ref.copy()
            
        qr_list = scanner.detect_and_decode(frame)
        system_state["status"] = analyzer.analyze(qr_list)
        system_state["qr_count"] = len(qr_list)
        system_state["last_update"] = time.time()
        
        draw_info(frame, qr_list)
        
        # Kamera yayını üzerine durumu yazdır
        status_text = system_state["status"]
        if status_text.startswith("KAPALI"):
            color = (0, 255, 0) # Green (BGR)
        elif status_text.startswith("ACIK"):
            color = (0, 0, 255) # Red
        else:
            color = (150, 150, 150) # Gray
            
        (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, status_text, (frame.shape[1] - tw - 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template('maincontent.html')

@app.route('/otomasyon')
def otomasyon():
    return render_template('otomasyonEkrani.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/state')
def get_state():
    return jsonify(system_state)

# --- CRUD ENDPOINTS FOR AUTOMATIONS ---

@app.route('/api/automations', methods=['GET'])
def get_automations():
    return jsonify(automations_db)

@app.route('/api/automations', methods=['POST'])
def add_automation():
    data = request.json
    new_id = "oto_" + str(uuid.uuid4())[:8]
    automations_db[new_id] = {
        "name": data.get("name", "İsimsiz Otomasyon"),
        "kabin_tipi": data.get("kabin_tipi", "Bilinmiyor"),
        "fiziksel_parametreler": {
            "kabin_yuksekligi_m": float(data.get("kabin_yuksekligi_m", 2.50)),
            "qr_koordinatlari": {
                "x": float(data.get("x_koordinati", 0.0)),
                "y": float(data.get("y_koordinati", 0.0)),
                "z": float(data.get("z_koordinati", 2.15))
            }
        },
        "analiz_toleranslari": {
            "mesafe_toleransi": float(data.get("mesafe_toleransi", 0.05)),
            "aci_toleransi": float(data.get("aci_toleransi", 0.20)),
            "derinlik_toleransi": float(data.get("derinlik_toleransi", 0.08))
        }
    }
    save_db(automations_db)
    return jsonify({"success": True, "id": new_id, "data": automations_db[new_id]})

@app.route('/api/automations/<auto_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_automation(auto_id):
    if auto_id not in automations_db:
        return jsonify({"error": "Not found"}), 404

    if request.method == 'GET':
        return jsonify(automations_db[auto_id])
        
    if request.method == 'DELETE':
        del automations_db[auto_id]
        save_db(automations_db)
        if current_config.ACTIVE_AUTO_ID == auto_id:
            current_config.ACTIVE_AUTO_ID = None
            system_state["automation_id"] = "Seçilmedi"
        return jsonify({"success": True})
        
    data = request.json
    db_item = automations_db[auto_id]
    
    if "kabin_yuksekligi_m" in data:
        db_item["fiziksel_parametreler"]["kabin_yuksekligi_m"] = float(data["kabin_yuksekligi_m"])
    if "x_koordinati" in data:
        db_item["fiziksel_parametreler"]["qr_koordinatlari"]["x"] = float(data["x_koordinati"])
    if "y_koordinati" in data:
        db_item["fiziksel_parametreler"]["qr_koordinatlari"]["y"] = float(data["y_koordinati"])
    if "z_koordinati" in data:
        db_item["fiziksel_parametreler"]["qr_koordinatlari"]["z"] = float(data["z_koordinati"])
    if "mesafe_toleransi" in data:
        db_item["analiz_toleranslari"]["mesafe_toleransi"] = float(data["mesafe_toleransi"])
    if "aci_toleransi" in data:
        db_item["analiz_toleranslari"]["aci_toleransi"] = float(data["aci_toleransi"])
    if "derinlik_toleransi" in data:
        db_item["analiz_toleranslari"]["derinlik_toleransi"] = float(data["derinlik_toleransi"])
        
    save_db(automations_db)
    
    # If the updated automation is currently active, apply changes immediately
    if current_config.ACTIVE_AUTO_ID == auto_id:
        current_config.DISTANCE_TOLERANCE = db_item["analiz_toleranslari"]["mesafe_toleransi"]
        current_config.ASPECT_RATIO_TOLERANCE = db_item["analiz_toleranslari"]["aci_toleransi"]
        current_config.DEPTH_TOLERANCE = db_item["analiz_toleranslari"].get("derinlik_toleransi", 0.08)
        
    return jsonify({"success": True})



@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        if 'DISTANCE_TOLERANCE' in data: current_config.DISTANCE_TOLERANCE = float(data['DISTANCE_TOLERANCE'])
        if 'ASPECT_RATIO_TOLERANCE' in data: current_config.ASPECT_RATIO_TOLERANCE = float(data['ASPECT_RATIO_TOLERANCE'])
        if 'DEPTH_TOLERANCE' in data: current_config.DEPTH_TOLERANCE = float(data['DEPTH_TOLERANCE'])
        if 'IS_ACTIVE' in data: current_config.IS_ACTIVE = bool(data['IS_ACTIVE'])
        return jsonify({"message": "Config updated", "IS_ACTIVE": current_config.IS_ACTIVE})
    
    return jsonify({
        "DISTANCE_TOLERANCE": current_config.DISTANCE_TOLERANCE,
        "ASPECT_RATIO_TOLERANCE": current_config.ASPECT_RATIO_TOLERANCE,
        "IS_ACTIVE": getattr(current_config, 'IS_ACTIVE', True)
    })

@app.route('/api/set_target', methods=['POST'])
def set_target():
    data = request.json
    auto_id = data.get('id')
    if auto_id in automations_db:
        auto_data = automations_db[auto_id]
        current_config.ACTIVE_AUTO_ID = auto_id
        current_config.DISTANCE_TOLERANCE = auto_data["analiz_toleranslari"]["mesafe_toleransi"]
        current_config.ASPECT_RATIO_TOLERANCE = auto_data["analiz_toleranslari"]["aci_toleransi"]
        current_config.DEPTH_TOLERANCE = auto_data["analiz_toleranslari"].get("derinlik_toleransi", 0.08)
        system_state["automation_id"] = auto_data["name"]
        system_state["cabinet_type"] = auto_data["kabin_tipi"]
        return jsonify({"success": True, "data": auto_data})
    return jsonify({"success": False}), 404

@app.route('/api/reset_baselines', methods=['POST'])
def reset_baselines():
    """Öğrenme hafızasını (baselines.json) sıfırlar.
    Sistem tüm kabinleri unutur ve sıfırdan öğrenmeye başlar."""
    analyzer.baselines = {}
    try:
        with open(analyzer.baselines_file, 'w') as f:
            json.dump({}, f)
        analyzer.history.clear()
        logger.info("BASELINES SIFIRLANDI - Sistem sifirdan ogrenecek.")
        return jsonify({"success": True, "message": "Ogrenme hafizasi sifirlandi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
