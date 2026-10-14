# Qualidade — Gestão da Qualidade em Ciclo Fechado (Issues + PDCA)

## Base didática autorizada (2026-10-14)

- Adicionado 3-Diagrama de Dispersão em Ferramentas. Filtros e elegibilidade de Pareto/Histograma, seleção de dois eixos, pares numéricos do mesmo registro, Pearson quando aplicável, contagens de exclusões, tabela por clique e Consultar IA com snapshot assinado. Unidades/moedas compatíveis e números exibidos com duas casas; sem inferência de causalidade. Operação em `documentos/specs/DISPERSAO.md`.

- Consulta textual das ferramentas com DeepSeek define `thinking.type=disabled` explicitamente, conforme documentação oficial do `deepseek-flash`, que habilita thinking por padrão. Ajuste visa resposta vazia ao atingir limite de saída, sem aumentar tokens nem alterar triagem JSON. Teste simulado verifica parâmetros de ambos os fluxos; sem nova chamada real ao provedor.

- Consulta IA das ferramentas preserva texto interrompido por limite de saída (`finish_reason=length`), identificando resposta parcial na interface. Sem texto ou filtro de conteúdo recebem mensagens específicas. Triagem JSON continua estrita; nenhuma repetição automática/chamada real na verificação.

- Padrão autorizado para todas as ferramentas: Consultar IA abre instruções editáveis e envia prompt + dados da análise somente após Enviar à IA. Componente compartilhado em `ferramentas_ia.js`; snapshot assinado por empresa/usuário, acessos LLM existentes, saída textual. Aplicado a Pareto/Histograma; novas ferramentas devem seguir o mesmo fluxo. Operação em `documentos/specs/CONSULTA_IA_FERRAMENTAS.md`. Sem chamada real ao provedor durante implementação/verificação.

- Ferramentas numeradas em 1-Pareto e 2-Histograma. Histograma reutiliza filtros/tenancy/elegibilidade de Pareto, com medidas temporais de Issues abertas sem RNC e medidas temporais/impacto das RNCs. Intervalos iguais automáticos/manuais, estatísticas e consulta por intervalo. Consulta somente leitura `/api/ferramentas/histograma`; operação em `documentos/specs/HISTOGRAMA.md`. Radios de cada ferramenta isolados por formulário para preservar Pareto.

- Estratificação do Pareto autorizada: base Issues somente `cadastrada`/`em_tratamento`, sem `finalizado_em` e sem RNC vinculada. Exclusão aplicada no backend antes de opções/filtros/totais/detalhamento; vínculo com RNC ocultado na tela. Base RNC mantém análise própria. Testes de filtros, exclusão de fechadas/vinculadas, status inconsistente com RNC, tenancy e interface passaram.

- Implementado menu Ferramentas → Pareto, com radio buttons Issues/RNCs, filtros por empresa/período/contexto, agrupamento e medidas. Categoria usa o campo factual `o_que` da Issue (snapshot na RNC), sem nova inferência ou alteração dos dados. RNC admite quantidade/horas/prejuízo com unidade/moeda compatível; ausências exibidas separadamente. Endpoint autenticado somente leitura `/api/ferramentas/pareto`, com tenancy. Operação em `documentos/specs/PARETO.md`; verificações em `tests/test_pareto.py` e `tests/check_pareto.cjs`.

- Toda RNC criada deve ter uma Issue de origem; nas cargas didáticas, criar a Issue antes de emitir a RNC pelo serviço existente. Nunca inserir RNC isolada.
- Adicionadas 40 Issues simuladas (ISSUE-0038 a ISSUE-0077), das quais 30 originaram RNC-2026-002 a RNC-2026-031; 10 ficaram abertas. Adicionadas 30 ações 5W2H, 30 observações e 30 pendências. Dados identificados por `SIM-FERR-20261014`; registros anteriores preservados.
- Carga idempotente em `_popular_ferramentas.py`: ensaio em memória sem argumentos; `--apply` grava após backup. Integridade/FKs, renderização dos objetos pela API e preservação das linhas anteriores verificadas antes do commit. Backup: `data/backups/qualidade_antes_ferramentas_20261014T125345103801Z.db`.
- Medições didáticas em `documentos/exemplos_ferramentas/amostras_simuladas.json`; orientações em `documentos/exemplos_ferramentas/README.md`. Nenhuma chamada LLM, aprovação ou conclusão de RNC realizada.

