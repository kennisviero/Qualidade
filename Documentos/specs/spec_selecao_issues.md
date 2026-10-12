# Especificação técnica — Seleção de Issues para RNC com IA

Versão: 1.0  
Data: 11/10/2026  
Status: Proposta técnica para revisão  
Documento de referência: `documentos/PRD/PRD_Selecao_issues.md`

## 1. Objetivo e limites

Especificar a seleção de Issues, a triagem por modelo LLM, a revisão humana das candidatas e a geração rastreável de RNCs. Esta entrega é documental: não implementa endpoints, migrações, telas ou chamadas externas.

Os contratos, nomes de tabelas e parâmetros abaixo são propostas de implementação derivadas do PRD. Não indicam funcionalidades já disponíveis. Decisões de produto ainda abertas no PRD continuam pendentes e estão reunidas na seção 15.

A solução proposta mantém FastAPI, SQLite e a SPA HTML/CSS/JavaScript. A emissão de RNC deve reutilizar o serviço de negócio existente, sem contornar suas validações nem modificar seu comportamento para acomodar a triagem.

## 2. Componentes e responsabilidades

- `app/routers/issue_selecao.py`: autenticação, autorização, validação dos contratos e respostas HTTP.
- `app/services/issue_triagem.py`: elegibilidade, snapshots, execução de análise e validação do retorno.
- `app/services/llm_client.py`: interface para chamar o provedor configurado; leitura de credenciais exclusivamente no backend.
- `app/services/rnc_emissao.py`: serviço compartilhado de emissão, a extrair do fluxo existente preservando sua assinatura funcional e validações.
- `app/db.py`: migrações aditivas das tabelas de análise e geração.
- `app/static/js/issue_selecao.js`: seleção inicial, acompanhamento da análise, revisão e resultados.
- `app/static/index.html` e `app/static/css/style.css`: submenu e elementos da tela.
- `tests/test_issue_selecao.py`: contratos, tenancy, falhas e concorrência com provedor simulado.

Não chamar endpoints HTTP internos para emitir RNC. Router atual e novo fluxo devem usar o mesmo serviço de negócio. A refatoração só deve prosseguir após testes demonstrarem preservação das regras atuais.

## 3. Autorização e escopo de empresa

Proposta: `admin` e `editor` podem analisar e gerar; `visualizador` não executa operações. A matriz definitiva depende de aprovação.

- Todo lote pertence a exatamente uma empresa.
- Administrador global informa a empresa selecionada.
- Demais usuários operam exclusivamente na própria empresa.
- Cada Issue, acesso LLM, análise e candidata deve pertencer à empresa da operação.
- Nunca confiar em empresa ou conteúdo da Issue enviados pelo navegador; recarregar os dados no backend.
- Recursos de outra empresa não devem ser expostos, inclusive em consultas por ID.
- Proposta: somente usuários com permissão de escrita acessam o histórico nesta primeira versão.

O backend precisa oferecer a resolução do acesso LLM sem expor credenciais. Proposta: endpoint de opções limitado a ID, nome, provedor e modelo dos acessos ativos. A manutenção de credenciais continua restrita aos administradores.

## 4. Elegibilidade e montagem do lote

São elegíveis Issues com status `cadastrada` ou `em_tratamento`. Registros fechados são excluídos. Proposta: Issues já vinculadas a uma RNC não entram no lote enquanto a política de múltiplas RNCs por Issue não for definida.

O backend valida todos os IDs antes de chamar o modelo. IDs duplicados, inexistentes, não elegíveis ou de outra empresa rejeitam o pedido inteiro; não analisar silenciosamente um subconjunto.

Mapeamento proposto dos dados disponíveis:

| Campo da entrada LLM | Origem proposta |
| --- | --- |
| id_issue / codigo_issue | ID e código do registro |
| status | Status atual da Issue |
| fato | Comportamento observado |
| requisito | Comportamento esperado |
| evidencia | Evidências objetivas mencionadas |
| impacto | Impacto declarado |
| ambiente | Ambiente informado |
| envolvidos | Envolvidos ou afetados |
| acao_emergencial | Ação emergencial registrada |
| detectado_em | Data/hora de detecção |
| origem_deteccao | Forma de detecção, identificada como contexto, sem inferir canal formal |
| local | Local informado; não converter automaticamente em setor/processo |

Área/processo e canal formal permanecem ausentes quando não houver um campo correspondente. Campos históricos removidos não devem ser recriados por esta funcionalidade.

Dados de identificação pessoal só são enviados quando necessários e aprovados. Não enviar chave de API, senhas, sessões, histórico inteiro da empresa nem arquivos anexos.

