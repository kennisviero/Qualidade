# Operação da RNC

No menu RNC, selecionar um registro emitido. O Kanban continua à direita.
O filtro ao lado do seletor pesquisa código da RNC, código da Issue e descrição, ignorando acentos e diferenças de maiúsculas.
Aceita `*` para qualquer sequência e `?` para um caractere. Exemplos: `RNC-2026-*`, `ISSUE-000?`, `*falha*`. Padrões com curingas são comparados com o campo completo; sem curingas, a busca é por trecho.
Administradores e editores podem salvar complementos; visualizadores consultam.

## Abas

- Registro: emitente e responsável são usuários da empresa. Classificação e enquadramento podem ser complementados. Os fatos da Issue são somente para leitura.
- Contenção: ação imediata e definitiva, responsável, prazo, data de conclusão, validador e disposição. Bloqueio preventivo é uma opção de disposição.
- Investigação: múltiplas metodologias, líder/equipe e prazo de análise, além dos blocos de observação descritos abaixo. Use Ctrl/⌘ para selecionar várias metodologias e Salvar registro para persistir. Os campos 5 Porquês e Causa raiz continuam fora desta aba; não há bloco 6M.
- Plano de Ação: matriz com colunas O quê, Por quê, Onde, Quem, Quando, Como e Quanto, além de observações/status. Cada linha corresponde a uma ação na tabela `acoes`, vinculada pela coluna `rnc_id`. Usar Adicionar linha e Salvar linha; rascunhos de outras linhas são mantidos. Novas linhas não salvas podem ser descartadas. Designar aprovador e prazo do plano, salvando a designação antes de aprovar. Somente o aprovador escolhido, com papel admin/editor, pode aprovar. Linhas pendentes de salvamento precisam ser salvas antes da aprovação. Alterar ações ou trocar o aprovador retira a aprovação anterior. Movimentar status de execução no Kanban não retira a aprovação do conteúdo.
- Pendências: lista de campos ainda não preenchidos, pendências manuais com responsável/prazo e conclusão/reabertura. Também permite salvar auditor e prazo da eficácia. Não envia notificações.

## Preservação

### Observação e validação na Investigação

A aba Investigação registra início/período das ocorrências, frequência, turnos/horários, localização, sintomas/condições, condições sem falha, operadores e equipes presentes nas ocorrências. Os operadores são separados da equipe de investigação. Impacto acumulado inclui quantidade/unidade, horas perdidas, prejuízo financeiro/moeda e período de referência.

Usar Adicionar hipótese para registrar a hipótese e evidências favoráveis/contrárias. Cada hipótese aceita vários testes com procedimento, responsável, data, resultado e conclusão (confirmada, descartada ou inconclusiva). Salvar registro persiste observações em `rnc_observacoes` e hipóteses/testes em `rncs.investigacao_json`, mantendo as notas anteriores.

Arquivos de evidência são carregados diretamente na aba pelo botão Carregar evidências, sem exigir salvar os textos primeiro. Arquivos ficam na subpasta `investigacao/{codigo_rnc}/{uuid}` do repositório da Issue vinculada, sem substituir arquivos com nomes iguais. A tabela `rnc_evidencias` guarda vínculo com a RNC, nome/caminho, tamanho, MIME, usuário e data do carregamento. Limite: 20 MB por arquivo. Links permitem recuperar os arquivos com autenticação e isolamento da empresa; visualizadores podem baixar, mas não carregar. Carregar arquivos não salva automaticamente os campos textuais nem descarta rascunhos.
O botão Excluir ao lado do arquivo pede confirmação e remove o arquivo físico e seu registro. Administradores/editores da empresa podem excluir em RNC não concluída; a exclusão mantém os rascunhos do formulário e preserva o registro caso a remoção física falhe.

### Fatos da abertura

Novas emissões copiam os campos factuais da Issue para `rncs.fatos_snapshot_json` na mesma transação. Edições posteriores da Issue não alteram essa cópia. O snapshot não é editável pelas rotas de RNC. Os anexos físicos continuam no repositório existente; esta implementação não cria cópias imutáveis dos arquivos.

Para registros anteriores, a migração usa os fatos da triagem que originou a RNC quando disponíveis, complementados pelos campos atuais da Issue. Sem triagem, usa a Issue atual. `fatos_snapshot_origem` e `fatos_preservados_em` identificam essa reconstrução; não se presume que os dados complementares sejam os mesmos da emissão original.

## Banco e API

Migração aditiva e idempotente em `init_db`, com backup antes da primeira aplicação sobre tabela antiga. Campos de emitente/responsável, contenção, investigação, aprovador e snapshot ficam em `rncs`; tarefas ganham `acoes.rnc_id`; pendências ficam em `rnc_pendencias`.

`/api/rncs`: listagem, consulta e atualização. Subrotas: `/acoes`, `/aprovar-plano` e `/pendencias`. Todas validam isolamento da empresa e vínculos de usuários. Datas informadas e valores de listas são validados. Campos continuam opcionais nesta etapa.

O ciclo de seis status, alertas automáticos, parecer/evidência de eficácia e histórico completo de revisões continuam pendentes. Selecionar um validador de contenção registra a indicação, sem um fluxo separado de aceite do validador nesta versão.

## Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node tests/check_rnc_tabs.cjs
node tests/check_rnc_menu.cjs
node tests/check_issue_selecao.cjs
```
