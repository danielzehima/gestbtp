from flask import Blueprint, send_file
from flask_login import login_required
from app.models.rapport import Rapport
from app.models.chantier import Chantier
from app.models.tache import Tache
from app.pdf.generator import rapport_pdf, chantier_pdf, taches_pdf

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/rapport/<int:id>')
@login_required
def rapport(id):
    r = Rapport.query.get_or_404(id)
    buf = rapport_pdf(r)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"rapport_{r.id}.pdf")


@pdf_bp.route('/chantier/<int:id>')
@login_required
def chantier(id):
    c = Chantier.query.get_or_404(id)
    buf = chantier_pdf(c)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"chantier_{c.reference}.pdf")


@pdf_bp.route('/chantier/<int:id>/taches')
@login_required
def taches(id):
    c = Chantier.query.get_or_404(id)
    ts = Tache.query.filter_by(chantier_id=id).all()
    buf = taches_pdf(c, ts)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"taches_{c.reference}.pdf")
