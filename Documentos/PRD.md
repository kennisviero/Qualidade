# Product Requirements Document (PRD): Gestão da Qualidade (Issues + PDCA)

## 1. Visão Geral e Filosofia do Produto

Aplicação web leve, rápida e intuitiva para equipes técnicas e de gestão **registrarem, tratarem e analisarem issues** (não conformidades, defeitos e ocorrências) em **ciclo fechado PDCA**. Cada **empresa** tem seu espaço isolado, e cada **usuário** autenticado acessa apenas o que seu papel permite.

Princípios do *Total Quality Management* (TQM):

- A história da ciência e da tecnologia é uma história de Controle de Qualidade (QC) — um processo contínuo de resolução de problemas.
- O TQM é a aplicação do método científico aos negócios: escolhe-se um problema importante, obtêm-se os fatos, analisa-se os fatos e descobre-se a verdade subjacente.
- Um engenheiro superior é naturalmente orientado ao Controle de Qualidade (QC).
- Os defeitos devem ser corrigidos na origem, pois medidas paliativas são inúteis.

## 2. Escopo Técnico

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| Backend | Python + **FastAPI** | Leve, rápido, tipado (Pydantic), Swagger automático |
| Servidor | Uvicorn | ASGI padrão, roda em `localhost` |
| Frontend | HTML5, CSS3, JavaScript (SPA estática) | Sem build, servido pelo FastAPI |
| Gráficos | **Plotly.js** | Renderização interativa no cliente (aba Análise) |
| Banco de Dados | SQLite (`sqlite3`) | Zero configuração, portátil |
| Hash de senha | `bcrypt` | Nunca armazenar senha em texto puro |
| Autenticação | Login + senha, sessão por cookie | Simples agora; evolutiva para JWT depois |
| Autorização | Papéis (`admin`/`editor`/`visualizador`) | Controle de acesso por rota |

**Decisões de design:**
- Framework: **FastAPI** (API JSON tipada, validação automática, serve estáticos).
- **Login simples agora, evolutivo depois** — sessão por cookie; camada de auth separada para trocar por JWT sem refazer o resto.
- **Superusuário global:** `admin` / senha `admin`, semeado no primeiro start.
- **Fluxo centrado em Issue** — as ferramentas (Ishikawa, 5 Porquês, Pareto, Análise de tendência) são **abas do ciclo PDCA da issue**, não módulos avulsos. Mermaid foi removido do frontend; Plotly permanece.

## 3. Requisitos Funcionais

### 3.1. Empresa (Multi-tenant)
- Criar, editar e desativar empresas (`razao_social`, `cnpj`, `ativo`). No frontend: editar (admin), ativar/desativar e excluir (superusuário, com confirmação).
- **Empresa desativada** (`ativo = 0`): seus usuários não conseguem logar e as sessões abertas passam a receber 401 ("Empresa desativada"). O superusuário não é afetado.
- Cada empresa é um **tenant isolado**: um usuário de uma empresa nunca vê dados de outra.
- Uma empresa possui **N usuários** (relação 1 : N).

### 3.2. Usuário e Autenticação
- Criar, editar e desativar usuários (vinculados a uma empresa). No frontend: editar (nome, email, papel, posição, setor, senha opcional), ativar/desativar (exceto o próprio usuário) e excluir (com confirmação). Desativar = `PUT` com `ativo = 0`; `DELETE` exclui o registro.
- Login e logout com usuário + senha; senha armazenada como hash bcrypt.
- Papéis: `admin` (gerencia empresa/usuários) · `editor` (cria/edita processos, issues, ações) · `visualizador` (somente leitura).
- Superusuário `admin`/`admin` com acesso global (imune ao filtro de empresa).

### 3.3. Setores e Processos
- Hierarquias: **Empresa(1)→Setor(n)** (CRUD `setores`) e **Empresa(1)→Processo(n)** (CRUD `processos`).
- `processos` tem **gestão**: guardião (`responsavel_id`), aprovador final (`aprovador_id`), `status` (rascunho/em_revisao/aprovado), histórico versionado em `revisoes` e fluxo de aprovação (`aprovado_por_id` + `aprovacao_em`).
- **Documentos do processo**: explorador de árvore **filesystem-first** em `Vault/{empresa}/{setor}/{processo}/` (endpoints `/arvore`, `/arquivos`, `/pastas`, `/arquivo`, `/objetos`).

