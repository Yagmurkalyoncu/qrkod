import logging
from config import Config

def setup_logger():
    # Endüstriyel standartta bir logger oluşturuyoruz
    logger = logging.getLogger("DoorStatusScanner")
    
    # Log seviyesini config'den al
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Halihazırda handler varsa tekrar eklememek için kontrol et
    if not logger.handlers:
        # Konsola çıktı verecek handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        
        # Log formatı (Tarih - İsim - Seviye - Mesaj)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        logger.addHandler(ch)
        
    return logger

# Kolay erişim için global bir nesne
logger = setup_logger()
