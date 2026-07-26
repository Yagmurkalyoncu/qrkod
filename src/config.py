class Config:
    # Kamera ayarları
    # 0, 1 gibi tamsayılar webcam'i temsil eder. "video.mp4" gibi stringler video dosyasını temsil eder.
    CAMERA_SOURCE = 0 
    
    # Otonom Çalışma Ayarları (Önceden bilinen kapalı referans oranı)
    # Önceki testlerinizde kalibre olan başarılı oran 1.28 civarıydı.
    EXPECTED_BASELINE_RATIO = 1.28
    
    # Analiz Toleransları
    # Örnek: %15'lik (0.15) bir değişim toleransıdır.
    DISTANCE_TOLERANCE = 0.05 
    
    # QR kodların kendi içindeki çarpılma toleransı (açılı duruş için)
    ASPECT_RATIO_TOLERANCE = 0.20
    
    # Sistem Log seviyesi (INFO, DEBUG, ERROR)
    LOG_LEVEL = "INFO"
    
    # Ekranda gösterilecek metinlerin ayarları
    FONT_SCALE = 0.7
    FONT_THICKNESS = 2
