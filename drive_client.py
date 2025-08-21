import logging
import os
from datetime import date
from functools import lru_cache
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from typing import Union

from utils import retry

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Caminho para seu JSON da conta de serviço
CREDENTIALS_FILE = "shared/client_secrets.json"
TOKEN_PATH = "shared/token.json"

# Escopos necessários para Drive
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# ID da pasta no Google Drive onde os arquivos serão enviados
FOLDER_ID = os.environ["GDRIVE_BASE_FOLDER_ID"]


@lru_cache()
def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                return build("drive", "v3", credentials=creds)
            except RefreshError:
                pass
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def __get_or_create_subfolder(parent_folder_id: str, subfolder_name: str) -> str:
    service = authenticate()

    query = f"name = '{subfolder_name.strip()}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    folders = response.get("files", [])

    if folders:
        return folders[0]["id"]
    else:
        # Criar nova pasta
        metadata = {
            "name": subfolder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        logging.debug(f"Criada pasta: {subfolder_name}")
        return folder["id"]


@lru_cache(128)
def create_camera_path(camera_name) -> str:
    camera_uri = __get_or_create_subfolder(FOLDER_ID, camera_name)
    return camera_uri


@lru_cache(128)
def create_date_path(camera_uri: str, record_date: Union[str, date]) -> str:
    if isinstance(record_date, date):
        record_date = record_date.isoformat()
    return __get_or_create_subfolder(camera_uri, record_date)


def upload_file(filepath, folder_id):
    service = authenticate()

    filename = os.path.split(filepath)[-1]
    media = MediaFileUpload(filepath, resumable=True)

    # Verifica se já existe arquivo com mesmo nome na pasta
    query = f"'{folder_id}' in parents and name = '{filename}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])

    if items:
        # Se já existe, pega o primeiro e faz update (overwrite)
        file_id = items[0]["id"]
        updated_file = (
            service.files()
            .update(fileId=file_id, media_body=media)
            .execute()
        )
        logging.debug(f"Arquivo atualizado: {filename} (ID: {updated_file.get('id')})")
        return updated_file.get("id")
    else:
        # Se não existe, cria novo
        file_metadata = {"name": filename, "parents": [folder_id]}
        new_file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        logging.debug(f"Upload concluído: {filename} (ID: {new_file.get('id')})")
        return new_file.get("id")


def get_video_url(filename, camera_uri) -> Union[str, None]:
    service = authenticate()

    query = f"name = '{filename}' and '{camera_uri}' in parents and trashed = false"

    response = service.files().list(q=query, fields="files(id, name)").execute()
    folders = response.get("files", [])

    if folders:
        return f"https://drive.google.com/file/d/{folders[0]['id']}/view?usp=drive_link"

    return None
