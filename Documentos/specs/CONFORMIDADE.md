# CONFORMIDADE — Rastreabilidade e cobertura (closed-loop)

Vincula requisitos a controles (processo/issue/rnc/ação) e avalia conformidade, com matriz de
cobertura e lacunas em aberto (estilo gap-analysis). Fecha o ciclo "continuously verifying conformance"
do baseline. Aditivo: não altera `enquadramento_normativo`/`requisito_violado` (apenas referencia).

## Persistência
- `requisito_vinculos`: `id`, `empresa_id`, `requisito_id` (CASCADE), `alvo_tipo` (`processo|issue|rnc|acao`),
  `alvo_id`, `observacao`, `criado_por_id`, `criado_em`, `UNIQUE(requisito_id, alvo_tipo, alvo_id)`.
- `requisito_conformidade`: `id`, `empresa_id`, `requisito_id` (CASCADE), `processo_id` NULL (NULL = geral),
  `situacao` (`conforme|nao_conforme|nao_avaliado`), `evidencia`, `responsavel_id`, `avaliado_em`, `criado_por_id`.
- Triggers delete empresa (cascata) e usuário (set NULL) nas duas tabelas.

## API
- Vínculos (`/api/requisitos/{id}/vinculos`): `GET`, `POST` (valida alvo existente e **da mesma empresa**; 403 se de outra; 409 se duplicado), `DELETE /{vinculo_id}`.
- Conformidade (`/api/conformidade`): `POST` (upsert por requisito + processo opcional; valida situação/processo/responsável da empresa).
- `GET /api/conformidade/matriz?norma_id&empresa_id` → requisitos × situação + contagem de vínculos por alvo + **lacunas** (`sem_vinculo`, `nao_avaliados`, `nao_conformes`) + resumo.
- Leitura `get_current_user`; escrita `require_papel('admin','editor')`; tenancy por `scope`.

## Frontend
- Seção "Cobertura e Conformidade" (`app/static/js/cobertura.js`): seletor de norma, tabela editável de situação,
  adição/remoção de vínculos, resumo e **lacunas destacadas** (sem vínculo / não conforme). Escrita `editor-only`.

## Verificação
- `tests/test_conformidade.py` (vínculo valida empresa do alvo 403/404/409; conformidade enums 422; matriz/lacunas; tenancy 401/404) e `tests/check_cobertura.cjs`.
- Regras `regrasnegocio/RG.md` (`RG-RAS-*`, `RG-CNF-*`).
