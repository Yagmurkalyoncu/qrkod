import cv2
import sys
import math
import collections
import numpy as np
import json
import os
import logging

# ---------------- CONFIGURATION ---------------- #
class Config:
    # Kamera ayarları (0: varsayılan webcam, veya "video.mp4" gibi dosya yolu)
    CAMERA_SOURCE = 0 
    
    # Otonom Çalışma Ayarları (Önceden bilinen kapalı referans oranı)
    EXPECTED_BASELINE_RATIO = 1.28
    
    # Analiz Toleransları
    DISTANCE_TOLERANCE = 0.05 
    ASPECT_RATIO_TOLERANCE = 0.20
    
    # Sistem Log seviyesi (INFO, DEBUG, ERROR)
    LOG_LEVEL = "INFO"
    
    # Ekranda gösterilecek metinlerin ayarları
    FONT_SCALE = 0.7
    FONT_THICKNESS = 2

# ---------------- LOGGER SETUP ---------------- #
def setup_logger():
    logger = logging.getLogger("DoorStatusScanner")
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger()

# ---------------- CAMERA MODULE ---------------- #
class Camera:
    def __init__(self, source):
        self.source = source
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            logger.error(f"Kamera/Video kaynağı açılamadı: {self.source}")
            raise ValueError(f"Kaynak açılamadı: {self.source}")
        
        logger.info(f"Görüntü kaynağı başarıyla başlatıldı: {self.source}")

    def read_frame(self):
        success, frame = self.cap.read()
        if not success:
            logger.warning("Görüntü karesi alınamadı veya video bitti.")
        return success, frame

    def release(self):
        if self.cap:
            self.cap.release()
            logger.info("Kamera bağlantısı kapatıldı.")

# ---------------- QR SCANNER MODULE ---------------- #
class QRScanner:
    def __init__(self):
        self.detector = cv2.QRCodeDetector()

    def detect_and_decode(self, frame):
        detected_qrs = []
        success, decoded_info, points, _ = self.detector.detectAndDecodeMulti(frame)
        
        if success and points is not None:
            for i in range(len(decoded_info)):
                pts = points[i].astype(int)
                data = decoded_info[i]
                
                detected_qrs.append({
                    'data': data if data else "Bilinmeyen QR",
                    'points': pts
                })
                
        return detected_qrs

