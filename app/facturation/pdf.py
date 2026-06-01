"""Génération PDF des devis et factures BTP (ReportLab)."""
import urllib.request
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image)

PRIMARY = colors.HexColor('#FF6B00')
DARK = colors.HexColor('#111111')


def _fetch_logo(url):
    """Télécharge le logo de l'entreprise pour l'intégrer au PDF. None si échec."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            return BytesIO(r.read())
    except Exception:
        return None


def _fmt(n):
    """Formate un montant : 1 234 567 FCFA."""
    return f"{float(n or 0):,.0f}".replace(',', ' ') + " FCFA"


def document_pdf(doc, entreprise):
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('Small', fontName='Helvetica', fontSize=9, textColor=colors.grey))
    s.add(ParagraphStyle('Right', fontName='Helvetica', fontSize=10, alignment=2))
    story = []

    titre = "DEVIS" if doc.type.value == 'devis' else "FACTURE"

    # En-tête : identité de l'entreprise (logo + coordonnées) à gauche,
    # titre + numéro à droite.
    ent_nom = (getattr(entreprise, 'raison_sociale', None) or
               (entreprise.nom if entreprise else "Entreprise"))
    coord = []
    if entreprise:
        if entreprise.adresse:
            coord.append(entreprise.adresse)
        ligne2 = ' · '.join(filter(None, [entreprise.telephone, entreprise.email]))
        if ligne2:
            coord.append(ligne2)
        if entreprise.site_web:
            coord.append(entreprise.site_web)
    coord_html = '<br/>'.join(coord)

    # Bloc texte entreprise
    ent_par = Paragraph(
        f"<b><font size=14>{ent_nom}</font></b>" +
        (f"<br/><font size=8 color='grey'>{coord_html}</font>" if coord_html else ""),
        s['Normal'])

    # Logo (si dispo) au-dessus / à gauche du nom
    logo_buf = _fetch_logo(getattr(entreprise, 'logo_url', None))
    if logo_buf:
        try:
            img = Image(logo_buf, width=3*cm, height=2*cm, kind='proportional')
            left_cell = [img, Spacer(1, 0.2*cm), ent_par]
        except Exception:
            left_cell = ent_par
    else:
        left_cell = ent_par

    head = [[
        left_cell,
        Paragraph(f"<b><font size=22 color='#FF6B00'>{titre}</font></b><br/>"
                  f"<font size=11>N° {doc.numero}</font>", s['Right']),
    ]]
    t = Table(head, colWidths=[10*cm, 6*cm])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t)
    story.append(Spacer(1, 0.6*cm))

    # Bloc client + dates
    infos = [
        [Paragraph("<b>Client</b>", s['Normal']),
         Paragraph(f"<b>Date d'émission :</b> {doc.date_emission.strftime('%d/%m/%Y') if doc.date_emission else '—'}", s['Normal'])],
        [Paragraph(doc.client_nom or '—', s['Normal']),
         Paragraph(f"<b>Échéance :</b> {doc.date_echeance.strftime('%d/%m/%Y') if doc.date_echeance else '—'}", s['Normal'])],
        [Paragraph((doc.client_adresse or '') + ('<br/>' + doc.client_tel if doc.client_tel else ''), s['Small']),
         Paragraph((f"<b>Chantier :</b> {doc.chantier.nom}" if doc.chantier else ''), s['Normal'])],
    ]
    ti = Table(infos, colWidths=[9*cm, 7*cm])
    ti.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    story.append(ti)
    story.append(Spacer(1, 0.6*cm))

    # Tableau des lignes
    rows = [["Désignation", "Qté", "Unité", "P.U.", "Total HT"]]
    for l in doc.lignes:
        rows.append([
            Paragraph(l.designation, s['Normal']),
            f"{float(l.quantite):g}",
            l.unite or '',
            _fmt(l.prix_unitaire),
            _fmt(l.total_ligne),
        ])
    tbl = Table(rows, colWidths=[7.5*cm, 1.5*cm, 1.8*cm, 2.8*cm, 2.9*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    # Totaux
    tot = [
        ["", "Total HT", _fmt(doc.total_ht)],
        ["", f"TVA ({float(doc.tva_taux):g}%)", _fmt(doc.montant_tva)],
        ["", "TOTAL TTC", _fmt(doc.total_ttc)],
    ]
    tt = Table(tot, colWidths=[9*cm, 3.5*cm, 3.5*cm])
    tt.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 2), (-1, 2), 12),
        ('TEXTCOLOR', (1, 2), (-1, 2), PRIMARY),
        ('LINEABOVE', (1, 2), (-1, 2), 1, PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tt)

    if doc.notes:
        story.append(Spacer(1, 0.6*cm))
        story.append(Paragraph(f"<b>Notes :</b> {doc.notes}", s['Small']))
    if doc.conditions:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<b>Conditions :</b> {doc.conditions}", s['Small']))

    story.append(Spacer(1, 1*cm))
    if doc.type.value == 'devis':
        story.append(Paragraph("Bon pour accord (date + signature) :", s['Normal']))
    else:
        story.append(Paragraph("Merci de votre confiance.", s['Small']))

    pdf.build(story)
    buf.seek(0)
    return buf
