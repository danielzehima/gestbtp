"""Devis & Factures BTP : chaque entreprise gère ses documents."""
from datetime import date, datetime
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, send_file)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.facturation import (Document, LigneDocument, TypeDocument,
                                    StatutDocument)
from app.models.chantier import Chantier
from app.models.user import RoleEnum
from app.auth.decorators import role_required, client_data_write
from app.utils.plans import abonnement_requis, current_compte_id, get_compte

facturation_bp = Blueprint('facturation', __name__, url_prefix='/facturation')


def _scoped():
    """Documents de l'entreprise courante (admin = tout)."""
    if current_user.role == RoleEnum.ADMIN:
        return Document.query
    cid = current_compte_id(current_user)
    return Document.query.filter_by(compte_id=cid) if cid else Document.query.filter(db.false())


def _get_doc_or_404(id):
    doc = Document.query.get_or_404(id)
    if current_user.role != RoleEnum.ADMIN and doc.compte_id != current_compte_id(current_user):
        abort(404)
    return doc


def _generer_numero(compte_id, type_doc):
    """Numéro auto : DEV-2026-0001 / FAC-2026-0001 (par entreprise et par an)."""
    prefix = 'DEV' if type_doc == TypeDocument.DEVIS else 'FAC'
    annee = date.today().year
    n = Document.query.filter_by(compte_id=compte_id, type=type_doc).filter(
        db.extract('year', Document.date_creation) == annee).count() + 1
    return f"{prefix}-{annee}-{n:04d}"


@facturation_bp.route('/')
@login_required
@abonnement_requis
def liste():
    type_filter = request.args.get('type')
    q = _scoped()
    if type_filter in ('devis', 'facture'):
        q = q.filter_by(type=TypeDocument(type_filter))
    documents = q.order_by(Document.date_creation.desc()).all()
    return render_template('facturation/liste.html', documents=documents, type_filter=type_filter)


def _chantier_choices():
    if current_user.role == RoleEnum.ADMIN:
        chantiers = Chantier.query.all()
    else:
        cid = current_compte_id(current_user)
        chantiers = Chantier.query.filter_by(compte_id=cid).all()
    return [(0, '— Aucun —')] + [(c.id, f"{c.reference} - {c.nom}") for c in chantiers]


@facturation_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@role_required('conducteur')
@client_data_write
def nouveau():
    type_doc = request.args.get('type', 'devis')
    type_doc = type_doc if type_doc in ('devis', 'facture') else 'devis'
    if request.method == 'POST':
        compte = get_or_create()
        doc = Document(
            compte_id=compte.id,
            chantier_id=int(request.form.get('chantier_id') or 0) or None,
            type=TypeDocument(request.form.get('type', 'devis')),
            numero=_generer_numero(compte.id, TypeDocument(request.form.get('type', 'devis'))),
            client_nom=request.form.get('client_nom', '').strip(),
            client_adresse=request.form.get('client_adresse', '').strip(),
            client_email=request.form.get('client_email', '').strip(),
            client_tel=request.form.get('client_tel', '').strip(),
            date_emission=_parse_date(request.form.get('date_emission')) or date.today(),
            date_echeance=_parse_date(request.form.get('date_echeance')),
            tva_taux=request.form.get('tva_taux') or 18,
            notes=request.form.get('notes', '').strip(),
            conditions=request.form.get('conditions', '').strip(),
        )
        db.session.add(doc)
        db.session.flush()
        _save_lignes(doc)
        db.session.commit()
        flash(f"{doc.type.value.capitalize()} {doc.numero} créé.", 'success')
        return redirect(url_for('facturation.detail', id=doc.id))

    return render_template('facturation/form.html', mode='Créer', type_doc=type_doc,
                           chantiers=_chantier_choices(), doc=None)


@facturation_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('conducteur')
@client_data_write
def modifier(id):
    doc = _get_doc_or_404(id)
    if request.method == 'POST':
        doc.chantier_id = int(request.form.get('chantier_id') or 0) or None
        doc.client_nom = request.form.get('client_nom', '').strip()
        doc.client_adresse = request.form.get('client_adresse', '').strip()
        doc.client_email = request.form.get('client_email', '').strip()
        doc.client_tel = request.form.get('client_tel', '').strip()
        doc.date_emission = _parse_date(request.form.get('date_emission')) or doc.date_emission
        doc.date_echeance = _parse_date(request.form.get('date_echeance'))
        doc.tva_taux = request.form.get('tva_taux') or 18
        doc.notes = request.form.get('notes', '').strip()
        doc.conditions = request.form.get('conditions', '').strip()
        # remplacer les lignes
        for l in list(doc.lignes):
            db.session.delete(l)
        db.session.flush()
        _save_lignes(doc)
        db.session.commit()
        flash(f"{doc.type.value.capitalize()} {doc.numero} mis à jour.", 'success')
        return redirect(url_for('facturation.detail', id=doc.id))
    return render_template('facturation/form.html', mode='Modifier', type_doc=doc.type.value,
                           chantiers=_chantier_choices(), doc=doc)


