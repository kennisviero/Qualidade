from reportlab.pdfgen import canvas
import os

p = r'C:\Produttare\Qualidade\documentos\exemplos_turma_teste1\RNC_2026_002_passo_a_passo_para_alunos.pdf'
os.makedirs(os.path.dirname(p), exist_ok=True)
c = canvas.Canvas(p)
c.setFont('Helvetica-Bold', 14)
c.drawString(40, 800, 'RNC-2026-002 - Roteiro para alunos (MASP)')
c.setFont('Helvetica', 9)
c.drawString(40, 770, 'ISSUE-0038/RNC-2026-002 | Etiqueta incorreta 19/180 (10,56%) | Contencao: segregar/suspender | Disposicao: retrabalho')
c.drawString(40, 750, 'Investigacao: Hipotese "Arquivo de impressao antigo" (Metodo/Ishikawa), inconclusiva, sem resultado. Teste: 3 lotes x 200.')
c.drawString(40, 730, 'Acao em backlog: Bloquear versoes antigas e validar codigo por leitura (resp 5, prazo 2026-08-22), eficacia pendente.')
c.drawString(40, 710, 'Passos: 1) Fatos vs hipoteses 2) Avaliar evidencias 3) Ferramentas 4) Propor testes 5) Sintese MASP (5W2H+criterio eficacia)')
c.drawString(40, 690, 'Perguntas: evidencias comprovadas? Falta p/ confirmar/descartar? Teste suficiente? Criterio eficacia antes de encerrar?')
c.drawString(40, 670, 'Checklist: reconstrucao, avaliacao, ferramenta, testes/criterio, 5W2H/criterio eficacia, sintese MASP')
c.drawString(40, 650, 'Refs: atividade.md, documentos/exemplos_turma_teste1/README.md, manifesto.json, RNC-2026-002/ISSUE-0038')
c.save()
print(p)
