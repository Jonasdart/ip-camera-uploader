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
main_container_name = "ipcam-app-orchestrator"


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


def start_monitoring(cam_id: int) -> Container:
    name = f"ipcam-app-monitoring-{cam_id}"
    entrypoint = f"python record.py --camera={cam_id}"

    return __up_base_container(name, entrypoint)


def provisione_uploader() -> Container:
    name = f"ipcam-app-queue-uploader"
    entrypoint = f"python queue_uploader.py"

    return __up_base_container(name, entrypoint)


def provisione_cleanup() -> Container:
    name = f"ipcam-app-cleanup"
    entrypoint = f"python cleanup.py"

    return __up_base_container(name, entrypoint)


if __name__ == "__main__":
    containers: List[Container] = []
    logging.info("Provisioning queue videos uploader")
    containers.append(provisione_uploader())

    logging.info("Provisioning local videos cleanup")
    containers.append(provisione_cleanup())

    logging.info("Starting cameras monitoring")

    cameras_list = camera_model.list_cameras()
    for cam in cameras_list:
        containers.append(start_monitoring(cam.wid))
        logging.info(f"🔁 Camera: {cam.normalized_name()} | IP: {cam.ip} | Started")

    sleep(3600)
    for container in containers:
        container.remove(force=True)
