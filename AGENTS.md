# Qualidade — Gestão da Qualidade em Ciclo Fechado (Issues + PDCA)

App web para registrar/tratar/analisar **issues** (não conformidades, defeitos, ocorrências) com ciclo fechado PDCA (Captura → Contenção → Investigação → Ação → Análise), baseado em TQM / ISO 9001. Multi-tenant (empresa) + login por usuário.

## Stack

- Backend: Python + FastAPI + Uvicorn
- Banco: SQLite (`sqlite3`), arquivo `data/qualidade.db` (ou env `QUALIDADE_DB`)
- Hash de senha: `bcrypt` (biblioteca `bcrypt`, não passlib)
- Frontend: SPA estática (HTML/CSS/JS + Plotly.js), servida pelo FastAPI em `/`

## Como rodar / testar

```powershell
cd C:\Produttare\Qualidade
pip install -r requirements.txt   # se necessário
python -m pytest -q               # 69 testes passam
uvicorn app.main:app --reload     # http://localhost:8000 (Swagger /docs)
```

Ou duplo clique em `iniciar.bat` (instala deps se faltar, abre navegador, sobe servidor).

## Acesso / Regras de negócio

- Superusuário inicial: email `admin` / senha `admin` (seed no primeiro start em `app/db.py::seed_admin`).
- Papéis: `admin`, `editor`, `visualizador`.
  - `admin` empresa (empresa_id preenchido) gerencia usuários da própria empresa.
  - `admin` com `empresa_id = NULL` = superusuário global (cria empresas, vê tudo).
  - `editor`: cria/edita processos, issues, ações.
  - `visualizador`: só leitura (403 em escrita).
- Tenancy: **Empresa(1)→Setor(n)→Usuário(n)**, 1 empresa : N usuários. Isolamento por `empresa_id` em `issues` (tenancy direta); `usuarios.empresa_id` é derivado do `setor_id`.
- Auth: **login simples agora, evolutivo depois** — sessão por cookie (`sessions` table, token httponly). Camada separada em `app/auth.py` para trocar por JWT/2FA sem refazer o resto.

## Estrutura

```
Qualidade/
  PRD.md  README.md  OPERACAO.md  iniciar.bat  requirements.txt
  Documentos/PRD.md            # PRD completo (empresa + usuários + segurança)
  app/
    main.py        # FastAPI + routers + estáticos + lifespan(init_db)
    db.py          # schema + migração (issues) + seed admin
    docs.py        # pastas físicas (empresa/setor/processo) + safe_rel, save/delete de arquivo
    auth.py        # hash bcrypt, sessão, get_current_user, require_papel, is_superuser
    calculations.py # pareto() (usado por /api/issues/stats)
    routers/       # auth, empresas, usuarios, setores, processos, issues, transcricao
    static/        # index.html, css/style.css, js/app.js
  Vault/      # repositório físico de arquivos (env QUALIDADE_DOCS)
  tests/           # conftest (DB+docs temp), test_issues, test_processos, test_gestao, test_api, test_auth, etc.
```

## Decisões travadas

- **Regra de ouro: nunca alterar uma feature que já está funcionando, em hipótese alguma, em detrimento de outra correção — exceto com autorização explícita do usuário.** Correções devem ser aditivas (não quebrar comportamento existente); se uma correção exigir mudar algo que já funciona, pedir autorização antes.
- FastAPI (não Flask/Django).
- Login/senha simples, senha `admin`/`admin`, bcrypt — **evoluir depois** (JWT, refresh, reset, 2FA).
- Papéis `admin`/`editor`/`visualizador` (enum extensível).
- Hierarquia **Empresa(1)→Setor(n)→Usuário(n)** (sem N:N por ora): `usuarios.setor_id` (FK `ON DELETE SET NULL`), `empresa_id` derivado do setor na criação/edição. Atributo **`posicao`** com enum fixo: `Presidente`, `Diretoria`, `Gerente`, `Supervisor`, `Encarregado`, `Colaborador` (vazio = não informada; valor fora do enum → 422). Superusuário global continua com `empresa_id = NULL`.
- **Processos**: **Empresa(1)→Processo(n)**. O **setor é um campo de cadastro** em `processos.setor_id` (FK `ON DELETE SET NULL`), **não faz parte da chave** — `UNIQUE(empresa_id, nome)`. Hierarquias: **Empresa(1)→Setor(n)** (CRUD `setores`) e **Empresa(1)→Processo(n)** (CRUD `processos`).
- **Gestão do processo**: `processos` tem guardião (`responsavel_id`), aprovador final (`aprovador_id`), `status` (rascunho/em_revisao/aprovado) e `criado_por_id`. A sintaxe é versionada na tabela `revisoes` (cada "Salvar" cria revisão; "Aprovar" grava `aprovado_por_id` + `aprovacao_em`). Responsáveis vinculados a usuários cadastrados. **No frontend, a gestão e os documentos do processo moram na seção "Processos".**
- **Documentos**: explorador de árvore **filesystem-first** — raiz = pasta física `Vault/{empresa}/{setor}/{processo}/` (com subpastas; `processos.pasta` guarda o caminho criado). Endpoints: `/arvore`, `/arquivos` (upload por subpasta), `/arquivos/criar`, `/pastas`, `/arquivo?caminho`, `/objetos?caminho` (delete recursivo), com `safe_rel` bloqueando path traversal. **Sem tabela `documentos`** (autor não rastreado; data = mtime do arquivo). Renomear entidade não move a pasta. **Excluir processo/setor/empresa apaga a pasta física correspondente** (`Vault/.../processo`, `Vault/.../setor`, `Vault/empresa`).
- `GET /api/usuarios` liberado para qualquer autenticado (mesma empresa) — usado nos dropdowns de guardião/aprovador/operador/inspetor.

