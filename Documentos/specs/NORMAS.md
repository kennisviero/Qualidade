# NORMAS — Catálogo de Normas e Regulamentos (submódulo Requisitos)

Captura e organização de normas/regulamentos de **fontes diversas**, por empresa — o primeiro
pilar do baseline Siemens (`Requirements/TC_Requirements_MGT.pdf`: "understand... standards and
regulations from diverse sources" + "capture and organize"). Primeiro consumidor do motor de PDM.
Aditivo: não altera módulos existentes.

## Objetivo e limites
- Registrar normas/regulamentos com metadados e vincular o documento (PDF) versionado no PDM.
- Organizar por tipo de fonte, status e emissor, com busca.
- Fora desta fase: requisitos/cláusulas derivados, rastreabilidade, conformidade, parsing por IA (fases seguintes).

## Persistência
- `normas`: `id`, `empresa_id` (tenancy), `codigo` serial `NORMA-NNNN` `UNIQUE(empresa_id,codigo)`,
  `tipo_fonte` (`norma_tecnica|regulamento_legal|requisito_contratual|requisito_cliente|politica_interna|outro`),
  `titulo`, `identificador_externo` (ex.: `ISO 9001:2015`, `Lei 14.133/2021`), `emissor`, `edicao_versao`,
  `data_publicacao`, `data_vigencia`, `status` (`vigente|em_revisao|obsoleta`), `escopo`, `observacoes`,
  `documento_id` → `documentos_controlados` (`ON DELETE SET NULL`), `criado_por_id`, datas.
- Triggers `BEFORE DELETE` em `empresas` (cascata) e `usuarios` (set NULL).

## Operação
- Criar com `criar_documento=true` (padrão) gera, na mesma transação, um documento controlado `tipo='norma'`
  (via `create_documento_interno`) e vincula `documento_id`. O arquivo da norma é anexado/versionado no PDM.
- Editar atualiza só os metadados da norma; o documento segue o ciclo do PDM. Excluir remove a norma (o documento
  controlado permanece como objeto independente do PDM).

## API (`/api/normas`)
- `GET ''` (filtros `tipo_fonte|status|emissor|q`), `GET /{id}`, `POST ''`, `PUT /{id}`, `DELETE /{id}`.
- Leitura: `get_current_user`; escrita: `require_papel('admin','editor')`; tenancy por `scope`/`fetch_norma`.
- Validação de enums `tipo_fonte`/`status` (422).

## Verificação
- `tests/test_normas.py` (cria com/sem documento, filtros/update, validações 422, visualizador 403, tenancy 401/404)
  e `tests/check_normas.cjs` (menu/section, lista, detalhe sanitizado, vínculo PDM, visualizador sem escrita, reset).
- Regras em `regrasnegocio/RG.md` (`RG-NOR-*`).
