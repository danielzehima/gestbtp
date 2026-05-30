from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.tache import Tache, PrioriteTache, StatutTache

taches_api = Blueprint('taches_api', __name__, url_prefix='/api/taches')


@taches_api.get('/')
@jwt_required()
def liste():
    q = Tache.query
    cid = request.args.get('chantier_id', type=int)
    statut = request.args.get('statut')
    if cid:
        q = q.filter_by(chantier_id=cid)
    if statut:
        q = q.filter_by(statut=StatutTache(statut))
    return jsonify([t.to_dict() for t in q.all()])


@taches_api.post('/')
@jwt_required()
def create():
    d = request.get_json() or {}
    t = Tache(
        chantier_id=d['chantier_id'], titre=d['titre'],
        description=d.get('description'),
        responsable_id=d.get('responsable_id'),
        priorite=PrioriteTache(d.get('priorite', 'moyenne')),
        statut=StatutTache(d.get('statut', 'a_faire')),
        date_limite=datetime.fromisoformat(d['date_limite']).date() if d.get('date_limite') else None,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify(t.to_dict()), 201


@taches_api.put('/<int:id>')
@jwt_required()
def update(id):
    t = Tache.query.get_or_404(id)
    d = request.get_json() or {}
    for f in ('titre', 'description', 'responsable_id', 'chantier_id'):
        if f in d:
            setattr(t, f, d[f])
    if 'priorite' in d:
        t.priorite = PrioriteTache(d['priorite'])
    if 'statut' in d:
        t.statut = StatutTache(d['statut'])
    if 'date_limite' in d:
        t.date_limite = datetime.fromisoformat(d['date_limite']).date() if d['date_limite'] else None
    db.session.commit()
    return jsonify(t.to_dict())


@taches_api.patch('/<int:id>/statut')
@jwt_required()
def change_statut(id):
    t = Tache.query.get_or_404(id)
    d = request.get_json() or {}
    t.statut = StatutTache(d['statut'])
    db.session.commit()
    return jsonify(t.to_dict())


@taches_api.delete('/<int:id>')
@jwt_required()
def delete(id):
    t = Tache.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    return '', 204
