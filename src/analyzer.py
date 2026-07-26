import math
import collections
import numpy as np
import json
import os
from logger import logger
from config import Config

class DoorStatusAnalyzer:
    def __init__(self):
        # Stabilite (titreme engelleme) icin son 15 karenin (yaklasik yarim saniye) sonucunu tutan liste
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
        """4 köşe koordinatından merkezi hesaplar."""
        x = np.mean(points[:, 0])
        y = np.mean(points[:, 1])
        return x, y

    def _calculate_width(self, points):
        """QR kodun ortalama genişliğini hesaplar (Üst ve alt kenarların ortalaması)."""
        width_top = np.linalg.norm(points[0] - points[1])
        width_bottom = np.linalg.norm(points[2] - points[3])
        return (width_top + width_bottom) / 2.0

    def _calculate_height(self, points):
        """QR kodun ortalama yüksekliğini hesaplar."""
        height_left = np.linalg.norm(points[0] - points[3])
        height_right = np.linalg.norm(points[1] - points[2])
        return (height_left + height_right) / 2.0

    def _calculate_aspect_ratio(self, points):
        """QR kodun en-boy oranını hesaplar. (Perspektif çarpılmasını anlamak için)"""
        w = self._calculate_width(points)
        h = self._calculate_height(points)
        if h == 0:
            return 1.0
        return w / h

    def _calculate_distance(self, center1, center2):
        """İki merkez noktası arasındaki Öklid mesafesini hesaplar."""
        return math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

    def analyze(self, qr_list):
        """
        Anlık görüntüyü analiz ederek kapının durumunu döndürür (Stabilize edilmiş haliyle).
        """
        raw_status = self._get_raw_status(qr_list)
        self.history.append(raw_status)
        
        # Oylama sistemi: Son 15 karede en çok görülen durumu kabul et
        status_counts = collections.Counter(self.history)
        most_common_status = status_counts.most_common(1)[0][0]
        
        return most_common_status

    def _get_raw_status(self, qr_list):
        """Kareden anlık hesaplanan ham durumu döndürür."""

        # Kural 1: Eğer 2 kapaktan biri veya ikisi görünmüyorsa kesinlikle AÇIK (veya kameradan çıkmış)
        if len(qr_list) < 2:
            return "ACIK (Eksik QR)"
        
        # Çok fazla QR varsa durumu bilemeyiz
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

        # Benzersiz kabin anahtarı oluştur (isimleri alfabetik sıralayarak)
        sorted_keys = sorted([data1, data2])
        cabinet_key = f"{sorted_keys[0]} | {sorted_keys[1]}"

        # 1. Kural: EĞER BU KABİNİ İLK DEFA GÖRÜYORSA (ÖĞRENME AŞAMASI)
        if cabinet_key not in self.baselines:
            # Şu an kapalı olduğunu varsay ve kaydet
            baseline_data = {
                "distance_ratio": current_distance_ratio,
                data1: {"aspect": aspect1},
                data2: {"aspect": aspect2}
            }
            self._save_baseline(cabinet_key, baseline_data)
            return "KAPALI (Ogrenildi)"

        # 2. Kural: DAHA ÖNCE ÖĞRENİLMİŞ BİR KABİNSE (KONTROL AŞAMASI)
        baseline = self.baselines[cabinet_key]

        # Sürgülü Kapı Kontrolü (Mesafe uzamış mı?)
        base_distance = baseline["distance_ratio"]
        ratio_diff = abs(current_distance_ratio - base_distance) / (base_distance if base_distance > 0 else 1)
        if ratio_diff > Config.DISTANCE_TOLERANCE:
            logger.debug(f"Aralık tespit edildi. Ogrenilen: {base_distance:.2f}, Guncel: {current_distance_ratio:.2f}")
            return "ACIK (Aralanmis)"

        # Menteşeli Kapı Kontrolü (QR kodlar açılı/perspektif bozulmuş mu?)
        diff1 = abs(aspect1 - baseline[data1]["aspect"])
        diff2 = abs(aspect2 - baseline[data2]["aspect"])

        if diff1 > Config.ASPECT_RATIO_TOLERANCE or diff2 > Config.ASPECT_RATIO_TOLERANCE:
            logger.debug(f"Eklemli açılma tespit edildi. Fark1: {diff1:.2f}, Fark2: {diff2:.2f}")
            return "ACIK (Eklemli Acilmis)"

        # Her iki testten de geçtiyse, tam olarak kavuşmuş durumdadırlar.
        return "KAPALI"
