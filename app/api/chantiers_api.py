from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.chantier import Chantier, StatutChantier

chantiers_api = Blueprint('chantiers_api', __name__, url_prefix='/api/chantiers')


def _parse_date(s):
    return datetime.fromisoformat(s).date() if s else None


@chantiers_api.get('/')
@jwt_required()
def liste():
    return jsonify([c.to_dict() for c in Chantier.query.all()])


@chantiers_api.get('/<int:id>')
@jwt_required()
def detail(id):
    return jsonify(Chantier.query.get_or_404(id).to_dict())


@chantiers_api.post('/')
@jwt_required()
def create():
    d = request.get_json() or {}
    ch = Chantier(
        nom=d['nom'], reference=d['reference'], adresse=d.get('adresse'),
        client_id=d.get('client_id'), responsable_id=d.get('responsable_id'),
        budget=d.get('budget', 0),
        statut=StatutChantier(d.get('statut', 'preparation')),
        date_debut=_parse_date(d.get('date_debut')),
        date_fin_prev=_parse_date(d.get('date_fin_prev')),
        description=d.get('description'),
    )
    db.session.add(ch)
    db.session.commit()
    return jsonify(ch.to_dict()), 201


@chantiers_api.put('/<int:id>')
@jwt_required()
def update(id):
    ch = Chantier.query.get_or_404(id)
    d = request.get_json() or {}
    for f in ('nom', 'reference', 'adresse', 'description',
              'client_id', 'responsable_id', 'budget'):
        if f in d:
            setattr(ch, f, d[f])
    if 'statut' in d:
        ch.statut = StatutChantier(d['statut'])
    if 'date_debut' in d:
        ch.date_debut = _parse_date(d['date_debut'])
    if 'date_fin_prev' in d:
        ch.date_fin_prev = _parse_date(d['date_fin_prev'])
    db.session.commit()
    return jsonify(ch.to_dict())


@chantiers_api.delete('/<int:id>')
@jwt_required()
def delete(id):
    ch = Chantier.query.get_or_404(id)
    db.session.delete(ch)
    db.session.commit()
    return '', 204
