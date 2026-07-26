import cv2
import sys
from config import Config
from logger import logger
from camera import Camera
from qr_detector import QRScanner
from analyzer import DoorStatusAnalyzer

def draw_info(frame, qr_list, status):
    """Ekrana durum bilgisini ve QR bounding box'larını çizer."""
    # Duruma göre renk belirle (BGR)
    if status == "KAPALI":
        color = (0, 255, 0) # Yeşil

    else:
        color = (0, 0, 255) # Kırmızı (AÇIK)

    # Durum metnini sol üst köşeye daha büyük ve arkaplanlı yazdır
    text = f"DURUM: {status}"
    font_scale = Config.FONT_SCALE * 1.5
    thickness = Config.FONT_THICKNESS + 1
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    
    cv2.rectangle(frame, (10, 10), (20 + text_w, 20 + text_h + 10), (0, 0, 0), -1)
    cv2.putText(frame, text, (15, 20 + text_h), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    # QR kodları çiz
    for qr in qr_list:
        pts = qr['points']
        # Çokgeni çizmek için numpy array'in şeklini (N, 1, 2) olarak ayarlamak gerekir
        pts_reshape = pts.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_reshape], isClosed=True, color=(255, 0, 0), thickness=2)
        
        # QR bilgisini kodun üstüne yaz
        x, y = int(pts[0][0]), int(pts[0][1])
        cv2.putText(frame, qr['data'], (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

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
            # Video dosyası okunuyorsa bitmiş olabilir, bu durumda döngüden çık
            break

        # QR Kodları tara
        qr_list = scanner.detect_and_decode(frame)

        # Durumu analiz et
        status = analyzer.analyze(qr_list)

        # Ekrana çizim yap
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
