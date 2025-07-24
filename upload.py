import datetime
import os
from drive_client import upload_file, create_date_path, create_camera_path
from record import compress_video


def main():
    source_path = "recs"
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).date()

    for camera in os.listdir(source_path):
        yesterday_sources_path = os.path.join(
            source_path, camera, yesterday.isoformat()
        )
        if not os.path.exists(yesterday_sources_path):
            continue

        camera_remote_folder_id = create_camera_path(camera)
        date_remote_folder_id = create_date_path(camera_remote_folder_id, yesterday)

        for file in os.listdir(yesterday_sources_path):
            file_full_path = os.path.join(yesterday_sources_path, file)
            if not file.endswith(".mp4") or file.endswith("processed.mp4"):
                continue

            compress_file_path = file_full_path.replace(".mp4", "_compressed.mp4")
            thumbnail_path = file_full_path.replace(".mp4", ".jpg")
            processed_path = file_full_path.replace(".mp4", "processed.mp4")

            print(f"Comprimindo {file_full_path}...")
            compress_video(file_full_path, compress_file_path)

            upload_file(compress_file_path, date_remote_folder_id)
            if os.path.exists(thumbnail_path):
                upload_file(thumbnail_path, date_remote_folder_id)

            # Apaga arquivos: original, comprimido, thumbnail e processed
            for f in [
                file_full_path,
                compress_file_path,
                thumbnail_path,
                processed_path,
            ]:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"Arquivo removido: {f}")


if __name__ == "__main__":
    main()
