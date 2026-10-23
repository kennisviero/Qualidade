# Agente local QA — Qualidade

Perfil: `.codex/agents/QA.toml`, cópia revisável em `qa/QA.toml`. O perfil herda as permissões/modelo do agente principal; não adiciona credenciais nem executa sozinho. Solicite no Codex: **“Use o agente QA para verificar as regras alteradas e atualizar o livro-razão.”** O reconhecimento do perfil depende de o cliente carregar agentes locais; criação do arquivo não comprova uma execução do agente.

Formato conferido na [documentação oficial de agentes locais](https://learn.chatgpt.com/docs/agent-configuration/subagents). Stack correta: `stack/stack.md`; `stack.dm` citado na solicitação não existe. Fonte de regras: `regrasnegocio/RG.md`.

## Comandos propostos

`package.json` foi ativado a partir de `qa/package.proposed.json` após o usuário solicitar a execução pelo agente QA. Playwright foi instalado como dependência de desenvolvimento, com versões registradas em `package-lock.json`. Os scripts abaixo constituem a lista de comandos do harness. Configurações principais de build continuam exigindo consulta antes de novas alterações.

No PowerShell desta máquina, use `npm.cmd` no lugar de `npm`: o shim npm.ps1 é bloqueado pela política de execução, que não foi alterada.

| Comando após aprovação | Finalidade |
|---|---|
| `npm run qa:unit` | Funções críticas, datas, estatística, assinatura, JSON e caminhos |
| `npm run qa:backend` | Suíte backend existente e novas integrações, com isolamento |
| `npm run qa:ui` | Todos os scripts check_*.cjs; DOM simulado, não navegador E2E |
| `npm run qa:e2e` | Playwright/Edge real, servidor exclusivo na porta 18765 |
| `npm run qa:inventory` | Catálogo de regras, endpoints, funções e vínculos explícitos |
| `npm test` | Executa todas as etapas e registra falha se qualquer uma falhar |

Para repetir somente as integrações novas após um ajuste: `npm.cmd run qa:backend -- --focus=qa`. É o mesmo script aprovado, com filtro fixo no runner; não aceita comandos ou seletores arbitrários. Essa execução focada não substitui o resultado da suíte backend completa.

### Exceção autorizada: leitura da base ativa

Em 16/10/2026 o usuário autorizou usar a base ativa para testes. O foco fixo `npm.cmd run qa:backend -- --focus=live-readonly` é separado das suítes mutantes: usa SQLite em modo somente leitura e consultas GET ao servidor local existente. Não importa/inicializa o aplicativo nem executa Pytest/conftest, migrações ou worker adicional. A autenticação usa sessão já válida, sem registrar seu token ou criar/revogar sessões.

Essa autorização não muda o padrão de isolamento dos demais comandos nem autoriza limpeza, exclusões, emissão/encerramento de RNC, gravação de diagramas ou chamadas reais ao provedor. Sem servidor/sessão, o relatório registra o bloqueio; validação SQLite isoladamente não é apresentada como sucesso dos testes HTTP. Logs ativos contêm resultados agregados, sem relatos, chaves ou tokens.

### Exceção autorizada: leitura da base ativa

Em 16/10/2026 o usuário autorizou usar a base ativa para testes. O foco fixo `npm.cmd run qa:backend -- --focus=live-readonly` é separado das suítes mutantes: usa SQLite em modo somente leitura e consultas GET ao servidor local existente. Não importa/inicializa o aplicativo nem executa Pytest/conftest, migrações ou worker adicional. A autenticação usa sessão já válida, sem registrar seu token ou criar/revogar sessões.

Essa autorização não muda o padrão de isolamento dos demais comandos nem autoriza limpeza, exclusões, emissão/encerramento de RNC, gravação de diagramas ou chamadas reais ao provedor. Sem servidor/sessão, o relatório registra o bloqueio; validação SQLite isoladamente não é apresentada como sucesso dos testes HTTP. Logs ativos contêm resultados agregados, sem relatos, chaves ou tokens.

Playwright segue o padrão oficial de [servidor de teste](https://playwright.dev/docs/test-webserver) e [configuração](https://playwright.dev/docs/test-configuration). O Edge instalado é usado sem baixar navegadores adicionais. Requer Node.js, dependência dev Playwright instalada e `.venv` existente. Não há alteração em requirements.txt, configuração FastAPI ou build da aplicação para instalar o harness.

## Isolamento e evidências

- Runner define SQLite/Vault temporários. Plugin Pytest impede uso dos caminhos ativos e bloqueia transporte HTTP real. Os testes existentes continuam usando seu conftest temporário.
- E2E sobe o backend separado, nunca reutiliza localhost:8000 ou um servidor que já esteja na porta QA. Credenciais admin usadas são exclusivamente do seed temporário.
- Navegador só acessa 127.0.0.1:18765; Plotly é substituído por stub local nesses cenários. Não se declara cobertura do gráfico Plotly por esses testes. SVG de Relações é renderizado pelo código real.
- Cada comando cria pasta `qa/evidencias/<UTC>-<pid>-<suite>`, logs .txt com início/comando/saída/exit code, JUnit para Pytest/Playwright e summary.json. E2E anexa console, screenshot e trace nas falhas e screenshot de sucesso do diagrama.
- Logs contêm somente dados sintéticos; não utilizar chaves reais. As pastas temporárias são preservadas para investigação; não há exclusão recursiva automática.
- `qa/ULTIMA_EXECUCAO.json` aponta para a execução mais recente. `qa/RESULTADOS.md` é o livro-razão humano. Rodar inventário após testes atualiza a matriz com os últimos JUnit de cada suíte.
- Cobertura por regra é parcial até haver revisão de suas assertivas. Existência de um teste no módulo não é evidência de cobertura de todas as regras do módulo. Não se declara 100% nem cobertura de linhas sem ferramenta de medição.

## Tratamento de falhas

Preservar a primeira falha. Classificar produto/teste/ambiente; criar regressão; aplicar correção mínima autorizada; repetir a suíte afetada. Ajustar o teste antigo do Ishikawa requer preservar as assertivas dos dados enviados e verificar separadamente os títulos padrão, sem remover a comparação dos fatos. Falhas funcionais que mudem regra protegida são propostas ao usuário antes da alteração.
