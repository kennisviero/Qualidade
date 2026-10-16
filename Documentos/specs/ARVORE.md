# Diagrama de Árvore da RNC

Atualização: seção de árvore retirada da interface a pedido do usuário.
O planejamento passa a utilizar o Ishikawa em Investigação, com Objetivo RNC
e seis títulos de categoria editáveis. Títulos e conteúdos são persistidos
em investigacao_json.etapa_ishikawa ao clicar em Salvar registro.
Dados anteriormente gravados da árvore permanecem preservados no banco.
O texto abaixo registra a implementação anterior, agora descontinuada na tela.

Na aba 4. Plano de Ação, a seção Planejamento aparece antes de Aprovação e prazo do plano.
Informe o objetivo mensurável da RNC e clique em Criar Diagrama de Árvore.
Adicione entregas e seus desdobramentos. Cada item permite descrição, responsável,
prazo, recursos/restrições e critério de aceite. O objetivo é a raiz comum.
Salvar objetivo e árvore persiste somente esse planejamento, preservando rascunhos
da matriz. As tarefas ainda são incluídas manualmente no 5W2H.
Excluir ramo solicita confirmação e remove seus descendentes do rascunho;
é necessário salvar para persistir a exclusão.

Persistência aditiva: rncs.objetivo e rncs.arvore_json, migrados pelo init_db
no próximo início do servidor. API existente PUT /api/rncs/{id}, campos objetivo
e arvore. Leitura retorna rnc_objetivo e rnc_arvore. Limite: 200 itens.
Valida usuários da empresa, datas, identificadores únicos e hierarquia sem ciclos
ou pais ausentes. Editores/admin podem editar RNC aberta; encerradas são somente leitura.
Não há geração por IA nem criação automática de ações nesta versão.
