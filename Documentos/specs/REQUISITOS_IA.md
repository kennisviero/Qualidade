# REQUISITOS_IA — Parsing de norma e análise de lacunas (IA, OpenRouter)

Camada de IA do submódulo Requisitos, reusando o adapter LLM e o CRUD de acessos existentes.
Sempre com aprovação humana; nenhuma gravação automática. Sem chamada real ao provedor nos testes.

## Parsing norma → requisitos (sugestão)
- `POST /api/requisitos/sugerir` (`norma_id`, `acesso_id`): usa o `texto_extraido` da revisão mais recente do
  documento da norma (gerado pela leitura do PDM — Fase 1). Sem texto → 400 (orienta rodar a leitura antes).
- Serviço `app/services/requisitos_ia.py`: chama `llm_client.analisar_issues(..., json_mode=True)` com instruções
  para extrair `[{codigo_clausula,titulo,texto,categoria,obrigatoriedade}]`; valida o JSON estritamente e
  normaliza categoria/obrigatoriedade. Regra "não inventar". Retorna candidatos — **não persiste**.
- UI (`requisitos.js`): botão "Sugerir requisitos (IA)" → lista de candidatos com "Aprovar"; aprovar cria via `POST /api/requisitos`.
- Acesso LLM reusa `/api/configuracao/llm` (OpenRouter) — sem novo cadastro; escrita exige admin/editor; 502 em erro do provedor.

## Análise de lacunas (Consultar IA)
- `POST /api/conformidade/matriz/preparar` (`norma_id`): monta a matriz de cobertura e anexa `consulta_ia`
  (snapshot assinado via `app/services/ferramentas_ia.py` `context('conformidade', …)`).
- UI (`cobertura.js`): botão "Consultar IA (lacunas)" → `openToolAI('conformidade', result)`; envio explícito pelo
  componente compartilhado `ferramentas_ia.js` ao endpoint `/api/ferramentas/ia/consultar` (valida a assinatura).

## Verificação
- `tests/test_requisitos_ia.py` com **transporte LLM simulado** (monkeypatch `app.services.requisitos_ia.analisar_issues`):
  sugestão feliz, sem texto (400), JSON inválido (502) e snapshot assinado da matriz. Sem chamada real.
- Regras `regrasnegocio/RG.md` (`RG-IAN-*`).
