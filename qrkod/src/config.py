import time

class Config:
    CAMERA_SOURCE = 0 
    EXPECTED_BASELINE_RATIO = 1.28
    DISTANCE_TOLERANCE = 0.05 
    ASPECT_RATIO_TOLERANCE = 0.20
    DEPTH_TOLERANCE = 0.08
    ACTIVE_AUTO_ID = None
    IS_ACTIVE = True

current_config = Config()

system_state = {
    "status": "BEKLENİYOR",
    "cabinet_type": "Bilinmiyor",
    "automation_id": "Seçilmedi",
    "qr_count": 0,
    "last_update": time.time()
}
