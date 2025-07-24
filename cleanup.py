import os
import time
from datetime import datetime, timedelta
from tinydb import TinyDB

db = TinyDB("db.json")
dir_path = "gravacoes"

for cam in db.all():
    dias = cam["dias"]
    cutoff = time.time() - dias * 86400

    for f in os.listdir(dir_path):
        if f.startswith(cam["nome"]) and f.endswith(".mp4"):
            path = os.path.join(dir_path, f)
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                print(f"Removido: {f}")
