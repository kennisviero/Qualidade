# Regras de negócio implementadas — Qualidade

**Data do levantamento:** 16/10/2026.  
**Escopo:** código atual do backend, banco, SPA, serviços e testes do projeto Qualidade.  
**Objetivo:** registrar o comportamento já implementado, incluindo recursos mantidos somente na API. Notas históricas de `AGENTS.md` foram usadas como contexto; o código atual prevalece neste levantamento.

## Como ler e manter este catálogo

- Cada regra possui um identificador estável `RG-<módulo>-<número>`.
- **API:** validação, cálculo ou efeito implementado no servidor. **DB:** restrição/persistência no SQLite. **UI:** comportamento da interface. **PROMPT:** instrução enviada à IA, cuja obediência semântica não é garantida por validação de código. **OP:** rotina operacional implementada em script.
- As fontes indicadas em cada seção são relativas a este arquivo e permitem rastrear as regras. Os testes citados são evidências existentes; não significam que toda a suíte foi executada novamente para produzir esta documentação.
- Regras de uma rota não devem ser presumidas para outras. As diferenças entre rotas e as limitações observadas estão registradas na seção 23.
- Ao alterar comportamento, atualizar a regra correspondente, suas fontes e testes. Criar novo ID para nova regra; não reutilizar ID de regra removida para outro significado.

## 1. Acesso, autenticação e papéis

