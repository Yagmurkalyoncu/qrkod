import cv2
import time
import numpy as np
import uuid
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from config import current_config, logger
from database import automations_db, save_db, system_state
from scanner import QRScanner
from analyzer import DoorStatusAnalyzer

app = Flask(__name__)
# Frontend React uygulamasına izin ver (Örn: localhost:5173)
CORS(app)

scanner = QRScanner()
analyzer = DoorStatusAnalyzer()

def draw_info(frame, qr_list):
    for qr in qr_list:
        pts = qr['points'].reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=(255, 0, 0), thickness=3)

def gen_frames():
    camera = cv2.VideoCapture(current_config.CAMERA_SOURCE)
    while True:
        success, frame = camera.read()
        if not success: break
        
        if not current_config.IS_ACTIVE:
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            black_frame[:] = (20, 15, 10) 
            ret, buffer = cv2.imencode('.jpg', black_frame)
            system_state["status"] = "DURDURULDU"
            system_state["qr_count"] = 0
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            continue
            
        qr_list = scanner.detect_and_decode(frame)
        system_state["status"] = analyzer.analyze(qr_list)
        system_state["qr_count"] = len(qr_list)
        system_state["last_update"] = time.time()
        
        draw_info(frame, qr_list)
        
        status_text = system_state["status"]
        if status_text.startswith("KAPALI"):
            color = (0, 255, 0)
        elif status_text.startswith("ACIK"):
            color = (0, 0, 255)
        else:
            color = (150, 150, 150)
            
        (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, status_text, (frame.shape[1] - tw - 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

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
            "aci_toleransi": float(data.get("aci_toleransi", 0.20))
        }
    }
    save_db(automations_db)
    return jsonify({"success": True, "id": new_id, "data": automations_db[new_id]})

@app.route('/api/automations/<auto_id>', methods=['PUT'])
def update_automation(auto_id):
    if auto_id not in automations_db:
        return jsonify({"success": False, "error": "Not found"}), 404
    
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
        
    save_db(automations_db)
    
    if current_config.ACTIVE_AUTO_ID == auto_id:
        current_config.DISTANCE_TOLERANCE = db_item["analiz_toleranslari"]["mesafe_toleransi"]
        current_config.ASPECT_RATIO_TOLERANCE = db_item["analiz_toleranslari"]["aci_toleransi"]
        
    return jsonify({"success": True})

@app.route('/api/automations/<auto_id>', methods=['DELETE'])
def delete_automation(auto_id):
    if auto_id in automations_db:
        del automations_db[auto_id]
        save_db(automations_db)
        if current_config.ACTIVE_AUTO_ID == auto_id:
            current_config.ACTIVE_AUTO_ID = None
            system_state["automation_id"] = "Seçilmedi"
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        if 'DISTANCE_TOLERANCE' in data: current_config.DISTANCE_TOLERANCE = float(data['DISTANCE_TOLERANCE'])
        if 'ASPECT_RATIO_TOLERANCE' in data: current_config.ASPECT_RATIO_TOLERANCE = float(data['ASPECT_RATIO_TOLERANCE'])
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
        system_state["automation_id"] = auto_data["name"]
        system_state["cabinet_type"] = auto_data["kabin_tipi"]
        return jsonify({"success": True, "data": auto_data})
    return jsonify({"success": False}), 404

if __name__ == '__main__':
    logger.info("Modüler Backend Başlatılıyor (Port: 5000)...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
