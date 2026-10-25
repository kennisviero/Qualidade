from fpdf import FPDF
import sqlite3, json
from datetime import datetime

conn = sqlite3.connect(r'C:\Produttare\Qualidade\data\qualidade.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM rncs WHERE codigo='RNC-2026-002'")
r = cur.fetchone()
d = dict(r)
inv = json.loads(d.get('investigacao_json') or '{}')
fs = json.loads(d.get('fatos_snapshot_json') or '{}')
cur.execute('SELECT * FROM issues WHERE id=?', (d['issue_id'],))
i = dict(cur.fetchone())
cur.execute('SELECT * FROM acoes WHERE rnc_id=?', (d['id'],))
acoes = [dict(a) for a in cur.fetchall()]
conn.close()

def clean(s):
    if s is None:
        return ''
    s = str(s)
    # replace common unicode issues
    s = s.replace('\u00e7','c').replace('\u00e3','a').replace('\u00f5','o').replace('\u00e1','a').replace('\u00e9','e').replace('\u00ed','i').replace('\u00f3','o').replace('\u00fa','u')
    s = s.replace('\u00c7','C').replace('\u00c3','A').replace('\u00d5','O')
    s = s.replace('\u201c','"').replace('\u201d','"').replace('\u2018',"'").replace('\u2019',"'").replace('\u2013','-').replace('\u2014','-')
    return s

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font('Arial', 'B', 14)
pdf.multi_cell(0, 8, clean('Roteiro para alunos - MASP com RNC-2026-002 (Empresa TESTE 1)'), align='C')
pdf.ln(4)
pdf.set_font('Arial', '', 9)
pdf.cell(0, 5, clean(f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'), ln=1)
pdf.ln(4)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('1) Objetivo'), ln=1)
pdf.set_font('Arial', '', 9)
pdf.multi_cell(0, 4, clean('Reconstruir o caso RNC-2026-002/ISSUE-0038, avaliar evidencias e decisoes registradas, cruzar com ferramentas de qualidade e elaborar sintese MASP.'))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('2) Caso (fatos originais)'), ln=1)
pdf.set_font('Arial', '', 9)
pdf.multi_cell(0, 4, clean(f"ISSUE: {i['codigo']} | RNC: {d['codigo']} | Status RNC: {d['status']} | Status ISSUE: {i['status']}"))
pdf.multi_cell(0, 4, clean(f"O que/onde/quando/quem: {fs.get('o_que')} / {fs.get('onde')} / {fs.get('quando')} / {fs.get('quem')}"))
pdf.multi_cell(0, 4, clean(f"Comportamento observado: {fs.get('comportamento_observado')}"))
pdf.multi_cell(0, 4, clean(f"Evidencias: {fs.get('evidencias_objetivas')}"))
pdf.multi_cell(0, 4, clean(f"Impacto/Ambiente: {fs.get('impacto')}/{fs.get('ambiente')}"))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('3) Contencao registrada'), ln=1)
pdf.set_font('Arial', '', 9)
pdf.multi_cell(0, 4, clean(f"Acao imediata: {d.get('acao_contencao_imediata')}"))
pdf.multi_cell(0, 4, clean(f"Contencao definitiva: {d.get('acao_contencao_definitiva')}"))
pdf.multi_cell(0, 4, clean(f"Disposicao inicial: {d.get('disposicao_inicial')}"))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('4) Investigacao'), ln=1)
pdf.set_font('Arial', '', 9)
pdf.multi_cell(0, 4, clean(f"Metodologias: {d.get('metodologias_json')}"))
hlist = inv.get('hipoteses') or []
for h in hlist:
    pdf.multi_cell(0, 4, clean(f"Hipotese: {h.get('descricao')}"))
    pdf.multi_cell(0, 4, clean(f"  Evid. favoraveis: {h.get('evidencias_favoraveis')}"))
    pdf.multi_cell(0, 4, clean(f"  Evid. contrarias: {h.get('evidencias_contrarias')}"))
    for t in h.get('testes') or []:
        pdf.multi_cell(0, 4, clean(f"  Teste: {t.get('procedimento')} | Amostra: {t.get('amostra')}"))
        pdf.multi_cell(0, 4, clean(f"    Resultado esperado: {t.get('resultado_esperado')}"))
        pdf.multi_cell(0, 4, clean(f"    Resultado: '{t.get('resultado')}' | Conclusao: {t.get('conclusao')}"))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('5) Acoes (5W2H)'), ln=1)
