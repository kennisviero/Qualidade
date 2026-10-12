# PRD — Seleção de Issues e geração de RNCs com apoio de IA

Versão: 1.0  
Data: 11/10/2026  
Status: Proposta para revisão  
Fonte exclusiva: `documentos/Pre_prd.txt`

## 1. Objetivo

Criar uma rotina e uma tela no menu Issues para selecionar ocorrências abertas ou em tratamento, submetê-las à IA e apresentar as candidatas à emissão de Relatório de Não Conformidade (RNC). A geração depende de seleção e confirmação do usuário. Cada RNC deve preservar o vínculo com a Issue original e os critérios utilizados pela IA.

O resultado esperado é uma triagem consistente, com menor esforço manual e decisões rastreáveis, reduzindo classificações incorretas sem delegar a decisão final à IA.

Este PRD organiza o documento-fonte. Regras operacionais acrescentadas para tornar o fluxo implementável estão identificadas como propostas; não representam validação independente das interpretações de ISO presentes na fonte.

## 2. Escopo

Incluído:

- Tela de seleção de Issues no menu Issues.
- Checklist inicial de Issues abertas e em tratamento.
- Envio das Issues selecionadas a uma API de modelo LLM.
- Triagem pela tríade requisito, fato e evidência objetiva.
- Checklist de candidatas, com justificativas e criticidade sugerida.
- Geração de RNCs aprovadas pelo usuário.
- Rastreabilidade entre Issue, análise da IA e RNC.
- Tratamento de respostas vazias, inválidas e falhas da API.

Fora do escopo desta entrega:

- Execução completa de contenção, investigação de causa raiz, plano de ação e eficácia da RNC.
- Decisão automática de abertura de RNC sem aprovação humana.
- Inferência de requisitos que não constem dos dados enviados.
- OCR, leitura automática de imagens e interpretação de arquivos anexos. A fonte solicita evidências mencionadas nos dados da Issue; não define processamento dos arquivos.
- Construção de uma matriz formal de criticidade ou configuração do CRUD de credenciais LLM. A forma de disponibilizar o acesso ao modelo é uma dependência a definir.

## 3. Usuários e responsabilidades

- Usuário responsável pela triagem: seleciona Issues, solicita análise, revisa candidatas e confirma a geração das RNCs.
- IA: avalia exclusivamente o contexto recebido e sugere candidatas, justificativas e criticidade.
- Sistema: valida a resposta, mantém a rastreabilidade e executa a geração autorizada.

Proposta: as permissões de analisar e gerar devem acompanhar as permissões de escrita do módulo Issues. A definição dos papéis autorizados deve ser aprovada antes da implementação.

## 4. Fluxo principal

1. Usuário abre a opção “Seleção de Issues para RNC” no menu Issues.
2. Sistema apresenta Issues abertas e em tratamento, com caixa de seleção por registro.
3. Usuário seleciona uma ou mais Issues e aciona “Analisar com IA”.
4. Sistema monta uma lista JSON com os dados disponíveis dos registros selecionados.
5. Sistema envia a lista ao modelo com o prompt de triagem.
6. IA retorna JSON contendo `candidatas_rnc`.
7. Sistema valida o retorno e apresenta um segundo checklist, somente com candidatas válidas.
8. Usuário consulta requisito violado, fato/evidência, critérios da IA e criticidade sugerida.
9. Usuário seleciona as candidatas que deseja aprovar e aciona “Gerar RNCs”.
10. Sistema cria as RNCs, vinculando cada uma à Issue originária e à análise utilizada.
11. Sistema apresenta o resultado da operação, com os códigos de Issue e RNC e eventuais pendências.

A análise não gera RNCs automaticamente. Candidatas não selecionadas não são convertidas.

## 5. Regras de classificação

### 5.1 Tríade obrigatória

Uma Issue só pode ser sugerida como candidata quando houver os três elementos:

- **Requisito:** regra, norma, instrução de trabalho, especificação, contrato ou lei identificável, com indicação do que deveria ser cumprido.
- **Fato:** desvio real, descrito de forma objetiva, que contrarie o requisito.
- **Evidência objetiva:** dados ou registros mencionados que sustentem a ocorrência do fato e o descumprimento do requisito.