# ---------------- ANALYZER MODULE ---------------- #
class DoorStatusAnalyzer:
    def __init__(self):
        # Stabilite için son 15 karenin sonucunu tutan liste
        self.history = collections.deque(maxlen=15)
        self.baselines_file = os.path.join(os.path.dirname(__file__), 'baselines.json')
        self.baselines = self._load_baselines()

    def _load_baselines(self):
        if os.path.exists(self.baselines_file):
            try:
                with open(self.baselines_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Baselines dosyasi okunamadi: {e}")
        return {}

    def _save_baseline(self, key, data):
        self.baselines[key] = data
        try:
            with open(self.baselines_file, 'w') as f:
                json.dump(self.baselines, f, indent=4)
            logger.info(f"YENI KABIN OGRENILDI: {key}")
        except Exception as e:
            logger.error(f"Baselines dosyasi kaydedilemedi: {e}")

    def _calculate_center(self, points):
        x = np.mean(points[:, 0])
        y = np.mean(points[:, 1])
        return x, y

    def _calculate_width(self, points):
        width_top = np.linalg.norm(points[0] - points[1])
        width_bottom = np.linalg.norm(points[2] - points[3])
        return (width_top + width_bottom) / 2.0

    def _calculate_height(self, points):
        height_left = np.linalg.norm(points[0] - points[3])
        height_right = np.linalg.norm(points[1] - points[2])
        return (height_left + height_right) / 2.0

    def _calculate_aspect_ratio(self, points):
        w = self._calculate_width(points)
        h = self._calculate_height(points)
        if h == 0:
            return 1.0
        return w / h

    def _calculate_distance(self, center1, center2):
        return math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

    def analyze(self, qr_list):
        raw_status = self._get_raw_status(qr_list)
        self.history.append(raw_status)
        
        status_counts = collections.Counter(self.history)
        most_common_status = status_counts.most_common(1)[0][0]
        
        return most_common_status

    def _get_raw_status(self, qr_list):
        if len(qr_list) < 2:
            return "ACIK (Eksik QR)"
        
        if len(qr_list) > 2:
            return "BILINMIYOR (Cok fazla QR)"

        qr1, qr2 = qr_list[0], qr_list[1]
        data1, data2 = qr1['data'], qr2['data']

        if not data1 or not data2:
            return "BILINMIYOR (QR Icerigi Okunamadi)"

        pts1, pts2 = qr1['points'], qr2['points']
        center1 = self._calculate_center(pts1)
        center2 = self._calculate_center(pts2)

        distance = self._calculate_distance(center1, center2)
        avg_width = (self._calculate_width(pts1) + self._calculate_width(pts2)) / 2.0
        current_distance_ratio = distance / avg_width if avg_width > 0 else 0

        aspect1 = self._calculate_aspect_ratio(pts1)
        aspect2 = self._calculate_aspect_ratio(pts2)

        sorted_keys = sorted([data1, data2])
        cabinet_key = f"{sorted_keys[0]} | {sorted_keys[1]}"

        if cabinet_key not in self.baselines:
            baseline_data = {
                "distance_ratio": current_distance_ratio,
                data1: {"aspect": aspect1},
                data2: {"aspect": aspect2}
            }
            self._save_baseline(cabinet_key, baseline_data)
            return "KAPALI (Ogrenildi)"

        baseline = self.baselines[cabinet_key]

        base_distance = baseline["distance_ratio"]
        ratio_diff = abs(current_distance_ratio - base_distance) / (base_distance if base_distance > 0 else 1)
        if ratio_diff > Config.DISTANCE_TOLERANCE:
            logger.debug(f"Aralık tespit edildi. Ogrenilen: {base_distance:.2f}, Guncel: {current_distance_ratio:.2f}")
            return "ACIK (Aralanmis)"

        diff1 = abs(aspect1 - baseline[data1]["aspect"])
        diff2 = abs(aspect2 - baseline[data2]["aspect"])

        if diff1 > Config.ASPECT_RATIO_TOLERANCE or diff2 > Config.ASPECT_RATIO_TOLERANCE:
            logger.debug(f"Eklemli açılma tespit edildi. Fark1: {diff1:.2f}, Fark2: {diff2:.2f}")
            return "ACIK (Eklemli Acilmis)"

        return "KAPALI"

# ---------------- MAIN APPLICATION ---------------- #
def draw_info(frame, qr_list, status):
    if status.startswith("KAPALI"):
        color = (0, 255, 0)
    else:
        color = (0, 0, 255)

    text = f"DURUM: {status}"
    font_scale = Config.FONT_SCALE * 1.5
    thickness = Config.FONT_THICKNESS + 1
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    
    cv2.rectangle(frame, (10, 10), (20 + text_w, 20 + text_h + 10), (0, 0, 0), -1)
    cv2.putText(frame, text, (15, 20 + text_h), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    for qr in qr_list:
        pts = qr['points']
        pts_reshape = pts.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_reshape], isClosed=True, color=(255, 0, 0), thickness=2)
        x, y = int(pts[0][0]), int(pts[0][1])
        cv2.putText(frame, qr['data'], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

def main():
    logger.info("Sistem başlatılıyor...")

    try:
        camera = Camera(Config.CAMERA_SOURCE)
    except Exception as e:
        logger.error("Kamera başlatılamadı, çıkış yapılıyor.")
        sys.exit(1)

    scanner = QRScanner()
    analyzer = DoorStatusAnalyzer()

    logger.info("Otonom sistem başlatıldı. Çıkmak için 'Q' tuşuna basın.")

    while True:
        success, frame = camera.read_frame()
        if not success:
            break

        qr_list = scanner.detect_and_decode(frame)
        status = analyzer.analyze(qr_list)
        draw_info(frame, qr_list, status)

        cv2.imshow("Kabin Kapagi Durum Tespiti", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('Q')]:
            break

    camera.release()
    cv2.destroyAllWindows()
    logger.info("Sistem kapatıldı.")

if __name__ == "__main__":
    main()
