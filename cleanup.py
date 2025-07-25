import datetime
import os
from camera_model import list_cameras, normalize_name
from record import base_dir, upload_video


def main():
    today = datetime.date.today()

    for camera in list_cameras():
        oldest_sources = os.path.join(base_dir, normalize_name(camera["name"]))
        print(oldest_sources)
        oldest_sources = [
            os.path.join(oldest_sources, day)
            for day in os.listdir(oldest_sources)
            if not day == today.isoformat()
        ]

        for day_path in oldest_sources:
            if not os.path.exists(day_path):
                print(f"Nenhuma gravação para limpar no dia {today.isoformat()}")
                continue

            for file in os.listdir(day_path):
                file_full_path = os.path.join(day_path, file)
                print(f"Verificando arquivo {file_full_path}")
                if file.endswith("_.mp4") or file.endswith(".jpg"):
                    if os.path.exists(file_full_path):
                        os.remove(file_full_path)
                    continue

                upload_video(
                    file_full_path,
                    camera["name"],
                    to_exclude=True,
                    suffix_to_exclude=["_processed_.mp4", "_compressed_.mp4", ".jpg"],
                )


if __name__ == "__main__":
    main()