Campos vazios permanecem vazios. Ausência de requisito ou evidência não pode ser suprida pelo backend ou pelo modelo. A Issue pode ser submetida com dados insuficientes; nesse caso a análise não deve sugerir candidatura por suposição.

## 5. Contratos HTTP propostos

Prefixo: `/api/issues/selecao`. Registrar o router antes de rotas genéricas de Issue por ID, para evitar ambiguidade de caminhos.

### 5.1 Consulta de elegíveis

`GET /api/issues/selecao/elegiveis?empresa_id=4&status=em_tratamento&busca=ISSUE&page=1&page_size=50`

Retorna `itens`, `total`, `page` e `page_size`. Cada item contém ID, código, resumo, status, detecção, impacto e data de criação. Proposta: ordenar por criação decrescente e ID decrescente em empate.

Filtros opcionais: código/resumo e status. `page_size` limitado pelo servidor. Não retornar chaves ou justificativas de outras análises nessa consulta.

### 5.2 Opções de modelo

`GET /api/issues/selecao/acessos-llm?empresa_id=4`

Retorna somente acessos ativos da empresa autorizada, contendo ID, nome, provedor e modelo. Não retorna chave ou dados sensíveis. Ausência de opções bloqueia a análise na tela.

### 5.3 Solicitar análise

`POST /api/issues/selecao/analises`

Cabeçalho obrigatório proposto: `Idempotency-Key`, UUID gerado pelo cliente para a intenção de análise.

```json
{
  "empresa_id": 4,
  "acesso_llm_id": 7,
  "issue_ids": [123, 124]
}
```

Resposta `202`:

```json
{
  "analise_id": 81,
  "status": "pendente",
  "total_issues": 2,
  "url_status": "/api/issues/selecao/analises/81"
}
```

Repetição da mesma chave e mesmo payload retorna a análise existente, sem nova chamada. Mesma chave com payload diferente retorna `409`.

### 5.4 Consultar análise

`GET /api/issues/selecao/analises/{analise_id}`

Retorna estado, datas, contagens, erro normalizado quando houver e candidatas válidas. Para cada candidata: ID, ID/código da Issue, resumo original, justificativa completa, criticidade sugerida, estado de geração e eventual código da RNC.

Não retornar a resposta bruta do provedor como HTML ou conteúdo executável. Mensagens internas do provedor precisam ser normalizadas para evitar exposição de credenciais.

### 5.5 Gerar RNCs selecionadas

`POST /api/issues/selecao/analises/{analise_id}/geracoes`

Cabeçalho obrigatório proposto: `Idempotency-Key` independente da chave da análise.

```json
{
  "confirmar": true,
  "itens": [
    {
      "candidata_id": 301,
      "dados_rnc": {}
    }
  ]
}
```

`dados_rnc` representa os campos do contrato de emissão existente. O objeto vazio é apenas ilustrativo: a geração é bloqueada até que os campos obrigatórios estejam preenchidos e a classificação de destino definida. Não usar defaults fictícios para responsáveis, prazos, metodologia ou criticidade.

Resposta `200`, com resultados por item:

```json
{
  "geracao_id": 91,
  "status": "parcial",
  "itens": [
    {
      "candidata_id": 301,
      "codigo_issue": "ISSUE-0123",
      "status": "gerada",
      "codigo_rnc": "RNC-2026-001"
    },
    {
      "candidata_id": 302,
      "codigo_issue": "ISSUE-0124",
      "status": "pendente",
      "erro_codigo": "issue_alterada"
    }
  ]
}
```

Esse exemplo de resposta mostra um lote de dois itens; a requisição ilustrativa anterior mostra a estrutura de um item. Nunca incluir resultados de candidatas que não foram selecionadas.

`GET /api/issues/selecao/geracoes/{geracao_id}` permite recuperar o resultado após perda de conexão.

### 5.6 Erros padronizados

| HTTP | Situação |
| --- | --- |
| 401 | Sessão ausente ou expirada |
| 403 | Papel ou escopo de empresa não autorizado |
| 404 | Recurso inexistente ou inacessível por ID |
| 409 | Conflito de idempotência, estado ou recurso já vinculado |
| 413 | Lote ou conteúdo excede limite de tamanho |
| 422 | Contrato inválido ou obrigatórios ausentes |
| 503 | Serviço de processamento indisponível antes de aceitar o lote |

Falhas do provedor ocorridas após o aceite são consultadas no estado da análise. Não retornar sucesso com lote fictício ou incompleto.

## 6. Persistência proposta

