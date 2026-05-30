from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tache_id = db.Column(db.Integer, db.ForeignKey('taches.id'))
    message = db.Column(db.String(500), nullable=False)
    lue = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'message': self.message, 'lue': self.lue,
            'date_creation': self.date_creation.isoformat(),
        }
