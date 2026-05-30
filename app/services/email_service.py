from flask import current_app
from flask_mail import Message
from app.extensions import mail


def send_email(to: str, subject: str, body: str):
    try:
        msg = Message(subject=subject, recipients=[to], body=body,
                      sender=current_app.config['MAIL_DEFAULT_SENDER'])
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f"Mail failed: {exc}")
        return False
