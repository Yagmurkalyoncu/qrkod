import os
import math
import collections
import numpy as np
import json
from .config import current_config, system_state
from .db_manager import automations_db, save_db
import time

class DoorStatusAnalyzer:
    def __init__(self):
        self.history = collections.deque(maxlen=15)
        self.baselines_file = os.path.join(os.path.dirname(__file__), 'baselines.json')
        os.makedirs(os.path.dirname(self.baselines_file), exist_ok=True)
        self.baselines = self._load_baselines()
        
        # Kalibrasyon ve Hysteresis Durumları
        self.calibration_buffer = []
        self.REQUIRED_CALIBRATION_FRAMES = 20
        self.current_solid_status = "BILINMIYOR"
        self.status_counter = 0
        self.REQUIRED_CONSECUTIVE_FRAMES = 5  # Durum değiştirmek için gereken peş peşe aynı sonuç sayısı

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

    def _filter_reflections(self, qr_list):
        if len(qr_list) <= 2:
            return qr_list
        qr_list.sort(key=lambda qr: self._calculate_width(qr['points']), reverse=True)
        return qr_list[:2]

    def _update_hysteresis(self, new_raw_status):
        # Eğer okunamadı veya eksik QR ise anında tepki verme, mevcut durumu koru ama sayacı sıfırla
        if "BILINMIYOR" in new_raw_status or "Eksik" in new_raw_status:
            # Sadece çok uzun süre QR görülmezse durumu ACIK(Eksik) yap
            self.history.append(new_raw_status)
            c = collections.Counter(self.history)
            if c[new_raw_status] >= 10:
                self.current_solid_status = new_raw_status
            return self.current_solid_status

        # Durum değişimi kontrolü
        if new_raw_status == self.current_solid_status:
            self.status_counter = 0
            self.history.append(new_raw_status)
        else:
            self.status_counter += 1
            if self.status_counter >= self.REQUIRED_CONSECUTIVE_FRAMES:
                self.current_solid_status = new_raw_status
                self.status_counter = 0
                self.history.clear()
        
        return self.current_solid_status

    def analyze(self, qr_list):
        if not current_config.IS_ACTIVE:
            self.calibration_buffer.clear()
            return "DURDURULDU"
            
        raw_status = self._get_raw_status(qr_list)
        return self._update_hysteresis(raw_status)

    def _get_raw_status(self, qr_list):
        filtered_qrs = self._filter_reflections(qr_list)
        
        if len(filtered_qrs) < 2: return "ACIK (Eksik QR)"
        if len(filtered_qrs) > 2: return "BILINMIYOR (Cok fazla QR)"

        filtered_qrs.sort(key=lambda qr: self._calculate_center(qr['points'])[0])

        qr1, qr2 = filtered_qrs[0], filtered_qrs[1]
        data1, data2 = qr1['data'], qr2['data']
        
        if not data1 or not data2: return "BILINMIYOR (QR Okunamadi)"

        pts1, pts2 = qr1['points'], qr2['points']
        center1 = self._calculate_center(pts1)
        center2 = self._calculate_center(pts2)
        dist = self._calculate_distance(center1, center2)
        avg_w = (self._calculate_width(pts1) + self._calculate_width(pts2)) / 2.0
        
        cur_dist_ratio = dist / avg_w if avg_w > 0 else 0
        aspect1 = self._calculate_aspect_ratio(pts1)
        aspect2 = self._calculate_aspect_ratio(pts2)

        cabinet_key = f"{data1} | {data2}"

        # --- KALİBRASYON (MENTÖRÜN İSTEDİĞİ ORTALAMA HESABI) ---
        # Eğer kalibrasyon yoksa veya eski sürüm bir kalibrasyonsa (genişlik bilgisi yoksa), yeniden kalibre et
        if cabinet_key not in self.baselines or "qr1_width" not in self.baselines[cabinet_key]:
            self.calibration_buffer.append({
                "dist": cur_dist_ratio,
                "a1": aspect1,
                "a2": aspect2,
                "w1": self._calculate_width(pts1),
                "w2": self._calculate_width(pts2)
            })
            
            if len(self.calibration_buffer) < self.REQUIRED_CALIBRATION_FRAMES:
                pct = int((len(self.calibration_buffer) / self.REQUIRED_CALIBRATION_FRAMES) * 100)
                return f"KALIBRASYON... %{pct}"
            
            # Kalibrasyon tamamlandı: Ortalama ve maksimum sapmayı (varyans) hesapla
            dists = [x["dist"] for x in self.calibration_buffer]
            a1s = [x["a1"] for x in self.calibration_buffer]
            a2s = [x["a2"] for x in self.calibration_buffer]
            w1s = [x["w1"] for x in self.calibration_buffer]
            w2s = [x["w2"] for x in self.calibration_buffer]
            
            avg_dist = np.mean(dists)
            std_dist = np.std(dists)
            avg_a1 = np.mean(a1s)
            avg_a2 = np.mean(a2s)
            avg_w1 = np.mean(w1s)
            avg_w2 = np.mean(w2s)
            
            # Sensör/Kamera titremesine göre dinamik tolerans belirleme
            # Eğer kamera çok titriyorsa toleransı genişlet, netse daralt
            dynamic_dist_tol = max(current_config.DISTANCE_TOLERANCE, (std_dist / avg_dist) * 3.0) 
            # Aspect ratio çok dalgalanıyorsa esnek bırak (min %20, duruma göre artar)
            dynamic_aspect_tol = max(current_config.ASPECT_RATIO_TOLERANCE, np.std(a1s)*3, np.std(a2s)*3)
            # Derinlik (Z Ekseni) toleransı
            dynamic_depth_tol = max(current_config.DEPTH_TOLERANCE, np.std(w1s/avg_w1)*3, np.std(w2s/avg_w2)*3)

            self._save_baseline(cabinet_key, {
                "distance_ratio": float(avg_dist),
                "qr1_aspect": float(avg_a1),
                "qr2_aspect": float(avg_a2),
                "qr1_width": float(avg_w1),
                "qr2_width": float(avg_w2),
                "dynamic_dist_tol": float(dynamic_dist_tol),
                "dynamic_aspect_tol": float(dynamic_aspect_tol),
                "dynamic_depth_tol": float(dynamic_depth_tol)
            })
            self.calibration_buffer.clear()
            return "KAPALI (Ogrenildi)"

        # --- NORMAL ANALİZ ---
        base = self.baselines[cabinet_key]
        
        # Dinamik toleransları kullan (Mentör isteği)
        dist_tol = base.get("dynamic_dist_tol", current_config.DISTANCE_TOLERANCE)
        aspect_tol = base.get("dynamic_aspect_tol", current_config.ASPECT_RATIO_TOLERANCE)
        
        # 1. Mesafe İhlali
        ratio_diff = abs(cur_dist_ratio - base.get("distance_ratio", cur_dist_ratio)) / (base.get("distance_ratio", cur_dist_ratio) or 1)
        distance_violated = ratio_diff > dist_tol
        
        # 2. Açı İhlali
        aspect_violated = (abs(aspect1 - base.get("qr1_aspect", aspect1)) > aspect_tol or 
                           abs(aspect2 - base.get("qr2_aspect", aspect2)) > aspect_tol)
        
        # 3. Derinlik (Z Ekseni) İhlali - Biri büyürken diğeri aynı kalıyorsa
        base_w1 = base.get("qr1_width", self._calculate_width(pts1)) or 1
        base_w2 = base.get("qr2_width", self._calculate_width(pts2)) or 1
        cur_w1 = self._calculate_width(pts1)
        cur_w2 = self._calculate_width(pts2)
        scale1 = cur_w1 / base_w1
        scale2 = cur_w2 / base_w2
        depth_tol = base.get("dynamic_depth_tol", current_config.DEPTH_TOLERANCE)
        depth_violated = abs(scale1 - scale2) > depth_tol # Büyüme oranları dinamik Z toleransından fazla farklıysa
        
        if distance_violated and not aspect_violated and not depth_violated:
            return "ACIK (Surgulu Acilmis)"
        elif aspect_violated or depth_violated:
            return "ACIK (Mentese Acilmis)"
            
        return "KAPALI"
