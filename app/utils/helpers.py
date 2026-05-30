import os
import uuid
from werkzeug.utils import secure_filename


def allowed_file(filename: str, extensions: set) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


def unique_filename(filename: str) -> str:
    safe = secure_filename(filename)
    ext = safe.rsplit('.', 1)[1].lower() if '.' in safe else ''
    return f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex


def save_upload(file_storage, folder: str) -> tuple:
    os.makedirs(folder, exist_ok=True)
    fname = unique_filename(file_storage.filename)
    path = os.path.join(folder, fname)
    file_storage.save(path)
    return fname, path
