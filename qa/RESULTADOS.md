# Livro-razão QA

## Preparação — 16/10/2026

- Perfil QA preparado em qa/QA.toml e instalado em .codex/agents/QA.toml.
- Manifesto de comandos proposto em qa/package.proposed.json; aprovação solicitada antes de criar package.json/instalar dependência de desenvolvimento.
- Novos testes unitários, integração HTTP e E2E em navegador real preparados. Testes não executados nesta etapa enquanto a autorização dos comandos está pendente.
- Infraestrutura registra logs, JUnit e status de saída por execução; nenhuma chamada real LLM ou uso da base operacional é previsto.
- Ponto conhecido para reprodução: RG-LAC-013, usuário sem empresa recebendo base global em ferramentas estatísticas. Novo teste exige negar o acesso; não normaliza a exposição como resultado aceitável.
- Teste legado test_investigacao_etapas_porques_ishikawa compara JSON sem títulos padrão atuais. Diagnóstico histórico a confirmar na execução autorizada; não foi simplesmente removido/ignorado.

## Execução autorizada — 16/10/2026

Usuário solicitou usar o agente QA. Manifesto proposto ativado e Playwright instalado. Comandos executados por `npm.cmd run qa:*`, sem alterar a política PowerShell. Bancos/Vault temporários e bloqueio de transporte HTTP externo mantidos; nenhum uso da base ativa ou chamada real LLM.

| Execução | Resultado | Evidência |
|---|---|---|
| Unitários | 13 passaram, exit 0 | [Log](evidencias/2026-10-16T15-46-27-720Z-18428-unit/unit.txt), [JUnit](evidencias/2026-10-16T15-46-27-720Z-18428-unit/unit.xml) |
| Backend inicial | 173 passaram, 4 falharam, exit 1 | [Log](evidencias/2026-10-16T15-46-33-385Z-684-backend/backend.txt), [JUnit](evidencias/2026-10-16T15-46-33-385Z-684-backend/backend.xml) |
| Backend completo após ajustes | 177 passaram em 187,99 s, exit 0 | [Log](evidencias/2026-10-16T15-52-16-757Z-14228-backend/backend.txt), [JUnit](evidencias/2026-10-16T15-52-16-757Z-14228-backend/backend.xml) |
| Interface simulada | 10 scripts passaram, exit 0 | [Resumo](evidencias/2026-10-16T15-48-24-275Z-8556-ui/summary.json) |
| E2E inicial/Edge | 3 passaram, exit 0; encerramento manual do servidor QA necessário | [Log](evidencias/2026-10-16T15-48-30-485Z-20504-e2e/e2e.txt), [JUnit](evidencias/2026-10-16T15-48-30-485Z-20504-e2e/e2e.xml) |
| E2E após correção de encerramento | 3 passaram em 15,1 s, exit 0; saída automática confirmada | [Log](evidencias/2026-10-16T15-52-44-359Z-10784-e2e/e2e.txt), [JUnit](evidencias/2026-10-16T15-52-44-359Z-10784-e2e/e2e.xml), [Screenshot](evidencias/2026-10-16T15-52-44-359Z-10784-e2e/relacoes-sucesso.png) |
| Integrações QA focadas após reforço do contrato global | 16 passaram em 13,04 s, exit 0 | [Log](evidencias/2026-10-16T15-53-40-843Z-16380-backend/backend.txt), [JUnit](evidencias/2026-10-16T15-53-40-843Z-16380-backend/backend.xml) |
| Inventário e rastreabilidade | 299 regras, 115 endpoints, 235 funções, 153 cenários estáticos; exit 0 | [Log](evidencias/2026-10-16T15-55-36-237Z-4392-inventory/inventory.txt), [Matriz](COBERTURA.md), [Inventário](inventario.json) |

### Diagnóstico e ajustes

- **Produto — RG-LAC-013:** três regressões reproduziram conta editor sem empresa recebendo HTTP 200 e dados de outras empresas em Pareto, Histograma e Dispersão. Agente principal corrigiu o scope compartilhado em `pareto.analysis`, negando conta não global sem empresa antes da leitura. Consulta global do superusuário preservada. Execução focada `npm.cmd run qa:backend -- --focus=qa` verificou adicionalmente HTTP 200 com registro criado para superusuário e recusa da conta sem empresa nas três ferramentas. Segunda execução completa confirmou 177 sucessos.
- **Teste obsoleto — Ishikawa:** comparação exata omitia os seis títulos padrão já persistidos. Expected corrigido com os seis literais explícitos, preservando todos os fatos enviados e a comparação exata (inclusive ausência de campos extras).
- **Harness Windows — E2E:** os três cenários passaram, mas a árvore npm/Node/Python aguardava encerramento. PIDs 15428/12712/19644 foram identificados por linha de comando `qa.server`, cadeia de pais e início 12:48:31 local, e encerrados exclusivamente nessa execução. Inspeção CIM inicialmente negada no sandbox e repetida com aprovação. Introduzido endpoint de encerramento somente em `qa.server` temporário e globalTeardown cooperativo; nova execução confirmou saída automática em 15,1 s.
- **Ambiente:** avisos Pytest de cache sem permissão e depreciação HTTPX/TestClient não alteraram os exit codes. Logs originais preservados.

