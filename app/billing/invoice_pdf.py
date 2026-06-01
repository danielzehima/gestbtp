"""Facture d'abonnement SaaS GESTBTP (émise par TON SaaS vers l'abonné),
générée à partir d'un paiement réussi.
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

PRIMARY = colors.HexColor('#FF6B00')


def _fmt(n):
    return f"{float(n or 0):,.0f}".replace(',', ' ') + " FCFA"


def abonnement_invoice_pdf(paiement, compte):
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('Small', fontName='Helvetica', fontSize=9, textColor=colors.grey))
    s.add(ParagraphStyle('Right', fontName='Helvetica', fontSize=10, alignment=2))
    story = []

    # En-tête : GESTBTP (émetteur) / FACTURE
    head = [[
        Paragraph("<b>GESTBTP</b><br/><font size=8 color='grey'>Plateforme de gestion de chantier<br/>"
                  "Abidjan, Côte d'Ivoire<br/>contact@gestbtp.com</font>", s['Normal']),
        Paragraph("<b><font size=22 color='#FF6B00'>FACTURE</font></b><br/>"
                  f"<font size=10>N° {paiement.reference}</font>", s['Right']),
    ]]
    t = Table(head, colWidths=[9*cm, 7*cm]); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t); story.append(Spacer(1, 0.8*cm))

    # Client (l'entreprise abonnée)
    d = (paiement.date_paiement or paiement.date_creation)
    infos = [[
        Paragraph(f"<b>Facturé à</b><br/>{compte.nom}<br/>"
                  f"<font size=9 color='grey'>{compte.owner.email if compte.owner else ''}</font>", s['Normal']),
        Paragraph(f"<b>Date :</b> {d.strftime('%d/%m/%Y') if d else '—'}<br/>"
                  f"<b>Statut :</b> Payé", s['Right']),
    ]]
    ti = Table(infos, colWidths=[9*cm, 7*cm]); ti.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(ti); story.append(Spacer(1, 0.8*cm))

    # Ligne unique : abonnement
    plan = (paiement.plan or '').capitalize()
    rows = [
        ["Description", "Montant"],
        [f"Abonnement GESTBTP — Forfait {plan} (1 mois)", _fmt(paiement.montant)],
        ["TOTAL PAYÉ", _fmt(paiement.montant)],
    ]
    tbl = Table(rows, colWidths=[12*cm, 4*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 2), (1, 2), PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Facture acquittée — paiement reçu via GeniusPay. "
                           "Merci de votre confiance.", s['Small']))

    pdf.build(story)
    buf.seek(0)
    return buf
