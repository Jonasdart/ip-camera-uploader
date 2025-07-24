import datetime
import os
import subprocess
import threading
import time
from typing import Dict

import camera_model

base_dir = "shared/recs"


def compress_video(input_path: str):
    output_path = input_path.replace(".mp4", "_compressed_.mp4")
    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-vcodec",
        "libx264",
        "-crf",
        "28",
        "-preset",
        "fast",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    return output_path


def prepare_video_to_view(video_path: str):
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        video_path.replace(".mp4", "_processed_.mp4"),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def generate_thumbnail(video_path):
    thumb_path = video_path.replace(".mp4", ".jpg")
    thumb_cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-ss",
        "00:00:01",
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        thumb_path,
    ]
    subprocess.run(thumb_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def start_recording(rtsp_url, camera_name):
    now = datetime.datetime.now()

    output_dir = (
        f"{base_dir}/{camera_model.normalize_name(camera_name)}/{now.date().isoformat()}"
    )
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{camera_model.normalize_name(camera_name)}_{now.isoformat(timespec='seconds')}.mp4"

    print(f"🎥 Gravando: {filename}")
    print(os.path.join(output_dir, filename))

    cmd = [
        "ffmpeg",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-t",
        cam.get("segment_duration", "00:01:00"),
        "-vcodec",
        "copy",
        "-acodec",
        "aac",
        "-strict",
        "-2",
        os.path.join(output_dir, filename),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    return os.path.join(output_dir, filename)


def start_monitoring(camera):
    ip = camera.get("ip")
    user = camera.get("user")
    passw = camera.get("passw")
    name = camera.get("name", ip)
    rtsp = f"rtsp://{user}:{passw}@{ip}/stream"

    try:
        print(f"🔌 Conectando à câmera {name} ONVIF em {ip}...")
        filename = start_recording(rtsp, name)
        generate_thumbnail(filename)
        time.sleep(0.1)
    except Exception as e:
        print(f"❌ Erro ao conectar à câmera {name}: {e}")


if __name__ == "__main__":
    execution_threads: Dict[str, threading.Thread] = {}
    while True:
        for cam in camera_model.list_cameras():
            cam_name = camera_model.normalize_name(cam["name"])
            if cam_name in execution_threads and execution_threads[cam_name].is_alive():
                continue

            _thread = threading.Thread(
                target=start_monitoring, args=(cam,), name=cam_name
            )
            _thread.daemon = True
            _thread.start()
            execution_threads[cam_name] = _thread
        time.sleep(0.1)
