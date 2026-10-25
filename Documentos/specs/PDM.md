# PDM — Documentos Controlados (motor de repositório de arquivos)

Motor genérico e multi-tenant de gestão de documentos sobre o Vault já existente.
Baseline: Siemens Teamcenter Requirements Management (`Requirements/TC_Requirements_MGT.pdf`).
Submódulo: **Requisitos** (compartilhável com MASP e Processos). Não altera `processos`/`revisoes`
nem qualquer módulo existente — é aditivo.

## Objetivo e limites
- Capturar, versionar e controlar documentos (bytes no Vault, metadados em SQLite).
- Ciclo de vida, check-out/check-in com lock-out exclusivo, ciclo de aprovação e trilha de auditoria.
- Fora desta fase: variantes, processo de mudança formal, rastreabilidade/conformidade, parsing por IA que *grava* requisitos (Fase 5).

## Persistência (SQLite + Vault)
- `documentos_controlados`: `id`, `empresa_id` (tenancy), `codigo` serial `DOC-NNNN` `UNIQUE(empresa_id,codigo)`,
  `titulo`, `tipo` (`norma|procedimento|instrucao|formulario|politica|contrato|outro`),
  `estado` (`rascunho|em_revisao|em_aprovacao|aprovado|obsoleto`), `revisao_atual_id`,
  `responsavel_id`, `aprovador_id`, `checkout_por_id`+`checkout_em`, `pasta`, `criado_por_id`, datas.
- `documento_revisoes`: `documento_id`, `numero` `UNIQUE(documento_id,numero)`, `descricao_mudanca`,
  `estado` (`rascunho|aprovada|obsoleta`), `arquivo_nome`, `arquivo_hash`, `texto_extraido`, `origem_texto`,
  autor/revisor/aprovador + datas.
- `documento_auditoria`: cadeia SHA-256 (`hash_anterior`+payload → `hash_atual`) por operação.
- Vault: `Vault/{empresa}/_pdm/{codigo}/R{numero}/arquivo` (helpers de `app/docs.py`).
- Triggers `BEFORE DELETE` em `empresas` (cascata) e `usuarios` (set NULL).

## Estados e transições
- Criar → documento `rascunho` + revisão R01 `rascunho` + auditoria `criado`.
- Check-out (livre→meu) exige editor; segundo usuário recebe **409**. Documento obsoleto não aceita check-out.
- Nova revisão e upload de arquivo exigem check-out pelo próprio usuário; upload só em revisão `rascunho`.
- Aprovar: só `aprovador_id` (ou superusuário); exige check-in (sem check-out ativo); marca a maior revisão `aprovada`,
  as anteriores `obsoleta`, documento `aprovado` e `revisao_atual_id`.
- Obsoletar: documento `obsoleto`, revisões `obsoleta`, check-out liberado.

## Captura / leitura (por IA via OpenRouter)
- `POST .../revisoes/{n}/ler` (editor): extração digital local (`app/services/captura.py` via `pypdf`/`python-docx`);
  se vazio e `acesso_id` informado (acesso LLM OpenRouter ativo da empresa), renderiza a página (PyMuPDF) e lê por
  modelo de visão (`llm_client.ler_documento_visao`). Grava `texto_extraido`/`origem_texto` (`digital|ia|vazio`).
- CRUD do acesso LLM reusa `/api/configuracao/llm` (`llm_acessos`) — sem CRUD novo. Sem `pymupdf` ou sem acesso, degrada.

## API (`/api/pdm/documentos`)
- `GET ''` (filtros `tipo|estado|responsavel_id|q`), `GET /{id}`, `POST ''`, `PUT /{id}`, `DELETE /{id}` (apaga pasta).
- `GET/POST /{id}/revisoes`; `POST/GET /{id}/revisoes/{n}/arquivo` (upload/download); `POST /{id}/revisoes/{n}/ler`.
- `POST /{id}/checkout` | `/checkin` | `/aprovar` | `/obsoletar`; `GET /{id}/auditoria` (com `integra`).
- Leitura: `get_current_user`; escrita: `require_papel('admin','editor')`; tenancy por `scope`/`fetch_doc`.

## Verificação
- `tests/test_pdm.py` (fluxo completo, lock-out concorrente→409, aprovação restrita, visualizador, tenancy 401/403,
  auditoria encadeada, leitura digital sem LLM) e `tests/check_pdm.cjs` (menu/section, lista com lock-out, detalhe
  sanitizado, visualizador sem escrita, reset). Regras em `regrasnegocio/RG.md` (`RG-PDM-*`, `RG-CAP-*`).