## Atualização autorizada (2026-10-11) — campos duplicados da Issue

- A pedido do usuário, restauradas as larguras anteriores do formulário RNC e matriz 5W2H, com rolagem horizontal quando necessária. Exclusão dos anexos e cartões do Kanban exibindo somente código permanecem.

- Investigação RNC permite excluir evidências com confirmação, removendo arquivo e metadados; valida papel/empresa/RNC não concluída e mantém metadados em falha física. Kanban da seção RNC filtra ações vinculadas a RNC e exibe apenas código, mantendo descrição no tooltip e comportamento da tela Issue. Layout RNC prioriza formulário e reserva 220–280px ao Kanban; larguras mínimas e rolagem horizontal do workspace/matriz removidas, com colunas 5W2H proporcionais.

- Investigação RNC ampliada sem bloco 6M: observação temporal, localização, sintomas/condições, operadores/equipes, impacto acumulado (quantidade/unidade, horas, valor/moeda/período). Observações persistidas em `rnc_observacoes`; hipóteses com testes/responsável/data/resultado/conclusão em `rncs.investigacao_json`. Evidências por upload na aba: arquivos físicos no Vault da Issue vinculada, metadados em `rnc_evidencias`, acesso por `/api/rncs/{id}/evidencias`, limite 20 MB. Upload preserva rascunhos; arquivos homônimos são separados por UUID. Valida tenancy/usuários, datas, valores não negativos e permissões; falha de gravação remove o arquivo recém-criado. Migração aplicada sem alterar 37 Issues, 1 RNC, 1 ação e 3 usuários; backup `data/backups/qualidade_antes_rnc_abas_20261011T235916086032Z.db`.
- Verificação da ampliação da Investigação: 130 testes backend passaram; verificações SPA de abas, salvamento, upload, filtro e seleção passaram. Arquivos reais de evidência não foram adicionados à base ativa durante os testes.

- Filtro RNC aceita curingas `*` (qualquer sequência) e `?` (um caractere). Com curingas, compara o padrão completo com cada código/descrição; sem curingas, mantém busca por trecho. Acentos/maiúsculas ignorados e metacaracteres de regex tratados literalmente. Exemplos: `RNC-2026-*`, `ISSUE-000?`, `*falha*`.

- Filtro textual ao lado do seletor RNC por código RNC/Issue ou descrição, insensível a acentos/maiúsculas. Plano de ação convertido em matriz: sete colunas 5W2H, observações, status e salvar por linha; novas linhas podem ser incluídas/descartadas antes de salvar. Persistência usa `acoes.rnc_id` e campos existentes; atualizar linha mantém rascunhos das demais, invalida aprovação e atualiza Kanban. Status das linhas acompanha mudanças de raia.

- Cabeçalho RNC apresenta Status no Kanban abaixo da consulta da Issue de origem. Atualiza após movimentação de cartões, sem reconstruir o formulário/perder rascunhos. Quando tarefas da RNC estão em raias diferentes, mostra raias e quantidades. Status do ciclo de vida continua separado. Verificação SPA cobre movimentação e preservação de campo não salvo.

- Metodologias da Investigação da RNC agora permitem múltipla seleção de 5 Porquês/Ishikawa/FMEA. Lista persistida em `rncs.metodologias_json`, migrada da metodologia anterior; API aceita `metodologias`, elimina duplicatas e valida opções. Coluna singular preservada para compatibilidade. Migração aplicada e seleção/salvamento verificados.

- Remoção autorizada de 5 Porquês e Causa raiz da aba 3 da RNC: controles removidos, coluna `rncs.causa_raiz` eliminada e chave `porques` removida de `rncs.investigacao_json`; notas de análise e dados de investigação da Issue preservados. Backup `data/backups/qualidade_antes_rnc_abas_20261011T232803640464Z.db`. Migração idempotente e salvamento da aba verificados. Abas específicas serão definidas posteriormente.

- Impacto/ambiente da RNC são picklists editáveis com as opções da Issue. Colunas próprias em `rncs`, inicializadas dos fatos preservados; salvar não altera o snapshot original. Migração aplicada à RNC-2026-001 mantendo Alto/Homologação e snapshot intacto. Verificados formulário, persistência e rejeição de opções inválidas.

