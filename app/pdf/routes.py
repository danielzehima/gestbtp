from flask import Blueprint, send_file, abort
from flask_login import login_required, current_user
from app.models.rapport import Rapport
from app.models.chantier import Chantier
from app.models.tache import Tache
from app.models.compte import Compte
from app.models.user import RoleEnum
from app.pdf.generator import rapport_pdf, chantier_pdf, taches_pdf
from app.utils.plans import require_feature, current_compte_id

pdf_bp = Blueprint('pdf', __name__)


def _entreprise_du_chantier(chantier):
    """Compte (entreprise) propriétaire du chantier, pour l'en-tête du PDF."""
    if chantier and chantier.compte_id:
        return Compte.query.get(chantier.compte_id)
    return None


def _check_acces_chantier(chantier):
    """Vérifie que le chantier appartient à l'entreprise (admin = tout)."""
    if current_user.role != RoleEnum.ADMIN:
        if chantier.compte_id != current_compte_id(current_user):
            abort(404)


@pdf_bp.route('/rapport/<int:id>')
@login_required
@require_feature('export_pdf')
def rapport(id):
    r = Rapport.query.get_or_404(id)
    _check_acces_chantier(r.chantier)
    buf = rapport_pdf(r, _entreprise_du_chantier(r.chantier))
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"rapport_{r.id}.pdf")


@pdf_bp.route('/chantier/<int:id>')
@login_required
@require_feature('export_pdf')
def chantier(id):
    c = Chantier.query.get_or_404(id)
    _check_acces_chantier(c)
    buf = chantier_pdf(c, _entreprise_du_chantier(c))
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"chantier_{c.reference}.pdf")


@pdf_bp.route('/chantier/<int:id>/taches')
@login_required
@require_feature('export_pdf')
def taches(id):
    c = Chantier.query.get_or_404(id)
    _check_acces_chantier(c)
    ts = Tache.query.filter_by(chantier_id=id).all()
    buf = taches_pdf(c, ts, _entreprise_du_chantier(c))
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"taches_{c.reference}.pdf")
