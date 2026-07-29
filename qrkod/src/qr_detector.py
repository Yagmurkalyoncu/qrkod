import cv2
import numpy as np

# pyzbar: ZBar motoru kullanan çok güçlü barkod/QR okuyucu
try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

class QRScanner:
    def __init__(self):
        self.point_history = {}
        self.alpha = 0.25
        
        # WeChat (en güçlü, AI tabanlı)
        self.use_wechat = False
        try:
            self.wechat_detector = cv2.wechat_qrcode_WeChatQRCode()
            self.use_wechat = True
        except:
            pass
        
        # OpenCV standart (yedek)
        self.cv_detector = cv2.QRCodeDetector()

    # Smoothing (nokta geçmişi) mekanizması sistemde tutarsızlığa yol açtığı için tamamen kaldırıldı.

    def _make_variants(self, frame):
        """Farklı ön işleme varyantları oluşturur."""
        variants = [(frame, 1.0)]
        
        # 1. Adaptif Eşikleme (Karanlık/Gölgeli Ortamlar İçin)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        variants.append((cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR), 1.0))
        
        # 2. CLAHE (Lokal Kontrast Artırma)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        variants.append((cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR), 1.0))
        
        return variants

    def detect_and_decode(self, frame):
        """
        Tüm varyant + decoder kombinasyonlarından bulunan QR'ları birleştirir.
        Tek bir deneme ikisini birden bulamasa bile, farklı varyantlarda bulunan
        farklı QR'lar toplanarak eksiksiz sonuç elde edilir.
        """
        variants = self._make_variants(frame)
        merged = {}  # key: (data, kaba_konum) -> qr dict (en güvenilir/en büyük olanı tut)

        decode_fns = []
        if self.use_wechat:
            decode_fns.append(self._decode_wechat)
        if HAS_PYZBAR:
            decode_fns.append(self._decode_pyzbar)
        decode_fns.append(self._decode_opencv)

        for variant_frame, scale in variants:
            for decode_fn in decode_fns:
                qrs = decode_fn(variant_frame, scale)
                for qr in qrs:
                    self._merge_detection(merged, qr)
                # Erken çıkış: zaten 2 farklı QR bulunduysa daha fazla varyant denemeye gerek yok
                if len(merged) >= 2:
                    return list(merged.values())

        return list(merged.values())

    def _merge_detection(self, merged, qr):
        """Aynı QR'ı (aynı data + yakın konum) farklı varyantlarda tekrar tekrar
        eklememek için, konum bazlı birleştirme yapar. Aynı yerdeki tespit
        tekrar gelirse büyüğünü (daha güvenilir olanı) tutar."""
        import math
        cx = np.mean(qr['points'][:, 0])
        cy = np.mean(qr['points'][:, 1])
        w = np.max(qr['points'][:, 0]) - np.min(qr['points'][:, 0])

        for key, existing in merged.items():
            ecx = np.mean(existing['points'][:, 0])
            ecy = np.mean(existing['points'][:, 1])
            ew = np.max(existing['points'][:, 0]) - np.min(existing['points'][:, 0])
            dist = math.hypot(cx - ecx, cy - ecy)
            if dist < max(w, ew) * 0.5:  # aynı fiziksel QR'ın tekrar tespiti
                if w > ew:  # daha büyük/net olan tespiti tercih et
                    merged[key] = qr
                return

        merged[f"{qr['data']}_{int(cx)}_{int(cy)}"] = qr

    def _decode_pyzbar(self, frame, scale):
        """pyzbar (ZBar) ile QR kod okuma - Çok güçlü endüstriyel okuyucu."""
        detected_qrs = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        
        results = pyzbar.decode(gray, symbols=[pyzbar.ZBarSymbol.QRCODE])
        
        for result in results:
            data = result.data.decode('utf-8', errors='ignore')
            if not data:
                continue
            
            # pyzbar polygon noktalarını OpenCV formatına çevir
            # DİKKAT: result.rect kameranın hafif sağa sola yatmasında bounding box'ı bozar.
            # result.polygon ise tam 4 köşeyi verir, açılı duruşlardan etkilenmez!
            polygon = result.polygon
            if len(polygon) == 4:
                pts = np.array([[p.x, p.y] for p in polygon], dtype=float) / scale
            else:
                # Nadiren polygon 4 nokta vermezse fallback olarak rect kullan
                rect = result.rect
                x, y, w, h = rect.left, rect.top, rect.width, rect.height
                pts = np.array([
                    [x, y],
                    [x + w, y],
                    [x + w, y + h],
                    [x, y + h]
                ], dtype=float) / scale
            
            detected_qrs.append({'data': data, 'points': pts.astype(int)})
        
        return detected_qrs

    def _decode_wechat(self, frame, scale):
        """WeChat QR detektörü (AI tabanlı, en güçlü)."""
        if not self.use_wechat:
            return []
        detected_qrs = []
        decoded_info, points = self.wechat_detector.detectAndDecode(frame)
        if len(decoded_info) > 0 and points:
            for i in range(len(decoded_info)):
                data = decoded_info[i] if decoded_info[i] else ""
                if not data:
                    continue
                pts = np.array(points[i], dtype=float) / scale
                detected_qrs.append({'data': data, 'points': pts.astype(int)})
        return detected_qrs

    def _decode_opencv(self, frame, scale):
        """OpenCV standart QR detektörü (en zayıf, yedek)."""
        detected_qrs = []
        success, decoded_info, points, _ = self.cv_detector.detectAndDecodeMulti(frame)
        if success and points is not None:
            for i in range(len(decoded_info)):
                data = decoded_info[i] if decoded_info[i] else ""
                if not data:
                    continue
                pts = points[i].astype(float) / scale
                detected_qrs.append({'data': data, 'points': pts.astype(int)})
        return detected_qrs