## Módulo Issue — Registro e Tratamento (especificação completa)

Fluxo ISO 9001 (ação corretiva) em ciclo fechado PDCA. Tela com **5 abas**. Tenancy: **empresa → issue → ação**.

### Estrutura (5 abas PDCA)
1. **Captura (Plan)** — setor, processo, **tipo**, **severidade**, **etapa_captura**, descrição (com transcrição TXT/PDF/DOCX), data, origem (interno/externo), produto, norma, reincidência + `status` (`registrado`/`em_investigacao`/`plano_acao`/`em_execucao`/`finalizado`) + **Anexos** em `Vault/{empresa}/{codigo}/`.
2. **Contenção (Plan/Do)** — Bloqueio de Lote (4 blocos) + decisão "investigar a causa?" SIM/NÃO → se SIM, checkbox `[ ] Ishikawa` `[ ] 5 Porquês` (≥1 obrigatório).
3. **Investigação (Do)** — editor 6Ms (só se `usar_ishikawa`) e **5 Porquês** (só se `usar_porques`): numerado sequencial; se ambos marcados, cada porquê = 1 item do Ishikawa (sem repetição); senão resposta livre. + `causa_raiz`.
4. **Ação (Check/Act)** — ações (5W2H); liberada quando `status != registrado`. "Gerar ações do Ishikawa" cria 1 ação por causa. **Finalizar** exige todas as tarefas `finalizada` + resultado + nota.
5. **Análise (Check)** — **Pareto automático por dimensão** (status/tipo/severidade/origem/produto/setor) e **tendência** criação vs finalização (Plotly).

### Bloqueio de Lote (Aba 2) — 4 blocos
- Rastreabilidade temporal: `ultimo_ok_em`, `alarme_em`, `margem_seguranca_min`.
- Identificação: `codigo_material` (SKU/PN), `lote`, `ordem_producao`, `sn_inicio`, `sn_fim`.
- Localização: `linha_posto`, `status_estoque`, `posicao_estoque`.
- Responsabilidade: `operador_id`, `inspetor_id` (FK usuarios), `motivo_bloqueio`.

### Tabelas
- `issues`: `id`, `codigo` (UNIQUE por empresa, `RNC-0001`), `empresa_id` NOT NULL (tenancy direta), `setor_id`/`processo_id` NULL, `pasta`, `tipo` (default `nao_conformidade`), `severidade` (default `media`), `etapa_captura`, campos das abas, `investigar_causa`/`usar_ishikawa`/`usar_porques`/`autorizado_por_id`/`autorizado_em`, `ishikawa_id` FK, `porques` JSON (`[{numero, item_ishikawa, resposta}]`), `causa_raiz`, `resultado_esperado` (do plano), `resultado_alcancado`, `nota_atingimento` (1–5), `finalizado_em`/`finalizado_por_id`, `status`, `criado_por_id`, datas.
- `acoes`: `issue_id` FK (ON DELETE CASCADE), `descricao`, `responsavel_id`, `prazo_limite`, `data_inicio` (NULL = backlog), `status` (`backlog`/`iniciada`/`em_andamento`/`em_revisao`/`finalizada`), `observacao`, `por_que`/`onde`/`como`/`quanto`, `ordem`.

