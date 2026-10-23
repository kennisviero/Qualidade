from pathlib import Path
import re, html
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import fitz

root = Path(__file__).resolve().parents[2]
out = root / 'Documentos/ferramentas.pdf'
pdfmetrics.registerFont(TTFont('ArialDoc', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialDocBold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFontFamily('ArialDoc',normal='ArialDoc',bold='ArialDocBold',italic='ArialDoc',boldItalic='ArialDocBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyDoc',fontName='ArialDoc',fontSize=9.5,leading=13,spaceAfter=7,textColor=colors.HexColor('#273444')))
styles.add(ParagraphStyle(name='TitleDoc',fontName='ArialDocBold',fontSize=25,leading=30,spaceAfter=17,textColor=colors.HexColor('#153a56')))
styles.add(ParagraphStyle(name='SectionDoc',fontName='ArialDocBold',fontSize=14,leading=18,spaceBefore=15,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor('#153a56')))
styles.add(ParagraphStyle(name='CellDoc',fontName='ArialDoc',fontSize=8.6,leading=11))
styles.add(ParagraphStyle(name='BulletDoc',parent=styles['BodyDoc'],leftIndent=12,firstLineIndent=-9))

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#16658b">\1</link>',s)
    return re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)

lines=(root/'Documentos/ferramentas.md').read_text(encoding='utf-8').splitlines()
story=[]
i=0
while i<len(lines):
    line=lines[i].strip()
    if not line:
        i+=1; continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',c) for c in cells):
                rows.append([Paragraph(inline(c),styles['CellDoc']) for c in cells])
            i+=1
        table=Table(rows,colWidths=[155,170,174.27],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e3edf4')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7fa')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),0.6,colors.HexColor('#94abba'))]))
        story.extend([table,Spacer(1,10)]); continue
    if line.startswith('# '): style=styles['TitleDoc']; line=line[2:]
    elif line.startswith('## '): style=styles['SectionDoc']; line=line[3:]
    elif line.startswith('- '): style=styles['BulletDoc']; line='• '+line[2:]
    elif re.match(r'^\d+\. ',line): style=styles['BulletDoc']
    else: style=styles['BodyDoc']
    story.append(Paragraph(inline(line),style)); i+=1

def footer(c,doc):
    c.saveState()
    c.setStrokeColor(colors.HexColor('#c3d1dc')); c.line(48,40,A4[0]-48,40)
    c.setFont('ArialDoc',8); c.setFillColor(colors.HexColor('#536b7d'))
    c.drawString(48,27,'QUALIDADE | Ferramentas aplicadas a Issues e RNCs')
    c.drawRightString(A4[0]-48,27,f'Página {doc.page}')
    c.restoreState()

SimpleDocTemplate(str(out),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=44,bottomMargin=56,title='Ferramentas da qualidade',author='Qualidade').build(story,onFirstPage=footer,onLaterPages=footer)
doc=fitz.open(out)
for n,page in enumerate(doc):
    page.get_pixmap(matrix=fitz.Matrix(1.15,1.15)).save(str(root/f'tmp/pdfs/ferramentas-{n+1}.png'))
    for block in page.get_text('blocks'):
        x0,y0,x1,y1,*_=block
        assert x0>=40 and x1<=A4[0]-40 and y0>=35 and y1<=A4[1]-20,(n,block)
text=''.join(p.get_text() for p in doc)
assert 'verificação' in text and 'dispersão' in text and 'Referências da ASQ' in text
assert '\ufffd' not in text
print(f'PDF gerado e renderizado: {len(doc)} páginas A4; acentos e limites verificados.')