@facturation_bp.route('/<int:id>')
@login_required
def detail(id):
    doc = _get_doc_or_404(id)
    return render_template('facturation/detail.html', doc=doc)


@facturation_bp.route('/<int:id>/statut', methods=['POST'])
@login_required
@role_required('conducteur')
@client_data_write
def changer_statut(id):
    doc = _get_doc_or_404(id)
    nouveau = request.form.get('statut', '')
    try:
        doc.statut = StatutDocument(nouveau)
        db.session.commit()
        flash("Statut mis à jour.", 'success')
    except ValueError:
        flash("Statut invalide.", 'danger')
    return redirect(url_for('facturation.detail', id=doc.id))


@facturation_bp.route('/<int:id>/convertir', methods=['POST'])
@login_required
@role_required('conducteur')
@client_data_write
def convertir(id):
    """Convertit un devis accepté en facture."""
    devis = _get_doc_or_404(id)
    if devis.type != TypeDocument.DEVIS:
        flash("Seul un devis peut être converti en facture.", 'warning')
        return redirect(url_for('facturation.detail', id=devis.id))
    facture = Document(
        compte_id=devis.compte_id, chantier_id=devis.chantier_id,
        type=TypeDocument.FACTURE,
        numero=_generer_numero(devis.compte_id, TypeDocument.FACTURE),
        client_nom=devis.client_nom, client_adresse=devis.client_adresse,
        client_email=devis.client_email, client_tel=devis.client_tel,
        date_emission=date.today(), tva_taux=devis.tva_taux,
        notes=devis.notes, conditions=devis.conditions,
    )
    db.session.add(facture)
    db.session.flush()
    for l in devis.lignes:
        db.session.add(LigneDocument(document_id=facture.id, position=l.position,
                                     designation=l.designation, quantite=l.quantite,
                                     prix_unitaire=l.prix_unitaire, unite=l.unite))
    devis.statut = StatutDocument.ACCEPTE
    db.session.commit()
    flash(f"Devis converti en facture {facture.numero}.", 'success')
    return redirect(url_for('facturation.detail', id=facture.id))


@facturation_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('conducteur')
@client_data_write
def supprimer(id):
    doc = _get_doc_or_404(id)
    db.session.delete(doc)
    db.session.commit()
    flash("Document supprimé.", 'info')
    return redirect(url_for('facturation.liste'))


@facturation_bp.route('/<int:id>/pdf')
@login_required
def pdf(id):
    doc = _get_doc_or_404(id)
    from app.facturation.pdf import document_pdf
    # L'en-tête du PDF utilise TOUJOURS l'identité de l'entreprise propriétaire du document
    buf = document_pdf(doc, doc.compte)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f"{doc.numero}.pdf")


# ----- Helpers -----
def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return None


def get_or_create():
    from app.services.compte_service import get_or_create_compte
    return get_or_create_compte(current_user)


def _save_lignes(doc):
    """Lit les lignes du formulaire (champs répétés) et les enregistre."""
    designations = request.form.getlist('designation[]')
    quantites = request.form.getlist('quantite[]')
    prix = request.form.getlist('prix_unitaire[]')
    unites = request.form.getlist('unite[]')
    pos = 0
    for i, des in enumerate(designations):
        des = (des or '').strip()
        if not des:
            continue
        try:
            qte = float(quantites[i]) if i < len(quantites) and quantites[i] else 0
        except ValueError:
            qte = 0
        try:
            pu = float(prix[i]) if i < len(prix) and prix[i] else 0
        except ValueError:
            pu = 0
        db.session.add(LigneDocument(
            document_id=doc.id, position=pos, designation=des,
            quantite=qte, prix_unitaire=pu,
            unite=(unites[i].strip() if i < len(unites) else '') or None,
        ))
        pos += 1