- RNC: abas Registro, Contenção, Investigação, Plano de Ação e Pendências, editáveis por admin/editor. `/api/rncs` lista/consulta/edita com tenancy; emitente/responsável e aprovador são usuários da própria empresa. Contenção ganha ação imediata, prazo, conclusão e validador; investigação tem causa raiz e conteúdo JSON próprio. Ações 5W2H vinculadas por `acoes.rnc_id`, aprovador/usuário/data de aprovação persistidos; alteração do plano invalida aprovação. Pendências próprias com responsável/prazo e conclusão/reabertura.
- Fatos da Issue copiados na emissão em `rncs.fatos_snapshot_json`, sem edição pela API. RNC histórica migrada com snapshot da triagem quando disponível e complemento da Issue atual, origem explicitada. Migração aplicada preservando 37 Issues, 1 RNC, 1 ação e 3 usuários; backup `data/backups/qualidade_antes_aplicar_abas_rnc_20261011T231032190503Z.db`. Ciclo de seis status e notificações continuam pendentes.
- Verificação das abas RNC: suíte completa com 127 testes passando; scripts `check_rnc_tabs.cjs`, `check_rnc_menu.cjs` e `check_issue_selecao.cjs` passaram. Operação em `Documentos/specs/OPERACAO_RNC.md`.

- A pedido do usuário, RNC histórica `RNC-2026-001` (Issue ID 6) recebeu ação ID 1 no Backlog, sem data de início. Backup `data/backups/qualidade_antes_backlog_rnc_20261011T224706938327Z.db`; dados da RNC e status da Issue preservados.

- Emissão de nova RNC cria automaticamente uma ação de tratamento no Backlog, com início vazio, líder/prazo de análise se informados, na mesma transação da RNC e fechamento da Issue. Geração idempotente não duplica o cartão. Kanban retorna `rnc_codigo` e o exibe quando vinculado; código da Issue permanece disponível. RNCs históricas não foram alteradas.

- Tela RNC reorganizada conforme padrão da Issue: cabeçalho com código/status e consulta de origem; blocos de identificação, ocorrência, enquadramento/contenção, responsáveis, investigação e prazos em grids 2/3 colunas. Campos de consulta readonly, datas formatadas, seletor compacto e Kanban à direita preservados.

- Menu retrátil pelo botão no cabeçalho, com preferência local persistida. Nova seção RNC lista registros emitidos por empresa e permite consultar dados e Issue de origem; Kanban global existente também é renderizado à direita nessa seção, mantendo cinco raias e movimentação vigente. Layout estreito preserva lado a lado com rolagem horizontal.

- Complemento da RNC: usuário autorizou remover Origem do gatilho da tela e tornar todos os demais campos opcionais na emissão, incluindo responsáveis, classificação, equipe e prazos. API aceita complemento vazio; valida enums e tenancy de usuários quando informados. Coluna e valores históricos de origem preservados para compatibilidade. Emissão continua fechando a Issue e exigindo aprovação explícita na seleção.

- Prompt padrão flexibilizado a pedido do usuário (`triagem-rnc-v2`): triagem preliminar aceita expectativa descrita, suporte factual textual e cenários simulados identificados na justificativa; não exige norma formal/anexo. Pendências devem constar na justificativa, preservando proibição de inventar dados e aprovação humana da emissão. Histórico anterior preservado.

- API DeepSeek adicionada ao adapter e ao cadastro: host `api.deepseek.com`, Chat Completions/JSON e `max_tokens`. Acesso 2 corrigido de página de chaves/modelo Coder para `https://api.deepseek.com` e `deepseek-flash`, conforme documentação oficial consultada; chave preservada. Backup `data/backups/qualidade_antes_deepseek_20261011T215627678349Z.db`. Testes com transporte simulado; chamada real não executada.

