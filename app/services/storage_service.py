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