### 3.4. Módulo Issue — Registro e Tratamento (ciclo PDCA)

Fluxo ISO 9001 (ação corretiva) em ciclo fechado PDCA, tela com **5 abas**, tenancy **empresa → issue → ação**.

**Abas:**
1. **Captura (Plan)** — setor, processo, **tipo**, **severidade**, **etapa_captura**, descrição (com transcrição TXT/PDF/DOCX), data, origem (interno/externo), produto, norma, reincidência + `status` (`registrado`/`em_investigacao`/`plano_acao`/`em_execucao`/`finalizado`) + anexos em `Vault/{empresa}/{codigo}/`.
2. **Contenção (Plan/Do)** — Bloqueio de Lote (4 blocos: rastreabilidade temporal, identificação, localização, responsabilidade) + decisão "investigar a causa?" SIM/NÃO → se SIM, checkbox Ishikawa / 5 Porquês (≥1 obrigatório).
3. **Investigação (Do)** — editor 6Ms (só se `usar_ishikawa`) e **5 Porquês** (só se `usar_porques`): numerado; se ambos marcados, cada porquê = 1 item do Ishikawa (sem repetição); senão resposta livre. Salva `causa_raiz`. A aba fica desabilitada enquanto `investigar_causa` for falso.
4. **Ação (Check/Act)** — plano 5W2H (`descricao`, `por_que`, `onde`, `como`, `quanto`, responsável, prazo, observação); criar ação é permitido em qualquer status (não há trava em `registrado`, pois sem investigação a issue não sai desse status de outra forma); **"Gerar ações do Ishikawa"** cria 1 ação por causa (loop de POSTs no cliente).
5. **Análise (Check)** — **Pareto automático por dimensão** (status/tipo/severidade/origem/produto/setor) e **tendência** de criação vs finalização por mês (Plotly).

**Regras:**
- `investigar_causa=false` → abas de investigação (Ishikawa/5 Porquês) desabilitadas (front + backend rejeita).
- `investigar_causa=true` → checkbox ≥1.
- **Status**: `registrado` → `em_investigacao` (ao salvar os 5 Porquês) → `plano_acao` (ao criar ação, só se o status atual for `registrado` ou `em_investigacao`; nunca regride) → `em_execucao` (quando a 1ª ação sai do backlog no kanban) → `finalizado`.
- **Finalizar**: só via `POST /finalizar` (o `PUT` da issue recusa `status=finalizado` com 422). Exige ao menos 1 ação, todas `finalizada`, `resultado_alcancado` não vazio e `nota_atingimento` (1–5) → `status=finalizado` (escala 1 não atingido · 2 pouco · 3 médio · 4 próximo · 5 100%).
- **Excluir**: uma transação SQL (acoes → ishikawa vinculado → issue) com rollback explícito em falha; depois do commit apaga `Vault/{empresa}/{codigo}/` e a do ishikawa.

**Kanban (Tarefas)**: quadro **global da empresa**, drag-and-drop entre colunas (`backlog`/`iniciada`/`em_andamento`/`em_revisao`/`finalizada`); sair do backlog define `data_inicio`.

**Transcrição/Anexos**: `POST /api/transcricao` (TXT/PDF/DOCX, sem áudio/OCR); anexos via explorador de arquivos em `Vault/{empresa}/{codigo}/` (mesmos endpoints do processo).

## 4. Requisitos Não Funcionais

- **Usabilidade:** responsiva, clara, sem poluição visual.
- **Portabilidade:** SQLite + Python — Windows/Linux/macOS.
- **Desempenho:** gráficos gerados em tempo real (Pareto/tendência).
- **Segurança:** senhas com hash bcrypt; autorização em toda rota; `visualizador` recebe 403 em escrita; isolamento total entre empresas.
- **Evolutividade:** camada de auth separada, papéis extensíveis, pronto para JWT/2FA no futuro.

