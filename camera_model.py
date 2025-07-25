from typing import List
from tinydb import TinyDB, Query

import drive_client

db = TinyDB("shared/db.json")


def normalize_name(name: str):
    return name.replace(" ", "_").lower()


def add_camera(name: str, ip: str, user: str, passw: str, segment_duration: str, date_range: int):
    camera_folder_id = drive_client.create_camera_path(name)
    camera_collection = db.table("cameras")
    camera_collection.insert(
        {
            "name": name,
            "ip": ip,
            "user": user,
            "passw": passw,
            "segment_duration": segment_duration,
            "date_range": date_range,
            "camera_folder_id": camera_folder_id
        }
    )
    

def list_cameras() -> List[dict]:
    camera_collection = db.table("cameras")
    return camera_collection.all()


def get_camera_data(camera_id: int) -> dict:
    camera_collection = db.table("cameras")
    return camera_collection.get(doc_id=camera_id)    