### Limites

E2E valida login, captura/fechamento Issue e persistência/reabertura de Afinidades/Relações com SVG real. Plotly usa stub local; gráficos Plotly não foram validados visualmente. Não há alegação de 100% de cobertura das 299 regras nem medição de linhas.

## Pendências

1. Expandir rastreabilidade explícita: 17 das 299 regras têm cenários nomeados com IDs. Testes legados passaram, mas suas assertivas ainda precisam ser vinculadas individualmente às demais regras.
2. Avaliar atualização futura HTTPX/TestClient e permissões do cache Pytest; avisos não bloqueantes, sem alterar dependências/build nesta tarefa.

## Base ativa — leitura autorizada em 16/10/2026

Usuário autorizou testar a base ativa. Executado exclusivamente `npm.cmd run qa:backend -- --focus=live-readonly`, usando `qa/live_readonly.py` sem imports do app/lifespan. SQLite aberto com `mode=ro` e `query_only`; HTTP GET somente para `127.0.0.1:8000`, sem redirects/proxy. Autenticação reutiliza sessão existente válida em memória. Nenhum login/logout, gravação de negócio, limpeza, exclusão, encerramento, chamada LLM ou cópia de credenciais para evidências.

| Rodada | Resultado | Evidência |
|---|---|---|
| Inicial | 22 passaram e 6 falharam por expectativas incorretas do harness, exit 1 | [Log](evidencias/2026-10-16T16-01-20-713Z-12496-backend/live-readonly.txt), [JUnit](evidencias/2026-10-16T16-01-20-713Z-12496-backend/live-readonly.xml) |
| Contratos corrigidos | 28 passaram, exit 0 | [Log](evidencias/2026-10-16T16-02-47-859Z-20448-backend/live-readonly.txt), [JUnit](evidencias/2026-10-16T16-02-47-859Z-20448-backend/live-readonly.xml) |
| Correspondência de campos reforçada | 28 passaram, exit 0 | [Log](evidencias/2026-10-16T16-03-10-390Z-18156-backend/live-readonly.txt), [JUnit](evidencias/2026-10-16T16-03-10-390Z-18156-backend/live-readonly.xml), [Resumo](evidencias/2026-10-16T16-03-10-390Z-18156-backend/live-readonly.json) |

As seis falhas iniciais eram do teste: a API RNC expõe a identidade formal em `rnc_id` (o `id` corresponde à Issue), e SQL `NOT finalizado_em` excluía valores NULL incorretamente. Ajustado para `IS NULL OR =''`, conforme elegibilidade implementada; nenhuma alteração do produto nesta rodada.

Integridade SQLite e FKs passaram. Servidor respondeu com a mesma identidade de sessão e registros do banco selecionado: 77 Issues, 31 RNCs, 3 usuários, 1 setor e nenhum processo. IDs, códigos, empresas, estados e campos de cadastro/relato selecionados foram comparados somente em memória, sem registrar conteúdo. Cinco ferramentas consultadas nas duas bases; 34 Issues elegíveis e 31 RNCs. Dispersão retornou 30 pares RNC, validando subconjunto elegível (não se presume que todos tenham medidas completas). Listas de diagramas salvos vazias corresponderam ao banco. KPIs/stats/trends/Kanban foram checados quanto a HTTP 200 e tipo estrutural; esta rodada não recalcula todos seus indicadores.

Não houve falha de produto confirmada no smoke ativo. Como outros usuários podem editar simultaneamente, isto não comprova preservação exata da base durante toda a janela nem cobertura funcional de escrita na base ativa. O manifesto `package.json` não foi alterado.

## Diagrama de Matriz — 16/10/2026

Criados `tests/test_matriz.py`, `tests/check_matriz.cjs` e `qa/e2e/matriz.spec.cjs`. Somente os testes isolados criam/alteram dados; ativo recebe SQL somente leitura e GET. IA backend usa mock; E2E intercepta a resposta localmente no navegador. Nenhuma chamada real ao provedor.

