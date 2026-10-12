# Operação — Seleção de Issues para RNC

Implementação de 11/10/2026, baseada em `PRD/PRD_Selecao_issues.md` e `specs/spec_selecao_issues.md`.

## Como usar

1. Um administrador cadastra um acesso em Configuração: nome, provedor, modelo, URL base, chave e situação ativa.
2. No menu Issues, abrir **Selecionar para RNC** e escolher o acesso LLM da empresa selecionada. Se houver somente um acesso ativo, ele já vem selecionado. O seletor continua disponível para alteração.
3. Filtrar Issues cadastradas/em tratamento, marcar até 20, revisar o prompt editável e acionar **Enviar para a IA**. O botão Restaurar prompt padrão recupera as instruções originais.
4. Acompanhar as etapas **Enviando para a IA → Aguardando a IA processar → Recebendo dados da IA**. A etapa de recebimento começa quando o provedor retorna uma resposta HTTP de sucesso; ao terminar a validação, aparece a confirmação de conclusão. A análise também fica disponível no histórico da empresa.
5. Revisar requisito violado, fato/evidência, critérios e criticidade sugerida.
6. Marcar somente as candidatas aprovadas. O complemento da RNC é opcional na emissão.
7. Se desejar, escolher separadamente a classificação Maior/Menor. Não existe conversão automática da sugestão BAIXA/MÉDIA/ALTA.
8. Contenção, responsável/data, disposição, líder, equipe, metodologia, três prazos e auditor podem ficar vazios. Não há mínimo de membros nesta etapa. Origem do gatilho foi removida do formulário; valores históricos são preservados.
9. Confirmar **Gerar RNCs selecionadas**. Cada RNC emitida fecha sua Issue, conforme o fluxo anterior.
10. Conferir códigos gerados e pendências. Corrigir somente os itens pendentes; dados relevantes alterados na Issue exigem nova análise.

## Compatibilidade do LLM

Adapter: Chat Completions com autenticação Bearer e resposta JSON. Provedor deve ser cadastrado como **Groq**, **OpenAI**, **OpenRouter**, **Compatível** ou **OpenAI-compatible**. O nome do provedor não permite usar protocolos diferentes como se fossem equivalentes.

Groq: URL base `https://api.groq.com/openai/v1`. É necessário selecionar um modelo que aceite Chat Completions, JSON mode e `max_completion_tokens`. Referência consultada: [API Reference — Groq](https://console.groq.com/docs/api-reference).

OpenRouter: provedor **OpenRouter**, URL base `https://openrouter.ai/api/v1`, modelo com suporte a Chat Completions. O adapter consulta o catálogo oficial antes do envio: aplica `response_format` somente se o modelo aceitar esse parâmetro e limita `max_tokens` à capacidade anunciada. Sem JSON mode, o prompt continua pedindo JSON e o backend valida rigorosamente a resposta antes de aceitar candidatas. A página de gerenciamento de chaves não é uma URL de API. Referências: [Chat Completions — OpenRouter](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [Ling 3.1 Flash — parâmetros](https://openrouter.ai/inclusionai/ling-3.1-flash).

Hosts HTTPS permitidos inicialmente: `api.groq.com`, `api.openai.com` e `openrouter.ai`, porta 443. Provedores adicionais com o mesmo protocolo precisam ter seus hosts explicitamente autorizados em `QUALIDADE_LLM_ALLOWED_HOSTS`, separados por vírgula. URLs internas, redirecionamentos e destinos que resolvam para IP não público são bloqueados.

Não é feito teste externo ao salvar credenciais ou abrir o menu. A chamada externa ocorre apenas após o usuário solicitar a análise das Issues selecionadas.

Limites: 20 Issues, entrada de até 100 KB incluindo instruções, saída de até 200 KB e timeout de 60 segundos. O provedor pode impor contexto ou quotas menores. Nesse caso, a análise informa a falha e o usuário pode reduzir o lote; dados não são truncados silenciosamente.

## Permissões e histórico

- Administradores e editores podem analisar, revisar e emitir na própria empresa.
- Visualizadores não acessam a rotina de triagem.
- Superusuário opera na empresa explicitamente selecionada.
- Editores recebem apenas ID/nome/provedor/modelo dos acessos ativos, sem acesso às credenciais.
- O histórico guarda snapshots, hashes, justificativas, sugestão de criticidade, modelo, versão e texto exato do prompt enviado, além dos responsáveis pela solicitação/aprovação. O texto aparece em “Prompt utilizado na análise”.
- Apagar uma Issue deixa seu ID de referência nulo, mas mantém código, dados enviados e justificativas no histórico. Uma candidata com Issue removida não pode ser emitida.
- Limpeza não apaga arquivos nem a auditoria da triagem. A exclusão da empresa remove os registros associados à empresa, seguindo a política de exclusão já existente.

## Processamento e recuperação

O backend executa um processador de lotes persistidos. Quando não há trabalho, ele só consulta o banco, sem adquirir bloqueio de escrita. Durante a chamada ao LLM não mantém transação SQLite aberta.

Lotes pendentes são retomados. Um processamento sem conclusão há mais de 120 segundos é marcado como interrompido, permitindo nova tentativa explícita; não reenviar automaticamente uma chamada que pode já ter sido processada pelo provedor.

Geração usa chave de idempotência e transação SQLite com savepoint por candidata. O lote pode ter sucesso parcial: falhas de um item não confirmam RNC nem fechamento daquele item. A operação e seus resultados são confirmados juntos, permitindo recuperar a resposta após perda de conexão. Não fica uma operação parcialmente confirmada sem resultado recuperável.

Ao reabrir a análise pelo histórico, a tela apresenta também o resultado da última geração. As chamadas e a aprovação possuem chaves independentes; repetição da mesma requisição não cria duplicidade.

## Migração e validação

Novas tabelas são aditivas. Na primeira inicialização sobre uma base existente, o sistema cria backup em `data/backups/qualidade_antes_triagem_*.db` antes de aplicar o schema. Os cadastros, anexos, códigos e endpoints anteriores são preservados.

Verificações:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node tests/check_issue_selecao.cjs
node --check app/static/js/issue_selecao.js
```

Os testes padrão usam banco temporário e adapter simulado. A qualidade das classificações de um modelo real continua dependendo da avaliação com casos revisados pelo SGQ; não foi presumida a partir dos testes funcionais.

Decisões aplicadas: submenu Selecionar para RNC, admin/editor, acesso ativo explícito por empresa, uma análise simultânea por usuário, candidata sem pré-seleção, complemento obrigatório da RNC, preservação do fechamento vigente e bloqueio de Issues já vinculadas. Não selecionar uma candidata não exige justificativa nesta versão.

Matriz de criticidade, avaliação normativa e prazo de retenção do histórico permanecem decisões do SGQ. A rotina não inventa essas políticas e não elimina análises automaticamente.
