"""Réglages globaux du site (clé/valeur).
Utilisé par exemple pour stocker l'URL de la vidéo de démonstration choisie
par l'administrateur depuis le panneau d'administration.
"""
from datetime import datetime
from app.extensions import db


class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text)
    date_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        row = cls.query.get(key)
        return row.value if row and row.value else default

    @classmethod
    def set(cls, key, value):
        row = cls.query.get(key)
        if row is None:
            row = cls(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
        db.session.commit()
        return row
