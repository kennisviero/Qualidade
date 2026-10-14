# Consulta à IA das ferramentas

Padrão obrigatório para ferramentas atuais e futuras: botão Consultar IA no resultado gerado; janela com acesso LLM da empresa, instruções editáveis e prévia dos dados. Enviar à IA envia o prompt exato junto com parâmetros, resultados e registros da análise. Abrir a janela/listar acessos não chama o provedor. Aplicado a Pareto e Histograma; próximas ferramentas devem usar o mesmo componente `ferramentas_ia.js` e serviço `ferramentas_ia.context`.

Dados da análise exibida são assinados no backend, vinculados à empresa e ao usuário, para preservar inclusive o instante de referência das medidas temporais. A IA usa este snapshot sem recalcular a análise nem aceitar adulteração. Alterar filtros/base/empresa invalida a janela. Após reinício do servidor, uma assinatura antiga exige gerar o gráfico novamente. A chave da assinatura é mantida no processo; a instalação atual usa um único processo de aplicação.

Endpoints autenticados: GET `/api/ferramentas/ia/acessos?empresa_id=...` (somente ID/nome/provedor/modelo ativos com chave cadastrada) e POST `/api/ferramentas/ia/consultar` (acesso_id, prompt, snapshot e assinatura). Valida tenancy, proprietário do snapshot e acesso ativo da mesma empresa. Todos os usuários autenticados da empresa podem consultar. Superusuário precisa escolher uma empresa. Chave LLM somente no backend; não incluída no snapshot ou resposta.

Adapter Chat Completions existente reutilizado com saída textual, mantendo o comportamento JSON da triagem. Prompt do usuário é preservado, sem remoção de símbolos. Mensagem de sistema distingue instruções dos registros e solicita limitar conclusões às evidências. Não há alteração em Issues/RNCs, aprovação, emissão automática, retry automático ou chamada real durante testes. Resposta exibida como texto; sem execução de HTML/modelo. A chamada ocorre fora da transação de banco.

Limites: instruções de 12.000 caracteres, snapshot de 1.000.000 caracteres, resposta de 200 KB e timeout do adapter de 60s. Falhas do provedor aparecem na janela. Envio duplicado durante uma consulta é bloqueado na interface. Respostas de contexto anterior são descartadas. Consulta não possui histórico persistente nesta versão.

Respostas textuais interrompidas com `finish_reason=length` preservam o texto e exibem aviso de resposta parcial (`completa=false`). Sem texto, explicam o limite atingido; filtro de conteúdo e outros motivos são erros específicos. Não se repete automaticamente a chamada. A triagem JSON continua rejeitando qualquer resposta incompleta. A instrução de sistema pede síntese sem reproduzir todos os registros, preservando as instruções do usuário.

Consultas textuais com provedor DeepSeek enviam `thinking: {type: disabled}` explicitamente. A documentação oficial informa que `deepseek-flash` inicia com thinking habilitado por padrão; resposta direta evita consumir o orçamento apenas antes da resposta visível. O limite de tokens existente foi mantido e a triagem JSON não recebeu mudança de modo. Referência: https://api-docs.deepseek.com/guides/thinking_mode/ (consultada em 14/10/2026). Verificação com transporte simulado; resultado real depende de novo envio do usuário.

Verificação: `tests/test_ferramentas_ia.py`, `tests/check_ferramentas_ia.cjs`, testes de Pareto/Histograma e regressão da triagem.
