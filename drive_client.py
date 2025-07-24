from datetime import date
import os
from typing import Union
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from functools import lru_cache

# Caminho para seu JSON da conta de serviço
CREDENTIALS_FILE = "client_secrets.json"
TOKEN_PATH = "shared/token.json"

# Escopos necessários para Drive
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# ID da pasta no Google Drive onde os arquivos serão enviados
FOLDER_ID = "1uwzZpdiQFCCilR0xEYeRHvTkV8YsMoOR"


@lru_cache()
def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
            
    return build("drive", "v3", credentials=creds)


def __get_or_create_subfolder(parent_folder_id: str, subfolder_name: str) -> str:
    service = authenticate()

    query = f"name = '{subfolder_name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed = false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    folders = response.get('files', [])

    if folders:
        return folders[0]['id']  # Já existe
    else:
        # Criar nova pasta
        metadata = {
            'name': subfolder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(body=metadata, fields='id').execute()
        print(f'Criada pasta: {subfolder_name}')
        return folder['id']
    

def create_camera_path(camera_id: str) -> str:
    return __get_or_create_subfolder(FOLDER_ID, camera_id)


def create_date_path(camera_folder_id: str, record_date: Union[str, date]) -> str:
    if isinstance(record_date, date):
        record_date = record_date.isoformat()
    return __get_or_create_subfolder(camera_folder_id, record_date)


def upload_file(filepath, folder_id):
    service = authenticate()

    filename = os.path.basename(filepath)
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    print(f'Upload concluído: {filename} (ID: {file.get("id")})')
    
    return file.get("id")