| Execução | Resultado | Evidência |
|---|---|---|
| Backend completo | 191 passaram, exit 0; inclui os 14 casos iniciais Matriz | [Log](evidencias/2026-10-16T16-20-30-975Z-18040-backend/backend.txt), [JUnit](evidencias/2026-10-16T16-20-30-975Z-18040-backend/backend.xml) |
| Matriz focada com complementos | 15 passaram, exit 0; subconjunto + teste adicional, não somar como execução completa de 192 | [Log](evidencias/2026-10-16T16-23-41-268Z-8440-backend/backend.txt), [JUnit](evidencias/2026-10-16T16-23-41-268Z-8440-backend/backend.xml) |
| Matriz focada final com mais de 60 ações selecionadas | 15 passaram, exit 0 | [Log](evidencias/2026-10-16T16-25-35-013Z-11336-backend/backend.txt), [JUnit](evidencias/2026-10-16T16-25-35-013Z-11336-backend/backend.xml) |
| Interface final | 11 scripts passaram, exit 0 | [Matriz](evidencias/2026-10-16T16-24-48-398Z-8604-ui/check_matriz.txt), [Resumo](evidencias/2026-10-16T16-24-48-398Z-8604-ui/summary.json) |
| E2E inicial | 4 passaram, exit 0 | [Log](evidencias/2026-10-16T16-21-48-283Z-9112-e2e/e2e.txt) |
| E2E final com prompt contextual/IA simulada | 4 passaram, exit 0 | [Log](evidencias/2026-10-16T16-23-52-142Z-11428-e2e/e2e.txt), [JUnit](evidencias/2026-10-16T16-23-52-142Z-11428-e2e/e2e.xml), [Screenshot](evidencias/2026-10-16T16-23-52-142Z-11428-e2e/matriz-sucesso.png) |
| Ativo somente leitura com Matriz | 33 passaram, exit 0; inclui fontes, listas e geração Uma RNC/Geral sem salvar | [Log](evidencias/2026-10-16T16-24-23-798Z-3340-backend/live-readonly.txt), [JUnit](evidencias/2026-10-16T16-24-23-798Z-3340-backend/live-readonly.xml) |
| Inventário atualizado | 309 regras, 122 endpoints, 244 funções, 161 cenários estáticos; exit 0 | [Log](evidencias/2026-10-16T16-24-50-832Z-9036-inventory/inventory.txt) |

Todos os testes Matriz passaram na primeira execução. Ajustes de produto feitos pelo agente principal durante a revisão (prévia para relato longo e reabilitação de botões ao invalidar respostas pendentes) receberam regressões focadas. Avisos conhecidos de cache Pytest/depreciação HTTPX não alteraram os resultados.

### Rastreabilidade Matriz revisada (cobertura parcial por regra)

| Regras | Cenário/assertiva |
|---|---|
| RG-MAT-001/002 | `test_matriz_context_selection_sources_and_auth`: uma origem, Geral com duas, inválidos/duplicados/ausentes; fontes filtradas e ações ligadas à RNC selecionada |
| RG-MAT-003/004 | `test_matriz_rejects_invalid_cells_lines_and_evidence`: nove variantes de coordenadas, justificativa, duplicatas, origens e evidência; `test_matriz_limits_long_report_and_same_company_other_user`: limites 41 linhas/61 colunas/21 RNCs |
| RG-MAT-005/006 | `test_matriz_pending_is_not_none_and_original_plans_unchanged`: distingue não avaliada, nenhuma e positiva; fotografia integral de Issues/RNCs/ações antes/depois idêntica; E2E cruza RNCs e compara Kanban original |
| RG-MAT-007 | `test_matriz_persistence_revision_and_snapshot` e `test_matriz_tenancy_viewer_and_snapshot_identity`: reabrir mantém plano antigo, revisão concorrente 409, troca contexto 422, tenancy e visualizador |
| RG-MAT-008 | `test_matriz_ai_explicit_signed_snapshot_and_mock_provider`: assinatura adulterada rejeitada e nenhum provedor antes do envio; usuário distinto da mesma empresa rejeitado; E2E verifica prompts de ambos contextos, instrução editada, snapshot correto e resposta simulada exibida |
| RG-MAT-009 | DOM/E2E: ajuda para ambos contextos, justificativa obrigatória, aplicar/cancelar rascunho antes de consultar; DOM invalida resposta obsoleta e reabilita Gerar/Filtrar |
| RG-MAT-010 | Relato com mais de 2.000 caracteres mantém integral na origem e usa prévia identificada em linha, aceita ao preparar |

O inventário automático só extrai IDs dos nomes; os testes Matriz têm rastreabilidade revisada nesta tabela, ainda não nos nomes. Não considerar as demais regras como descobertas/cobertas por estes resultados. O teste final exercitou também geração com 61 ações reais vinculadas a uma RNC exclusivamente no banco temporário: resposta 422 confirmada.
