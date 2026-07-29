import os
import json

db_path = os.path.join(os.path.dirname(__file__), 'automations_db.json')

def load_db():
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Geriye dönük uyumluluk: Eski kayıtlara X ve Y ekle
            for k, v in data.items():
                if "x" not in v.get("fiziksel_parametreler", {}).get("qr_koordinatlari", {}):
                    v["fiziksel_parametreler"]["qr_koordinatlari"]["x"] = 0.0
                    v["fiziksel_parametreler"]["qr_koordinatlari"]["y"] = 0.0
            return data
    return {}

def save_db(data):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

automations_db = load_db()
