import cv2
import numpy as np

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
