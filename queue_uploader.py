import camera_model
from record import upload_video, generate_thumbnail


def main():
    for file_to_upload in camera_model.get_upload_queue():
        try:
            generate_thumbnail(file_to_upload.filename)
        except Exception as err:
            print(err)
            
        camera_data = camera_model.get_camera_data(file_to_upload.camera_id)

        try:
            upload_video(
                file_to_upload.filename,
                file_to_upload.camera_id,
                camera_data.name,
                to_compress=file_to_upload.to_compress,
                to_exclude=file_to_upload.to_exclude,
                suffix_to_exclude=["_processed_.mp4", "_compressed_.mp4"],
            )
        except Exception as err:
            print(err)
            file_to_upload.put()
        

if __name__ == "__main__":
    main()
