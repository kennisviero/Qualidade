# REQUISITOS — Requisitos/cláusulas de uma Norma (submódulo Requisitos)

Requisitos derivados de uma norma, com categoria e obrigatoriedade, import/export e variantes de
documento no PDM. Aditivo; não altera módulos existentes.

## Persistência — `requisitos`
`id`, `empresa_id` (tenancy), `norma_id` → `normas(id)` ON DELETE CASCADE, `codigo_clausula`, `titulo` NOT NULL,
`texto`, `categoria` (`normativo|interno|cliente|legal`), `obrigatoriedade` (`obrigatorio|recomendado|informativo`),
`estado` (`ativo|revogado`), `ordem`, `criado_por_id`, datas. Índice `(norma_id, ordem)`. Triggers delete empresa/usuário.
**Variantes**: `documento_revisoes.variante` (migração aditiva em `init_db`); criar revisão aceita rótulo de variante.

## API (`/api/requisitos`)
- `GET ''?norma_id&empresa_id&categoria&estado&q`, `POST ''`, `PUT /{id}`, `DELETE /{id}` — enums validados (422), tenancy por `scope`; a norma precisa ser da empresa.
- `POST /importar` (multipart `norma_id`+arquivo): CSV (stdlib), DOCX (python-docx), XLSX (openpyxl; degrada se ausente). Cria em lote numa transação; sanitiza campos.
- `GET /exportar?norma_id&formato=csv|xlsx`: CSV sempre; XLSX se openpyxl disponível.
- Leitura `get_current_user`; escrita `require_papel('admin','editor')`.

## Frontend
- Sub-painel dentro do detalhe da Norma (`app/static/js/requisitos.js`, chamado por `normas.js`): lista por norma,
  adicionar/excluir, Importar/Exportar, botão "Sugerir requisitos (IA)" (Fase 5). Escrita `editor-only`.

## Extensão IREB (Fase A)
- **Prioridade (MoSCoW)**: `requisitos.prioridade` (`''|must|should|could|wont`), com filtro e validação (422). IREB cap. 4.
- **Atributos configuráveis (attribute schema)**: `requisito_atributo_defs` (esquema por empresa: chave/rótulo/tipo `texto|numero|data|lista|booleano`/opções/obrigatório) — CRUD **admin** em `/api/requisitos/atributos/defs`; `requisito_atributo_valores` (valor por requisito), gravado em `PUT /api/requisitos/{id}/atributos` com validação por tipo/obrigatório. IREB cap. 3.
- **Relações requisito↔requisito**: `requisito_relacoes` (`deriva_de|refina|depende|conflita|duplica`) — `GET/POST/DELETE /api/requisitos/{id}/relacoes` (rejeita auto-relação 422, duplicado 409, destino de outra empresa 404). IREB cap. 6.
- **Tipo de relação no vínculo**: `requisito_vinculos.tipo_relacao` (`satisfaz|verifica|implementa|mitiga|outro`), default `satisfaz` (retrocompatível).
- `GET /api/requisitos/{id}` devolve o requisito com `atributos`, `vinculos` e `relacoes` (usado pelo painel de edição na UI).

## Change request e impacto econômico
- **Change request** (IREB cap. 5): `requisito_mudancas` (proposta → aprovada/rejeitada) por requisito. `GET/POST /api/requisitos/{id}/mudancas` e `POST /{id}/mudancas/{mid}/decidir`; reusa o padrão de aprovação do PDM; UI no painel de edição do requisito.
- **Impacto econômico**: campos `custo_atual`/`custo_projetado`/`volume` no requisito; `economia = (custo_atual − custo_projetado) × volume`. `GET /api/requisitos/impacto?norma_id=` devolve economia por requisito + total; tela **Análise de impacto** (`impacto.js`) com tabela editável + gráfico Plotly. É a versão QMS do caso "$150→$50 × N" do Teamcenter (não é trade study de PLM/BOM).
- **Versionamento**: `requisito_versoes` guarda snapshot numerado (R01/R02…) dos campos do requisito — manual (`POST /{id}/versoes`) e automático ao aprovar uma mudança. `GET /{id}/versoes` lista o histórico (painel de edição).
- **Variantes**: campo `requisitos.variante` (rótulo de contexto) + tipo de relação `variante_de` (liga variante ↔ requisito base).

## Verificação
- `tests/test_requisitos.py` (CRUD, enums 422, tenancy 401/404, import/export CSV, variante), `tests/test_requisitos_rm.py` (prioridade, atributos, relações, tipo de vínculo, árvore, change request, impacto, regressão `/exportar`), `tests/check_requisitos.cjs` e `tests/check_impacto.cjs`.
- Regras `regrasnegocio/RG.md` (`RG-REQ-*`).
