from app.extensions import db
from app.models.notification import Notification


def notify_user(user_id: int, message: str, tache_id: int = None):
    notif = Notification(user_id=user_id, message=message, tache_id=tache_id)
    db.session.add(notif)
    db.session.commit()
    return notif
