import logging

def setup_logger():
    logger = logging.getLogger("DoorStatusScanner")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

logger = setup_logger()

class Config:
    CAMERA_SOURCE = 0 
    EXPECTED_BASELINE_RATIO = 1.28
    DISTANCE_TOLERANCE = 0.05 
    ASPECT_RATIO_TOLERANCE = 0.20
    ACTIVE_AUTO_ID = None
    IS_ACTIVE = True

current_config = Config()
