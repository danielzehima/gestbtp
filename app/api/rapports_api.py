from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.rapport import Rapport

rapports_api = Blueprint('rapports_api', __name__, url_prefix='/api/rapports')


@rapports_api.get('/')
@jwt_required()
def liste():
    q = Rapport.query
    cid = request.args.get('chantier_id', type=int)
    if cid:
        q = q.filter_by(chantier_id=cid)
    return jsonify([r.to_dict() for r in q.order_by(Rapport.date.desc()).all()])


@rapports_api.get('/<int:id>')
@jwt_required()
def detail(id):
    return jsonify(Rapport.query.get_or_404(id).to_dict())


@rapports_api.post('/')
@jwt_required()
def create():
    d = request.get_json() or {}
    r = Rapport(
        chantier_id=d['chantier_id'],
        auteur_id=int(get_jwt_identity()),
        date=datetime.fromisoformat(d['date']).date() if d.get('date') else None,
        meteo=d.get('meteo'),
        travaux_realises=d.get('travaux_realises'),
        difficultes=d.get('difficultes'),
        main_oeuvre=d.get('main_oeuvre'),
        observations=d.get('observations'),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@rapports_api.delete('/<int:id>')
@jwt_required()
def delete(id):
    r = Rapport.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    return '', 204
