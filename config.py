import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "cookies.json")

DEFAULT_CONFIG = {
    "target_url": "https://hseconomicsbd.com",
    "domain": "hseconomicsbd.com",
    "cookies": {
        "hseastudentId": "1035",
        "hseastudentToken": "9155c8fca455c876a3266861b5da1d96",
        "PHPSESSID": "7q5m2juk8qmd1ci0ai046v1slg"
    },
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "browser_type": "edge",  # options: 'edge', 'chrome', 'playwright'
    "admin_password": "admin"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(new_config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=4)
