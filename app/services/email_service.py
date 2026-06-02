import json
import urllib.request
import urllib.error
from flask import current_app
from flask_mail import Message
from app.extensions import mail


def _send_via_resend(to, subject, body, html=None):
    """Envoi via l'API HTTP de Resend (fiable sur Vercel/serverless)."""
    api_key = current_app.config.get('RESEND_API_KEY')
    sender = current_app.config.get('RESEND_FROM') or current_app.config['MAIL_DEFAULT_SENDER']
    if not api_key:
        return False
    payload = {
        'from': sender,
        'to': [to],
        'subject': subject,
        'text': body,
    }
    if html:
        payload['html'] = html
    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        current_app.logger.error(f"Resend HTTP {e.code}: {e.read()[:300]}")
        return False
    except Exception as exc:
        current_app.logger.error(f"Resend erreur: {exc}")
        return False


def _send_via_smtp(to, subject, body):
    """Repli SMTP (Flask-Mail) si Resend n'est pas configuré."""
    try:
        msg = Message(subject=subject, recipients=[to], body=body,
                      sender=current_app.config['MAIL_DEFAULT_SENDER'])
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f"Mail SMTP failed: {exc}")
        return False


def send_email(to: str, subject: str, body: str, html: str = None):
    """Envoie un email. Utilise Resend si configuré, sinon repli SMTP."""
    if current_app.config.get('RESEND_API_KEY'):
        return _send_via_resend(to, subject, body, html)
    return _send_via_smtp(to, subject, body)
