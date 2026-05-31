"""Panneau d'administration : réglages globaux du site
(vidéo de démonstration, etc.).
"""
import re
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.setting import Setting
from app.auth.decorators import role_required
from app.services.storage_service import upload_file, is_configured, create_signed_upload_url

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Extensions vidéo autorisées (uploadées via Supabase Storage)
VIDEO_EXTS = {'mp4', 'webm', 'mov', 'm4v', 'ogv'}

_YT = re.compile(r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})')
_VM = re.compile(r'vimeo\.com/(?:video/)?(\d+)')


def normalize_video_url(url: str) -> str:
    """Convertit une URL YouTube/Vimeo en URL d'embed lisible dans un iframe.
    Sinon, retourne l'URL telle quelle (cas d'un fichier vidéo .mp4)."""
    if not url:
        return ''
    m = _YT.search(url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    m = _VM.search(url)
    if m:
        return f"https://player.vimeo.com/video/{m.group(1)}"
    return url


def is_iframe_url(url: str) -> bool:
    """True = on l'affiche en <iframe> (YouTube/Vimeo) ; False = <video> (fichier)."""
    if not url:
        return False
    return ('youtube.com' in url) or ('vimeo.com' in url)


@admin_bp.route('/parametres', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def parametres():
    if request.method == 'POST':
        # 1) Cas suppression : on retire la vidéo personnalisée
        if request.form.get('action') == 'reset':
            Setting.set('demo_video_url', '')
            flash("Vidéo de démonstration réinitialisée (valeur par défaut utilisée).", 'info')
            return redirect(url_for('admin.parametres'))

        # 2) Cas fichier uploadé
        f = request.files.get('video_file')
        if f and f.filename:
            ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            if ext not in VIDEO_EXTS:
                flash(f"Format vidéo non supporté ({ext}). Utilisez : {', '.join(sorted(VIDEO_EXTS))}.", 'danger')
                return redirect(url_for('admin.parametres'))
            if not is_configured():
                flash("Supabase Storage n'est pas configuré, impossible d'uploader la vidéo.", 'danger')
                return redirect(url_for('admin.parametres'))
            try:
                public_url = upload_file(f, folder='videos', default_content_type=f.mimetype or 'video/mp4')
                Setting.set('demo_video_url', public_url)
                flash("Vidéo de démonstration mise à jour avec succès.", 'success')
            except Exception as e:
                current_app.logger.error(f"Upload vidéo échoué : {e}")
                flash(f"Échec de l'upload : {e}", 'danger')
            return redirect(url_for('admin.parametres'))

        # 3) Cas URL YouTube/Vimeo
        url = (request.form.get('video_url') or '').strip()
        if url:
            Setting.set('demo_video_url', normalize_video_url(url))
            flash("URL de la vidéo de démonstration enregistrée.", 'success')
            return redirect(url_for('admin.parametres'))

        flash("Aucune vidéo fournie.", 'warning')
        return redirect(url_for('admin.parametres'))

    current_video = Setting.get('demo_video_url') or current_app.config.get('DEMO_VIDEO_URL', '')
    return render_template('admin/parametres.html',
                           current_video=current_video,
                           is_iframe=is_iframe_url(current_video))


@admin_bp.route('/video/sign-upload', methods=['POST'])
@login_required
@role_required('admin')
def sign_upload():
    """Renvoie une URL d'upload signée pour envoyer la vidéo DIRECTEMENT à
    Supabase depuis le navigateur (contourne la limite de taille de Vercel)."""
    if not is_configured():
        return jsonify(ok=False, error="Supabase Storage non configuré"), 400
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', 'video.mp4')
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in VIDEO_EXTS:
        return jsonify(ok=False, error=f"Format non supporté : {ext}"), 400
    try:
        upload_url, public_url = create_signed_upload_url(folder='videos', filename=filename)
        return jsonify(ok=True, upload_url=upload_url, public_url=public_url)
    except Exception as e:
        current_app.logger.error(f"sign-upload échec : {e}")
        return jsonify(ok=False, error=str(e)), 500


@admin_bp.route('/video/save', methods=['POST'])
@login_required
@role_required('admin')
def save_video():
    """Enregistre l'URL publique de la vidéo après upload direct vers Supabase."""
    data = request.get_json(silent=True) or {}
    public_url = (data.get('public_url') or '').strip()
    if not public_url:
        return jsonify(ok=False, error="URL manquante"), 400
    Setting.set('demo_video_url', public_url)
    return jsonify(ok=True)