- Base de homologação: usuário autorizou ajustar dez Issues abertas para testar critérios de RNC. Atualizadas ISSUE-0002, 0005, 0008, 0011, 0014, 0017, 0020, 0023, 0026 e 0029 com requisitos específicos, desvios e evidências textuais detalhadas, explicitamente simuladas. Status cadastrada preservado; nenhuma RNC emitida, nenhum resultado histórico alterado. Backup `data/backups/qualidade_antes_exemplos_triagem_20261011T195913836662Z.db`. Resultado de uma nova chamada à IA ainda não verificado.
- Compatibilidade OpenRouter: catálogo oficial consultado antes da chamada; `response_format` só enviado se suportado, limite de saída respeita o máximo do modelo. Ling 3.1 Flash não anuncia JSON mode; instrução JSON e validação estrita do backend preservadas. Verificação real do lote da análise #1 (8 Issues) retornou HTTP 429 após ajuste; nenhuma Issue/RNC alterada e nenhuma repetição automática realizada.
- Clique no envio da seleção: único acesso LLM ativo selecionado automaticamente (continua editável). Botão desabilita apenas durante processamento; formulário usa `novalidate`, com validação explícita de acesso, quantidade (1–20) e prompt no handler, para exibir a pendência em vez de impedir o clique silenciosamente. Teste da SPA cobre lote de 18 Issues e acesso ausente. Servidor ativo confirmou endpoint do prompt e um acesso ativo na empresa 4.
- Progresso da análise: interface exibe Enviando para a IA, Aguardando a IA processar e Recebendo dados da IA, destacando a etapa atual e marcando as concluídas. Worker persiste `parametros_json.etapa`; adapter sinaliza espera antes da chamada HTTP e recebimento após resposta de sucesso. Status finais/erros e enum original das análises permanecem preservados; nenhuma migração de schema necessária.
- Envio à IA: geração de UUID funciona também em HTTP sem `crypto.randomUUID`; falhas e andamento aparecem junto ao botão. Prompt editável antes do envio, restauração do padrão e texto exato persistido no histórico (`parametros_json.prompt_text`), usado pelo worker com validação de hash. OpenRouter aceito com base `https://openrouter.ai/api/v1`; URL antiga da página de chaves corrigida na base ativa após backup, preservando chave/modelo. Testes do provedor usam transporte simulado.
- Selecionar para RNC: dois blocos lado a lado, com três colunas de Issues à esquerda e três colunas de candidatas à direita. Área direita fica em branco até a resposta da IA. Cartões mostram tempo desde o cadastro da Issue (`criado_em`). Cartões e controles compactos, fonte 11px; complemento de RNC em uma coluna dentro da candidata. Em telas estreitas o workspace permite rolagem horizontal preservando as seis colunas.
- Checkboxes dos cartões de seleção/candidatas ficam no canto superior direito, 22px. Consulta da Issue por duplo clique no código em azul escuro; Enter também abre para acesso por teclado. Botão Consultar removido dos cartões.

- Implementado submenu Selecionar para RNC para admin/editor. `/api/issues/selecao`: elegíveis paginados, opções LLM sem chave, usuários da empresa, histórico, solicitação/consulta de análises e geração idempotente. Quatro tabelas aditivas preservam snapshots/justificativas e vínculos. Worker persistido no SQLite, sem lock de escrita quando ocioso, sem transação durante chamada externa; chamada só ocorre após solicitação explícita. Primeiro schema faz backup de base existente.
- Emissão extraída em `app/services/rnc_emissao.py`, preservando validações e fechamento vigente. Novo checklist exige complemento dos obrigatórios de RNC, separa criticidade sugerida da classificação maior/menor e admite pendências por item com rollback. IDs de Issues removidas ficam nulos no histórico; snapshots permanecem. Adapter Chat Completions/JSON, hosts autorizados e nenhuma credencial no frontend. Operação descrita em `documentos/specs/OPERACAO_Selecao_issues.md`.
- Verificação da implementação: suíte completa com 108 testes passando; checklist/campos/geração/reset da SPA verificados por `node tests/check_issue_selecao.cjs`. Migração aplicada à base ativa, preservando 37 Issues, 3 usuários e 1 empresa; backup `data/backups/qualidade_antes_triagem_20261011T180456226369Z.db`. Testes usaram LLM simulado, sem chamadas reais ao provedor.

- Menu Configuração (administradores): CRUD de acessos LLM por empresa em `/api/configuracao/llm`. Tabela `llm_acessos`: nome, provedor, modelo, URL base, chave, ativo e datas. Consultas não retornam a chave; edição com chave vazia preserva a existente. Cadastro não realiza chamadas ao provedor. Chaves ficam armazenadas no SQLite e somente o backend as lê.

- Captura: lista de cartões abertos substituída por seletor compacto; Nova Issue, KPIs, seletor e formulário ficam na coluna esquerda. Kanban permanece na coluna direita desde o topo, inclusive em telas pequenas (rolagem horizontal do workspace quando necessário).