### 6.1 llm_triagens

Campos: ID, empresa_id, acesso_llm_id, solicitado_por_id, idempotency_key, request_hash, status, provedor_snapshot, modelo_snapshot, versao_prompt, parametros_json, criado_em, iniciado_em, concluido_em, erro_codigo e erro_mensagem_segura.

Estados: `pendente`, `processando`, `concluida` e `falha`. Resultado vazio continua sendo `concluida`, com zero candidatas.

Restrições: unicidade de empresa/idempotency_key; referência à empresa. Guardar snapshot de provedor/modelo sem credenciais para preservar o histórico se a configuração mudar.

### 6.2 llm_triagem_issues

Campos: ID, triagem_id, empresa_id, issue_id, codigo_issue_snapshot, entrada_json, entrada_hash, candidata, justificativa_json e criticidade_sugerida.

Restrições: unicidade de triagem/Issue; criticidade, quando presente, em `BAIXA`, `MÉDIA`, `ALTA`; candidata é booleana. A ausência da Issue na lista de candidatas resulta em `candidata=false`, sem inventar justificativa de rejeição.

`entrada_json` guarda exatamente os dados relevantes enviados. O hash é calculado sobre JSON canônico, ordenando chaves e preservando a representação consistente dos valores.

### 6.3 llm_rnc_geracoes

Campos: ID, empresa_id, triagem_id, aprovado_por_id, idempotency_key, request_hash, status, criado_em e concluido_em.

Estados: `processando`, `concluida`, `parcial` e `falha`. Restrições: unicidade de empresa/idempotency_key e vínculo à triagem da mesma empresa.

### 6.4 llm_rnc_geracao_itens

Campos: ID, geracao_id, empresa_id, triagem_issue_id, rnc_id, codigo_rnc_snapshot, dados_aprovados_json, status, erro_codigo e erro_mensagem_segura.

Restrições: unicidade de geração/candidata. O vínculo efetivo entre candidata e RNC deve ter proteção adicional contra geração duplicada em operações concorrentes, além da regra vigente de Issue/RNC.

O histórico mantém snapshot do código da Issue, código da RNC e critérios. Exclusões de entidades não podem apagar silenciosamente essa auditoria. Proposta: referências opcionais com `ON DELETE SET NULL` quando necessário e snapshots obrigatórios; validar a política de retenção antes da migração.

Os vínculos ativos entre empresas e entidades devem ser verificados na transação; usar chaves compostas de empresa/ID quando compatíveis com o schema. Não depender apenas de filtros de tela.

## 7. Execução da análise e adapter LLM

1. Autorizar empresa e validar acesso LLM ativo e elegibilidade de todas as Issues.
2. Gerar payload, snapshots e hashes.
3. Gravar a análise pendente e seus itens em transação curta.
4. Processador assume a análise e marca `processando`.
5. Ler a credencial no backend e preparar a chamada conforme o adapter do provedor.
6. Executar a requisição sem manter transação SQLite aberta.
7. Validar resposta estritamente.
8. Persistir resultado validado e marcar `concluida`, ou registrar falha segura.

Interface interna proposta:

```python
analisar_issues(acesso, instrucoes, issues, limites) -> ResultadoTriagem
```

O nome livre do provedor cadastrado não determina sozinho o protocolo. A implementação deve declarar adapters suportados e rejeitar configurações incompatíveis antes do envio. O primeiro adapter e seu contrato externo devem ser definidos e documentados na implementação; esta spec não presume compatibilidade universal.

Proposta de execução inicial: processador persistente no backend consultando trabalhos pendentes, adequado ao uso local com uma instância. Tarefas apenas em memória não oferecem recuperação de reinício. Uma implantação com múltiplos workers exige mecanismo de aquisição exclusiva e estratégia de recuperação antes de ser habilitada.

Análises interrompidas durante uma chamada externa devem ser marcadas como falha recuperável após reinício. Não reenviar automaticamente, pois o provedor pode ter processado a primeira chamada.

## 8. Prompt e validação do retorno

Versão inicial proposta: `triagem-rnc-v1`. Armazenar texto versionado no backend e registrar sua identificação/hash na análise.

O prompt deve estabelecer tríade, exclusões, proibição de inventar dados e saída JSON. Texto de Issue é dado não confiável e nunca substitui as instruções do sistema.

Resposta aceita:

```json
{
  "candidatas_rnc": [
    {
      "id_issue": 123,
      "titulo": "Resumo original",
      "justificativa": {
        "requisito_violado": "Requisito identificado",
        "fato_e_evidencia": "Fato e evidência mencionados",
        "criterios_ia": "Fundamentação da tríade"
      },
      "criticidade_sugerida": "ALTA"
    }
  ]
}
```