## 5. Modelo de Dados (SQLite)

**`empresas`**
- `id` INTEGER PK · `razao_social` TEXT · `cnpj` TEXT · `ativo` INTEGER (0/1) · `criado_em` TEXT

**`setores`**
- `id` INTEGER PK · `empresa_id` INTEGER FK → empresas · `nome` TEXT · `criado_em` TEXT

**`usuarios`**
- `id` INTEGER PK · `empresa_id` INTEGER FK → empresas (coluna física, preenchida a partir do setor na criação/edição; NULL = superusuário) · `setor_id` INTEGER FK → setores (`ON DELETE SET NULL`) · `nome` TEXT · `email` TEXT UNIQUE · `senha_hash` TEXT · `papel` TEXT (`admin`/`editor`/`visualizador`) · `posicao` TEXT (Presidente/Diretoria/Gerente/Supervisor/Encarregado/Colaborador) · `ativo` INTEGER · `criado_em` TEXT

**`processos`**
- `id` INTEGER PK · `empresa_id` INTEGER FK NOT NULL · `setor_id` INTEGER FK NULL (campo de cadastro, `ON DELETE SET NULL`) · `nome` TEXT · `descricao` TEXT · `sintaxe` TEXT · `ativo` TEXT · `pasta` TEXT · `responsavel_id`/`aprovador_id` FK usuarios · `status` (rascunho/em_revisao/aprovado) · `criado_por_id` · `criado_em` · `atualizado_em` · **UNIQUE(empresa_id, nome)** (índice). A aprovação (`aprovado_por_id`, `aprovacao_em`) fica registrada em `revisoes`.

**`revisoes`**
- `id` INTEGER PK · `processo_id` FK (`ON DELETE CASCADE`) · `numero` INTEGER · `sintaxe` TEXT · `revisado_por_id` FK · `aprovado_por_id` FK · `criado_em` TEXT · `revisao_em` TEXT · `aprovacao_em` TEXT

**`issues`** (migração de `nao_conformidades`)
- `id` INTEGER PK · `codigo` TEXT (UNIQUE por empresa, `RNC-0001`) · `empresa_id` FK NOT NULL (tenancy direta) · `setor_id`/`processo_id` FK NULL · `pasta` TEXT
- `tipo` (default `nao_conformidade`) · `severidade` (default `media`) · `etapa_captura` TEXT
- Aba Captura: `descricao`, `data`, `origem` (interno/externo), `produto`, `norma`, `reincidencia`
- Bloqueio: `ultimo_ok_em`, `alarme_em`, `margem_seguranca_min`, `codigo_material`, `lote`, `ordem_producao`, `sn_inicio`, `sn_fim`, `linha_posto`, `status_estoque`, `posicao_estoque`, `operador_id`, `inspetor_id`, `motivo_bloqueio`
- `investigar_causa`/`usar_ishikawa`/`usar_porques` · `autorizado_por_id`/`autorizado_em`
- `ishikawa_id` FK · `porques` JSON (`[{numero, item_ishikawa, resposta}]`) · `causa_raiz`
- `resultado_esperado` · `resultado_alcancado` · `nota_atingimento` (1–5)
- `finalizado_em`/`finalizado_por_id` · `status` (registrado/em_investigacao/plano_acao/em_execucao/finalizado) · `criado_por_id` · datas

**`ishikawas`**
- `id` INTEGER PK · `setor_id` FK NOT NULL · `nome` TEXT · `efeito` TEXT · `ativo` TEXT · `descricao` TEXT · `categorias` JSON (nomes dos 6Ms) · `causas` JSON · `pasta` TEXT · `criado_em` TEXT · `atualizado_em` TEXT · UNIQUE(setor_id, nome)

**`acoes`**
- `id` INTEGER PK · `issue_id` FK `ON DELETE CASCADE` · `descricao` · `resultado_esperado` (coluna existente, não usada pela API) · `responsavel_id` FK · `prazo_limite` · `data_inicio` (NULL = backlog) · `status` (`backlog`/`iniciada`/`em_andamento`/`em_revisao`/`finalizada`) · `observacao` · `por_que`/`onde`/`como`/`quanto` · `ordem`