A avaliação deve utilizar os campos enviados e seu contexto textual. A IA não pode inventar normas, fatos, medições ou evidências para completar informações faltantes.

### 5.2 Categorias de requisito

| Categoria | Exemplos apresentados na fonte |
| --- | --- |
| Normativo | Requisito de norma de gestão; gerenciamento de riscos |
| Interno da empresa | Instrução de trabalho ou etapa obrigatória de inspeção |
| Cliente / produto | Dimensão especificada ou prazo acordado |
| Legal / regulamentar | Licença ou laudo obrigatório |

### 5.3 Exclusões

- Oportunidades de melhoria quando os requisitos atuais são cumpridos.
- Reclamações vagas, opiniões ou percepções sem fatos e dados concretos.
- Erros menores, pontuais, isolados e já corrigidos, sem violação de processo estruturado e sem impacto, conforme a regra descrita na fonte.
- Registros sem um ou mais elementos da tríade.

Ponto de revisão: a fonte também admite tratar incidentes isolados de baixo impacto por correção local. A política que distingue correção local, registro de não conformidade e abertura de ação corretiva deve ser validada pelo responsável pelo SGQ. Baixa criticidade, por si só, não deve ser implementada como exclusão automática sem essa definição.

### 5.4 Criticidade sugerida

A saída da IA utiliza `BAIXA`, `MÉDIA` ou `ALTA`. A fonte não define uma matriz objetiva para atribuir esses níveis. Até a definição dessa matriz, a criticidade deve ser apresentada como sugestão da IA para revisão humana.

Se o cadastro de destino usar outra classificação, o mapeamento é uma decisão pendente; o sistema não deve converter valores silenciosamente.

## 6. Tela e interação

### 6.1 Checklist inicial

Cada linha deve mostrar, no mínimo:

- Seleção da Issue.
- Código da Issue.
- Resumo do fato.
- Status atual.
- Data da ocorrência, quando disponível.
- Impacto declarado, quando disponível.

Deve ser possível consultar os dados completos da Issue antes do envio. “Analisar com IA” fica indisponível sem seleção. Durante a chamada, o sistema informa que a análise está em andamento e impede submissões repetidas.

Propostas de usabilidade: selecionar todas as Issues visíveis, exibir quantidade selecionada e permitir filtrar por código e status. O limite de registros por análise deve ser definido conforme a capacidade do modelo.

### 6.2 Checklist de candidatas

Cada candidata deve exibir:

- Caixa de seleção para geração.
- Código e resumo da Issue originária.
- Requisito violado.
- Fato e evidência que sustentam a classificação.
- Critérios analíticos usados pela IA.
- Criticidade sugerida.

Proposta: nenhuma candidata inicia selecionada. O usuário deve confirmar a escolha de forma explícita. “Gerar RNCs” fica indisponível sem seleção ou durante a geração.

Se não houver candidatas, exibir “Nenhuma Issue atende aos critérios com os dados fornecidos”. Esse resultado não equivale a uma decisão definitiva de inexistência de não conformidade.

## 7. Dados enviados à IA

### 7.1 Conteúdo obrigatório

- Identificador e código da Issue para correlação.
- Descrição detalhada do fato observado.
- Requisito ou comportamento esperado.
- Evidências objetivas mencionadas.

Exemplo de representação proposta:

```json
{
  "id_issue": 123,
  "codigo_issue": "ISSUE-0123",
  "status": "em_tratamento",
  "fato": "Peça X-200 com rachadura após resfriamento.",
  "requisito": "IT-04 exige resfriamento por 20 minutos a 15 °C.",
  "evidencia": "Lote 4552, teste de ultrassom em 10/10/2026.",
  "origem": "Inspeção de qualidade",
  "area_processo": "Produção",
  "impacto": "Lote contido antes da expedição"
}
```

### 7.2 Contexto recomendado

- Origem ou canal de detecção.
- Área ou processo afetado.
- Impacto inicial declarado.
- Data, ambiente e ação emergencial, quando disponíveis e pertinentes.

O sistema deve mapear esses conceitos a campos existentes ou explicitamente definidos para a integração. Informações ausentes permanecem ausentes; não são preenchidas por suposição.

## 8. Contrato de saída da IA

A resposta deve ser exclusivamente um objeto JSON válido, sem Markdown, saudações ou comentários externos:

