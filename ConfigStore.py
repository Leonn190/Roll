import json
import os

CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "FPS": 180,
    "Volume": 50,
    "Luminosidade": 75,
}


def load_config():
    config = dict(DEFAULT_CONFIG)
    if not os.path.exists(CONFIG_PATH):
        save_config(config)
        return config

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            config.update(raw)
    except Exception:
        pass

    return config


def save_config(config):
    data = {
        "FPS": int(config.get("FPS", DEFAULT_CONFIG["FPS"])),
        "Volume": int(config.get("Volume", DEFAULT_CONFIG["Volume"])),
        "Luminosidade": int(config.get("Luminosidade", DEFAULT_CONFIG["Luminosidade"])),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
