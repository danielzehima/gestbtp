"""Stockage des photos dans Supabase Storage (bucket public).

On utilise l'API REST Storage de Supabase avec la clé service_role
(uploads côté serveur, qui contourne les limites de fichiers de l'hébergeur
et conserve les photos de façon permanente).
"""
import uuid
import urllib.request
import urllib.error
from werkzeug.utils import secure_filename
from flask import current_app


def _cfg():
    return (
        current_app.config['SUPABASE_URL'].rstrip('/'),
        current_app.config['SUPABASE_SERVICE_KEY'],
        current_app.config['SUPABASE_BUCKET'],
    )


def is_configured():
    base, key, bucket = _cfg()
    return bool(base and key and bucket)


def _headers(key, content_type=None, upsert=False):
    h = {'Authorization': f'Bearer {key}', 'apikey': key}
    if content_type:
        h['Content-Type'] = content_type
    if upsert:
        h['x-upsert'] = 'true'
    return h


def upload_file(file_storage, folder='videos', default_content_type='application/octet-stream'):
    """Variante générique pour tout type de fichier (vidéo, doc, etc.).
    Retourne l'URL publique. Lève RuntimeError en cas d'échec."""
    base, key, bucket = _cfg()
    if not (base and key):
        raise RuntimeError("Supabase Storage non configuré (SUPABASE_URL / SUPABASE_SERVICE_KEY manquants).")

    safe = secure_filename(file_storage.filename or 'file')
    ext = safe.rsplit('.', 1)[1].lower() if '.' in safe else ''
    name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    path = f"{folder}/{name}"

    data = file_storage.read()
    content_type = file_storage.mimetype or default_content_type
    url = f"{base}/storage/v1/object/{bucket}/{path}"
    req = urllib.request.Request(url, data=data, method='POST',
                                 headers=_headers(key, content_type, upsert=True))
    try:
        urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Upload Supabase échoué ({e.code}): {e.read()[:200]}")
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def create_signed_upload_url(folder='videos', filename='file'):
    """Crée une URL d'upload SIGNÉE pour que le navigateur envoie le fichier
    DIRECTEMENT à Supabase (sans passer par le serveur, donc sans la limite
    de taille de l'hébergeur). Retourne (upload_url, public_url)."""
    import json as _json
    base, key, bucket = _cfg()
    if not (base and key):
        raise RuntimeError("Supabase Storage non configuré.")
    safe = secure_filename(filename or 'file')
    ext = safe.rsplit('.', 1)[1].lower() if '.' in safe else 'mp4'
    path = f"{folder}/{uuid.uuid4().hex}.{ext}"

    url = f"{base}/storage/v1/object/upload/sign/{bucket}/{path}"
    req = urllib.request.Request(url, data=b'{}', method='POST',
                                 headers=_headers(key, 'application/json'))
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = _json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Signature upload Supabase échouée ({e.code}): {e.read()[:200]}")

    signed_path = body.get('url')  # ex: /object/upload/sign/photos/videos/xxx.mp4?token=...
    upload_url = f"{base}/storage/v1{signed_path}"
    public_url = f"{base}/storage/v1/object/public/{bucket}/{path}"
    return upload_url, public_url


def upload_photo(file_storage, folder='chantiers'):
    """Envoie un fichier vers Supabase Storage. Retourne l'URL publique."""
    base, key, bucket = _cfg()
    if not (base and key):
        raise RuntimeError("Supabase Storage non configuré (SUPABASE_URL / SUPABASE_SERVICE_KEY manquants).")

    safe = secure_filename(file_storage.filename or 'photo')
    ext = safe.rsplit('.', 1)[1].lower() if '.' in safe else 'jpg'
    path = f"{folder}/{uuid.uuid4().hex}.{ext}"

    data = file_storage.read()
    content_type = file_storage.mimetype or 'image/jpeg'

    url = f"{base}/storage/v1/object/{bucket}/{path}"
    req = urllib.request.Request(url, data=data, method='POST',
                                 headers=_headers(key, content_type, upsert=True))
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Upload Supabase échoué ({e.code}): {e.read()[:200]}")

    # URL publique (bucket public)
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def delete_photo(public_url):
    """Supprime un objet à partir de son URL publique. Silencieux en cas d'échec."""
    base, key, bucket = _cfg()
    marker = f"/object/public/{bucket}/"
    if not public_url or marker not in public_url:
        return
    path = public_url.split(marker, 1)[1]
    url = f"{base}/storage/v1/object/{bucket}/{path}"
    req = urllib.request.Request(url, method='DELETE', headers=_headers(key))
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass
