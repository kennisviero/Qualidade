# Encerramento da RNC

A aba 6. Encerramento permite salvar aprovador da própria empresa, conclusão e lições aprendidas opcionais. Somente admin/editor escolhido como aprovador pode confirmar o encerramento, usando POST `/api/rncs/{id}/encerrar` com `confirmar: true`. O botão envia os campos atuais do formulário e grava tudo na mesma transação, sem exigir Salvar registro antes. Selecionar o aprovador atualiza a disponibilidade do botão imediatamente.

Exige aprovador identificado, pelo menos uma ação no plano e nenhuma pendência aberta. Conclusão e lições aprendidas são opcionais. A aprovação finaliza automaticamente todas as ações vinculadas à RNC e registra usuário/data e status `concluida` na mesma transação. A tela atualiza os dois Kanbans após a aprovação, aplicando os dados retornados pelo encerramento ao quadro mesmo quando sua leitura anterior estiver desatualizada. Repetição pelo aprovador é idempotente. A RNC concluída permanece disponível para consulta e suas ações não podem ser movimentadas no Kanban.

Persistência em `rncs`: `encerramento_aprovador_id`, `encerramento_conclusao`, `licoes_aprendidas`, `encerramento_aprovado_por_id`, `encerramento_aprovado_em`. Colunas aditivas com backup pelo fluxo de `init_db`; registros anteriores preservados.

Eficácia, padronização, treinamento, auditoria e compartilhamento permanecem no plano 5W2H. O encerramento não infere eficácia a partir da conclusão das tarefas; a conclusão deve registrar a avaliação do aprovador.

## Reabertura

O menu RNC contém Consultar RNCs e Reativar RNC (admin/editor). O submenu de reativação lista somente RNCs encerradas, exige motivo, chama a mesma API de reabertura e abre a RNC com edição liberada após sucesso.

O botão Reabrir RNC aparece no cabeçalho de RNCs encerradas para admin/editor. Exige motivo e usa POST `/api/rncs/{id}/reabrir` com `confirmar: true`. Registra autor/data/motivo e uma cópia do encerramento anterior em `encerramento_historico_json`, muda o status para `reaberta` e limpa a aprovação corrente. Conteúdo da investigação, conclusão e lições aprendidas permanece. Os cartões finalizados passam automaticamente para Em andamento na mesma transação e voltam a aceitar movimentação. A data de início existente é preservada; se ausente, recebe a data da reabertura. Nova aprovação finaliza novamente todos os cartões.

Ações de RNCs encerradas também ficam protegidas contra edição e exclusão pelos endpoints da Issue; a exclusão da Issue de origem fica bloqueada até a reabertura. A atualização do formulário e do Kanban após aprovação ocorre em paralelo, evitando que a reconstrução das abas atrase a atualização do quadro.

## Superusuário

O superusuário global também pode confirmar o encerramento com um aprovador da empresa identificado. `encerramento_aprovador_id` mantém o aprovador escolhido e `encerramento_aprovado_por_id` registra o usuário que efetivamente executou a confirmação, sem substituir uma identidade pela outra. Usuários comuns continuam sujeitos à escolha do aprovador. Aprovar sem identificar aprovador continua bloqueado.

Verificação reproduzível: `_verify_rnc_http.py` inicia um servidor Uvicorn real sobre cópia temporária do SQLite e confirma por HTTP encerramento pelo superusuário, cartões finalizados, bloqueio de edição, reabertura e retomada da edição. A base ativa não é modificada nesse teste.

## Correção operacional de 2026-10-12

O servidor ativo manteve o processo antigo atendendo mesmo após o WatchFiles anunciar recarregamento. A inspeção de `/openapi.json` comprovou que a API ainda exigia o motivo antigo. Os processos duplicados foram encerrados e uma única instância foi iniciada sem `--reload`. Após alterações futuras no backend, reiniciar essa instância e verificar o schema servido antes de declarar a correção disponível.

Reativação não exige motivo; se vazio, o histórico registra “Reativação solicitada pelo usuário.”. O submenu seleciona automaticamente a RNC quando existe apenas uma encerrada. O formulário abre em uma janela separada, preservando o workspace original da RNC. Verificação na base ativa via `_reactivate_rnc_live.py`, com backup antes: RNC-2026-001 reaberta e ação 1 em andamento.