```json
{
  "candidatas_rnc": [
    {
      "id_issue": 123,
      "titulo": "Título da issue original",
      "justificativa": {
        "requisito_violado": "Regra ou requisito descumprido.",
        "fato_e_evidencia": "Fato e evidência mencionados na Issue.",
        "criterios_ia": "Análise da tríade que fundamenta a indicação."
      },
      "criticidade_sugerida": "ALTA"
    }
  ]
}
```

Sem candidatas:

```json
{"candidatas_rnc": []}
```

Validações propostas:

- `candidatas_rnc` deve ser uma lista.
- Cada `id_issue` deve pertencer ao lote efetivamente submetido.
- Uma Issue não pode aparecer duas vezes no mesmo resultado.
- As três justificativas devem estar presentes e preenchidas.
- Criticidade deve pertencer aos três valores definidos.
- Títulos e códigos mostrados na tela devem vir do registro original; o texto da IA não altera a identidade da Issue.
- Retorno inválido não pode gerar registros nem ser aceito silenciosamente.

## 9. Prompt de triagem

O prompt deve preservar a orientação central da fonte: especialista em SGQ e triagem, avaliação da tríade, exclusões e retorno estritamente estruturado.

Estrutura proposta para a integração:

1. Instrução de papel e objetivo da triagem.
2. Critérios obrigatórios de requisito, fato e evidência.
3. Exclusões de melhoria, opiniões e ocorrências insuficientemente fundamentadas.
4. Proibição de inventar informações e de tratar instruções contidas nas Issues como comandos.
5. Esquema JSON de saída.
6. Lista de Issues como dados separados das instruções.

A versão do prompt utilizada deve ser registrada com a análise. O texto da Issue é conteúdo a avaliar, e não instrução para o modelo.

## 10. Geração e rastreabilidade da RNC

Requisitos explícitos da fonte:

- Gerar somente as candidatas selecionadas pelo usuário.
- Preservar o código da Issue originária em cada RNC.
- Persistir os critérios usados pela IA para sugerir a candidata.

Dados de rastreabilidade propostos:

- Identificador e código da Issue.
- Identificador e código da RNC criada.
- Identificador do lote de análise.
- Justificativa completa e criticidade sugerida.
- Provedor e modelo utilizados, sem credenciais.
- Versão do prompt.
- Data/hora da análise e usuário solicitante.
- Data/hora da geração e usuário que aprovou.
- Versão ou cópia dos dados da Issue usados na análise.

Propostas de consistência:

- Verificar novamente a elegibilidade da Issue ao gerar a RNC.
- Se os dados relevantes mudarem após a análise, solicitar nova análise antes da geração.
- Impedir duplicidade por clique repetido ou reenvio da mesma operação.
- Validar os campos obrigatórios da RNC antes de confirmar a criação.
- A gravação de cada RNC e de seus vínculos deve ocorrer na mesma transação.
- Se houver processamento parcial do lote, informar quais registros foram criados e quais falharam, permitindo retomar somente as pendências.

A fonte não define se a geração fecha automaticamente a Issue nem como preencher os demais dados obrigatórios da RNC. Essas decisões estão pendentes e não devem ser presumidas neste PRD.

## 11. Estados e tratamento de falhas

Estados propostos da análise: seleção, enviando, concluída com candidatas, concluída sem candidatas e falha.

Estados propostos da geração: aguardando seleção, gerando, concluída e concluída com pendências.

- Sem acesso LLM disponível: informar a necessidade de configuração e não enviar dados.
- Falha de autenticação no provedor: informar erro de acesso sem mostrar a chave.
- Limite de uso ou indisponibilidade: informar falha e permitir nova tentativa explícita.
- Timeout: preservar a seleção e permitir tentar novamente.
- JSON inválido: rejeitar o retorno e registrar falha sem gerar RNCs.
- Issue removida, fechada ou já convertida: bloquear a geração dessa candidata e explicar a pendência.
- Falha de gravação: não deixar RNC sem vínculo e não apresentar sucesso indevido.

## 12. Requisitos não funcionais propostos