Validações obrigatórias:

- Um único objeto JSON; não aceitar cercas Markdown ou texto externo.
- Lista obrigatória; IDs inteiros pertencentes ao lote, sem duplicidade.
- Justificativas obrigatórias, textuais, não vazias e dentro dos limites.
- Criticidade com valor exato do enum; não normalizar classificação desconhecida silenciosamente.
- Campos inesperados devem ser rejeitados pelo contrato estrito.
- Resposta cortada ou maior que o limite resulta em falha.
- Nenhuma parte de um retorno inválido deve ser publicada como resultado válido.

O título do modelo não substitui o resumo nem o código do cadastro. Validar o formato não comprova a veracidade da análise: a revisão humana continua obrigatória.

## 9. Integridade na emissão de RNC

Antes de emitir, validar confirmação explícita, acesso à análise concluída, pertencimento e seleção das candidatas, completude dos dados da RNC e política de vínculo vigente.

Para cada candidata:

1. Abrir transação curta com controle de escrita.
2. Recarregar a Issue e conferir elegibilidade.
3. Recalcular o hash dos campos enviados; divergência relevante resulta em `issue_alterada`.
4. Verificar vínculo anterior e restrições de unicidade.
5. Invocar o serviço compartilhado de emissão na mesma transação.
6. Gravar vínculo de análise, critérios da IA e dados aprovados.
7. Confirmar a transação e atualizar o resultado da candidata.

Falha em qualquer passo reverte a emissão e seus vínculos daquele item. Os demais itens podem continuar: o PRD admite resultado parcial.

Hash de snapshot não deve depender de um timestamp genérico de atualização quando o conteúdo enviado permanece idêntico. Por outro lado, mudança de status para fechado ou existência de RNC bloqueia a candidata mesmo que o hash textual seja igual.

Se a resposta HTTP for perdida, a consulta da geração recupera o resultado. Repetir a mesma chave retorna a operação existente; reprocessar pendências exige nova chave e não pode incluir candidatas já emitidas.

O fechamento automático da Issue segue a regra de emissão vigente quando reutilizada. Qualquer intenção de mudar essa regra por causa do novo fluxo depende de decisão explícita, conforme a pendência do PRD.

## 10. Tela e estados da SPA

Proposta de submenu: “Selecionar para RNC”, sem remover Capturar, Dashboard ou Limpeza.

Bloco inicial: empresa, acesso LLM, filtros, contador, checklist paginado, seleção de todas as linhas visíveis e “Analisar com IA”. Seleção de uma página não seleciona registros invisíveis automaticamente.

Bloco de acompanhamento: número da análise, quantidade enviada, status e mensagem de falha segura. Proposta: polling a cada dois segundos durante processamento, interrompido em estado terminal ou ao sair da tela.

Bloco de candidatas: segundo checklist, nenhuma pré-selecionada, resumo original, requisito, fato/evidência, critérios e criticidade sugerida. Permitir consulta da Issue e preenchimento dos obrigatórios da RNC antes de confirmar.

Bloco de resultado: por candidata, código da Issue, código da RNC ou pendência. Disponibilizar retomada apenas dos itens pendentes.

Ao trocar empresa: cancelar polling, limpar seleção, resultados e IDs de edição. Respostas antigas devem ser descartadas se empresa/análise não corresponderem ao estado atual. Alterações de filtro não devem selecionar novos registros automaticamente.

Ao expirar sessão: suspender ações e solicitar autenticação pelo mecanismo atual. Renderizar texto com `textContent` ou escaping; nunca usar HTML bruto do modelo.

## 11. Limites operacionais propostos

Valores iniciais para revisão, não definidos no PRD:

- Até 20 Issues por análise.
- Até 100 KB de JSON de entrada, medidos em UTF-8.
- Até 200 KB de resposta do modelo.
- Timeout externo total de 60 segundos.
- Uma análise em processamento por usuário e limite de empresa a definir.
- Sem retry automático da chamada ao provedor.
- Paginação padrão de 50, máxima de 100 registros.

Verificar orçamento de tokens e limite de saída do adapter. Se exceder o limite, solicitar redução do lote; não truncar fatos ou evidências silenciosamente. Parâmetros efetivos usados devem constar no histórico.

## 12. Segurança e observabilidade

