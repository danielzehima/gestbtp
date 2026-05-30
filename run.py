import os
from app import create_app, db
from app.models.user import User, RoleEnum

app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'RoleEnum': RoleEnum}


@app.cli.command('init-db')
def init_db():
    """Crée les tables et un admin par défaut."""
    db.create_all()
    if not User.query.filter_by(email='admin@gestbtp.com').first():
        admin = User(nom='Administrateur', email='admin@gestbtp.com', role=RoleEnum.ADMIN)
        admin.set_password('Admin1234!')
        db.session.add(admin)
        db.session.commit()
        print("Admin créé : admin@gestbtp.com / Admin1234!")
    else:
        print("Admin déjà existant.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
