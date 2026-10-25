from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

out = r'C:\Produttare\Qualidade\documentos\exemplos_turma_teste1\RNC_2026_002_passo_a_passo_para_alunos.pdf'
doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Justify', alignment=4))

story = []
story.append(Paragraph('RNC-2026-002 - Roteiro para alunos (MASP)', styles['Title']))
story.append(Spacer(1,12))
story.append(Paragraph('<b>Objetivo</b>', styles['Heading2']))
story.append(Paragraph('Reconstruir o caso ISSUE-0038/RNC-2026-002, avaliar evidencias e decisoes registradas, cruzar com as ferramentas de qualidade e elaborar sintese MASP.', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>1) Caso</b>', styles['Heading2']))
story.append(Paragraph('- ISSUE-0038 / RNC-2026-002 (emitida)<br/>- Etiqueta incorreta: 19 unidades nao conformes em 180 inspecionadas (10,56%)<br/>- Contencao: segregar lote e suspender liberacao<br/>- Disposicao inicial: retrabalho<br/>- Impacto: Alto / Ambiente: Homologacao', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>2) Investigacao</b>', styles['Heading2']))
story.append(Paragraph('- Hipotese: "Arquivo de impressao antigo" (Metodo/Ishikawa)<br/>- Evidencias favoraveis: Relato didatico de falha recorrente no mesmo posto<br/>- Evidencias contrarias: Ainda nao avaliadas<br/>- Teste planejado: Comparar condicao atual e corrigida em 3 lotes equivalentes (200 unidades/condicao). Comparar taxas, condicoes e rastreabilidade.<br/>- Resultado do teste: (vazio) | Conclusao: inconclusiva', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>3) Acoes (5W2H)</b>', styles['Heading2']))
story.append(Paragraph('- Acao: Bloquear versoes antigas e validar codigo por leitura<br/>- Por que/Onde/Como/Quanto: Reduzir repeticao / Linha 1 / posto de inspecao / Revisar instrucao, testar em 3 lotes e registrar resultados / R$ 200,00 (estimativa simulada)<br/>- Responsavel/Prazo/Status: 5 / 2026-08-22 / backlog (inicio: vazio)<br/>- Observacao: Criterio de aceite: evidencia comparavel em tres lotes; avaliacao de eficacia pendente.', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>4) Roteiro passo a passo (MASP)</b>', styles['Heading2']))
story.append(Paragraph('1) Reconstruir: Liste fatos originais (ISSUE-0038) e snapshot da RNC-2026-002. Separe o que esta comprovado do que e hipotese.<br/>2) Avaliar: Verifique se a contencao tem suporte nas evidencias. Hipoteses estao marcadas como inconclusivas (sem resultado de teste).<br/>3) Cruzar com ferramentas: Utilize Pareto, Histograma, Dispersao, Afinidades, Relacoes e Matriz. Para cada uma: pergunta, dados/filtros, achados, limitacoes.<br/>4) Propor testes/acoes: Defina teste para "Arquivo de impressao antigo" (3 lotes x 200) com criterio de decisao e revise a acao em backlog.<br/>5) Sintese MASP: Problema priorizado, hipoteses/testes, plano 5W2H, criterio de eficacia (mesmo metodo, evidencia comparavel) e licoes aprendidas.', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>5) Perguntas guiadas</b>', styles['Heading2']))
story.append(Paragraph('1) Quais evidencias efetivamente comprovam o desvio? Quais sao apenas relatos/hipoteses?<br/>2) A hipotese "Arquivo de impressao antigo" e plausivel? Que evidencias faltam para confirma-la ou descarta-la?<br/>3) O teste planejado (3 lotes x 200) e suficiente? O que precisa ser registrado para torna-lo conclusivo?<br/>4) A acao em backlog tem criterio de aceite claro? O que falta para iniciar/concluir e avaliar eficacia?<br/>5) Ha recorrencia com outras RNCs/Issues da empresa TESTE 1 que mude a priorizacao?<br/>6) Qual criterio de eficacia voce proporia (limite/mesmo metodo/amostra) antes de encerrar a RNC?', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>6) Checklist de entrega</b>', styles['Heading2']))
story.append(Paragraph('[ ] Reconstrucao do caso (fatos vs hipoteses)<br/>[ ] Avaliacao de evidencias/decisoes<br/>[ ] Uso de pelo menos 1 ferramenta (pergunta/dados/filtros/achados/limitacoes)<br/>[ ] Proposta de testes e criterio de decisao<br/>[ ] Plano 5W2H e criterio de eficacia<br/>[ ] Sintese MASP final', styles['Normal']))
story.append(Spacer(1,6))

story.append(Paragraph('<b>Referencias</b>', styles['Heading2']))
story.append(Paragraph('- atividade.md<br/>- documentos/exemplos_turma_teste1/README.md<br/>- documentos/exemplos_turma_teste1/manifesto.json<br/>- Sistema: RNC-2026-002 / ISSUE-0038 / investigacao_json / acoes', styles['Normal']))

doc.build(story)
print(out)