- Sessão e permissões verificadas em todos os endpoints.
- Credenciais somente no backend e excluídas de logs, snapshots e respostas.
- URL do provedor aceita apenas conforme protocolo suportado; restringir destinos autorizados e revalidar redirecionamentos para impedir acesso indevido a serviços internos.
- Integração externa não pode acessar arquivos, executar ferramentas ou comandos.
- Proibir instruções embutidas nas Issues de controlar a chamada ou alterar o contrato.
- Registrar IDs de operação, empresa, duração, contagens e códigos de erro seguros.
- Não gravar payload completo em logs operacionais; snapshots ficam no histórico sujeito à política de acesso e retenção.
- Medir taxas de candidatura, aprovação, geração, falha e duração. Metas continuam pendentes.

## 13. Migração e compatibilidade

- Criar somente tabelas e índices adicionais necessários.
- Não apagar nem recriar Issues, RNCs, ações, usuários ou anexos.
- Migração idempotente, com backup anterior à aplicação na base real.
- Extrair serviço de emissão com testes que comparem o comportamento antes/depois.
- Preservar códigos e relações existentes; código da RNC continua gerado pelo serviço de emissão.
- Cadastros antigos não recebem candidaturas ou justificativas artificiais.
- Não chamar o LLM durante inicialização do banco ou abertura da tela.
- Nenhuma análise implica alteração do status de Issue.

## 14. Plano de testes e rastreabilidade

| Grupo | Cobertura e ligação ao PRD |
| --- | --- |
| Elegibilidade e checklist | CA-01, CA-02, CA-03: seleção, filtros, fechadas e lote exato |
| Triagem revisada pelo SGQ | CA-04, CA-05, CA-06: tríade, melhoria, evidências insuficientes |
| Retorno do adapter | CA-07, CA-08, CA-09: vazio, válido, IDs indevidos, duplicados, JSON e enum inválidos |
| Aprovação e geração | CA-10, CA-11: seleção parcial, obrigatórios, vínculo e critérios persistidos |
| Idempotência e concorrência | CA-12: duplo clique, mesma chave e geração simultânea da mesma Issue |
| Snapshot e status | CA-13: alteração relevante, alteração irrelevante, fechamento e vínculo após análise |
| Erros externos | CA-14: timeout, autenticação, limite, indisponibilidade e resposta truncada |
| Permissões e tenancy | CA-15: editor, admin, visualizador e acesso entre empresas |
| Transações e retomada | CA-16: falha de um item, rollback, recuperação e retomada de pendências |

Testes do sistema usam adapter falso e banco temporário. Nenhum teste padrão chama API real ou usa credenciais de produção. Avaliação do modelo real é separada, explicitamente autorizada e baseada em amostra revisada pelo SGQ.

Testes adicionais: reinício com análise pendente/processando, exclusão de acesso LLM, troca de empresa durante polling, sessão expirada, conteúdo malicioso, ausência de chave em respostas e nenhuma regressão nos módulos existentes.

## 15. Decisões pendentes e propostas de resolução

1. Aprovar nome do submenu e papéis admin/editor para análise e emissão.
2. Aprovar seleção explícita de acesso LLM ativo por empresa e primeiro adapter suportado.
3. Aprovar limites iniciais, processamento persistente e política de retomada.
4. Definir matriz BAIXA/MÉDIA/ALTA; manter a sugestão separada da criticidade obrigatória da RNC, sem mapeamento implícito.
5. Definir tela de complementação dos dados obrigatórios da RNC antes da emissão.
6. Confirmar comportamento de encerramento da Issue sem alterar o fluxo vigente por suposição.
7. Confirmar bloqueio de Issue já vinculada a RNC ou outra política expressa.
8. Validar pelo SGQ o critério de correção local versus RNC e ação corretiva.
9. Definir retenção e exclusão do histórico, além dos efeitos sobre limpeza da base.
10. Confirmar que não selecionar candidata não exige motivo nesta primeira versão.

Essas propostas tornam a discussão técnica concreta. Elas não encerram as decisões de produto do PRD e não autorizam mudanças nas funcionalidades existentes.

## 16. Ordem de implementação

1. Resolver pendências de emissão, adapter e permissões.
2. Criar schema aditivo, modelos estritos e serviço de emissão compartilhado com regressão.
3. Implementar consultas, seleção e snapshots, sem chamada externa.
4. Implementar adapter, processamento e validação com respostas controladas.
5. Implementar revisão humana e complementação dos dados da RNC.
6. Implementar emissão transacional, idempotência e resultados parciais.
7. Validar todos os critérios de aceite e depois avaliar a triagem com o SGQ.

Condição de conclusão: critérios do PRD atendidos, pendências resolvidas, testes relevantes passando, rastreabilidade comprovada e comportamento atual preservado.
