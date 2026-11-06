"""One source of truth for the web whitepaper and its actual PDF."""
import io
import os
from pathlib import Path
from xml.sax.saxutils import escape
from fastapi import APIRouter, Response
from ecosystem import DEFAULT_MINTS
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.pagesizes import A4

from whitepaper_text import CHAPTERS

def document():
    return {'title': 'FEELESS', 'subtitle': 'Less Noise. More Alpha.', 'tagline': 'A FeeLess Future.',
            'version': '1.2', 'date': '2026-10-02', 'status': 'Product whitepaper · implementation and policy disclosures',
            'launch_target': 'Q2 2027 · target, not a guarantee',
            'contracts': [{'name': name, 'mint': os.getenv(f'{name}_MINT', DEFAULT_MINTS[name]), 'chain': 'Solana'} for name in ['FEE', 'RFEE', 'FEECAT']],
            'chapters': [{'id': f'chapter-{i + 1}', 'number': i + 1, 'title': title, 'text': text} for i, (title, text) in enumerate(CHAPTERS)]}

def render_pdf():
    data = document()
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=52, leftMargin=52, topMargin=70, bottomMargin=55,
                            title='FEELESS — Less Noise. More Alpha.', author='FEELESS')
    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=10, leading=16, textColor=colors.HexColor('#33483d'), spaceAfter=18)
    heading = ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=18, leading=24, textColor=colors.HexColor('#073d27'), spaceAfter=13)
    eyebrow = ParagraphStyle('Eyebrow', fontName='Helvetica-Bold', fontSize=8, leading=12, textColor=colors.HexColor('#248c60'), spaceAfter=10)
    cover = ParagraphStyle('Cover', fontName='Helvetica-Bold', fontSize=52, leading=59, textColor=colors.HexColor('#063b26'))
    story = [Spacer(1, 80), Paragraph('FEELESS', cover), Spacer(1, 24), Paragraph('Less Noise. More Alpha.', heading),
             Paragraph('A FeeLess Future.', body), Spacer(1, 45), Paragraph('WHITEPAPER / VERSION 1.0', eyebrow),
             Paragraph('Economic fee-back. Connected intelligence. A community-first on-chain workspace.', body),
             Spacer(1, 30), Paragraph(escape(data['status']), body), Paragraph('Public platform launch target: Q2 2027. Not a guarantee.', body), PageBreak(),
             Paragraph('Contents', heading)]
    for chapter in data['chapters']:
        story.append(Paragraph(f'{chapter["number"]:02d} / {escape(chapter["title"])}', body))
    story += [PageBreak(), Paragraph('Contract registry', heading), Paragraph('Owner-supplied Solana mints. Exact-address matching, not a security endorsement.', body)]
    for contract in data['contracts']:
        story += [Paragraph(contract['name'], eyebrow), Paragraph(contract['mint'], body)]
    story.append(PageBreak())
    for chapter in data['chapters']:
        story.append(KeepTogether([Paragraph(f'{chapter["number"]:02d} / FEELESS', eyebrow),
                                  Paragraph(escape(chapter['title']), heading), Paragraph(escape(chapter['text']), body)]))
        story.append(Spacer(1, 15))
    def page(canvas, document):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#05160d')); canvas.rect(0, h - 43, w, 43, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#00efa0')); canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(52, h - 27, 'FEELESS')
        canvas.setFillColor(colors.HexColor('#d9eee1')); canvas.setFont('Helvetica', 7)
        canvas.drawRightString(w - 52, h - 27, 'LESS NOISE. MORE ALPHA.')
        canvas.setStrokeColor(colors.HexColor('#b5d4bf')); canvas.line(52, 39, w - 52, 39)
        canvas.setFillColor(colors.HexColor('#668974')); canvas.setFont('Helvetica', 7)
        canvas.drawString(52, 26, f'FEELESS / v1.0 / {data["date"]}')
        canvas.drawRightString(w - 52, 26, f'{document.page:02d}')
        logo = Path(__file__).parent.parent / 'frontend/public/assets/feeless-logo.png'
        if document.page == 1 and logo.exists():
            canvas.drawImage(str(logo), w - 142, h - 217, width=75, height=80, mask='auto', preserveAspectRatio=True)
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()

router = APIRouter(prefix='/api/docs')
@router.get('/whitepaper')
async def web_whitepaper():
    return document()

@router.get('/whitepaper.pdf')
def pdf_whitepaper(download: bool = False):
    return Response(render_pdf(), media_type='application/pdf', headers={
        'Content-Disposition': f'{"attachment" if download else "inline"}; filename="FEELESS-Whitepaper-v1.0.pdf"',
        'Cache-Control': 'public, max-age=3600'})