**`sessions`**
- `token` TEXT PK · `user_id` INTEGER FK → usuarios · `criado_em` TEXT · `expira_em` TEXT

**`projects`** e **`datasets`** (legado das ferramentas avulsas, mantidos; sem uso no frontend)
- `projects`: `id` · `empresa_id` FK · `nome` · `descricao` · `criado_em`
- `datasets`: `id` · `project_id` FK (`ON DELETE CASCADE`) · `nome` · `tipo` · `dados` · `criado_em`

## 6. API (resumo)

| Método | Rota | Descrição | Acesso |
|--------|------|-----------|--------|
| POST | `/api/auth/login` | Login | público |
| POST | `/api/auth/logout` | Logout | autenticado |
| GET | `/api/auth/me` | Dados do usuário logado | autenticado |
| GET/POST | `/api/empresas` | Listar/criar empresas | admin/superusuário |
| GET/PUT | `/api/empresas/{id}` | Detalhe/editar (inclui `ativo`) | admin (da própria empresa) |
| DELETE | `/api/empresas/{id}` | Excluir empresa (apaga a pasta no Vault) | superusuário |
| GET/POST | `/api/usuarios` | Listar/criar usuários | admin (GET: qualquer autenticado da mesma empresa) |
| PUT | `/api/usuarios/{id}` | Editar / desativar (`ativo = 0`) | admin |
| DELETE | `/api/usuarios/{id}` | Excluir usuário | admin |
| GET/POST | `/api/setores` | Listar/criar setores | autenticado / editor+ |
| PUT/DELETE | `/api/setores/{id}` | Editar/excluir setor | editor+ |
| GET/POST | `/api/processos` | Listar/criar processos | autenticado / editor+ |
| GET | `/api/processos/{id}` | Detalhe | autenticado |
| PUT/DELETE | `/api/processos/{id}` | Editar/excluir | editor+ |
| GET | `/api/processos/{id}/revisoes` | Histórico | autenticado |
| POST | `/api/processos/{id}/revisoes` | Criar revisão | editor+ |
| POST | `/api/processos/{id}/aprovar` | Aprovar revisão atual | editor+ |
| GET | `/api/processos/{id}/arvore`·`/arquivo` | Ler documentos do processo | autenticado |
| POST/DELETE | `/api/processos/{id}/arquivos`·`/arquivos/criar`·`/pastas`·`/objetos` | Upload, criar arquivo/pasta, excluir | editor+ |
| GET/POST | `/api/issues` | Listar/criar issues | autenticado / editor+ |
| GET | `/api/issues/{id}` | Detalhe | autenticado |
| PUT/DELETE | `/api/issues/{id}` | Editar (não aceita `status=finalizado`)/excluir | editor+ |
| GET | `/api/issues/kanban` | Kanban global de ações | autenticado |
| GET | `/api/issues/stats` | Pareto por dimensão | autenticado |
| GET | `/api/issues/trends` | Tendência criação vs finalização | autenticado |
| POST | `/api/issues/{id}/ishikawa` | Vincular Ishikawa | editor+ |
| PUT | `/api/issues/{id}/ishikawa` | Atualizar Ishikawa vinculado (merge de categorias) | editor+ |
| PUT | `/api/issues/{id}/porques` | Salvar 5 Porquês + causa raiz | editor+ |
| GET | `/api/issues/{id}/acoes` | Listar ações 5W2H | autenticado |
| POST | `/api/issues/{id}/acoes` | Criar ação 5W2H | editor+ |
| PUT/DELETE | `/api/issues/{id}/acoes/{aid}` | Editar/excluir ação | editor+ |
| PUT | `/api/issues/{id}/acoes/{aid}/status` | Mover no kanban (sair do backlog → `data_inicio`) | editor+ |
| POST | `/api/issues/{id}/finalizar` | Finalizar issue | editor+ |
| GET | `/api/issues/{id}/arvore`·`/arquivo` | Ler anexos da issue | autenticado |
| POST/DELETE | `/api/issues/{id}/arquivos`·`/arquivos/criar`·`/pastas`·`/objetos` | Upload, criar arquivo/pasta, excluir | editor+ |
| POST | `/api/transcricao` | Transcrever TXT/PDF/DOCX | autenticado |
| GET/POST, GET/PUT/DELETE | `/api/projects`, `/api/projects/{id}` | Legado (sem uso no frontend) | autenticado / editor+ |
| GET/POST, POST, DELETE | `/api/projects/{id}/datasets`, `.../datasets/csv`, `/api/datasets/{id}` | Legado (sem uso no frontend) | autenticado / editor+ |

