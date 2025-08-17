from datetime import datetime, timedelta
import signal
import sys
from time import sleep
from typing import List
import camera_model
import docker
import os
from docker.models.containers import Container
from docker.errors import NotFound
import logging

docker_client = docker.from_env()
local_path = os.path.abspath(".")
logger = logging.basicConfig(level=os.environ.get("LOG_LEVEL", logging.INFO))
use_docker_env = os.environ.get("DOCKER_ENV", "False") == "True"
BASE_CONTAINER_NAME = "ipcam-app"
main_container_name = BASE_CONTAINER_NAME + "-orchestrator"
containers: List[Container] = []


def __get_last_minutes(minutes=1):
    return datetime.now() - timedelta(minutes=minutes)


def __up_base_container(name: str, entrypoint: str) -> Container:
    try:
        container = docker_client.containers.get(name)
        container.remove(force=True)
    except NotFound:
        ...

    volumes = {
        local_path: {"bind": "/app", "mode": "rw"},
        "/etc/timezone": {"bind": "/etc/timezone", "mode": "ro"},
        "/etc/localtime": {"bind": "/etc/localtime", "mode": "ro"},
    }

    container = docker_client.containers.create(
        "ipcam-app",
        command=entrypoint,
        auto_remove=False,
        volumes_from=[main_container_name] if use_docker_env else None,
        volumes=volumes if not use_docker_env else None,
        detach=True,
        environment={"GDRIVE_BASE_FOLDER_ID": os.environ["GDRIVE_BASE_FOLDER_ID"]},
        restart_policy={"Name": "always"},
        name=name,
        labels={"ipcam": "managed"},
    )
    container.start()

    logging.debug(f"Container: {container.id} | {container.name}")
    logging.debug(f"Container status: {container.status}")

    return container


def get_container_logs(container_name: str, minutes_range: int = 1) -> str:
    since = __get_last_minutes(minutes_range)
    container = docker_client.containers.get(container_name)
    logs = container.logs(stream=False, since=since).decode()

    return logs.split("\n")


def start_monitoring(cam_id: int) -> Container:
    name = f"{BASE_CONTAINER_NAME}-monitoring-{cam_id}"
    entrypoint = f"python record.py --camera={cam_id}"

    return __up_base_container(name, entrypoint)


def provisione_uploader() -> Container:
    name = f"{BASE_CONTAINER_NAME}-queue-uploader"
    entrypoint = f"python queue_uploader.py"

    return __up_base_container(name, entrypoint)


def provisione_cleanup() -> Container:
    name = f"{BASE_CONTAINER_NAME}-cleanup"
    entrypoint = f"python cleanup.py"

    return __up_base_container(name, entrypoint)


def cleanup_and_exit(signum=None, frame=None):
    logging.warning("🛑 Recebido sinal de encerramento. Parando containers...")
    for container in containers:
        try:
            container.stop(timeout=5)
            logging.warning(f"Container {container.name} parado.")
        except Exception as e:
            logging.error(f"Erro ao parar container: {e}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    logging.info("Provisioning queue videos uploader")
    containers.append(provisione_uploader())

    logging.info("Starting cameras monitoring")
    cameras_list = camera_model.list_cameras()
    for cam in cameras_list:
        containers.append(start_monitoring(cam.wid))
        logging.info(f"🔁 Camera: {cam.normalized_name()} | IP: {cam.ip} | Started")

    sleep(3600)
