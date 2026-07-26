import cv2
import numpy as np
from logger import logger

class QRScanner:
    def __init__(self):
        # OpenCV'nin dahili QR kod tespit edicisini kullanıyoruz.
        self.detector = cv2.QRCodeDetector()

    def detect_and_decode(self, frame):
        """
        Görüntüdeki tüm QR kodları tespit eder ve çözer.
        :param frame: Kameradan alınan görüntü (Bgr veya Grayscale)
        :return: tespit edilen QR kodların listesi.
                 Her eleman: {'data': string, 'points': numpy array (4 köşe)}
        """
        detected_qrs = []
        
        # detectAndDecodeMulti, aynı anda birden fazla QR kodu bulabilir
        success, decoded_info, points, _ = self.detector.detectAndDecodeMulti(frame)
        
        if success and points is not None:
            for i in range(len(decoded_info)):
                # points array'i (N, 4, 2) şeklinde döner
                pts = points[i].astype(int)
                data = decoded_info[i]
                
                detected_qrs.append({
                    'data': data if data else "Bilinmeyen QR",
                    'points': pts
                })
                
        return detected_qrs
