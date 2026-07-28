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

# ---------------- LOGGER SETUP ---------------- #
def setup_logger():
    logger = logging.getLogger("DoorStatusScanner")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

logger = setup_logger()

# ---------------- LOAD DB ---------------- #
db_path = os.path.join(os.path.dirname(__file__), 'src', 'automations_db.json')

def load_db():
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Geriye dönük uyumluluk: Eski kayıtlara X ve Y ekle
            for k, v in data.items():
                if "x" not in v.get("fiziksel_parametreler", {}).get("qr_koordinatlari", {}):
                    v["fiziksel_parametreler"]["qr_koordinatlari"]["x"] = 0.0
                    v["fiziksel_parametreler"]["qr_koordinatlari"]["y"] = 0.0
            return data
    return {}

def save_db(data):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

automations_db = load_db()

# ---------------- DYNAMIC CONFIGURATION ---------------- #
class Config:
    CAMERA_SOURCE = 0 
    EXPECTED_BASELINE_RATIO = 1.28
    DISTANCE_TOLERANCE = 0.05 
    ASPECT_RATIO_TOLERANCE = 0.20
    ACTIVE_AUTO_ID = None
    IS_ACTIVE = True

current_config = Config()

system_state = {
    "status": "BEKLENİYOR",
    "cabinet_type": "Bilinmiyor",
    "automation_id": "Seçilmedi",
    "qr_count": 0,
    "last_update": time.time()
}

# ---------------- QR SCANNER MODULE ---------------- #
class QRScanner:
    def __init__(self):
        self.point_history = {}
        self.alpha = 0.25 # %25 yeni veri, %75 eski veri (Yüksek stabilite)
        try:
            self.detector = cv2.wechat_qrcode_WeChatQRCode()
            self.use_wechat = True
        except:
            self.detector = cv2.QRCodeDetector()
            self.use_wechat = False

    def _smooth_points(self, data, pts):
        if data not in self.point_history:
            self.point_history[data] = pts.astype(np.float32)
            return pts
        
        smoothed = self.alpha * pts.astype(np.float32) + (1.0 - self.alpha) * self.point_history[data]
        self.point_history[data] = smoothed
        return smoothed.astype(int)

    def _preprocess_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return enhanced_bgr

    def detect_and_decode(self, frame):
        detected_qrs = self._attempt_decode(frame)
        if len(detected_qrs) < 2:
            processed_frame = self._preprocess_frame(frame)
            processed_qrs = self._attempt_decode(processed_frame)
            if len(processed_qrs) > len(detected_qrs):
                detected_qrs = processed_qrs
        return detected_qrs

    def _attempt_decode(self, frame):
        detected_qrs = []
        if self.use_wechat:
            decoded_info, points = self.detector.detectAndDecode(frame)
            if len(decoded_info) > 0 and points:
                for i in range(len(decoded_info)):
                    pts = np.array(points[i], dtype=int)
                    data = decoded_info[i] if decoded_info[i] else "Bilinmeyen QR"
                    pts = self._smooth_points(data, pts)
                    detected_qrs.append({'data': data, 'points': pts})
        else:
            success, decoded_info, points, _ = self.detector.detectAndDecodeMulti(frame)
            if success and points is not None:
                for i in range(len(decoded_info)):
                    pts = points[i].astype(int)
                    data = decoded_info[i] if decoded_info[i] else "Bilinmeyen QR"
                    pts = self._smooth_points(data, pts)
                    detected_qrs.append({'data': data, 'points': pts})
        return detected_qrs

# ---------------- ANALYZER MODULE ---------------- #
class DoorStatusAnalyzer:
    def __init__(self):
        self.history = collections.deque(maxlen=15)
        self.baselines_file = os.path.join(os.path.dirname(__file__), 'src', 'baselines.json')
        os.makedirs(os.path.dirname(self.baselines_file), exist_ok=True)
        self.baselines = self._load_baselines()

    def _load_baselines(self):
        if os.path.exists(self.baselines_file):
            try:
                with open(self.baselines_file, 'r') as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_baseline(self, key, data):
        self.baselines[key] = data
        try:
            with open(self.baselines_file, 'w') as f:
                json.dump(self.baselines, f, indent=4)
        except: pass

    def _calculate_center(self, points):
        return np.mean(points[:, 0]), np.mean(points[:, 1])

    def _calculate_width(self, points):
        return (np.linalg.norm(points[0]-points[1]) + np.linalg.norm(points[2]-points[3])) / 2.0

    def _calculate_height(self, points):
        return (np.linalg.norm(points[0]-points[3]) + np.linalg.norm(points[1]-points[2])) / 2.0

    def _calculate_aspect_ratio(self, points):
        h = self._calculate_height(points)
        return self._calculate_width(points) / h if h != 0 else 1.0

    def _calculate_distance(self, c1, c2):
        return math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)

    def analyze(self, qr_list):
        if not current_config.IS_ACTIVE:
            return "DURDURULDU"
            
        raw_status = self._get_raw_status(qr_list)
        self.history.append(raw_status)
        return collections.Counter(self.history).most_common(1)[0][0]

    def _get_raw_status(self, qr_list):
        if len(qr_list) < 2: return "ACIK (Eksik QR)"
        if len(qr_list) > 2: return "BILINMIYOR (Cok fazla QR)"

        qr1, qr2 = qr_list[0], qr_list[1]
        data1, data2 = qr1['data'], qr2['data']
        
        try:
            parsed1 = json.loads(data1)
            system_state["cabinet_type"] = parsed1.get("kabin_tipi", system_state["cabinet_type"])
            if "otomasyon_id" in parsed1 and not current_config.ACTIVE_AUTO_ID:
                system_state["automation_id"] = parsed1["otomasyon_id"]
        except:
            pass

        if not data1 or not data2: return "BILINMIYOR (QR Okunamadi)"

        pts1, pts2 = qr1['points'], qr2['points']
        center1 = self._calculate_center(pts1)
        center2 = self._calculate_center(pts2)
        dist = self._calculate_distance(center1, center2)
        avg_w = (self._calculate_width(pts1) + self._calculate_width(pts2)) / 2.0
        cur_dist_ratio = dist / avg_w if avg_w > 0 else 0

        aspect1 = self._calculate_aspect_ratio(pts1)
        aspect2 = self._calculate_aspect_ratio(pts2)

        cabinet_key = f"{sorted([data1, data2])[0]} | {sorted([data1, data2])[1]}"

        if cabinet_key not in self.baselines:
            self._save_baseline(cabinet_key, {
                "distance_ratio": cur_dist_ratio,
                data1: {"aspect": aspect1},
                data2: {"aspect": aspect2}
            })
            return "KAPALI (Ogrenildi)"

        base = self.baselines[cabinet_key]
        ratio_diff = abs(cur_dist_ratio - base["distance_ratio"]) / (base["distance_ratio"] or 1)
        if ratio_diff > current_config.DISTANCE_TOLERANCE: return "ACIK (Aralanmis)"

        if abs(aspect1 - base[data1]["aspect"]) > current_config.ASPECT_RATIO_TOLERANCE or \
           abs(aspect2 - base[data2]["aspect"]) > current_config.ASPECT_RATIO_TOLERANCE:
            return "ACIK (Eklemli Acilmis)"

        return "KAPALI"

# ---------------- FLASK APP ---------------- #
app = Flask(__name__)
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
            # Create a simple dark frame (saves CPU/Bandwidth)
            # We rely on CSS overlay for the beautiful text, not OpenCV
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            black_frame[:] = (20, 15, 10) # Very dark blueish black
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
    
    # If the updated automation is currently active, apply changes immediately
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
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
