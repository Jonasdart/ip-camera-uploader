import datetime
import os
import subprocess
import threading
import time
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
from pathlib import Path

import camera_model
from drive_client import create_camera_path, create_date_path, upload_file
from utils import retry

base_dir = "shared/recs"
execution_threads: Dict[str, threading.Thread] = {}


def start_async(
    target: Callable,
    name: str = None,
    args: Iterable[Any] = (),
    kwargs: Mapping[str, Any] | None = None,
) -> threading.Thread:
    _thread = threading.Thread(
        target=target, args=args, kwargs=kwargs, name=name, daemon=True
    )
    _thread.start()

    return _thread


def thread_is_alive(cam_id: int) -> bool:
    is_alive = False
    try:
        is_alive = execution_threads[cam_id].is_alive()
    except KeyError:
        pass

    camera_model.set_status(cam_id, is_alive)
    return is_alive


@retry(0.5)
def upload_video(
    video_path: str,
    camera_id: int,
    camera_name: str,
    to_compress: Optional[bool] = False,
    to_exclude: Optional[bool] = False,
    suffix_to_exclude: Optional[list] = ["_compressed_.mp4"],
):
    if not os.path.exists(video_path):
        print("Video nao encontrado")
        return

    date_path_prefix = list(Path(video_path).parts)[-2]
    camera_remote_folder_id = create_camera_path(camera_id, camera_name)
    date_remote_folder_id = create_date_path(camera_remote_folder_id, date_path_prefix)

    file_to_upload = video_path
    if to_compress:
        print(f"Comprimindo {video_path}...")
        file_to_upload = compress_video(video_path)

    upload_file(file_to_upload, date_remote_folder_id)

    if to_exclude:
        exclude_video_files(video_path, suffix_to_exclude)


def exclude_video_files(video_path: str, files_suffix: Optional[list] = []):
    if video_path.endswith("_.mp4"):
        print("Only originals paths is allowed")
        return

    exclude_list = [video_path]
    exclude_list.extend([video_path.replace(".mp4", suffix) for suffix in files_suffix])
    for f in exclude_list:
        if os.path.exists(f):
            os.remove(f)
            print(f"Arquivo removido: {f}")


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
        "-vf",
        "scale=640:-2",
        "-c:v",
        "mpeg4",
        "-b:v",
        "500k",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        video_path.replace(".mp4", "_processed_.mp4"),
    ]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


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

    output_dir = f"{base_dir}/{camera_model.normalize_name(camera_name)}/{now.date().isoformat()}"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{camera_model.normalize_name(camera_name)}_{now.isoformat(timespec='seconds')}.mp4"
    output_path = os.path.join(output_dir, filename)

    print(f"🎥 Gravando: {filename}")
    print(output_path)

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
        output_path,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    return output_path


def start_monitoring(camera: dict, camera_id: int):
    ip = camera.get("ip")
    user = camera.get("user")
    passw = camera.get("passw")
    name = camera.get("name", ip)
    rtsp = f"rtsp://{user}:{passw}@{ip}/stream"

    filename = start_recording(rtsp, name)
    generate_thumbnail(filename)
    # prepare_video_to_view(filename)

    start_async(
        target=upload_video,
        args=(
            filename,
            camera_id,
            name,
        ),
        kwargs={"to_compress": False, "to_exclude": True},
    )
    time.sleep(0.1)


if __name__ == "__main__":
    try:
        while True:
            for cam in camera_model.list_cameras():
                cam_id = cam.doc_id
                cam_name = camera_model.normalize_name(cam["name"])
                if thread_is_alive(cam_id):
                    continue
                try:
                    print(f"🔌 Conectando à câmera {cam_name} ONVIF em {cam['ip']}...")
                    _thread = start_async(
                        target=start_monitoring,
                        args=(
                            cam,
                            cam_id,
                        ),
                        name=cam_name,
                    )
                    execution_threads[cam.doc_id] = _thread
                except Exception as e:
                    print(f"❌ Erro ao conectar à câmera {cam_name}: {e}")
            time.sleep(0.5)
    finally:
        for cam in camera_model.list_cameras():
            camera_model.set_status(cam.doc_id, False)