## 7. Estrutura do Projeto

```
C:\Produttare\Qualidade\
  PRD.md  README.md  OPERACAO.md  iniciar.bat  requirements.txt
  Documentos\PRD.md
  app/
    main.py            # FastAPI + routers + estáticos + lifespan(init_db)
    db.py              # schema + migração (issues) + seed admin
    auth.py            # login/logout, hash bcrypt, papéis, dependência de usuário
    calculations.py    # pareto() (usado em /api/issues/stats); dispersao()/controle() legados
    docs.py            # pastas físicas + safe_rel, save/delete de arquivo
    security.py        # SafeModel (sanitização de entrada contra XSS)
    routers/
      auth.py
      empresas.py
      usuarios.py
      setores.py
      processos.py
      documentos.py    # documentos do processo (arvore/arquivos/pastas/arquivo/objetos)
      issues.py
      transcricao.py
      projects.py      # legado, sem uso no frontend
      datasets.py      # legado, sem uso no frontend
    static/            # index.html, css/style.css, js/app.js
  tests/
    conftest.py        # DB + docs temporários
    test_api.py  test_auth.py  test_hierarquia.py  test_security.py  test_calculations.py
    test_issues.py  test_processos.py  test_gestao.py  test_vault_arquivos.py
    test_criterios_aceite.py   # critérios da seção 9 + regras da issue
  logdev/              # log de desenvolvimento (<ddmmaa>log.md)
  data/qualidade.db    # gerado em runtime
  Vault/               # arquivos (empresa/setor/processo)
```

## 8. Roadmap de Implementação

1. Scaffold + multi-tenant (`empresas`, `usuarios`, `empresa_id`) + seed `admin`/`admin`.
2. Auth: login/logout/me, hash bcrypt, sessão por cookie, papéis.
3. CRUD de empresas, setores, usuários, processos + gestão do processo (revisões/aprovação).
4. Documentos filesystem-first (`Vault/{empresa}/{setor}/{processo}`).
5. Módulo Issue (antiga RNC): schema `issues`/`acoes`, router, transcrição, kanban, 5 abas PDCA.
6. Análise: Pareto por dimensão (`/issues/stats`) + tendência (`/issues/trends`).
7. Refatoração PDCA: remoção das ferramentas avulsas da UI (Fluxograma/Mermaid, Pareto, Dispersão, Carta de Controle, Ishikawa standalone), gestão/documents migram para a seção Processos, frontend reescrito.
8. Testes (auth, papéis, isolamento, issue/PDCA, documentos) + docs.
9. ✅ Fechamento PRD × código (08/10/2026): regras da issue (PUT não finaliza; criar ação não regride status; finalizar exige resultado e ≥1 ação; exclusão com rollback explícito), gráficos da Análise corrigidos, aba Investigação desabilitada sem `investigar_causa`, editar/desativar empresas e usuários no frontend, empresa desativada bloqueia acesso, testes dos critérios de aceite (`tests/test_criterios_aceite.py`).
10. Próximos (escopo em aberto): Dashboard e Consultas gerais; JWT; reset de senha/2FA; deploy.

## 9. Critérios de Aceite Globais

- `admin`/`admin` loga e acessa tudo.
- Usuário da empresa X não acessa dados da empresa Y (teste automatizado).
- `visualizador` recebe 403 em qualquer escrita.
- Senhas nunca em texto puro no banco.
- A issue percorre o ciclo fechado: captura → contenção → investigação → ação → análise/finalização (com nota 1–5).