- Dashboard também apresenta barras empilhadas por envolvidos/afetados, ambiente e autor do registro. Considera cadastradas, em tratamento e fechadas de todos os períodos, por empresa selecionada; sem filtro mensal nessas distribuições, conforme correção do usuário. Autores são agrupados pelo ID escolhido (fallback criador), evitando juntar homônimos. Dados ausentes aparecem como Não informado.

- Submenu de Issues: Capturar, Dashboard e Limpeza da base de Issues (admin). Dashboard reúne cinco KPIs, status, impacto, tendência mensal e Issues abertas >15 dias, por empresa selecionada.
- Limpeza usa GET/POST `/api/issues/limpeza`: prévia, confirmação explícita e revisão da prévia. Opções fechadas sem RNC ou todas sem RNC; preserva Issues vinculadas a RNCs e todos os arquivos físicos. Faz backup SQLite antes da exclusão em transação única, com rollback em falha. Não executa limpeza ao abrir o submenu. Leituras de Issues/KPIs/stats/trends/kanban aceitam filtro `empresa_id`, respeitando tenancy.

- KPIs compactos (150px de largura, fonte 11px/17px), com cinco indicadores. Abertas >15 dias conta cadastradas/em tratamento desde `criado_em`; Tratativa >15 dias conta somente em tratamento desde `tratamento_iniciado_em`. Esse início é gravado na primeira transição e não reinicia a cada edição. Registros históricos sem início usam `atualizado_em` ou `criado_em` como referência aproximada na migração.

- Status da Issue agora são somente `cadastrada`, `em_tratamento`, `fechada`. Criar mantém cadastrada; primeiro input/change em registro salvo ou salvar alteração inicia tratamento. Emissão de RNC fecha a Issue na mesma transação; botão Fechar Issue usa `/api/issues/{id}/fechar` sem exigir ações. Fechamento registra data/usuário e é idempotente; ações não reabrem Issues fechadas. Endpoint legado `/finalizar` conserva validações de resultado/nota/tarefas, com status final `fechada`.
- A lista abaixo de Nova Issue mostra somente abertas. `/api/issues/kpis` informa totais por status (cadastradas e em tratamento) e fechadas no mês corrente, pela data de fechamento em UTC−03:00 (São Paulo). KPIs ficam abaixo do botão; API de listagem conserva o histórico de fechadas.

- Issue e RNC são registros separados: `issues.codigo` usa `ISSUE-0001`; tabela `rncs` guarda os campos formais e código `RNC-AAAA-NNN`, com `issue_id` único e FK composta por Issue/empresa. Migração converte códigos antigos de Issue `RNC-NNNN`, transfere campos `rnc_*` e remove essas colunas de `issues`. IDs, ações e caminhos físicos dos anexos são preservados. Endpoint de emissão continua em `/api/issues/{id}/emitir-rnc`; resposta mantém campos `rnc_*` calculados a partir de `rncs` para compatibilidade.

- Autor do registro agora é selecionável entre usuários cadastrados, com usuário logado como padrão. `issues.autor_registro_id` guarda a escolha; `criado_por_id` mantém quem efetivamente criou o registro. Issues anteriores usam o criador como autor até alteração explícita.

- Também autorizado remover do formulário as abas 2 Contenção, 3 Investigação, 4 Ação e 5 Análise. A UI mantém somente Captura, documentos e Kanban lateral. Removido o botão de emitir RNC que dependia da aba Análise. Dados e endpoints dessas etapas permanecem no backend.

- A pedido explícito do usuário, removido o bloco abaixo de “Plan — captura” e as colunas da tabela `issues`: `setor_id`, `processo_id`, `descricao`, `origem`, `produto`, `norma`, `reincidencia`, `tipo`, `severidade`, `etapa_captura`. Esta decisão substitui as referências anteriores a esses campos na Issue.
- Dados obrigatórios de abertura, Captura, Contenção, documentos, RNC e ações permanecem. A criação não exige mais setor/processo; mantém os dados factuais obrigatórios. A lista e o Kanban usam `comportamento_observado` como resumo. Pareto usa status e impacto.
- Migração idempotente em `init_db` remove somente as dez colunas; preserva os registros e relacionamentos restantes. Setores/processos e seus campos nos demais módulos permanecem.

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
