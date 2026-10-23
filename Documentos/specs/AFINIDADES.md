# Diagrama de Afinidades

Ferramentas → **4-Diagrama de Afinidades**. Abas **Diagrama** e **Como funciona — Issues e RNCs**.

## Bases e filtros

Selecionar empresa e base. Issues seguem a elegibilidade das ferramentas existentes: cadastradas/em tratamento, sem finalização e sem RNC vinculada. RNCs usam os fatos preservados na emissão, com observações da investigação. Cada cartão representa um registro inteiro e conserva seus códigos de origem, relato, comportamento esperado e evidências textuais. Nesta versão, observações de uma mesma RNC não viram cartões separados.

Filtros de período/data de referência, simulados, categoria, impacto, ambiente, local, status, pessoa, envolvidos e classificação da RNC reutilizam o Pareto, sem modificar sua implementação. A empresa é obrigatória. Cada quadro usa somente uma base.

## Organização

Carregar cartões inicia um quadro. Criar grupos, mover cartões pelo seletor, renomear e remover grupos. Remover um grupo devolve seus cartões a **Sem grupo**. Cada cartão pertence a no máximo um grupo. Nomes devem ser preenchidos e distintos; título obrigatório. Semelhança de significado é avaliada manualmente, sem classificação automática ou afirmação de causa raiz.

Admin/editor podem salvar e atualizar. Visualizadores podem consultar diagramas salvos e explorar agrupamentos temporários. Não há exclusão de diagramas nesta versão. Salvar conserva uma fotografia dos relatos e dos filtros; reabrir não atualiza os relatos com alterações posteriores na origem. Revisões concorrentes retornam 409 para impedir sobrescrita silenciosa. Trocar base/carregar outro quadro solicita descarte de alterações não salvas; trocar empresa/sessão limpa o contexto, conforme as demais ferramentas.

## Consulta IA

O botão prepara snapshot assinado contendo os cartões, grupos atuais, itens sem grupo, título e filtros. Abre o componente compartilhado com instruções editáveis e prévia. Somente **Enviar à IA** chama o provedor. As sugestões são textuais e exigem revisão; não movem cartões automaticamente. Nenhuma chamada real ao provedor foi executada na implementação/verificação.

## Persistência e API

Tabela aditiva `afinidades`: empresa, base, título, quadro JSON, revisão, criador e atualização. Criada idempotentemente no início do aplicativo. Não altera Issues/RNCs, ações ou aprovações.

- `GET /api/ferramentas/afinidades`: cartões e filtros com contexto assinado.
- `POST /api/ferramentas/afinidades/preparar`: valida os grupos contra o snapshot e assina o quadro atual para IA, sem gravação.
- `GET /api/ferramentas/afinidades/diagramas`: lista por empresa/base.
- `GET /api/ferramentas/afinidades/diagramas/{id}`: reabre e assina na sessão atual.
- `POST /api/ferramentas/afinidades/diagramas`: grava análise (admin/editor).
- `PUT /api/ferramentas/afinidades/diagramas/{id}`: atualiza com revisão obrigatória (admin/editor).

Assinatura impede alteração dos relatos no cliente; empresa e usuário são conferidos no backend. Snapshot anterior à reinicialização do servidor precisa ser recarregado. Limites: título 160 caracteres, 100 grupos, nome 120 caracteres, 2.000 IDs por grupo e snapshot de entrada até 1.000.000 caracteres.

## Verificação

`tests/test_afinidades.py`: bases, elegibilidade, filtros, snapshots, grupos inválidos, persistência, concorrência, tenancy e permissões. `node tests/check_afinidades.cjs`: abas, carregamento, conteúdo seguro, movimentação, salvamento e integração IA. Testes usam base temporária e não consultam provedores reais.
