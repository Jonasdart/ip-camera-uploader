from typing import List
from tinydb import TinyDB, Query

import drive_client

db = TinyDB("shared/db.json")


def normalize_name(name: str):
    return name.replace(" ", "_").lower()


def add_camera(
    name: str, ip: str, user: str, passw: str, segment_duration: str, date_range: int
):
    camera_collection = db.table("cameras")
    camera_id = camera_collection.insert(
        {
            "name": name,
            "ip": ip,
            "user": user,
            "passw": passw,
            "segment_duration": segment_duration,
            "date_range": date_range,
        }
    )
    camera_uri = drive_client.create_camera_path(camera_id, name)
    update_camera_uri(camera_id, camera_uri)


def edit_camera(
    camera_id: int,
    name: str,
    ip: str,
    user: str,
    passw: str,
    segment_duration: str,
    date_range: int,
):
    camera_collection = db.table("cameras")
    camera_collection.update(
        {
            "name": name,
            "ip": ip,
            "user": user,
            "passw": passw,
            "segment_duration": segment_duration,
            "date_range": date_range,
        },
        doc_ids=[camera_id],
    )


def update_camera_uri(camera_id: int, uri: str):
    camera_collection = db.table("cameras")
    camera_collection.update({"uri": uri}, doc_ids=[camera_id])


def list_cameras() -> List[dict]:
    camera_collection = db.table("cameras")
    return camera_collection.all()


def get_camera_data(camera_id: int) -> dict:
    camera_collection = db.table("cameras")
    return camera_collection.get(doc_id=camera_id)


def set_status(camera_id: int, status: bool):
    camera_collection = db.table("cameras")
    camera_collection.update({"recording": status}, doc_ids=[camera_id])
