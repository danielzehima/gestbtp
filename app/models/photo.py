from datetime import datetime
from app.extensions import db


class Photo(db.Model):
    __tablename__ = 'photos'

    id = db.Column(db.Integer, primary_key=True)
    chantier_id = db.Column(db.Integer, db.ForeignKey('chantiers.id'), nullable=False)
    chemin_fichier = db.Column(db.String(500), nullable=False)
    nom_fichier = db.Column(db.String(255))
    legende = db.Column(db.String(255))
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', foreign_keys=[uploader_id])

    def to_dict(self):
        return {
            'id': self.id, 'chantier_id': self.chantier_id,
            'chemin_fichier': self.chemin_fichier,
            'nom_fichier': self.nom_fichier, 'legende': self.legende,
            'date_upload': self.date_upload.isoformat() if self.date_upload else None,
        }
