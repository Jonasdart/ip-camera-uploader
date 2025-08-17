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
        print(f"Criada pasta: {subfolder_name}")
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
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    print(f'Upload concluído: {filename} (ID: {file.get("id")})')

    return file.get("id")


def get_video_url(filename, date_path, camera_uri) -> Union[str, None]:
    service = authenticate()

    print(filename, date_path, camera_uri, "To na linha 97 drive_client")
    subfolder_id = create_date_path(camera_uri, date_path)
    query = f"name = '{filename}' and '{subfolder_id}' in parents and trashed = false"

    response = service.files().list(q=query, fields="files(id, name)").execute()
    folders = response.get("files", [])

    if folders:
        return f"https://drive.google.com/file/d/{folders[0]['id']}/view?usp=drive_link"

    return None
