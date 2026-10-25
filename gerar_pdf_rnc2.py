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

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, 'Roteiro para alunos - MASP com RNC-2026-002 (Empresa TESTE 1)', ln=1, align='C')
pdf.ln(4)
pdf.set_font('Arial', '', 10)
pdf.cell(0, 6, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', ln=1)
pdf.ln(6)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '1) Objetivo', ln=1)
pdf.set_font('Arial', '', 10)
pdf.multi_cell(0, 5, 'Reconstruir o caso RNC-2026-002/ISSUE-0038, avaliar evidencias e decisoes registradas, cruzar com ferramentas de qualidade e elaborar sintese MASP.')
pdf.ln(2)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '2) Caso (fatos originais)', ln=1)
pdf.set_font('Arial', '', 10)
pdf.multi_cell(0, 5, f"ISSUE: {i['codigo']} | RNC: {d['codigo']} | Status RNC: {d['status']} | Status ISSUE: {i['status']}")
pdf.multi_cell(0, 5, f"O que/onde/quando/quem: {fs.get('o_que')} / {fs.get('onde')} / {fs.get('quando')} / {fs.get('quem')}")
pdf.multi_cell(0, 5, f"Comportamento observado: {fs.get('comportamento_observado')}")
pdf.multi_cell(0, 5, f"Evidencias: {fs.get('evidencias_objetivas')}")
pdf.multi_cell(0, 5, f"Impacto/Ambiente: {fs.get('impacto')}/{fs.get('ambiente')}")
pdf.ln(2)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '3) Contencao registrada', ln=1)
pdf.set_font('Arial', '', 10)
pdf.multi_cell(0, 5, f"Acao imediata: {d.get('acao_contencao_imediata')}")
pdf.multi_cell(0, 5, f"Contencao definitiva: {d.get('acao_contencao_definitiva')}")
pdf.multi_cell(0, 5, f"Disposicao inicial: {d.get('disposicao_inicial')}")
pdf.ln(2)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '4) Investigacao (aba Investigacao)', ln=1)
pdf.set_font('Arial', '', 10)
pdf.multi_cell(0, 5, f"Ishikawa/Metodologias: {d.get('metodologias_json')}")
pdf.multi_cell(0, 5, f"Analise (simulado): {inv.get('analise')}")
hlist = inv.get('hipoteses') or []
for h in hlist:
    pdf.multi_cell(0, 5, f"Hipotese: {h.get('descricao')}")
    pdf.multi_cell(0, 5, f"  Evidencias favoraveis: {h.get('evidencias_favoraveis')}")
    pdf.multi_cell(0, 5, f"  Evidencias contrarias: {h.get('evidencias_contrarias')}")
    for t in h.get('testes') or []:
        pdf.multi_cell(0, 5, f"  Teste planejado: {t.get('procedimento')}")
        pdf.multi_cell(0, 5, f"    Amostra: {t.get('amostra')} | Resultado esperado: {t.get('resultado_esperado')}")
        pdf.multi_cell(0, 5, f"    Criterio decisao: {t.get('criterio_decisao')} | Resultado: '{t.get('resultado')}' | Conclusao: {t.get('conclusao')}")
pdf.ln(2)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '5) Acoes (5W2H)', ln=1)
pdf.set_font('Arial', '', 10)
for a in acoes:
    pdf.multi_cell(0, 5, f"Acao: {a.get('descricao')}")
    pdf.multi_cell(0, 5, f"  Por que/Onde/Como/Quanto: {a.get('por_que')} / {a.get('onde')} / {a.get('como')} / {a.get('quanto')}")
    pdf.multi_cell(0, 5, f"  Responsavel/Prazo/Status: {a.get('responsavel_id')} / {a.get('prazo_limite')} / {a.get('status')} (inicio:{a.get('data_inicio')})")
    pdf.multi_cell(0, 5, f"  Obs: {a.get('observacao')}")
pdf.ln(2)

pdf.add_page()
pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '6) Roteiro passo a passo para cumprir a atividade', ln=1)
pdf.set_font('Arial', '', 10)
steps = [
  "Passo 1 - Reconstruir: Liste fatos originais (ISSUE-0038) e snapshot da RNC-2026-002. Identifique o que esta comprovado vs o que e hipotese.",
  "Passo 2 - Avaliar evidencias/decisoes: Verifique se contenção tem suporte. As hipoteses estao marcadas como inconclusivas (sem resultado de teste). Avalie se decisao de emissao e investigacao sao coerentes com evidencias.",
  "Passo 3 - Cruzar com ferramentas: Utilize Pareto/Histograma/Dispersao/Afinidades/Relações/Matriz (conforme orientacao). Formule pergunta, aplique filtros, registre achados e limitacoes.",
  "Passo 4 - Definir testes/acoes: Com base nos gaps, proponha testes para a hipotese 'Arquivo de impressao antigo' (3 lotes x 200 unid) e criterios de decisao. Revise a acao em backlog.",
  "Passo 5 - Sintese MASP: Problema priorizado, hipoteses/testes, plano 5W2H (quem/por que/onde/como/quanto/quando), criterio de eficacia (comparavel, mesmo metodo) e licoes aprendidas."
]
for s in steps:
    pdf.multi_cell(0, 5, f"- {s}")
pdf.ln(4)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '7) Perguntas guiadas (para responder em equipe)', ln=1)
pdf.set_font('Arial', '', 10)
qs = [
  "1) Quais evidencias efetivamente comprovam o desvio? Quais sao apenas relatos/hipoteses?",
  "2) A hipotese 'Arquivo de impressao antigo' e plausivel? Que evidencias faltam para confirma-la/descarta-la?",
  "3) O teste planejado (3 lotes x 200) e suficiente? Por que? O que precisa ser registrado para torná-lo conclusivo?",
  "4) A acao em backlog tem criterio de aceite claro? O que falta para iniciar/concluir e avaliar eficacia?",
  "5) Ao cruzar com as ferramentas, ha recorrencia com outras RNCs/Issues da empresa TESTE 1 que mude a priorizacao?",
  "6) Qual criterio de eficacia voce proporia (numero/limite, mesmo metodo, amostra) antes de encerrar a RNC?"
]
for q in qs:
    pdf.multi_cell(0, 5, f"- {q}")
pdf.ln(4)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '8) Checklist de entrega', ln=1)
pdf.set_font('Arial', '', 10)
ck = [
  "[ ] Reconstrucao do caso com fatos vs hipoteses",
  "[ ] Avaliacao de evidencias/decisoes",
  "[ ] Uso de pelo menos 1 ferramenta (com pergunta/dados/filtros/achados/limitacoes)",
  "[ ] Proposta de testes e criterio de decisao",
  "[ ] Plano 5W2H e criterio de eficacia",
  "[ ] Sintese MASP final"
]
for c in ck:
    pdf.multi_cell(0, 5, c)
pdf.ln(4)

pdf.set_font('Arial', 'B', 12)
pdf.cell(0, 8, '9) Referencias', ln=1)
pdf.set_font('Arial', '', 10)
pdf.multi_cell(0, 5, "- atividade.md (roteiro geral)")
pdf.multi_cell(0, 5, "- documentos/exemplos_turma_teste1/README.md")
pdf.multi_cell(0, 5, "- documentos/exemplos_turma_teste1/manifesto.json")
pdf.multi_cell(0, 5, "- Sistema: RNC-2026-002 (ISSUE-0038), investigacao_json, acoes")

out = r'C:\Produttare\Qualidade\documentos\exemplos_turma_teste1\RNC_2026_002_passo_a_passo_para_alunos.pdf'
pdf.output(out)
print(out)
