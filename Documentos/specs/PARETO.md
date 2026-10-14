# Ferramentas → Pareto

Consulta autenticada e somente leitura, por empresa selecionada no cabeçalho. Issues e RNCs são bases alternativas; uma ocorrência não é somada nas duas bases na mesma análise.

Regra de elegibilidade autorizada: a base Issues inclui exclusivamente registros `cadastrada` ou `em_tratamento`, sem data de finalização e sem RNC vinculada. Issues fechadas/finalizadas e Issues com RNC são excluídas antes da construção das opções, totais, gráfico e detalhamento. Esta regra é obrigatória no backend e não pode ser ampliada por filtros; o seletor de vínculo foi ocultado na interface. A base RNC continua usando os registros emitidos e seus filtros próprios.

Radio buttons Issues/RNCs precedem os filtros. Período por detecção/cadastro (Issues) ou detecção/emissão (RNCs), datas inclusivas no horário UTC−03:00. Filtros por categoria, impacto, ambiente, local, status, autor (Issues) ou responsável com fallback para líder (RNCs), envolvidos, dados simulados identificados, vínculo da Issue com RNC e classificação maior/menor da RNC.

A categoria usa `issues.o_que`; na RNC utiliza `fatos_snapshot_json.o_que`, preservando a descrição da emissão. Não existe nova inferência automática de categoria ou alteração nos registros. Textos livres equivalentes só se agrupam quando diferem por acentos, maiúsculas ou espaços. Classificações semânticas futuras exigem cadastro padronizado. Valores ausentes ficam em Não informado. Simulados são identificados pelos textos existentes e pelo prefixo SIM-FERR; ausência de marca não certifica que um registro é real.

Agrupamento por categoria, impacto, ambiente, local, status, pessoa ou envolvidos; RNC também por maior/menor. Medida padrão: número de registros. RNCs permitem quantidade afetada, horas perdidas e prejuízo em `rnc_observacoes`. Quantidades e custos exigem unidade/moeda comparável; o formulário solicita escolha explícita. API rejeita mistura de unidades/moedas. Medidas ausentes/inválidas não são convertidas em zero e são contabilizadas separadamente. Valor zero informado é válido. Não agrega ações ou hipóteses, evitando multiplicação de ocorrências por joins.

`GET /api/ferramentas/pareto` retorna opções disponíveis na empresa/base, resultados em ordem decrescente, percentual/acumulado, totais e registros de origem. Reutiliza `calculations.pareto`. Filtros e enumerações são validados; tenancy usa a regra existente de Issues, incluindo rejeição 403 de empresa alheia. A consulta não migra schema nem escreve na base.

Barras + linha acumulada + referência de 80%, tabela de contribuições e detalhamento por clique em barra/categoria. Alterar base/empresa limpa filtros e resultados; alterar filtro invalida resultado anterior. Respostas obsoletas são descartadas. Se Plotly estiver indisponível, as tabelas permanecem disponíveis.

Verificação: `tests/test_pareto.py`, `tests/check_pareto.cjs`, suíte backend completa e scripts de regressão das telas RNC/seleção.
