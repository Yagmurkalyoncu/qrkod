import cv2
import sys
import os
import numpy as np

sys.path.append('c:\\Users\\HP\\Desktop\\qr\\src')
from qr_detector import QRScanner

def read_img_unicode(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    return cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)

scanner = QRScanner()
files = ['c:\\Users\\HP\\Desktop\\qr\\sol.png', 'c:\\Users\\HP\\Desktop\\qr\\sağ.png']

for f in files:
    img = read_img_unicode(f)
    if img is None:
        print(f"Error reading {f}")
        continue
    
    qrs = scanner.detect_and_decode(img)
    print(f"File {os.path.basename(f)}: Found {len(qrs)} QR codes.")
    for q in qrs:
        print(f" -> Data: {q['data']}")
