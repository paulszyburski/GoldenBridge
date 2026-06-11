import json
import os

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def export_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        data = json.dump(f)
    return data