pdf.set_font('Arial', '', 9)
for a in acoes:
    pdf.multi_cell(0, 4, clean(f"Acao: {a.get('descricao')}"))
    pdf.multi_cell(0, 4, clean(f"  Por que/Onde/Como/Quanto: {a.get('por_que')} / {a.get('onde')} / {a.get('como')} / {a.get('quanto')}"))
    pdf.multi_cell(0, 4, clean(f"  Resp/Prazo/Status: {a.get('responsavel_id')} / {a.get('prazo_limite')} / {a.get('status')} (inicio:{a.get('data_inicio')})"))
    pdf.multi_cell(0, 4, clean(f"  Obs: {a.get('observacao')}"))

pdf.add_page()
pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('6) Roteiro passo a passo'), ln=1)
pdf.set_font('Arial', '', 9)
steps = [
  "1) Reconstruir: Liste fatos vs hipoteses (ISSUE-0038/RNC-2026-002).",
  "2) Avaliar: Verifique contecao e evidencias. Hipoteses marcadas como inconclusivas, sem resultado de teste.",
  "3) Cruzar: Use Pareto/Histograma/Dispersao/Afinidades/Relacoes/Matriz com pergunta, filtros, achados e limitacoes.",
  "4) Testes/acoes: Proponha teste p/ 'Arquivo de impressao antigo' (3 lotes x 200) e criterios. Revise acao em backlog.",
  "5) Sintese MASP: Problema priorizado, hipoteses/testes, plano 5W2H, criterio de eficacia (mesmo metodo) e licoes aprendidas."
]
for s in steps:
    pdf.multi_cell(0, 4, clean('- ' + s))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('7) Perguntas guiadas'), ln=1)
pdf.set_font('Arial', '', 9)
qs = [
  "1) Quais evidencias comprovam o desvio vs hipoteses?",
  "2) O que falta para confirmar/descartar 'Arquivo de impressao antigo'?",
  "3) O teste planejado e suficiente? O que precisa ser registrado?",
  "4) A acao em backlog tem criterio de aceite? O que falta para avaliar eficacia?",
  "5) Ha recorrencia em outras RNCs/Issues que mude a priorizacao?",
  "6) Qual criterio de eficacia proporia antes de encerrar a RNC?"
]
for q in qs:
    pdf.multi_cell(0, 4, clean('- ' + q))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('8) Checklist'), ln=1)
pdf.set_font('Arial', '', 9)
for c in ["[ ] Reconstrucao fatos vs hipoteses", "[ ] Avaliacao evidencias/decisoes", "[ ] Uso de ferramenta (pergunta/dados/filtros/achados/limitacoes)", "[ ] Proposta de testes/criterio decisao", "[ ] Plano 5W2H e criterio de eficacia", "[ ] Sintese MASP"]:
    pdf.multi_cell(0, 4, clean(c))
pdf.ln(2)

pdf.set_font('Arial', 'B', 11)
pdf.cell(0, 7, clean('9) Referencias'), ln=1)
pdf.set_font('Arial', '', 9)
pdf.multi_cell(0, 4, clean('- atividade.md'))
pdf.multi_cell(0, 4, clean('- documentos/exemplos_turma_teste1/README.md'))
pdf.multi_cell(0, 4, clean('- documentos/exemplos_turma_teste1/manifesto.json'))
pdf.multi_cell(0, 4, clean('- RNC-2026-002 / ISSUE-0038 / investigacao_json / acoes'))

out = r'C:\Produttare\Qualidade\documentos\exemplos_turma_teste1\RNC_2026_002_passo_a_passo_para_alunos.pdf'
pdf.output(out)
print(out)
