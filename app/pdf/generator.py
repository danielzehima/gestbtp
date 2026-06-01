from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

PRIMARY = colors.HexColor('#FF6B00')
DARK = colors.HexColor('#111111')


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name='H1Orange', fontName='Helvetica-Bold',
                         fontSize=20, textColor=PRIMARY, spaceAfter=12))
    s.add(ParagraphStyle(name='H2Dark', fontName='Helvetica-Bold',
                         fontSize=13, textColor=DARK, spaceAfter=8,
                         borderPadding=4))
    s.add(ParagraphStyle(name='Small', fontName='Helvetica',
                         fontSize=9, textColor=colors.grey))
    return s


def _accent(entreprise):
    try:
        return colors.HexColor(getattr(entreprise, 'couleur', None) or '#FF6B00')
    except Exception:
        return PRIMARY


def _header_footer(company='GESTBTP', accent=PRIMARY, contact=''):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(accent)
        canvas.rect(0, A4[1] - 1.5 * cm, A4[0], 1.5 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawString(2 * cm, A4[1] - 1 * cm, company)
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1 * cm,
                               datetime.now().strftime('%d/%m/%Y %H:%M'))
        canvas.setFillColor(colors.grey)
        canvas.setFont('Helvetica', 8)
        pied = f"Page {doc.page}" + (f" — {contact}" if contact else "")
        canvas.drawCentredString(A4[0] / 2, 1 * cm, pied)
        canvas.restoreState()
    return draw


def build_pdf(story, entreprise=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2.5 * cm, bottomMargin=2 * cm)
    company = (getattr(entreprise, 'raison_sociale', None)
               or (entreprise.nom if entreprise else 'GESTBTP'))
    accent = _accent(entreprise)
    contact = ''
    if entreprise:
        contact = ' · '.join(filter(None, [entreprise.telephone, entreprise.email])) or ''
    hf = _header_footer(company, accent, contact)
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    return buf


def rapport_pdf(rapport, entreprise=None):
    s = _styles()
    story = [Spacer(1, 0.5 * cm),
             Paragraph(f"Rapport journalier — {rapport.date.strftime('%d/%m/%Y')}", s['H1Orange'])]
    data = [
        ['Chantier', f"{rapport.chantier.reference} — {rapport.chantier.nom}"],
        ['Auteur', rapport.auteur.nom if rapport.auteur else '—'],
        ['Météo', rapport.meteo or '—'],
    ]
    t = Table(data, colWidths=[4 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6 * cm))
    for titre, val in [('Travaux réalisés', rapport.travaux_realises),
                       ('Difficultés rencontrées', rapport.difficultes),
                       ("Main d'œuvre présente", rapport.main_oeuvre),
                       ('Observations', rapport.observations)]:
        story.append(Paragraph(titre, s['H2Dark']))
        story.append(Paragraph((val or '—').replace('\n', '<br/>'), s['Normal']))
        story.append(Spacer(1, 0.4 * cm))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Signature : ______________________", s['Normal']))
    return build_pdf(story, entreprise)


def chantier_pdf(chantier, entreprise=None):
    s = _styles()
    story = [Spacer(1, 0.5 * cm),
             Paragraph(f"Fiche chantier — {chantier.nom}", s['H1Orange'])]
    data = [
        ['Référence', chantier.reference],
        ['Client', chantier.client.nom if chantier.client else '—'],
        ['Responsable', chantier.responsable.nom if chantier.responsable else '—'],
        ['Adresse', chantier.adresse or '—'],
        ['Budget', f"{chantier.budget} €"],
        ['Statut', chantier.statut.value],
        ['Date début', chantier.date_debut.strftime('%d/%m/%Y') if chantier.date_debut else '—'],
        ['Date fin prév.', chantier.date_fin_prev.strftime('%d/%m/%Y') if chantier.date_fin_prev else '—'],
    ]
    t = Table(data, colWidths=[4 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph("Description", s['H2Dark']))
    story.append(Paragraph((chantier.description or '—').replace('\n', '<br/>'), s['Normal']))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Signature : ______________________", s['Normal']))
    return build_pdf(story, entreprise)


def taches_pdf(chantier, taches, entreprise=None):
    s = _styles()
    story = [Spacer(1, 0.5 * cm),
             Paragraph(f"Tâches — {chantier.nom}", s['H1Orange'])]
    rows = [['Titre', 'Responsable', 'Priorité', 'Statut', 'Échéance']]
    for t in taches:
        rows.append([
            t.titre,
            t.responsable.nom if t.responsable else '—',
            t.priorite.value,
            t.statut.value,
            t.date_limite.strftime('%d/%m/%Y') if t.date_limite else '—',
        ])
    tbl = Table(rows, colWidths=[6 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
    ]))
    story.append(tbl)
    return build_pdf(story, entreprise)
