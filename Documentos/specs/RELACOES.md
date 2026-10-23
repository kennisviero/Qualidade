# Diagrama de Relações

Ferramentas → **5-Diagrama de Relações**, seguindo Afinidades: abas Diagrama e Como funciona — Issues e RNCs, filtros, salvamento manual, reabertura e consulta IA.

## Operação

1. Selecione empresa e base (Issues/RNCs), ajuste os filtros e carregue os registros. Campos de filtro vazios são omitidos.
2. Defina o título e crie fatores. Vincule zero ou mais registros de apoio a cada fator. O mesmo registro pode apoiar vários fatores. Um fator sem vínculo é uma proposta do analista.
3. Crie setas da origem que influencia ao destino influenciado, com justificativa obrigatória. Situação inicial: Hipótese. Sustentada por evidência declarada exige descrição da evidência/referência; a aplicação não comprova sua veracidade.
4. Revise o gráfico, os relatos e as contagens de entradas/saídas. Hipóteses aparecem em laranja tracejado; relações sustentadas em azul contínuo. Relações recíprocas e ciclos são permitidos. Autorrelações, setas duplicadas na mesma direção e referências a fatores inexistentes são rejeitadas.
5. Edite/remova relações ou renomeie/remova fatores. Remover fator remove suas relações. Salve manualmente para persistir; navegação entre seções preserva rascunho. Trocar base/carregar outro quadro/abrir outro diagrama pede confirmação de descarte. Empresa/sessão limpa o contexto.

As contagens orientam exploração; não determinam causa raiz ou prioridade. A organização gráfica é circular, automática, com rolagem quando necessário. Não há arraste/posicionamento manual, importação automática de Afinidades nem exclusão de diagramas nesta versão.

## Bases, permissões e persistência

Issues seguem os filtros e a elegibilidade do Pareto: cadastradas/em tratamento, sem finalização e sem RNC. RNCs usam fatos da emissão e observações. Relatos, comportamento esperado, evidências e código da Issue de origem ficam disponíveis para consulta. A ferramenta não modifica os registros de origem.

Tabela aditiva `relacoes` contém empresa, título, base, quadro JSON, revisão, criador e atualização. O quadro preserva filtros, fotografia dos relatos, fatores/vínculos, setas, situação, justificativas, evidências e contagens calculadas no servidor. Reabrir não atualiza a fotografia com mudanças posteriores na origem.

Admin/editor gravam. Visualizadores consultam e exploram temporariamente. Atualização exige revisão atual (409 em conflito). Empresa e usuário dos snapshots são validados. Exclusão de empresa remove os diagramas correspondentes; exclusão de usuário desvincula autoria e preserva análises, mantendo os fluxos existentes.

Limites: 40 fatores, 200 relações, título 160 caracteres, nome de fator 160, justificativa/evidência 3.000 e snapshot de entrada 1.000.000. Nomes de fatores/IDs únicos, sem repetição de vínculo dentro de um fator. O backend confere que vínculos pertencem à fotografia autenticada.

## Consulta IA

Preparar consulta gera snapshot assinado do quadro atual, incluindo fatores, fontes, setas e filtros. O componente compartilhado abre instruções editáveis e prévia; somente Enviar à IA chama o provedor. Sugestões não alteram o diagrama automaticamente. Respostas da IA não são persistidas. Após reinício do servidor, recarregue os registros ou reabra o diagrama para renovar a assinatura.

## API e verificação

- `GET /api/ferramentas/relacoes`: registros e opções, com snapshot assinado.
- `POST /api/ferramentas/relacoes/preparar`: valida e assina quadro atual para IA, sem gravação.
- `GET /api/ferramentas/relacoes/diagramas`: lista por empresa/base.
- `GET /api/ferramentas/relacoes/diagramas/{id}`: reabre na sessão atual.
- `POST /api/ferramentas/relacoes/diagramas`: cria (admin/editor).
- `PUT /api/ferramentas/relacoes/diagramas/{id}`: atualiza com revisão (admin/editor).

Migração idempotente no `init_db`. `_apply_relacoes_schema.py` aplica apenas a tabela/gatilhos, com backup e comparação em memória do conteúdo das tabelas anteriores, integridade/FKs. Testes em `tests/test_relacoes.py` e `tests/check_relacoes.cjs`; sem chamadas reais ao provedor.
