import math
import collections
import json
import os
import numpy as np

# Proje içi kütüphanelerden ayarları ve state'i çekiyoruz
from config import current_config
from database import system_state

class DoorStatusAnalyzer:
    def __init__(self):
        self.history = collections.deque(maxlen=15)
        self.baselines_file = os.path.join(os.path.dirname(__file__), 'data', 'baselines.json')
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