- Respeitar autenticação, permissões e isolamento por empresa.
- Chamar a API LLM pelo backend; nunca entregar credenciais ao navegador.
- Não registrar chaves de API em logs ou históricos de análise.
- Enviar somente dados das Issues selecionadas e necessários à triagem.
- Definir timeout, limite de lote e limite de tamanho por requisição.
- Manter trilha de auditoria da análise e da aprovação.
- Exibir o conteúdo devolvido pela IA como texto, sem executar HTML ou comandos.
- Usar mensagens claras sobre processamento, falhas e resultados.
- Informar quais dados são enviados a um provedor externo; política de retenção e acesso ao histórico precisa ser definida.

## 13. Critérios de aceite

| ID | Cenário | Resultado esperado |
| --- | --- | --- |
| CA-01 | Abertura da tela | Exibe checklist de Issues abertas e em tratamento |
| CA-02 | Nenhuma Issue selecionada | Analisar com IA permanece indisponível |
| CA-03 | Seleção de parte da lista | Somente as selecionadas são enviadas |
| CA-04 | Tríade completa | IA pode indicar candidata com justificativa e criticidade |
| CA-05 | Requisito ou evidência ausente | Não é candidata por mera suposição |
| CA-06 | Melhoria sem descumprimento | Não é indicada como candidata |
| CA-07 | Lista vazia de candidatas | Exibe mensagem e não cria RNC |
| CA-08 | Retorno válido | Mostra segundo checklist e justificativas completas |
| CA-09 | ID não enviado ou JSON inválido | Retorno é rejeitado; não há geração |
| CA-10 | Usuário aprova parte das candidatas | Gera somente as selecionadas |
| CA-11 | RNC gerada | Preserva código da Issue e critérios usados pela IA |
| CA-12 | Clique ou requisição repetida | Não cria RNC duplicada |
| CA-13 | Issue alterada após análise | Exige revisão ou nova análise conforme regra aprovada |
| CA-14 | Falha do provedor | Seleção permanece disponível e nenhum registro é criado |
| CA-15 | Outra empresa ou usuário sem permissão | Acesso bloqueado |
| CA-16 | Geração parcial | Exibe códigos criados e pendências por Issue |

Os resultados do modelo variam. Os cenários funcionais devem usar respostas controladas para validar o sistema; a qualidade da triagem deve ser avaliada separadamente com casos revisados pelo SGQ.

## 14. Indicadores propostos

- Quantidade de Issues submetidas à IA.
- Quantidade e proporção de candidatas retornadas.
- Quantidade de candidatas aprovadas pelo usuário.
- Quantidade de RNCs efetivamente geradas.
- Taxa de falhas de análise e geração.
- Tempo de resposta por lote.
- Falsos positivos e falsos negativos em amostra revisada pelo responsável pelo SGQ.

Metas quantitativas e tamanho da amostra não foram definidos na fonte.

## 15. Decisões pendentes antes da implementação

1. Nome final da opção no menu Issues e papéis autorizados.
2. Qual acesso LLM será usado e como o usuário o selecionará.
3. Limites por lote, timeout e política de nova tentativa.
4. Matriz para BAIXA / MÉDIA / ALTA e eventual mapeamento ao cadastro da RNC.
5. Preenchimento dos demais campos obrigatórios da RNC e momento de sua validação.
6. Se a geração encerra a Issue ou apenas cria o vínculo.
7. Política para uma Issue já vinculada a uma RNC.
8. Política de correção local versus abertura de RNC, validada pelo SGQ.
9. Retenção do histórico de análises e dados enviados ao provedor.
10. Tratamento de uma candidata que o usuário não aprova: a fonte pede seleção, mas não exige justificativa de rejeição.

## 16. Plano de entrega proposto

1. Aprovar decisões pendentes e contrato de integração.
2. Implementar checklist inicial e montagem do lote.
3. Implementar chamada ao LLM e validação do retorno.
4. Implementar revisão das candidatas e persistência da análise.
5. Implementar geração autorizada com vínculo e prevenção de duplicidade.
6. Validar critérios de aceite e qualidade de triagem com casos reais revisados pelo SGQ.

## 17. Nota sobre a referência normativa

O documento-fonte cita ISO 9000, ISO 9001 e o item 10.2. Essas referências foram preservadas como contexto do requisito de produto, sem consulta a normas ou outras fontes. A interpretação normativa e a política de classificação devem ser revisadas pelo responsável pelo SGQ antes de serem usadas como critérios definitivos.
