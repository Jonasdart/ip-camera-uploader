import datetime
import os
import subprocess
import time
from typing import Optional
from pathlib import Path
from queue import Queue
import argparse

import camera_model
from drive_client import create_camera_path, create_date_path, upload_file

base_dir = "shared/recs"
upload_queue = Queue()


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


def upload_video_from_queue():
    while True:
        item = upload_queue.get()
        if item is None:
            break

        (
            video_path,
            camera_id,
            camera_name,
            to_compress,
            to_exclude,
        ) = item

        if not os.path.exists(video_path):
            upload_queue.task_done()
            continue

        date_path_prefix = list(Path(video_path).parts)[-2]
        camera_remote_folder_id = create_camera_path(camera_id, camera_name)
        date_remote_folder_id = create_date_path(
            camera_remote_folder_id, date_path_prefix
        )

        file_to_upload = video_path
        if to_compress:
            print(f"Comprimindo {video_path}...")
            file_to_upload = compress_video(video_path)

        upload_file(file_to_upload, date_remote_folder_id)
        generate_thumbnail(video_path)

        if to_exclude:
            exclude_video_files(video_path, ["_compressed_.mp4"])

        upload_queue.task_done()
        time.sleep(0.1)


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
        "-y",
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


def start_recording(rtsp_url, camera_name, segment_duration="00:01:00"):
    now = datetime.datetime.now()

    output_dir = f"{base_dir}/{camera_model.normalize_name(camera_name)}/{now.date().isoformat()}"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{camera_model.normalize_name(camera_name)}_{now.isoformat(timespec='seconds')}.mp4"
    output_path = os.path.join(output_dir, filename)

    print(f"🎥 Gravando: {filename}")
    print(rtsp_url)

    cmd = [
        "ffmpeg",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-t",
        segment_duration,
        "-vcodec",
        "copy",
        "-acodec",
        "aac",
        "-strict",
        "-2",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    return output_path


def start_monitoring(camera: dict):
    ip = camera.get("ip")
    user = camera.get("user")
    passw = camera.get("passw")
    name = camera.get("name", ip)
    rtsp = f"rtsp://{user}:{passw}@{ip}/stream"

    filename = start_recording(rtsp, name, camera.get("segment_duration", "00:01:00"))

    return filename


def on_monitoring_done(filename: str, camera_id: int, camera_name: str):
    camera_model.put_upload_queue(
        filename=filename,
        camera_id=camera_id,
        camera_name=camera_name,
        to_compress=False,
        to_exclude=True,
    )


def start(camera_id: int):
    camera_data = camera_model.get_camera_data(camera_id)
    if camera_data is None:
        return

    filename = start_monitoring(camera_data)
    on_monitoring_done(filename, camera_id, camera_data["name"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Record Camera", add_help=False)
    parser.add_argument("--camera", help="camera ID", type=int, required=True)
    camera = parser.parse_args().camera

    try:
        camera_model.set_status(camera_id=camera, status=True)
        start(camera)
    except Exception as err:
        print(err)

    camera_model.set_status(camera_id=camera, status=False)
    exit()
