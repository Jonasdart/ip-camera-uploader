import datetime
import os
import camera_model
from record import base_dir, upload_video, generate_thumbnail


def main():
    for file_to_upload in camera_model.get_upload_queue():
        try:
            generate_thumbnail(file_to_upload["filename"])
        except Exception as err:
            print(err)

        try:
            upload_video(
                file_to_upload["filename"],
                file_to_upload["camera_id"],
                file_to_upload["camera_name"],
                to_compress=file_to_upload.get("to_compress", False),
                to_exclude=file_to_upload.get("to_exclude", True),
                suffix_to_exclude=["_processed_.mp4", "_compressed_.mp4"],
            )
        except Exception as err:
            print(err)
            camera_model.put_upload_queue(**file_to_upload)
        

if __name__ == "__main__":
    main()