### Regras
- `investigar_causa=false` → abas 1 e 2 do investigação (Ishikawa/5 Porquês) desabilitadas (frontend + backend rejeita criar/vincular).
- `investigar_causa=true` → checkbox ≥1.
- **`em_execucao`**: a issue entra em `em_execucao` automaticamente quando a 1ª ação sai do backlog (kanban). Antes, criar ação seta `plano_acao`.
- **Finalização**: todas as tarefas `finalizada` → botão "Finalizar issue" **força** `resultado_alcancado` + `nota_atingimento` (1–5) → `status=finalizado`. Escala: 1 não atingido · 2 pouco · 3 médio · 4 próximo do esperado · 5 100%.
- **Exclusão da issue**: em UMA transação SQL (apaga `acoes` → ishikawa vinculado → issue) com **rollback** em falha; após commit apaga pastas físicas (`Vault/{empresa}/{codigo}/` e a do ishikawa).

### Kanban + Análise
- **Kanban (Tarefas)**: quadro **global da empresa**, drag-and-drop entre colunas (backlog/iniciada/em_andamento/em_revisao/finalizada). Sair do backlog define `data_inicio`. Hierarquia empresa → issue → ação (1 ação : 1 issue).
- **Análise**: `GET /api/issues/stats` (Pareto por dimensão via `calculations.pareto`) e `GET /api/issues/trends` (criação vs finalização por mês). **Dashboard e Consultas gerais**: implementar depois (escopo em aberto).

### Transcrição / Anexos
- Transcrição: TXT/PDF/DOCX (`pypdf` + `python-docx`). **Sem áudio e sem OCR.** Endpoint `POST /api/transcricao` → `{ texto }`.
- Anexos: explorador de arquivos em `Vault/{empresa}/{codigo}/` (mesmos endpoints do processo).

### Reset + seed
- Reset = apagar `data/qualidade.db` **e limpar `Vault/`**.
- Seed: `admin`/`admin` (superusuário, empresa NULL), empresa 1 "Empresa teste", `carlos`/`carlos` (admin da empresa 1).

## Próximos passos possíveis

- Dashboard e Consultas gerais (escopo em aberto).
- Editar/desativar usuários e empresas no frontend (backend já tem PUT/DELETE).
- Trocar cookie por JWT quando precisar de API pública.
- Reset de senha / 2FA.
- Deploy (hoje roda só localhost).
- Mover/sincronizar pastas ao renomear empresa/setor/processo (hoje intencionalmente não move).

## Notas de sessão (2026-08-14)

- PRD gerado em `Documentos/PRD.md`; app completa (7 módulos + auth + multi-tenant) com 15 testes passando.
- Endpoints verificados via HTTP: login → cookie → `/api/auth/me`; rota sem sessão → 401.
- `tests/conftest.py` define `QUALIDADE_DB` com uuid para evitar conflito entre runs.
- **Sessão atual**: gestão do processo (guardião/aprovador/status/revisões/aprovação) + repositório de documentos com hierarquia física `Vault/{empresa}/{setor}/{processo}`. `conftest.py` também define `QUALIDADE_DOCS` temp. 21 testes passando.

## Notas de sessão (2026-08-15)

- **Removidos do sistema**: módulo Folha de Verificação e módulo Histograma. Menu renumerado: 1 Fluxograma · 2 Ishikawa · 3 Pareto · 4 Dispersão · 5 Carta de Controle.
- **Planejado**: módulo RNC. Dashboard e Consultas ficaram para depois.
- Testes: 53 passando após as remoções.

## Notas de sessão (2026-08-15 — tarde)

- **Módulo RNC implementado por completo** (back-end + frontend + testes):
  - `db.py`: tabelas `nao_conformidades` e `acoes` + seed `seed_demo`.
  - `docs.py`: `build_rnc_pasta` (`Vault/{empresa}/{codigo}/`).
  - `app/routers/nao_conformidades.py`: CRUD completo, 5 abas, kanban, finalização, exclusão transacional, anexos.
  - `app/routers/transcricao.py`: `POST /api/transcricao`.
  - Frontend: menu "6. RNC", 5 abas, kanban, anexos, transcrição.
  - Testes: `tests/test_rnc.py` (11 testes). **64 testes passando.**

## Notas de sessão (2026-08-15 — noite)

- **Reestruturação hierárquica**: `processos` agora é **Empresa(1)→Processo(n)**; Ishikawa standalone removido do menu (funcionalidade vive na aba 3 da RNC); opção "Projeto" removida da UI; RNC criável por superusuário via `empresa_id`.
- Testes: 65 passando.

## Notas de sessão (2026-09-15) — Refatoração para Issue + PDCA

