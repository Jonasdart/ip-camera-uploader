import sqlite3
from typing import List, Optional
import drive_client
from pydantic import BaseModel

DB_PATH = "shared/db.sqlite3"


class UploadQueue(BaseModel):
    wid: Optional[int] = None
    filename: str
    camera_id: int
    to_compress: bool = False
    to_exclude: bool = True

    def put(self):
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO upload_queue (filename, camera_id, to_compress, to_exclude)
                VALUES (?, ?, ?, ?)
            """,
                (
                    self.filename,
                    self.camera_id,
                    self.to_compress,
                    self.to_exclude,
                ),
            )
            
    def acknowledge(self):
        if not self.wid:
            raise sqlite3.IntegrityError("Set Object ID Before.")

        with get_connection() as conn:
            conn.execute("DELETE FROM upload_queue where id=?", (self.wid,))



def get_upload_queue(ack: bool = True) -> List[UploadQueue]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM upload_queue")
        rows = [UploadQueue(wid=row["id"], **row) for row in cursor.fetchall()]
        if ack:
            cursor.execute("DELETE FROM upload_queue")

        return rows


class Camera(BaseModel):
    wid: Optional[int] = None
    name: str
    ip: str
    user: str
    passw: str
    segment_duration: str = "00:00:30"
    date_range: int
    uri: Optional[str] = None
    recording: bool = False

    def normalized_name(self):
        return self.name.replace(" ", "_").lower()

    def save(self):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cameras (name, ip, user, passw, segment_duration, date_range)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    self.name,
                    self.ip,
                    self.user,
                    self.passw,
                    self.segment_duration,
                    self.date_range,
                ),
            )
            self.wid = cursor.lastrowid
            camera_uri = drive_client.create_camera_path(self.name)
            self.set_uri(camera_uri, cursor=cursor)

    def edit(self):
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE cameras
                SET name=?, ip=?, user=?, passw=?, segment_duration=?, date_range=?
                WHERE id=?
            """,
                (
                    self.name,
                    self.ip,
                    self.user,
                    self.passw,
                    self.segment_duration,
                    self.date_range,
                    self.wid,
                ),
            )

    def set_uri(self, uri: str, cursor: Optional[sqlite3.Cursor] = None):
        query = "UPDATE cameras SET uri=? WHERE id=?"

        if cursor is not None:
            cursor.execute(
                query,
                (uri, self.wid),
            )
        else:
            with get_connection() as conn:
                conn.execute(
                    query,
                    (uri, self.wid),
                )

        self.uri = uri

    def set_status(self, status: bool):
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE cameras SET recording=? WHERE id=?
            """,
                (1 if status else 0, self.wid),
            )


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_camera_data(camera_id: int) -> Camera:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM cameras WHERE id=?", (camera_id,))
        row = cursor.fetchone()
        return Camera(wid=row["id"], **row) if row else None


def list_cameras() -> List[Camera]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM cameras")
        return [Camera(wid=row["id"], **row) for row in cursor.fetchall()]


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ip TEXT,
            user TEXT,
            passw TEXT,
            segment_duration TEXT,
            date_range INTEGER,
            uri TEXT,
            recording BOOLEAN DEFAULT 0
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS upload_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            camera_id INTEGER,
            to_compress BOOLEAN DEFAULT 0,
            to_exclude BOOLEAN DEFAULT 1
        )
        """
        )

        conn.commit()


init_db()
