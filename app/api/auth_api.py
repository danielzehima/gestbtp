from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User, RoleEnum

auth_api = Blueprint('auth_api', __name__, url_prefix='/api/auth')


@auth_api.post('/register')
def register():
    data = request.get_json() or {}
    if User.query.filter_by(email=data.get('email', '').lower()).first():
        return jsonify(error="Email déjà utilisé"), 400
    user = User(
        nom=data.get('nom'), email=data['email'].lower(),
        telephone=data.get('telephone'),
        role=RoleEnum(data.get('role', 'client')),
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@auth_api.post('/login')
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=data.get('email', '').lower()).first()
    if not user or not user.check_password(data.get('password', '')) or not user.actif:
        return jsonify(error="Identifiants invalides"), 401
    token = create_access_token(identity=str(user.id),
                                additional_claims={'role': user.role.value})
    return jsonify(access_token=token, user=user.to_dict())


@auth_api.get('/me')
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    return jsonify(user=user.to_dict())