Autorização explícita do usuário para remover da UI as ferramentas independentes ("fica somente a ISSUE") e reorganizar o fluxo em **PDCA**. Decisões aplicadas:

- **Removidos da UI**: Fluxograma (Mermaid), Pareto, Dispersão, Carta de Controle e o menu RNC standalone. Sidebar agora: **Empresas → Setores → Processos → Usuários → Issues**. Mermaid e `fluxo-editor.js` removidos; Plotly mantido (aba Análise).
- **Issues** (novo rótulo do antigo RNC, código ainda `RNC-XXXX`): 5 abas PDCA — 1 Captura, 2 Contenção, 3 Investigação (Ishikawa + 5 Porquês), 4 Ação, 5 **Análise** (nova: Pareto por dimensão + tendência via `GET /api/issues/stats` e `/trends`).
- **Backend**: tabela `nao_conformidades` renomeada para `issues` (migração `_migrar_nao_conformidades` em `init_db`; preserva códigos serial via `sqlite_sequence`); `acoes.nao_conformidade_id` → `acoes.issue_id`; novas colunas `tipo` (default `nao_conformidade`), `severidade` (default `media`), `etapa_captura`; novo status `em_execucao` (setado quando a 1ª ação sai do backlog). Prefixo `/api/issues`; `PUT /api/issues/{id}/ishikawa` (update do ishikawa vinculado, merge de `categorias`). Removidos routers `nao_conformidades`, `ishikawas`, `charts` e endpoint `/api/setores/{id}/ishikawas/arvore`.
- **Processos no frontend**: a **gestão do processo** (guardião/aprovador/status/revisões/aprovação) e os **documentos do processo** migraram da seção Fluxograma para a seção **Processos** (painel aberto ao clicar no processo).
- **Testes**: 54 passando. Código back-end intacto para os módulos restantes (auth, tenacidade, segurança, documentos).
- Reset DB+Vault **não executado** (dados preservados; migração aplica em runtime no próximo `init_db`).

## Notas de sessão (2026-10-10) — Issue, RNC e Kanban

- A Issue deve nascer com dados objetivos para futura RNC: data/hora de detecção; autor/cargo do usuário autenticado; setor ou processo afetado; comportamento esperado e observado; evidências; impacto/gravidade; ação emergencial; local e forma de detecção. `ambiente` não traz o sufixo "(TI)". Impacto e envolvidos/afetados são picklists na UI. O código único é gerado no salvamento. Os campos e validações estão em `app/routers/issues.py` e `app/db.py`.
- O botão **Nova Issue** abre o formulário da aba Captura; a criação efetiva ocorre em **Salvar registro** após validação. Captura e Contenção permanecem visíveis. Não ocultar nem remover essas abas ou seus campos do banco. A migração destrutiva anterior foi removida; a inicialização do banco deve preservar os dados existentes.
- A promoção para RNC tem código próprio vinculado à Issue de origem e exige criticidade maior/menor, enquadramento normativo/contratual, origem do gatilho, contenção definitiva com responsável/data-hora, disposição inicial, líder, equipe de investigação com pelo menos duas pessoas, metodologia, prazos de análise/plano/eficácia e auditor da eficácia. Endpoint `POST /api/issues/{id}/emitir-rnc`.
- Layout atual: formulário de Issue à esquerda, largura máxima de 1180px; Kanban à direita no espaço restante. Cinco raias lado a lado, sem rolagem horizontal: `backlog`, `iniciada`, `em_andamento`, `em_revisao`, `finalizada`. Títulos visíveis: **Backlog**, **Início**, **Em andamento**, **Revisão**, **Finalizado**. Os títulos são centralizados, fonte 12px, sem altura mínima artificial; cartões compactos, fonte 12px. Detalhes completos no tooltip do cartão. Preservar essas decisões ao ajustar CSS.
- Em 2026-10-10, a base ativa `data/qualidade.db` foi limpa a pedido do usuário: 7 issues e 2 sessões removidas, mantendo 1 empresa, 1 setor e 3 usuários. Tabelas operacionais continuam definidas, porém vazias. `Vault/` não foi apagado. Cópia anterior em `data/backups/qualidade_antes_limpeza_20261011T012209720791Z.db` (timestamp UTC). As 7 issues daquela cópia já tinham campos de Captura vazios.
- Verificação após restauração do fluxo: `python -m pytest -q` → **69 passed**; `node --check app/static/js/app.js` sem erro. Alterações posteriores foram apenas CSS/rótulos do Kanban. Este diretório não possui repositório Git; não houve commit.
