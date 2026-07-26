import cv2
from logger import logger

class Camera:
    def __init__(self, source):
        """
        Kamera nesnesini başlatır.
        :param source: 0, 1 gibi webcam ID'si veya "video.mp4" gibi dosya yolu
        """
        self.source = source
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            logger.error(f"Kamera/Video kaynağı açılamadı: {self.source}")
            raise ValueError(f"Kaynak açılamadı: {self.source}")
        
        logger.info(f"Görüntü kaynağı başarıyla başlatıldı: {self.source}")

    def read_frame(self):
        """
        Kameradan tek bir kare (frame) okur.
        :return: success (bool), frame (numpy array)
        """
        success, frame = self.cap.read()
        if not success:
            logger.warning("Görüntü karesi alınamadı veya video bitti.")
        return success, frame

    def release(self):
        """Kamera kaynağını serbest bırakır."""
        if self.cap:
            self.cap.release()
            logger.info("Kamera bağlantısı kapatıldı.")