Fontes: [autenticação](../app/auth.py), [rotas de autenticação](../app/routers/auth.py), [cadastro de usuários](../app/routers/usuarios.py). Evidências: [test_auth.py](../tests/test_auth.py), [test_criterios_aceite.py](../tests/test_criterios_aceite.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-AUT-001 | O login usa email/identificador e senha. Credenciais incorretas são recusadas com 401. | API |
| RG-AUT-002 | Usuário inativo não pode entrar nem continuar usando uma sessão existente. | API |
| RG-AUT-003 | Usuário de empresa desativada não pode entrar nem continuar usando uma sessão existente. | API |
| RG-AUT-004 | Senhas são armazenadas como hash bcrypt e verificadas por comparação com o hash. Respostas públicas de usuário não retornam o hash. | API/DB |
| RG-AUT-005 | A sessão é identificada por token aleatório, persistida no banco e válida por oito horas contadas da criação. Ausência, expiração ou invalidade da sessão resulta em 401. | API/DB |
| RG-AUT-006 | O cookie de sessão é HTTP-only e SameSite=Lax. O logout apaga todas as sessões do usuário autenticado e remove o cookie. | API |
| RG-AUT-007 | Os papéis aceitos no cadastro/edição de usuários são `admin`, `editor` e `visualizador`. | API |
| RG-AUT-008 | Superusuário global é exatamente o usuário com papel `admin` e `empresa_id = NULL`. | API |
| RG-AUT-009 | Administração de usuários/empresas e configuração LLM exige admin; escrita de setores, processos, Issues, RNCs e diagramas exige admin/editor. As exceções de aprovação nominal são descritas nos módulos. | API |
| RG-AUT-010 | Visualizador pode consultar os recursos liberados a autenticados; não pode usar as rotas protegidas por admin/editor. Selecionar para RNC é exclusivo de admin/editor, inclusive suas consultas. | API/UI |
| RG-AUT-011 | Usuários comuns acessam entidades conforme empresa e verificações próprias de cada rota. O superusuário dispõe de consultas globais ou seleção explícita de empresa conforme o recurso. | API |
| RG-AUT-012 | Na SPA, empresa de usuário comum fica fixa; controles administrativos e de edição são apresentados conforme papel. Ocultar controle não substitui a permissão do backend. | UI |

## 2. Empresas e setores

Fontes: [empresas](../app/routers/empresas.py), [setores](../app/routers/setores.py), [schema](../app/db.py), [interface](../app/static/js/app.js). Evidências: [test_hierarquia.py](../tests/test_hierarquia.py), [test_processos.py](../tests/test_processos.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-EMP-001 | Somente o superusuário pode criar ou excluir empresas. Empresa nova é criada ativa. | API |
| RG-EMP-002 | Admin de empresa lista, consulta e atualiza somente sua própria empresa; superusuário pode administrar todas. | API |
| RG-EMP-003 | Cadastro de empresa contém razão social e CNPJ textual; a atualização também permite alterar o indicador ativo. Não há validação de dígitos do CNPJ nessas rotas. | API |
| RG-EMP-004 | A interface pede confirmação para desativar/excluir empresa e informa o bloqueio de acesso na desativação. | UI |
| RG-EMP-005 | Exclusão da empresa remove registros dependentes conforme FKs/gatilhos e tenta remover sua pasta física depois da exclusão SQL. Não é uma exclusão lógica. | API/DB |
| RG-EMP-006 | Cada setor pertence a uma empresa. Criar setor exige empresa existente; para usuário comum a empresa é a do usuário. | API/DB |
| RG-EMP-007 | Admin/editor podem criar, renomear e excluir setores do escopo permitido; autenticados podem listar. | API |
| RG-EMP-008 | Renomear empresa/setor não move automaticamente suas pastas físicas. | API |
| RG-EMP-009 | Excluir setor tenta apagar a pasta física correspondente; usuários e processos vinculados ao setor têm o vínculo de setor removido por FK, preservando seu vínculo com a empresa. Ishikawas do setor têm exclusão em cascata. | API/DB |

## 3. Usuários, vínculo organizacional e responsáveis

Fontes: [usuários](../app/routers/usuarios.py), [schema](../app/db.py), [interface](../app/static/js/app.js). Evidências: [test_auth.py](../tests/test_auth.py), [test_hierarquia.py](../tests/test_hierarquia.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-USU-001 | Qualquer autenticado pode listar usuários: superusuário vê todos; os demais recebem usuários da própria empresa. Isso alimenta os seletores de responsáveis. | API |
| RG-USU-002 | Somente admin cria, edita, ativa/desativa ou exclui usuários. Admin comum só altera usuários da própria empresa. | API |
| RG-USU-003 | Email é único no banco. Nome, email e senha fazem parte da entrada de criação; papel padrão é editor e usuário novo é ativo. | API/DB |
| RG-USU-004 | Na criação, setor é opcional. Quando informado, deve existir e ser acessível; a empresa do usuário criado é derivada desse setor. Sem setor, pode ser usada a empresa informada pelo superusuário ou a empresa do admin comum. | API |
| RG-USU-005 | Na edição, informar um setor válido atualiza setor e empresa do usuário. A empresa não possui campo independente no modelo de edição. | API |
| RG-USU-006 | Posição aceita vazio ou um de: Presidente, Diretoria, Gerente, Supervisor, Encarregado, Colaborador. Outro valor é recusado. | API |
| RG-USU-007 | Senha omitida ou vazia na edição preserva o hash existente. | API |
| RG-USU-008 | Exclusão de usuário é física e sujeita às FKs existentes. Não há regra universal de apagar todos os registros dos quais ele foi responsável. Sessões são dependentes do usuário. | API/DB |
| RG-USU-009 | Seletores de responsáveis respeitam as listas do módulo: seleção para RNC oferece ativos; as abas RNC filtram usuários da empresa, sem exigir atividade em todas as validações do servidor. | API/UI |

## 4. Processos, versões e aprovação

Fontes: [processos](../app/routers/processos.py), [schema](../app/db.py). Evidências: [test_gestao.py](../tests/test_gestao.py), [test_processos.py](../tests/test_processos.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-PRO-001 | Processo pertence diretamente à empresa. Setor é opcional e, se informado, deve pertencer à mesma empresa. | API/DB |
| RG-PRO-002 | Nome do processo é único dentro da empresa; mudar de setor não cria uma nova identidade de processo. | API/DB |
| RG-PRO-003 | Para superusuário, a empresa pode ser explícita ou derivada do setor na criação. Usuário comum cria na própria empresa. | API |
| RG-PRO-004 | Guardião/responsável e aprovador, quando preenchidos, precisam ser usuários da empresa do processo. | API |
| RG-PRO-005 | Criar processo grava autor, status rascunho, pasta física e revisão inicial número 1. | API/DB |
| RG-PRO-006 | Estados aceitos na edição cadastral são `rascunho`, `em_revisao` e `aprovado`. | API |
| RG-PRO-007 | Criar revisão incrementa o maior número existente, preserva a sintaxe e registra autor/data da revisão; atualiza a sintaxe corrente e coloca o processo em revisão. | API/DB |
| RG-PRO-008 | Aprovar exige uma revisão existente. Com aprovador definido, só esse usuário ou superusuário aprova; sem aprovador definido, a rota aceita admin/editor autorizado. | API |
| RG-PRO-009 | Aprovação registra aprovador/data na última revisão e muda o processo para aprovado. | API/DB |
| RG-PRO-010 | Renomear processo ou alterar setor não move a pasta já atribuída. | API |
| RG-PRO-011 | Excluir processo apaga suas revisões por cascata e tenta remover sua pasta física após o commit. | API/DB |

## 5. Documentos, arquivos e transcrição

Fontes: [repositório físico](../app/docs.py), [documentos de processo](../app/routers/documentos.py), [anexos de Issue](../app/routers/issues.py), [transcrição](../app/routers/transcricao.py). Evidências: [test_vault_arquivos.py](../tests/test_vault_arquivos.py), [test_gestao.py](../tests/test_gestao.py), [test_issues.py](../tests/test_issues.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-DOC-001 | Documentos comuns de processo/Issue são organizados pelo filesystem, sem tabela de documentos. A data apresentada vem da modificação física do arquivo. | API |
| RG-DOC-002 | Pasta de processo usa empresa/setor/processo, omitindo setor quando ausente. Pasta de Issue usa empresa/código. O caminho atribuído é persistido. | API/DB |
| RG-DOC-003 | Componentes dos nomes físicos são saneados, limitados a 80 caracteres e substituídos por `_` quando vazios após saneamento. | API |
| RG-DOC-004 | Nomes físicos repetidos recebem sufixos para evitar sobrescrita. Pastas de Issue/Ishikawa também evitam colisão com caminhos existentes. | API |
| RG-DOC-005 | Caminhos relativos são resolvidos dentro da pasta autorizada; tentativas de sair dela são rejeitadas. Excluir a própria raiz pela rota de objetos é proibido. | API |
| RG-DOC-006 | Autenticados autorizados podem listar árvores e abrir arquivos. Upload/criação de arquivo/criação de pasta/exclusão exige admin/editor. | API |
| RG-DOC-007 | Upload comum recusa arquivo sem conteúdo. Criar arquivo vazio é permitido pela operação específica de criação. Subpasta apontando para arquivo é inválida. | API |
| RG-DOC-008 | Excluir objeto remove arquivo ou pasta recursivamente. Pastas pedem confirmação na interface. Arquivo inexistente resulta em 404. | API/UI |
| RG-DOC-009 | Arquivos de imagem, PDF e texto podem ser abertos inline; outros tipos são entregues como download, conforme a rota de anexos. | API |
| RG-DOC-010 | Transcrição aceita somente TXT, PDF e DOCX e exige autenticação. Arquivo vazio ou formato não suportado é recusado. | API |
| RG-DOC-011 | TXT tenta UTF-8 e depois Latin-1. PDF extrai texto das páginas; DOCX extrai texto dos parágrafos. Não há áudio nem OCR. | API |
| RG-DOC-012 | A transcrição retorna texto para preenchimento do formulário; não cria Issue nem salva automaticamente o registro. | API/UI |
| RG-DOC-013 | O limite de 20 MB descrito na seção de evidências RNC é específico dessa rota; não está implementado como limite geral dos uploads comuns de processo/Issue. | API |

## 6. Issue — captura, identificação e autoria

Fontes: [Issues](../app/routers/issues.py), [SPA](../app/static/js/app.js), [formulário](../app/static/index.html), [schema](../app/db.py). Evidências: [test_issues.py](../tests/test_issues.py), [test_security.py](../tests/test_security.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-ISS-001 | Issue e RNC são entidades distintas. Issue pertence diretamente a uma empresa existente; cadastro não exige setor/processo. | API/DB |
| RG-ISS-002 | Nova Issue abre formulário; a gravação efetiva ocorre em Salvar registro. | UI |
| RG-ISS-003 | São obrigatórios, com conteúdo não vazio: data/hora da detecção, comportamento esperado, comportamento observado, evidências objetivas, impacto, ação emergencial, o que aconteceu, onde ocorreu, quando ocorreu, quem foi afetado/envolvido e como foi detectado. A atualização também valida o conjunto final desses campos. | API |
| RG-ISS-004 | Código de erro, ambiente, envolvidos/afetados adicional, hipótese inicial e campos complementares de bloqueio não integram a lista de obrigatórios do backend. | API |
| RG-ISS-005 | Código é gerado na gravação como `ISSUE-NNNN`, usando o maior número existente na empresa mais um. Código é único por empresa. | API/DB |
| RG-ISS-006 | Autor do registro é selecionável. Na criação, ausência usa o usuário logado; o criador efetivo é registrado separadamente e não muda com a edição do autor. | API/DB |
| RG-ISS-007 | Autor escolhido diferente do usuário logado deve pertencer à empresa da Issue. O usuário logado é aceito como autor pela exceção explícita do validador, inclusive superusuário global. | API |
| RG-ISS-008 | Operador e inspetor, quando informados, devem ser usuários da empresa da Issue. | API |
| RG-ISS-009 | Cadastro cria pasta de anexos, grava datas de criação/atualização e inicia com status cadastrada. | API/DB |
| RG-ISS-010 | A SPA usa comportamento observado como resumo e oferece seletores de impacto, ambiente e envolvidos/afetados. Não há classificação automática dos relatos na captura. | UI |
| RG-ISS-011 | Os campos antigos setor, processo, descrição genérica, origem, produto, norma, reincidência, tipo, severidade e etapa de captura foram removidos da tabela/formulário de Issue pela migração autorizada. Dados dos demais módulos não recebem essa remoção. | DB/UI |
| RG-ISS-012 | A tela atual de captura não apresenta as antigas abas completas de investigação/ação/análise da Issue. Documentos e Kanban continuam disponíveis; APIs legadas permanecem operacionais conforme seção 8. | UI/API |

## 7. Issue — estados, encerramento, exclusão e indicadores

Fontes: [Issues](../app/routers/issues.py), [SPA](../app/static/js/app.js), [migração](../app/db.py). Evidências: [test_issues.py](../tests/test_issues.py), [test_criterios_aceite.py](../tests/test_criterios_aceite.py), [test_issue_limpeza.py](../tests/test_issue_limpeza.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-EST-001 | Estados atuais de Issue: cadastrada, em tratamento e fechada. A API não aceita os antigos estados como novos valores de edição. | API |
| RG-EST-002 | Primeiro input/change de registro salvo na captura solicita início de tratamento; salvar atualização não vazia de Issue cadastrada também inicia tratamento no servidor. | UI/API |
| RG-EST-003 | Início de tratamento é gravado uma única vez com preservação do valor anterior. Repetir a solicitação não reinicia o prazo. | API/DB |
| RG-EST-004 | Edição comum de status só admite transição para em tratamento; encerramento usa rota própria. Não há reabertura da Issue fechada por edição de status. | API |
| RG-EST-005 | Fechar Issue manualmente não exige ações nem resultado/nota. Grava status fechado, data e usuário; repetir preserva o primeiro fechamento. | API |
| RG-EST-006 | Emitir RNC fecha a Issue na mesma transação. Mover/criar ações não reabre uma Issue já fechada. | API |
| RG-EST-007 | Endpoint legado finalizar exige resultado não vazio, nota entre 1 e 5, ao menos uma ação e todas as ações finalizadas. Grava resultado/nota e fecha a Issue. Essa exigência não se aplica à rota fechar. | API |
| RG-EST-008 | Seletor da captura mostra somente Issues abertas; a API de listagem conserva também as fechadas. | UI/API |
| RG-EST-009 | Excluir Issue exige admin/editor e acesso à empresa. RNC vinculada concluída/fechada bloqueia a exclusão até reabertura. | API |
| RG-EST-010 | Exclusão da Issue apaga ações, Ishikawa vinculado e Issue em transação com rollback em falha. RNC e dependentes seguem FKs. Após commit, tenta apagar pastas da Issue e do Ishikawa. | API/DB |
| RG-EST-011 | A SPA confirma fechamento e exclusão da Issue. | UI |
| RG-EST-012 | KPIs: cadastradas, em tratamento, fechadas no mês, abertas há mais de 15 dias e em tratamento há mais de 15 dias. Todos respeitam o escopo de consulta da empresa. | API |
| RG-EST-013 | Fechadas no mês considera data do fechamento no mês corrente em UTC−03:00. Datas inválidas não entram na contagem mensal. | API |
| RG-EST-014 | Abertas há mais de 15 dias usa criação; tratativa há mais de 15 dias usa início do tratamento e somente status em tratamento. O limiar é estritamente superior a 15 dias. | API |
| RG-EST-015 | Dashboard apresenta status, impacto, criação/fechamento mensal, abertas antigas e distribuições por envolvidos, ambiente e autor, com todos os períodos nas distribuições. Ausência aparece como Não informado. | UI/API |
| RG-EST-016 | Autores no dashboard são agrupados por ID do autor escolhido, com fallback para criador. Homônimos não são fundidos; a UI diferencia rótulos com ID quando necessário. | UI |
| RG-EST-017 | Tendências mensais da API agrupam pelo prefixo ano/mês das datas gravadas. Não aplicam a mesma conversão de fuso usada pelo KPI de fechadas no mês. | API |

## 8. Ações e Kanban; investigação legada de Issue

Fontes: [ações e APIs legadas](../app/routers/issues.py), [Kanban](../app/static/js/app.js), [RNC](../app/routers/rncs.py). Evidências: [test_issues.py](../tests/test_issues.py), [test_criterios_aceite.py](../tests/test_criterios_aceite.py), [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-ACO-001 | Cada ação pertence a uma Issue e pode também estar vinculada a uma RNC. O Kanban consulta ações pelo escopo da empresa da Issue. | API/DB |
| RG-ACO-002 | Raias aceitas: backlog, iniciada, em andamento, em revisão e finalizada. A UI usa Backlog, Início, Em andamento, Revisão e Finalizado. | API/UI |
| RG-ACO-003 | Nova ação começa no Backlog, com início vazio e ordem calculada a partir das ações existentes. | API/DB |
| RG-ACO-004 | Primeira saída do Backlog define início da ação. Voltar ao Backlog não apaga/reinicia esse início. | API |
| RG-ACO-005 | Criar ação ou tirar ação do Backlog pode iniciar tratamento de Issue cadastrada; não altera o estado de Issue já fechada. | API |
| RG-ACO-006 | Responsável informado deve pertencer à empresa da Issue/RNC. Campos 5W2H incluem descrição, responsável, prazo, por quê, onde, como, quanto e observação. | API |
| RG-ACO-007 | Ação é consultada/alterada/excluída somente dentro da Issue ou RNC indicada na rota. ID de ação de outro registro não é aceito como se fosse filho desse registro. | API |
| RG-ACO-008 | Ações de RNC encerrada não podem ser criadas/editadas/excluídas/movidas pelas rotas protegidas. O Kanban apresenta essas ações em Finalizado, inclusive na leitura de inconsistência histórica. | API/UI |
| RG-ACO-009 | Alterar conteúdo ou excluir ação vinculada a RNC invalida aprovação do plano nas rotas correspondentes. A simples movimentação de status no Kanban não possui essa invalidação no código atual. | API |
| RG-ACO-010 | Na seção RNC, o Kanban é filtrado para ações vinculadas a RNC. Cartão usa código RNC e resumo opcional; código da Issue continua disponível no contexto. Sem RNC, usa código Issue. | UI |
| RG-ACO-011 | Status no Kanban é separado do ciclo de vida da RNC. Cabeçalho e matriz acompanham raias; múltiplas raias mostram quantidades sem reconstruir todo o formulário e perder rascunhos. | UI |
| RG-ACO-012 | Semáforo de prazo é calculado por RNC a partir das ações não finalizadas. Prazo vencido ou no dia é vermelho; de um a três dias é amarelo; demais casos permanecem verdes. Vermelho prevalece sobre amarelo no conjunto da RNC. | UI |
| RG-ACO-013 | Semáforo usa o dia corrente de São Paulo e somente prazo no formato de data válida YYYY-MM-DD. Prazo ausente/inválido e ação finalizada não geram atraso; verde não comprova cumprimento quando não há prazo válido. | UI |
| RG-ACO-014 | Cartões de RNC concluída/fechada não são arrastáveis; a leitura os apresenta como finalizados mesmo diante de inconsistência histórica de raia. | UI/API |
| RG-LEG-001 | Na API legada de Issue, investigar causa exige ao menos uma de Ishikawa/5 Porquês. Marcar ferramenta sem habilitar investigação é rejeitado. | API |
| RG-LEG-002 | Criar/editar Ishikawa vinculado exige investigação e uso de Ishikawa habilitados. Nome deve ser único no setor; na criação sem setor, busca o primeiro da empresa. | API/DB |
| RG-LEG-003 | Edição de categorias do Ishikawa faz merge com as existentes; causas são atualizadas conforme conteúdo enviado. | API |
| RG-LEG-004 | Salvar 5 Porquês exige investigação e uso de 5 Porquês habilitados. Com Ishikawa, referências preenchidas a itens não podem se repetir. | API |
| RG-LEG-005 | Salvar 5 Porquês legado grava conteúdo/causa raiz e inicia tratamento se a Issue não estiver fechada; mantém fechada quando já encerrada. Essas APIs não correspondem às etapas próprias de investigação da RNC. | API |

## 9. Emissão de RNC e preservação dos fatos

Fontes: [serviço de emissão](../app/services/rnc_emissao.py), [modelo de emissão](../app/routers/issues.py), [snapshot/migração](../app/services/rnc_schema.py), [schema](../app/db.py). Evidências: [test_issues.py](../tests/test_issues.py), [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-EMI-001 | Toda RNC tem Issue de origem. Há no máximo uma RNC por Issue; vínculo composto garante a mesma empresa. | API/DB |
| RG-EMI-002 | Código RNC é próprio, `RNC-AAAA-NNN`, sequenciado por empresa/ano usando o maior número existente. Ano vem do relógio UTC da emissão. | API/DB |
| RG-EMI-003 | Emitir exige admin/editor com acesso à Issue e revalida os dados mínimos da captura. Nova emissão para Issue já vinculada é recusada. | API |
| RG-EMI-004 | Complemento de emissão é opcional, inclusive classificação, enquadramento, responsáveis, equipe, metodologia e prazos. Não existe mínimo atual de dois integrantes. | API |
| RG-EMI-005 | Classificação preenchida aceita maior/menor; não é equivalente à criticidade sugerida BAIXA/MÉDIA/ALTA da IA. | API/UI |
| RG-EMI-006 | Disposição aceita refugo, retrabalho, devolução ao fornecedor, liberação por concessão ou bloqueio preventivo. Metodologia aceita 5 Porquês, Ishikawa ou FMEA. | API |
| RG-EMI-007 | Origem do gatilho não aparece no complemento atual da UI, mas a API ainda aceita vazio ou auditoria interna/externa, reclamação do cliente ou inspeção de rotina. | API/UI |
| RG-EMI-008 | Líder, responsável pela contenção, auditor de eficácia e membros da equipe informados devem pertencer à empresa. Equipe é deduplicada na emissão. | API |
| RG-EMI-009 | Emissão salva uma fotografia dos fatos da Issue, usuário/data da emissão, origem da fotografia, impacto/ambiente próprios e ação imediata inicial copiada da ação emergencial. | API/DB |
| RG-EMI-010 | Os fatos preservados não são campos editáveis pela API RNC. Alterar campos próprios de impacto/ambiente da RNC não altera o snapshot. | API |
| RG-EMI-011 | Emissão cria uma ação de tratamento no Backlog, ligada à Issue e à RNC, sem início. Líder/prazo de análise, quando informados, alimentam responsável/prazo dessa ação. | API |
| RG-EMI-012 | RNC, ação inicial e fechamento da Issue são gravados na mesma transação. Falha não deve confirmar só uma parte do item. | API/DB |
| RG-EMI-013 | RNC histórica sem snapshot é migrada usando snapshot de triagem quando disponível e complemento da Issue atual; a origem dessa recuperação é registrada. Não é apresentada como captura original integral quando derivada da migração. | DB |

## 10. Selecionar para RNC — modo manual

Fontes: [seleção](../app/routers/issue_selecao.py), [interface](../app/static/js/issue_selecao.js). Evidências: [test_manual_valida_e_revalida_sem_llm](../tests/test_issue_selecao.py), [check_issue_selecao.cjs](../tests/check_issue_selecao.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-MAN-001 | Seleção oferece modos IA e manual. Manual usa movimentação entre listas e não chama provedor. | UI/API |
| RG-MAN-002 | Elegíveis são Issues da empresa cadastradas/em tratamento e sem RNC. Lista tem busca por código/relato, filtro de status e paginação; API aceita página ≥1, tamanho 1–100, padrão 50. | API |
| RG-MAN-003 | Validação manual exige requisito/expectativa, desvio observado e suporte factual preenchidos. Recusa marcadores normalizados de ausência, como não informado, não se aplica, sem evidência, sem desvio, a definir e a confirmar. | API |
| RG-MAN-004 | A checagem é textual; consistência factual precisa ser confirmada pelo usuário. O resultado inclui pendências, justificativa dos campos e hash do snapshot. | API |
| RG-MAN-005 | Gerar manualmente exige `confirmar=true` literal e hash igual ao snapshot atual. Mudança de dados exige nova validação. | API |
| RG-MAN-006 | A UI confirma que gerar RNC fecha as Issues de origem. Itens são processados individualmente no modo manual; uma falha é exibida no item sem apresentar sucesso indevido. | UI/API |

## 11. Selecionar para RNC — análise IA e geração aprovada

Fontes: [seleção](../app/routers/issue_selecao.py), [worker e prompt](../app/services/issue_triagem.py), [schema de histórico](../app/services/triagem_schema.py), [interface](../app/static/js/issue_selecao.js). Evidências: [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-TRI-001 | Solicitar análise exige empresa, acesso LLM ativo com chave e lote de 1 a 20 IDs positivos e distintos de Issues elegíveis da empresa. | API |
| RG-TRI-002 | Prompt pode ser editado/restaurado; texto informado tem 1–20.000 caracteres e não pode ser só espaços. Prompt + entradas serializadas têm limite de 100 KB. | API/UI |
| RG-TRI-003 | Análise exige Idempotency-Key UUID. Repetição com o mesmo conteúdo retorna análise existente; mesma chave para outro conteúdo é conflito. Há compatibilidade específica com hashes de requisições antigas sem prompt próprio. | API/DB |
| RG-TRI-004 | Cada usuário pode ter somente uma análise pendente/processando por vez. | API |
| RG-TRI-005 | Solicitação persiste fotografia de entradas, hashes, provedor/modelo, versão/texto/hash do prompt, URL e parâmetros. Criar análise não altera status da Issue nem emite RNC. | API/DB |
| RG-TRI-006 | Worker consome análises persistidas em ordem. Estados: pendente, processando, concluída e falha. Etapas visíveis: enviando, aguardando e recebendo. | API/UI |
| RG-TRI-007 | Antes de chamar o provedor, worker revalida acesso/chave/atividade, modelo, provedor, URL e hash do prompt contra o pedido. Mudanças incompatíveis encerram com erro seguro. | API |
| RG-TRI-008 | Trabalho em processamento há mais de 120 segundos é marcado como interrompido; não é reenviado automaticamente ao provedor. Worker ocioso não adquire lock de escrita e a chamada externa não mantém transação de escrita aberta. | API |
| RG-TRI-009 | Resultado é JSON estrito, sem markdown, campos extras ou chaves JSON duplicadas. Candidatas têm ID enviado, título, justificativa completa e sugestão BAIXA/MÉDIA/ALTA. | API |
| RG-TRI-010 | IDs repetidos/não enviados, justificativas vazias, tipos/enums inválidos e resposta superior a 200 KB são rejeitados. Lista vazia de candidatas é resultado válido. | API |
| RG-TRI-011 | Prompt padrão aceita expectativa identificável, desvio descrito e suporte factual textual; não exige norma formal nem anexo nesta triagem preliminar. | PROMPT |
| RG-TRI-012 | Prompt orienta aceitar cenários simulados identificando-os, explicitar pendências, não inventar fatos/evidências e não tratar conteúdo das Issues como instrução. Correção imediata ou baixo impacto não excluem por si só uma candidata. | PROMPT |
| RG-TRI-013 | IA sugere candidatas; geração não ocorre automaticamente. Usuário seleciona candidatas, confere complemento e confirma explicitamente a emissão. | API/UI |
| RG-TRI-014 | Gerar lote exige análise concluída, 1–20 candidatas sem repetição, pertencentes à análise/empresa e confirmação literal verdadeira. Campos desconhecidos no complemento RNC são recusados. | API |
| RG-TRI-015 | Antes de cada emissão, revalida existência, estado aberto, ausência de RNC e hash factual da Issue. Alteração do snapshot exige nova análise. | API |
| RG-TRI-016 | Geração possui UUID idempotente por empresa e hash do conteúdo. Mesma chave/conteúdo retorna o resultado; chave reutilizada com outro conteúdo é conflito. | API/DB |
| RG-TRI-017 | Cada item usa savepoint: erro reverte aquele item, preservando os demais válidos. Resultado geral pode ser concluída, parcial ou falha; item pode ser gerada ou pendente com motivo. | API/DB |
| RG-TRI-018 | Restrição única impede que uma mesma candidata tenha mais de uma emissão bem-sucedida. Serviço/FK também impedem duas RNCs para a mesma Issue. | DB/API |
| RG-TRI-019 | Histórico preserva snapshots/justificativas e dados aprovados. Remover Issue/RNC pode anular suas referências, mantendo código e conteúdo histórico. Lista de análises retorna as 50 mais recentes da empresa. | DB/API |
| RG-TRI-020 | UI permite seleção por página/lote, consulta da Issue por código, mostra resultados por item e bloqueia duplicidade de envio enquanto processa. Acesso único ativo é pré-selecionado. | UI |

## 12. RNC — registro, contenção e investigação

Fontes: [RNC](../app/routers/rncs.py), [interface de abas](../app/static/js/rncs.js), [schema RNC](../app/services/rnc_schema.py). Evidências: [test_issue_selecao.py](../tests/test_issue_selecao.py), [test_rnc_ishikawa_titulos.py](../tests/test_rnc_ishikawa_titulos.py), [check_rnc_tabs.cjs](../tests/check_rnc_tabs.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-RNC-001 | Autenticados consultam RNCs do escopo autorizado; registro de outra empresa é retornado como não encontrado na consulta individual. | API |
| RG-RNC-002 | A UI atual tem seis abas: Registro, Contenção, Investigação, Plano de Ação, Pendências e Encerramento. Permite consultar a Issue de origem. | UI |
| RG-RNC-003 | Admin/editor editam RNC não encerrada. Estados concluída/fechada bloqueiam alterações protegidas e tornam os formulários somente consulta. | API/UI |
| RG-RNC-004 | Registro admite resumo de até 25 caracteres. Esse resumo acompanha o código em seletores/cartões onde implementado. | API/UI |
| RG-RNC-005 | Responsáveis, emitente, validadores, equipe, revisores e aprovadores informados nas abas devem pertencer à empresa da RNC. | API |
| RG-RNC-006 | Impacto próprio aceita baixo/médio/alto/crítico; ambiente próprio produção/homologação/campo/linha/outro. Valor histórico idêntico ao já salvo pode ser preservado mesmo fora da lista normalizada. | API/UI |
| RG-RNC-007 | Metodologias admitem seleção múltipla de 5 Porquês, Ishikawa e FMEA; duplicatas são removidas. Coluna singular acompanha a primeira opção para compatibilidade. | API/DB |
| RG-RNC-008 | Contenção possui ação imediata/definitiva, responsável, prazo, conclusão, validador e disposição. Datas preenchidas nas abas são validadas como ISO; não há imposição geral de preenchimento de toda contenção para salvar. | API |
| RG-RNC-009 | Observações abrangem início/período, frequência, turnos, local, sintomas, condições sem falha, operadores/equipes e impacto acumulado. Atualização parcial preserva campos omitidos. | API/DB |
| RG-RNC-010 | Datas de observação são validadas; período final anterior ao inicial é recusado. Operadores são deduplicados e validados na empresa. | API |
| RG-RNC-011 | Quantidade afetada, horas perdidas e prejuízo admitem ausência ou número finito não negativo. Unidade, moeda e período do impacto são guardados separadamente; não existe conversão automática de moeda/unidade. | API/DB |
| RG-RNC-012 | Hipóteses guardam descrição, evidências favoráveis/contrárias e testes. Testes admitem procedimento, responsável, data, resultado, esperado, critério de decisão, configuração, amostra, repetições e evidências vinculadas. | API/DB |
| RG-RNC-013 | Repetições de teste, quando preenchidas, são inteiro estrito ≥1. Conclusão aceita vazio, confirmada, descartada ou inconclusiva. Evidência vinculada ao teste deve pertencer à mesma RNC. | API |
| RG-RNC-014 | Complementos guardam mudanças/antes/depois, abrangência, controles, motivo de não detecção, conclusões, limitações e revisão. Parecer aceita vazio, aceita ou complementar; revisor e datas são validados. | API |
| RG-RNC-015 | Investigação RNC tem etapas próprias de 5 Porquês e Ishikawa. 5 Porquês admite problema, até 20 passos pergunta/resposta/evidência e conclusão. Não exige exatamente cinco passos. | API/UI |
| RG-RNC-016 | Ishikawa próprio guarda efeito, seis ramos e conclusão; títulos dos ramos são editáveis até 200 caracteres e recebem valores padrão quando omitidos. | API/UI |
| RG-RNC-017 | Modelos estruturados de investigação rejeitam campos extras. A chave antiga `porques` na raiz da investigação RNC é recusada/removida por migração; ela não é a etapa atual `etapa_porques`. | API/DB |
| RG-RNC-018 | Filtro da lista RNC procura código RNC/Issue ou descrição, ignorando acentos/maiúsculas. Sem curingas usa trecho; `*` e `?` fazem comparação do padrão completo, com outros metacaracteres tratados literalmente. | UI |

## 13. Evidências físicas da investigação RNC

Fontes: [upload/download/exclusão](../app/routers/rncs.py), [persistência](../app/services/rnc_schema.py), [UI](../app/static/js/rncs.js). Evidências: [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-EVI-001 | Upload e exclusão exigem admin/editor, empresa autorizada e RNC não encerrada; download exige autenticação e vínculo com a RNC autorizada. | API |
| RG-EVI-002 | Upload exige pasta configurada na Issue de origem e conteúdo não vazio; limite de 20 MB por arquivo. | API |
| RG-EVI-003 | Arquivo fica em subpasta de investigação da Issue, com separação por código RNC e UUID; homônimos não sobrescrevem evidências existentes. | API |
| RG-EVI-004 | Metadados guardam RNC, nome, caminho único, tamanho, MIME e usuário/data de carga. | DB |
| RG-EVI-005 | Falha na transação de upload remove o arquivo recém-criado; não deixa só o arquivo sem seu registro confirmado. | API |
| RG-EVI-006 | Exclusão remove metadados e referências da evidência nos testes da investigação, além do arquivo quando presente. Falha física/SQL desfaz metadados e tenta restaurar o arquivo quando necessário. | API |
| RG-EVI-007 | Exclusão exige confirmação na UI. Upload preserva rascunhos dos demais campos da investigação. | UI |
| RG-EVI-008 | Download valida o caminho dentro da pasta da Issue e entrega como anexo. Falta de metadado ou arquivo retorna não encontrado. | API |

## 14. Árvore de objetivos e entregas da RNC

Fontes: [modelos/validação](../app/routers/rncs.py), [árvore na UI](../app/static/js/rncs.js). Evidências: [test_rnc_arvore.py](../tests/test_rnc_arvore.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-ARV-001 | RNC pode guardar objetivo até 4.000 caracteres e árvore própria de até 200 nós. Árvore não vazia exige objetivo não vazio. | API/DB |
| RG-ARV-002 | Cada nó tem ID inteiro positivo estrito e único, pai opcional, descrição, responsável, prazo, recursos e critério de aceite. | API |
| RG-ARV-003 | Nó exige descrição não vazia de até 2.000 caracteres; recursos e critério de aceite têm até 2.000. | API |
| RG-ARV-004 | Pai informado deve existir na própria árvore; autorreferência e ciclos são rejeitados. | API |
| RG-ARV-005 | Responsável deve pertencer à empresa e prazo preenchido deve ser data válida. Modelos de nó rejeitam atributos extras. | API |
| RG-ARV-006 | A árvore é persistida como parte da RNC, separada das ações do Kanban. Salvar nó não cria automaticamente ação 5W2H. | API/DB |

## 15. Plano de ação, pendências e aprovação RNC

Fontes: [RNC](../app/routers/rncs.py), [ações Issue](../app/routers/issues.py), [matriz](../app/static/js/rncs.js). Evidências: [test_issue_selecao.py](../tests/test_issue_selecao.py), [check_rnc_tabs.cjs](../tests/check_rnc_tabs.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-PLA-001 | Plano usa ações vinculadas por `rnc_id` e `issue_id`; criação pela rota RNC exige descrição não vazia, responsável da empresa e prazo válido quando informado. | API/DB |
| RG-PLA-002 | Matriz permite incluir/descartar linhas ainda não salvas e salvar por linha. Atualização preserva rascunhos das demais linhas e atualiza o Kanban. | UI |
| RG-PLA-003 | Criar/editar ação pela rota RNC invalida aprovação anterior do plano. Trocar aprovador também limpa usuário/data de aprovação. | API |
| RG-PLA-004 | Aprovar plano exige RNC editável, ao menos uma ação e usuário logado igual ao aprovador indicado. Essa rota não concede exceção nominal ao superusuário. | API |
| RG-PLA-005 | Aprovação registra usuário/data. A interface desabilita aprovação enquanto há linha não salva ou operação de linha em andamento. | API/UI |
| RG-PLA-006 | Pendência pertence à RNC e exige descrição não vazia; responsável e prazo, se informados, são validados. Inicia aberta com autor/data. | API/DB |
| RG-PLA-007 | Pendência só aceita aberta/concluída. Concluir registra usuário/data; reabrir limpa esses dados. Repetir o mesmo estado não refaz a conclusão. | API |
| RG-PLA-008 | RNC encerrada bloqueia inclusão/alteração de ações, aprovação de plano e inclusão/conclusão/reabertura de pendências. | API |

## 16. Encerramento e reativação da RNC

Fontes: [encerrar/reabrir](../app/routers/rncs.py), [abas](../app/static/js/rncs.js), [submenu reativação](../app/static/js/app.js). Evidências: [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-ENC-001 | Encerrar exige confirmação literal verdadeira, aprovador identificado da própria empresa e executor igual ao aprovador ou superusuário, com papel admin/editor. | API |
| RG-ENC-002 | Aprovador, conclusão e lições podem ser informados na própria requisição de encerramento; não é obrigatório salvar essa aba antes. Falha posterior reverte essas alterações na mesma transação. | API |
| RG-ENC-003 | Encerrar exige ao menos uma ação ligada à RNC e nenhuma pendência aberta. Não exige aprovação prévia do plano nem todas as ações previamente finalizadas. | API |
| RG-ENC-004 | Encerramento finaliza automaticamente as ações ligadas à RNC e as ações da Issue de origem ainda sem RNC, vinculando essas últimas à RNC. | API |
| RG-ENC-005 | Encerramento grava status concluída, usuário/data de aprovação e atualização. Nova chamada em concluída mantém o encerramento e reconcilia ações como finalizadas, respeitando a autorização do aprovador. | API |
| RG-ENC-006 | Reabrir exige admin/editor autorizado e confirmação verdadeira. Somente estados concluída/fechada podem ser reabertos. Não exige que o executor seja o antigo aprovador. | API |
| RG-ENC-007 | Reabertura preserva histórico do encerramento anterior, conclusão e lições, registrando executor/data/motivo. Motivo vazio recebe texto padrão; limite de 2.000 caracteres. | API/DB |
| RG-ENC-008 | Reabertura muda RNC para reaberta, limpa aprovação do encerramento e coloca ações finalizadas da RNC em andamento, preenchendo início ausente. | API |
| RG-ENC-009 | Reabrir RNC não reabre a Issue de origem nem limpa automaticamente a aprovação do plano. | API |
| RG-ENC-010 | UI oferece submenu Reativar RNC somente a editores/admin, lista encerradas e confirma reativação. Ciclo de vida e raias Kanban continuam conceitos separados. | UI |

## 17. Limpeza controlada de Issues

Fontes: [limpeza](../app/routers/issue_limpeza.py), [UI](../app/static/js/app.js). Evidências: [test_issue_limpeza.py](../tests/test_issue_limpeza.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-LIM-001 | Limpeza é exclusiva de admin e exige empresa selecionada/existente, sem permitir outra empresa para admin comum. | API |
| RG-LIM-002 | Há dois escopos: somente fechadas sem RNC ou todas sem RNC. Issues vinculadas a RNC são sempre preservadas nessa operação. | API |
| RG-LIM-003 | Consultar prévia não exclui dados. Prévia apresenta quantidades de Issues/ações, vinculadas preservadas e revisão derivada dos dados candidatos. | API |
| RG-LIM-004 | Executar exige confirmação e revisão igual à prévia atual; mudança na base candidata exige revisar a prévia. | API/UI |
| RG-LIM-005 | Antes da remoção de candidatos, cria backup SQLite. Sem candidatos retorna zero e não cria backup. | API |
| RG-LIM-006 | Exclui ações, Issues e Ishikawa não compartilhado em transação única; falha provoca rollback. Histórico de triagem conserva snapshots conforme suas FKs. | API/DB |
| RG-LIM-007 | Limpeza preserva todos os arquivos físicos, inclusive pastas das Issues removidas. É diferente da exclusão individual da Issue. | API |

## 18. Ferramentas — bases e filtros compartilhados

Fontes: [Pareto/base comum](../app/routers/pareto.py), [Histograma](../app/routers/histograma.py), [Dispersão](../app/routers/dispersao.py), [Afinidades](../app/routers/afinidades.py), [Relações](../app/routers/relacoes.py). Evidências: testes específicos das cinco ferramentas.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-FIL-001 | Ferramentas separam Issues e RNCs. Base Issues aceita somente cadastradas/em tratamento, sem finalização e sem RNC; vínculo com RNC exclui mesmo que o status da Issue esteja inconsistente. | API |
| RG-FIL-002 | Elegibilidade é aplicada antes de gerar opções, filtros, totais e detalhes. Base RNC usa registros emitidos com Issue de origem, incluindo seus estados conforme filtros. | API |
| RG-FIL-003 | Categoria é o campo factual `o_que`; em RNC usa snapshot da emissão. Não há classificação semântica automática para criar categoria. | API |
| RG-FIL-004 | RNC usa impacto/ambiente próprios e localização da observação, com fallback para local factual. Pessoa é responsável ou líder; na base Issue é autor ou criador. | API |
| RG-FIL-005 | Filtros: empresa, período/data de referência, simulados, categoria, impacto, ambiente, local, status, pessoa, envolvidos e classificação RNC. Datas de referência: detecção/cadastro para Issue; detecção/emissão para RNC. | API/UI |
| RG-FIL-006 | Início posterior ao fim é recusado. Período inclui limites; registros sem data válida para o período são excluídos e contabilizados. Datas com fuso são consideradas em UTC−03:00. | API |
| RG-FIL-007 | Comparação de categorias e filtros normaliza acentos, caixa e espaços. Opções ausentes não são inventadas. | API |
| RG-FIL-008 | Filtro de simulados aceita todos/somente/excluir. Identificação usa a presença de simulado ou SIM-FERR- nos campos textuais analisados; não garante detectar simulação sem marcação textual. | API |
| RG-FIL-009 | Unidade e moeda não são convertidas. Quantidade/prejuízo exigem rótulo correspondente para inclusão; misturas incompatíveis são rejeitadas quando a medida pede comparabilidade. | API |
| RG-FIL-010 | Consultas estatísticas são somente leitura. Afinidades/Relações só gravam suas análises próprias por ação explícita, sem alterar origens. | API |
| RG-FIL-011 | Radios das bases são isolados por formulário. Alterações de filtros/contexto invalidam análises ou exigem novo carregamento conforme a ferramenta; respostas obsoletas são descartadas por controle de sequência. | UI |

### 18.1 Pareto

Fontes: [backend](../app/routers/pareto.py), [cálculo](../app/calculations.py), [UI](../app/static/js/pareto.js). Evidências: [test_pareto.py](../tests/test_pareto.py), [check_pareto.cjs](../tests/check_pareto.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-PAR-001 | Agrupa por categoria, impacto, ambiente, local, status, pessoa ou envolvidos; classificação é exclusiva da base RNC. | API |
| RG-PAR-002 | Issue mede contagem de registros. RNC mede contagem, quantidade afetada, horas perdidas ou prejuízo. | API |
| RG-PAR-003 | Medida numérica ausente/inválida/não finita/negativa é excluída e contabilizada; não vira zero automaticamente. Ausência na dimensão pode formar Não informado. | API |
| RG-PAR-004 | Soma contribuições por grupo, ordena decrescente e calcula percentual e percentual acumulado sobre o total, apresentados com duas casas no cálculo de Pareto. | API |
| RG-PAR-005 | Total zero produz percentuais zero. Base vazia produz total zero e itens vazios. | API |
| RG-PAR-006 | Barras/tabela permitem consultar os registros de cada grupo. Filtro legado de vínculo existe na API, mas fica oculto na base Issue; elegibilidade fixa prevalece. | API/UI |

### 18.2 Histograma

Fontes: [backend](../app/routers/histograma.py), [UI](../app/static/js/histograma.js). Evidências: [test_histograma.py](../tests/test_histograma.py), [check_histograma.cjs](../tests/check_histograma.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-HIS-001 | Issue oferece idade desde cadastro e horas entre detecção/cadastro. RNC oferece idade desde emissão, horas detecção/emissão, detecção/contenção, horas perdidas, quantidade afetada e prejuízo. | API |
| RG-HIS-002 | Intervalos têm largura igual. Número automático usa teto de log2(n) + 1, limitado a 50; manual aceita 1–50. | API |
| RG-HIS-003 | Amostra com valores iguais forma um único intervalo. Limite superior pertence somente ao último intervalo, incluindo o máximo. | API |
| RG-HIS-004 | Apresenta n, mínimo, máximo, média, mediana e desvio padrão amostral quando n≥2. Sem amostra, estatísticas ficam ausentes; sem dois valores, desvio não é calculado. | API |
| RG-HIS-005 | Tempo exige datas com componente de horário válido; sem fuso usa UTC−03:00. Contenção usa `contencao_em` ou, na ausência, data de conclusão. | API |
| RG-HIS-006 | Valores ausentes e inválidos/negativos têm contagens separadas. Quantidade/moeda incompatível exige filtro de unidade/moeda. | API |
| RG-HIS-007 | Clique em intervalo consulta seus registros. Valores estatísticos são exibidos com duas casas, mantendo precisão interna. | UI |

### 18.3 Diagrama de Dispersão

Fontes: [backend](../app/routers/dispersao.py), [UI](../app/static/js/dispersao.js). Evidências: [test_dispersao.py](../tests/test_dispersao.py), [check_dispersao.cjs](../tests/check_dispersao.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-DIS-001 | Exige duas medidas diferentes disponíveis na base, usando o catálogo de medidas do Histograma. | API |
| RG-DIS-002 | Cada ponto contém X e Y do mesmo registro; listas independentes não são emparelhadas por posição. | API |
| RG-DIS-003 | Par sem uma medida completa é excluído e contabilizado; valores não numéricos/não finitos/negativos também são excluídos com contagem própria. | API |
| RG-DIS-004 | Eixos com quantidade/prejuízo respeitam unidade/moeda compatível. UI exige seleção desses filtros quando necessários. | API/UI |
| RG-DIS-005 | Pearson só é calculado com pelo menos dois pares e variação nos dois eixos; valor é limitado ao intervalo −1 a 1. Ausência de condições resulta em correlação indisponível. | API |
| RG-DIS-006 | Clique no ponto consulta registro; tabela conserva os pares. Números são exibidos com duas casas e precisão de cálculo é preservada. | UI |
| RG-DIS-007 | UI informa que correlação não comprova causalidade, pontos coincidentes podem se sobrepor e exemplos simulados podem ter relações construídas. | UI |
| RG-DIS-008 | Não há campo de hipótese a investigar nessa ferramenta na versão levantada; a proposta histórica de adicioná-lo não é regra já implementada. | UI |

## 19. Diagrama de Afinidades

Fontes: [API/persistência](../app/routers/afinidades.py), [UI](../app/static/js/afinidades.js), [operação](../Documentos/specs/AFINIDADES.md). Evidências: [test_afinidades.py](../tests/test_afinidades.py), [check_afinidades.cjs](../tests/check_afinidades.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-AFI-001 | Quadro trabalha com uma empresa e uma base por vez, com filtros/elegibilidade comuns e aba explicativa para Issues/RNCs. | API/UI |
| RG-AFI-002 | Cada cartão é um registro inteiro, preservando códigos, relato e detalhes factuais. Observações de uma RNC não viram cartões independentes. | API/UI |
| RG-AFI-003 | Grupos são criados/nomeados pelo usuário; cartões são movidos manualmente por seletor. Não há agrupamento semântico automático. | UI |
| RG-AFI-004 | Um cartão pode pertencer a no máximo um grupo do quadro; sem atribuição fica em Sem grupo. IDs fora do snapshot e repetições são recusados. | API |
| RG-AFI-005 | Título é obrigatório até 160 caracteres; máximo 100 grupos, nome não vazio até 120 e no máximo 2.000 IDs por grupo. Nomes devem ser distintos desconsiderando caixa e espaços externos. | API |
| RG-AFI-006 | Renomear grupo é permitido; remover grupo devolve seus cartões a Sem grupo. | UI |
| RG-AFI-007 | Salvar é manual e exige admin/editor; grava título, base, fotografia dos registros/filtros, grupos, autoria e revisão na tabela afinidades. Visualizador pode explorar temporariamente e consultar salvos. | API/DB/UI |
| RG-AFI-008 | Lista de salvos é filtrada por empresa/base. Reabrir mantém a fotografia original e gera assinatura para o usuário atual. Atualizar exige revisão vigente e preserva empresa/base; conflito retorna 409. | API |
| RG-AFI-009 | Navegar entre seções preserva o quadro. Trocar base/carregar outro quadro/abrir salvo confirma descarte se houver alterações; empresa/sessão limpa contexto. Não há autosave nem exclusão de diagrama nessa versão. | UI/API |
| RG-AFI-010 | Preparar IA valida o quadro e assina título, grupos, registros e itens sem grupo sem salvar. Sugestões são textuais e não movimentam cartões automaticamente; afinidade não comprova causa raiz. | API/UI |
| RG-AFI-011 | Excluir empresa remove seus diagramas por gatilho; excluir criador desvincula autoria e preserva análise. | DB |

## 20. Diagrama de Relações

Fontes: [API/persistência](../app/routers/relacoes.py), [UI](../app/static/js/relacoes.js), [operação](../Documentos/specs/RELACOES.md). Evidências: [test_relacoes.py](../tests/test_relacoes.py), [check_relacoes.cjs](../tests/check_relacoes.cjs).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-REL-001 | Segue seleção de empresa/base, filtros, aba explicativa, salvamento manual, revisões e consulta IA do padrão Afinidades, com tabela própria relacoes. | API/UI/DB |
| RG-REL-002 | Fator tem ID positivo único e nome não vazio único, até 160 caracteres. Diagrama admite até 40 fatores e título obrigatório até 160 caracteres. | API |
| RG-REL-003 | Fator pode vincular zero ou mais registros do snapshot, até 2.000 IDs sem repetição dentro do fator. O mesmo registro pode sustentar vários fatores. Sem vínculo, fator é proposta do analista. | API/UI |
| RG-REL-004 | Relação aponta da origem que influencia para destino influenciado. Ambos os fatores precisam existir e ser diferentes; autorrelação é recusada. | API |
| RG-REL-005 | Até 200 relações. Não pode haver duplicata na mesma direção; direção inversa e ciclos são permitidos. | API |
| RG-REL-006 | Relação exige justificativa não vazia até 3.000 caracteres e tipo hipótese ou evidenciada. Evidenciada exige texto de evidência/referência não vazio até 3.000. O servidor não comprova a veracidade dessa evidência. | API |
| RG-REL-007 | Entradas/saídas por fator são recalculadas no backend a partir das relações. Contagens não determinam causalidade, causa raiz ou prioridade. | API/UI |
| RG-REL-008 | UI desenha fatores em disposição circular e setas direcionais: hipóteses laranja tracejado, evidenciadas azul contínuo. Relações inversas recebem separação curva. | UI |
| RG-REL-009 | Usuário pode editar/remover relações, renomear fatores e alterar vínculos. Remover fator remove todas as suas relações. Não há arraste/posicionamento manual nem importação automática de Afinidades. | UI |
| RG-REL-010 | Grava fotografia de relatos/filtros, fatores/vínculos, relações, justificativas/evidências, autoria e revisão. Apenas admin/editor grava; visualizador consulta/explora temporariamente. | API/DB |
| RG-REL-011 | Reabrir gera assinatura da sessão atual; atualização confere revisão e mantém empresa/base. Navegação preserva quadro; descarte de rascunho e mudança de contexto seguem o padrão descrito em Afinidades. | API/UI |
| RG-REL-012 | Preparar IA valida e assina o diagrama atual sem gravação. Resposta não cria fatores/setas automaticamente nem é salva como parte da análise. | API/UI |
| RG-REL-013 | Exclusão de empresa remove diagramas; exclusão do criador limpa autoria sem apagar análises. Não há rota de exclusão individual de diagrama. | DB/API |

## 21. Configuração LLM e consulta IA das ferramentas

Fontes: [cadastro LLM](../app/routers/llm_acessos.py), [consulta ferramentas](../app/routers/ferramentas_ia.py), [assinatura](../app/services/ferramentas_ia.py), [adapter](../app/services/llm_client.py), [janela IA](../app/static/js/ferramentas_ia.js). Evidências: [test_llm_acessos.py](../tests/test_llm_acessos.py), [test_ferramentas_ia.py](../tests/test_ferramentas_ia.py), [test_issue_selecao.py](../tests/test_issue_selecao.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-LLM-001 | Cadastro LLM é por empresa e exclusivo de admin. Nome é único por empresa; nome/provedor/modelo/URL são obrigatórios e não vazios. | API/DB |
| RG-LLM-002 | Criar acesso exige chave. Editar com chave vazia preserva a anterior; empresa do acesso não pode ser trocada. | API |
| RG-LLM-003 | Consultas do cadastro não retornam a chave, apenas indicador de chave configurada. A chave fica no SQLite e é lida pelo backend. Criar/editar cadastro não chama o provedor. | API/DB |
| RG-LLM-004 | URL no cadastro deve ser HTTP/HTTPS, com host e sem credenciais/query/fragmento. A autorização mais restrita de execução é aplicada somente ao usar o acesso. | API |
| RG-LLM-005 | Execução suporta Groq, OpenAI, OpenRouter, DeepSeek e identificadores de provedor compatível. Exige HTTPS, porta padrão/443 e host autorizado. Hosts adicionais vêm de QUALIDADE_LLM_ALLOWED_HOSTS. | API |
| RG-LLM-006 | Destino padrão permitido: api.groq.com, api.openai.com, openrouter.ai e api.deepseek.com. Resolução precisa resultar em endereços públicos; redirects e uso de proxy do ambiente estão desabilitados. | API |
| RG-LLM-007 | Endpoint é Chat Completions; URL base recebe /chat/completions quando necessário. OpenRouter exige caminho /api/v1 ou /api/v1/chat/completions. | API |
| RG-LLM-008 | Chamada tem timeout de 60 segundos, conexão de 10 segundos e resposta limitada a 200 KB. Não há retry automático. Erros de credencial, limite, parâmetros, destino, conteúdo e transporte viram mensagens controladas. | API |
| RG-LLM-009 | Limite de saída padrão é 8.192 tokens. OpenRouter/DeepSeek usam max_tokens; demais usam max_completion_tokens. OpenRouter consulta catálogo e ajusta parâmetros/limite ao suporte declarado pelo modelo. | API |
| RG-LLM-010 | Triagem usa saída JSON e validação estrita. Consulta de ferramenta usa texto; DeepSeek textual envia thinking desabilitado sem mudar a triagem JSON. | API |
| RG-LLM-011 | Abrir Consultar IA apenas carrega acessos e instruções/prévia. Somente Enviar à IA envia prompt e dados ao provedor. Um acesso único é pré-selecionado; ausência de acesso ativo impede envio. | UI/API |
| RG-LLM-012 | Consulta de ferramenta exige prompt não vazio até 12.000 caracteres, snapshot até 1.000.000 e assinatura hexadecimal válida. Campos extras são rejeitados. | API |
| RG-LLM-013 | Snapshot contém ferramenta, empresa, usuário, parâmetros e resultado, assinado com HMAC. Assinatura/empresa/usuário são verificados; troca de usuário ou adulteração não autoriza consulta. | API |
| RG-LLM-014 | Chave de assinatura é gerada na inicialização do processo: reinício exige gerar análise ou reabrir diagrama para renovar snapshot. Não há validade temporal persistente independente desse processo. | API |
| RG-LLM-015 | Envio revalida acesso ativo, chave e empresa. Não mantém conexão/transação de banco durante a chamada externa e não altera dados de Issue/RNC. | API |
| RG-LLM-016 | Mudança de contexto invalida a consulta na interface; respostas obsoletas são descartadas. Envio é bloqueado na janela enquanto uma chamada está em andamento. | UI |
| RG-LLM-017 | Texto com finish_reason=length é preservado e marcado como parcial. Limite sem texto, conteúdo filtrado, texto vazio e outros términos recebem tratamento específico. JSON de triagem incompleto continua rejeitado. | API/UI |
| RG-LLM-018 | Prompt fixo das ferramentas orienta não inventar evidências/causas, distinguir simulação e hipótese e não executar ações. Prompt editável varia para Afinidades/Relações para apoiar revisão humana. | PROMPT/UI |
| RG-LLM-019 | Consultas textuais das ferramentas não têm histórico persistente de prompt/resposta nessa versão. Isso difere do histórico persistente da triagem para RNC. | API/DB |

## 22. Recursos auxiliares e preservação de dados

Fontes: [projetos](../app/routers/projects.py), [datasets](../app/routers/datasets.py), [schema/migrações/seed](../app/db.py), [segurança](../app/security.py), [cálculos](../app/calculations.py), [carga didática](../_popular_ferramentas.py). Evidências: [test_api.py](../tests/test_api.py), [test_security.py](../tests/test_security.py), [test_calculations.py](../tests/test_calculations.py).

| ID | Regra implementada | Camada |
|---|---|---|
| RG-AUX-001 | Projetos permanecem na API: pertencem à empresa, leitura para autenticados autorizados e escrita para admin/editor. Nome/descrição são cadastrados; menu Projeto não aparece na SPA atual. | API/UI |
| RG-AUX-002 | Datasets pertencem a projeto, herdando autorização pela empresa. Criação aceita nome, tipo e dados lista/objeto; exclusão do projeto remove datasets por cascata. | API/DB |
| RG-AUX-003 | Importação CSV usa UTF-8 com BOM opcional, ignora linhas totalmente vazias e usa primeira linha como cabeçalho. Pareto converte categoria/frequência; dispersão converte X/Y; controle extrai células numéricas; outros tipos viram dicionários por cabeçalho. | API |
| RG-AUX-004 | Rotinas de cálculo de dispersão e carta de controle permanecem na biblioteca, sem módulo independente atual de Carta de Controle. Controle usa média ±3 desvios amostrais; n=1 tem desvio zero. | API/biblioteca |
| RG-AUX-005 | Modelos derivados de SafeModel saneiam texto recursivamente, removendo tags/padrões de script/eventos/javascript. Exceções explícitas preservam senha, sintaxe, chave e snapshots/prompts conforme cada modelo. Não é uma validação factual de conteúdo. | API |
| RG-AUX-006 | A interface usa texto/escape para apresentar conteúdo dos usuários em seus componentes. O helper comum transforma erros estruturados de validação em mensagens com campo, preservando mensagens textuais. | UI |
| RG-AUX-007 | Conexões SQLite habilitam FKs. Identidades e dependências são preservadas pelas migrações específicas, não por reset automático de base/Vault. | DB |
| RG-AUX-008 | Migração converte estados antigos de Issue, fecha Issues já emitidas em RNC e complementa datas históricas faltantes usando atualização/criação como aproximação. | DB |
| RG-AUX-009 | Migração separa códigos e dados de RNC da Issue, preservando IDs, ações e caminhos; fatos antigos são recuperados com origem declarada. | DB |
| RG-AUX-010 | Seed cria superusuário admin quando inexistente e base demonstrativa Empresa teste/Carlos quando ausentes. Não deve ser entendido como autorização para resetar dados existentes. | DB |
| RG-AUX-011 | Carga didática de ferramentas possui ensaio em memória e aplicação explícita com backup; cria Issue antes de emitir RNC pelo serviço. Identificação da carga evita reaplicação; não aprova/conclui RNCs nem chama LLM. | OP |
| RG-AUX-012 | Scripts de aplicação das tabelas Afinidades/Relações fazem backup e conferem preservação do conteúdo anterior e integridade/FKs. Essas garantias são próprias desses scripts, não de toda gravação comum do sistema. | OP |

## 23. Diferenças e limites que não devem virar regras presumidas

Estes pontos descrevem o código levantado e evitam transformar intenção histórica em garantia inexistente. Não foram realizadas correções funcionais durante este levantamento.

| ID | Comportamento/limite observado | Fonte |
|---|---|---|
| RG-LAC-001 | A exigência explícita de confirmar emissão e estar aberta pertence aos fluxos de seleção manual/IA. A rota direta emitir-rnc revalida captura, vínculos e duplicidade, mas não recebe confirmar nem rejeita uma Issue apenas por já estar fechada. | issues.py; rnc_emissao.py; issue_selecao.py |
| RG-LAC-002 | Fechar Issue, finalizar Issue legado e encerrar RNC são três operações com pré-condições diferentes. Não há exigência universal de todas as tarefas já finalizadas para qualquer encerramento. | issues.py; rncs.py |
| RG-LAC-003 | RNC concluída é bloqueada nas rotas próprias e de ações protegidas. Edição dos fatos da Issue original não possui bloqueio geral por Issue fechada; snapshot da RNC permanece separado. | issues.py; rncs.py |
| RG-LAC-004 | Aprovação nominal de processo pode ser registrada pela rota aprovar. A edição cadastral também aceita status aprovado sem passar por essa rota; portanto status sozinho não garante presença de assinatura de aprovação. | processos.py |
| RG-LAC-005 | Issue valida conteúdo obrigatório, mas não valida genericamente enums de impacto/ambiente nem formato ISO de todos os textos de data na captura. A UI é mais restritiva com seletores e controles; RNC/ferramentas aplicam suas próprias validações. | issues.py; rncs.py; index.html |
| RG-LAC-006 | Usuário pode existir sem setor e, quando criado pelo superusuário, sem empresa. A hierarquia empresa→setor→usuário não é obrigatória para todos os registros no código atual. | usuarios.py |
| RG-LAC-007 | Em usuários/processos, alguns campos opcionais usam valor não nulo para decidir atualização; enviar null não remove necessariamente um vínculo existente. Não presumir que todo campo possa ser limpo por null. | usuarios.py; processos.py |
| RG-LAC-008 | Configurar URL LLM com formato aceito não garante que ela seja autorizada na execução nem que modelo/chave sejam válidos. Validações externas ocorrem quando o acesso é usado. | llm_acessos.py; llm_client.py |
| RG-LAC-009 | Campos de enquadramento, FMEA, auditor de eficácia, prazos, conclusão técnica e revisão podem ser registrados, mas não há motor que imponha conformidade normativa, eficácia comprovada, teste real ou preenchimento integral antes de todo encerramento. | rncs.py; rnc_emissao.py |
| RG-LAC-010 | Não há ciclo automático de seis estados RNC nem notificações operacionais implementadas. Há abas e eventos de emitir/concluir/reabrir; abas não são estados. | rncs.py; rncs.js |
| RG-LAC-011 | Diagramas salvam fotografia e não sincronizam automaticamente alterações/exclusões dos registros de origem. Resposta IA não substitui confirmação humana nem é incorporada automaticamente ao diagrama. | afinidades.py; relacoes.py; ferramentas_ia.js |
| RG-LAC-012 | Exclusões físicas de entidades/cadastros podem ser impedidas por FKs de outros módulos. Não existe garantia universal de excluir usuário com referências ou de mover pastas ao renomear. | db.py; routers de cadastro |
| RG-LAC-013 | Lacuna de isolamento reproduzida e corrigida pelo QA: ferramentas estatísticas rejeitam com 403 usuário não global sem empresa, antes de consultar registros/opções. A regra compartilhada do Pareto protege também Histograma e Dispersão. Consulta global do superusuário e filtros de contas vinculadas permanecem disponíveis. | pareto.py: analysis; tests/qa/test_integration_rules.py |
| RG-LAC-014 | No Ishikawa legado de Issue, o superusuário tem exceção na comparação da empresa do setor. Isso difere da validação estrita de mesma empresa de responsáveis/RNC. | issues.py: link_ishikawa |

## 24. Cobertura das fontes e recursos sem regra operacional ativa

Todos os routers registrados em [main.py](../app/main.py) foram considerados. A tabela permite localizar o ponto de manutenção de cada área.

| Área/rotas | Implementação principal | Seções |
|---|---|---|
| /api/auth | auth.py; routers/auth.py | 1 |
| /api/empresas; /api/setores; /api/usuarios | routers/empresas.py; setores.py; usuarios.py | 2–3 |
| /api/processos; revisoes; aprovar | routers/processos.py | 4 |
| Documentos de processo/Issue; /api/transcricao | docs.py; routers/documentos.py; transcricao.py; issues.py | 5 |
| /api/issues; kpis; kanban; stats; trends | routers/issues.py; static/js/app.js | 6–8 |
| /api/issues/{id}/emitir-rnc | services/rnc_emissao.py; routers/issues.py | 9 |
| /api/issues/selecao | routers/issue_selecao.py; services/issue_triagem.py; triagem_schema.py | 10–11 |
| /api/rncs | routers/rncs.py; services/rnc_schema.py; static/js/rncs.js | 12–16 |
| /api/issues/limpeza | routers/issue_limpeza.py | 17 |
| /api/ferramentas/pareto; histograma; dispersao | routers/pareto.py; histograma.py; dispersao.py | 18 |
| /api/ferramentas/afinidades; relacoes | routers/afinidades.py; relacoes.py | 19–20 |
| /api/configuracao/llm; /api/ferramentas/ia | routers/llm_acessos.py; ferramentas_ia.py; services/llm_client.py | 21 |
| /api/projects; /api/datasets | routers/projects.py; datasets.py | 22 |

Não estão catalogados como regras operacionais implementadas: JWT/2FA/reset de senha, notificações, sincronização automática de pastas, causa raiz determinada por IA, hipótese editável na Dispersão e ferramentas independentes antigas removidas da UI. Políticas de desenvolvimento, como não quebrar comportamento existente, continuam em `AGENTS.md`; não são validações de negócio executadas pela aplicação.

## 25. Diagrama de Matriz — Uma RNC e Geral

| ID | Regra implementada | Fonte |
|---|---|---|
| RG-MAT-001 | Uma RNC exige exatamente uma origem; Geral exige de duas a vinte RNCs únicas da mesma empresa. Origem ausente ou de outra empresa não gera matriz. | matriz.py: generate |
| RG-MAT-002 | Filtros de seleção compartilham a base RNC do Pareto. A fotografia contém as RNCs explicitamente selecionadas e suas ações reais vinculadas à RNC e à Issue correspondente. | matriz.py: sources; generate |
| RG-MAT-003 | Linhas declaram problema, hipótese ou fator evidenciado, com RNCs de origem da fotografia. Fator evidenciado exige referência de evidência. Limite de 40 linhas e 60 ações; seleção com mais ações é rejeitada. | matriz.py: Linha; Quadro; prepare |
| RG-MAT-004 | Cruzamentos aceitam Não avaliada, Nenhuma, Fraca, Média e Forte. Toda avaliação, inclusive Nenhuma, exige justificativa. Coordenadas duplicadas ou fora das linhas/colunas são rejeitadas. | matriz.py: Celula; prepare |
| RG-MAT-005 | Sem relação positiva indicada não equivale a ausência demonstrada de cobertura: a conclusão de ausência após avaliação exige todas as células da linha avaliadas e colunas não vazias. Ações excluídas são identificadas separadamente. | matriz.py: diagnostics; matriz.js: matRenderTable |
| RG-MAT-006 | Células podem relacionar problemas e ações de RNCs diferentes no contexto Geral, mantendo as origens e sem transferir ações, alterar planos, aprovações ou registros operacionais. | matriz.py: prepare; create; update |
| RG-MAT-007 | Matrizes são fotografias persistidas separadamente por empresa/contexto. Admin/editor salvam; visualizador consulta e explora temporariamente. Atualização exige revisão vigente e preserva empresa, contexto e seleção original de RNCs. | matriz.py: listing; detail; create; update |
| RG-MAT-008 | Preparar consulta à IA valida as edições e assina a matriz atual por empresa/usuário. Instruções editáveis distinguem Uma RNC/Geral. Somente Enviar à IA chama o provedor; resposta exibida não altera nem é salva automaticamente na matriz. | matriz.py: preview; ferramentas_ia.js |
| RG-MAT-009 | Aplicar/cancelar edição pendente do cruzamento precede salvar/consultar IA. Aba Como funciona explica ambos os contextos, intensidades, origem, fotografia e limites de interpretação. | matriz.js |
| RG-MAT-010 | Descrições iniciais acima de 2.000 caracteres recebem uma prévia identificada; o relato integral continua no snapshot e em Registros de origem. Não há pontuação, causa raiz ou eficácia determinada automaticamente. | matriz.py: generate; matriz.js |

Operação: [MATRIZ.md](../Documentos/specs/MATRIZ.md). Rotas `/api/ferramentas/matriz`, `/fontes`, `/preparar` e `/diagramas`.

### Estado da verificação do levantamento original

Leitura estática das fontes e consulta aos testes existentes; sem executar limpeza, emissão, chamadas LLM, migrações ou gravações na base ativa. O único artefato produzido por esta tarefa é este catálogo. A suíte completa não foi reexecutada para a documentação. O log da sessão registra a divergência anterior no teste de JSON exato da investigação Ishikawa; isso não foi tratado como ausência da etapa implementada.

## 26. PDM — Documentos Controlados e Captura

Fontes: `app/routers/documentos_controlados.py`; `app/services/captura.py`; `app/services/llm_client.py` (ler_documento_visao); `app/docs.py` (build_documento_pasta). Evidências: `tests/test_pdm.py`; `tests/check_pdm.cjs`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-PDM-001 | Código serial por empresa `DOC-NNNN`, único por empresa; bytes no Vault `Vault/{empresa}/_pdm/{codigo}/R{numero}/`, metadados em SQLite. | DB/API |
| RG-PDM-002 | Criar documento gera revisão R01 em rascunho e evento de auditoria; estado inicial rascunho. | API/DB |
| RG-PDM-003 | Check-out é exclusivo (lock-out): segundo usuário recebe 409; documento obsoleto não aceita check-out. | API |
| RG-PDM-004 | Criar revisão e enviar arquivo exigem check-out pelo próprio usuário; upload só em revisão rascunho. | API |
| RG-PDM-005 | Aprovar exige check-in (sem check-out ativo) e só o aprovador definido (ou superusuário); marca a maior revisão como aprovada, as anteriores obsoletas, documento aprovado e revisão vigente. | API |
| RG-PDM-006 | Obsoletar define documento e revisões como obsoletos e libera o check-out. | API |
| RG-PDM-007 | Tenancy por empresa: leitura exige sessão (401 sem login); documento de outra empresa retorna 403/404; escrita exige admin/editor (visualizador 403). | API |
| RG-PDM-008 | Toda operação (criar, revisão, arquivo, check-out/in, aprovar, obsoletar, leitura) registra evento com hash SHA-256 encadeado; `GET /auditoria` recalcula o encadeamento e informa `integra`. | API/DB |
| RG-CAP-001 | Leitura extrai texto digital local (TXT/PDF/DOCX via pypdf/python-docx) sem chamada externa quando há camada de texto (`origem=digital`). | API |
| RG-CAP-002 | Sem texto nativo e com acesso LLM OpenRouter ativo da empresa, renderiza a página (PyMuPDF) e lê por modelo de visão (`origem=ia`); sem PyMuPDF ou sem acesso, degrada para `origem=vazio`. | API |
| RG-CAP-003 | O acesso LLM reusa o cadastro existente `/api/configuracao/llm`; a leitura só ocorre com `acesso_id` explícito e ativo da própria empresa. Guardas de host/HTTPS/anti-SSRF do adapter são preservadas. | API |

Operação: [PDM.md](../Documentos/specs/PDM.md). Rotas `/api/pdm/documentos`.

## 27. Normas e Regulamentos

Fontes: `app/routers/normas.py`; reutiliza `create_documento_interno` do PDM. Evidências: `tests/test_normas.py`; `tests/check_normas.cjs`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-NOR-001 | Código serial por empresa `NORMA-NNNN`, único por empresa; tenancy por `empresa_id`/`scope`. | DB/API |
| RG-NOR-002 | `tipo_fonte` e `status` restritos a enums (422 fora do conjunto); fontes diversas cobrem norma técnica, regulamento legal, requisito contratual/cliente, política interna e outro. | API |
| RG-NOR-003 | Criar com `criar_documento` (padrão verdadeiro) gera, na mesma transação, um documento controlado tipo `norma` e vincula `documento_id`; com falso, a norma fica sem documento. | API/DB |
| RG-NOR-004 | Filtros por tipo de fonte, status e emissor e busca por código/título/identificador, todos restritos à empresa. | API |
| RG-NOR-005 | Escrita exige admin/editor (visualizador 403); leitura exige sessão (401 sem login); norma de outra empresa retorna 404. | API |
| RG-NOR-006 | Excluir a norma não remove o documento controlado vinculado (objeto independente do PDM); o FK usa `ON DELETE SET NULL`. | DB |

Operação: [NORMAS.md](../Documentos/specs/NORMAS.md). Rotas `/api/normas`.

## 28. Requisitos / cláusulas

Fontes: `app/routers/requisitos.py`; migração `documento_revisoes.variante` em `app/db.py`. Evidências: `tests/test_requisitos.py`; `tests/check_requisitos.cjs`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-REQ-001 | Requisito pertence a uma norma da mesma empresa (`norma_id`+`empresa_id`); norma de outra empresa retorna 404. Tenancy por `scope`. | API/DB |
| RG-REQ-002 | `categoria` (normativo/interno/cliente/legal), `obrigatoriedade` (obrigatorio/recomendado/informativo) e `estado` (ativo/revogado) restritos a enums (422). | API |
| RG-REQ-003 | Escrita exige admin/editor (visualizador 403); leitura exige sessão (401 sem login). | API |
| RG-REQ-004 | Importação CSV/DOCX/XLSX cria em lote numa transação, sanitizando campos; XLSX/DOCX degradam se a lib estiver ausente (400). Exportação CSV sempre; XLSX quando openpyxl presente. | API |
| RG-REQ-005 | Revisão de documento do PDM aceita rótulo de variante (`documento_revisoes.variante`), sem alterar o versionamento numérico. | API/DB |
| RG-REQ-006 | Prioridade MoSCoW (`''|must|should|could|wont`) validada (422) e filtrável; migração aditiva com default vazio. | API/DB |
| RG-REQ-007 | Esquema de atributos por empresa (`requisito_atributo_defs`) é configurado só por admin; tipo restrito a `texto|numero|data|lista|booleano`; `lista` exige opções; chave única por empresa (409). | API/DB |
| RG-REQ-008 | Valores de atributo (`PUT /{id}/atributos`) validados conforme tipo/opções da definição e obrigatoriedade (422); upsert por (requisito, def). | API |
| RG-REQ-009 | Relação requisito↔requisito restrita a `deriva_de|refina|depende|conflita|duplica`; rejeita auto-relação (422), duplicada (409) e destino de outra empresa (404). | API/DB |
| RG-REQ-010 | Vínculo de rastreabilidade carrega `tipo_relacao` (`satisfaz|verifica|implementa|mitiga|outro`), default `satisfaz` (preserva vínculos existentes). | API/DB |
| RG-REQ-011 | Change request: editor propõe mudança (`proposta`); admin/editor decide `aprovada`/`rejeitada` (grava aprovador/observação/data). Decisão em solicitação já decidida ou situação fora do enum → 422; tenancy por `scope`/`fetch_req`. | API/DB |
| RG-REQ-012 | Versionamento: snapshot numerado do requisito em `requisito_versoes` — manual (`POST /{id}/versoes`) e **automático ao aprovar uma mudança** (origem `mudanca:{id}`). Histórico somente leitura. | API/DB |
| RG-REQ-013 | Variante: campo `requisitos.variante` (rótulo de contexto, ex.: 127V/BR) e tipo de relação `variante_de` para ligar uma variante ao requisito base. | API/DB |

Operação: [REQUISITOS.md](../Documentos/specs/REQUISITOS.md). Rotas `/api/requisitos` (+ `/atributos/defs`, `/{id}/atributos`, `/{id}/relacoes`, `/{id}/mudancas`, `/impacto`).

## 31. Análise de impacto econômico

Fontes: `app/routers/requisitos.py` (campos `custo_atual`/`custo_projetado`/`volume`; endpoint `/impacto`). Evidências: `tests/test_requisitos_rm.py`; `tests/check_impacto.cjs`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-IMP-001 | Requisito guarda `custo_atual`, `custo_projetado` e `volume` (≥ 0 quando informados; podem ser nulos). Migração aditiva com default NULL. | API/DB |
| RG-IMP-002 | `economia = (custo_atual − custo_projetado) × volume` apenas quando os três existem; caso contrário economia ausente (não entra no total). | API |
| RG-IMP-003 | `/impacto` lista por norma/empresa com economia por requisito, ordenado desc, e resumo (economia_total, requisitos_com_dados); tenancy por `scope`; só a norma da empresa (404). | API |

## 29. Rastreabilidade e conformidade

Fontes: `app/routers/conformidade.py`; vínculos em `app/routers/requisitos.py`. Evidências: `tests/test_conformidade.py`; `tests/check_cobertura.cjs`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-RAS-001 | Vínculo requisito↔alvo aceita apenas `processo|issue|rnc|acao`; o alvo precisa existir (404) e ser da **mesma empresa** do requisito (403 se de outra). | API |
| RG-RAS-002 | Vínculo é único por (requisito, tipo, alvo) — duplicado retorna 409. Remoção restrita ao próprio requisito/empresa. | API/DB |
| RG-RAS-003 | Os campos legados `enquadramento_normativo`/`requisito_violado` não são alterados; os vínculos apenas os referenciam (leitura aditiva). | DB |
| RG-CNF-001 | Avaliação de conformidade por requisito (opcionalmente por processo) com `situacao` restrita a `conforme|nao_conforme|nao_avaliado` (422 fora do enum); upsert idempotente por (requisito, processo). | API |
| RG-CNF-002 | Processo e responsável informados na avaliação precisam ser da empresa (422 caso contrário). | API |
| RG-CNF-003 | A matriz de cobertura por norma retorna situação por requisito, contagem de vínculos por alvo e **lacunas** (`sem_vinculo`, `nao_avaliados`, `nao_conformes`) + resumo; só a norma da empresa é acessível (404). | API |

Operação: [CONFORMIDADE.md](../Documentos/specs/CONFORMIDADE.md). Rotas `/api/conformidade` e `/api/requisitos/{id}/vinculos`.

## 30. IA de Requisitos (parsing e análise de lacunas)

Fontes: `app/services/requisitos_ia.py`; `app/routers/requisitos.py` (`/sugerir`); `app/routers/conformidade.py` (`/matriz/preparar`); `app/static/js/ferramentas_ia.js`. Evidências: `tests/test_requisitos_ia.py`.

| ID | Regra implementada | Camada |
|---|---|---|
| RG-IAN-001 | Sugestão de requisitos usa o texto já lido da revisão do documento da norma; sem texto, retorna 400 (orienta rodar a leitura antes). Reusa o acesso LLM ativo da empresa (404 se ausente). | API |
| RG-IAN-002 | A IA apenas sugere; nada é persistido automaticamente. A criação dos requisitos ocorre por ação humana via `POST /api/requisitos`. Instruções proíbem inventar cláusulas. | API/PROMPT |
| RG-IAN-003 | O retorno da IA é validado estritamente (JSON com lista `requisitos`); categoria/obrigatoriedade fora do enum são normalizadas; JSON inválido retorna 502. | API |
| RG-IAN-004 | A análise de lacunas monta a matriz de cobertura e assina o snapshot (`context('conformidade', …)`); o envio ao provedor só ocorre pelo componente compartilhado após ação explícita, validando a assinatura. | API/UI |

Operação: [REQUISITOS_IA.md](../Documentos/specs/REQUISITOS_IA.md). Rotas `/api/requisitos/sugerir` e `/api/conformidade/matriz/preparar`.
