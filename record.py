import datetime
import logging
import os
import signal
import subprocess
import sys
from typing import Optional
from pathlib import Path
from queue import Queue
import argparse

import camera_model
from drive_client import create_camera_path, create_date_path, upload_file

base_dir = "shared/recs"
upload_queue = Queue()
camera = None


def upload_video(
    video_path: str,
    camera_id: int,
    camera_name: str,
    to_compress: Optional[bool] = False,
    to_exclude: Optional[bool] = False,
    suffix_to_exclude: Optional[list] = ["_compressed_.mp4"],
):
    if not os.path.exists(video_path):
        logging.warning("Video nao encontrado")
        return

    camera_remote_folder_id = create_camera_path(camera_name)

    camera_data = camera_model.get_camera_data(camera_id)
    camera_data.set_uri(camera_remote_folder_id)

    file_to_upload = video_path
    if to_compress:
        logging.debug(f"Comprimindo {video_path}...")
        file_to_upload = compress_video(video_path)

    upload_file(file_to_upload, camera_remote_folder_id)

    if to_exclude:
        exclude_video_files(video_path, suffix_to_exclude)


def exclude_video_files(video_path: str, files_suffix: Optional[list] = []):
    if video_path.endswith("_.mp4"):
        logging.warning("Only originals paths is allowed")
        return

    exclude_list = [video_path]
    exclude_list.extend([video_path.replace(".mp4", suffix) for suffix in files_suffix])
    for f in exclude_list:
        if os.path.exists(f):
            os.remove(f)
            logging.debug(f"Arquivo removido: {f}")


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


def start_recording(rtsp_url: str, camera: camera_model.Camera):
    now = datetime.datetime.now()

    output_dir = f"{base_dir}/{camera.normalized_name()}"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{camera.normalized_name()}_{now.strftime('%H:%M')}.mp4"
    output_path = os.path.join(output_dir, filename)

    logging.info(f"🎥 Gravando: {filename}")
    logging.debug(rtsp_url)

    cmd = [
        "ffmpeg",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-t",
        camera.segment_duration,
        "-vcodec",
        "copy",
        "-acodec",
        "aac",
        "-strict",
        "-2",
        "-y",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    return output_path


def start_monitoring(camera: camera_model.Camera):
    rtsp = f"rtsp://{camera.user}:{camera.passw}@{camera.ip}/stream"

    filename = start_recording(rtsp, camera)

    return filename


def start(camera: camera_model.Camera):
    logging.info(
        f"Recording segments for {camera.name} with {camera.segment_duration} of duration"
    )
    filename = start_monitoring(camera)
    upload_queue = camera_model.UploadQueue(filename=filename, camera_id=camera.wid)
    upload_queue.put()


def cleanup_and_exit(signum=None, frame=None):
    if camera:
        try:
            camera.set_status(False)
            logging.info(f"📷 Status da câmera {camera.wid} alterado para False.")
        except Exception as e:
            logging.error(f"Erro ao alterar status da câmera: {e}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    parser = argparse.ArgumentParser(prog="Record Camera", add_help=False)
    parser.add_argument("--camera", help="camera ID", type=int, required=True)
    camera_id = parser.parse_args().camera

    camera = camera_model.get_camera_data(camera_id)

    try:
        camera.set_status(True)
        start(camera)
    except Exception as err:
        logging.error(err)
    finally:
        cleanup_and_exit()
