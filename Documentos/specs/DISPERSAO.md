# Ferramentas → 3-Diagrama de Dispersão

Consulta autenticada, por empresa, somente leitura. Radio buttons Issues/RNCs e filtros iguais aos do Pareto/Histograma. Issues somente cadastradas/em tratamento, sem finalização e sem RNC. RNCs usam os fatos preservados e as observações próprias.

Escolha de duas medidas diferentes entre as disponíveis no Histograma: Issues — idade desde cadastro e detecção até cadastro; RNCs — idade desde emissão, detecção até emissão/contenção, horas perdidas, quantidade afetada e prejuízo. O instante de referência das idades é único por análise. Quantidade e custo exigem unidade/moeda comparável. Não extrai números de textos livres.

Cada ponto contém X e Y do mesmo registro, identificado por ID; não emparelha listas independentes. Pares incompletos, valores negativos/não finitos e datas ausentes para o período ficam fora, com contagens no resultado. Zero informado é válido. Dados completos mantêm precisão; exibição numérica com duas casas.

Correlação de Pearson somente com ao menos dois pares e variação em ambos os eixos. Sem condições, mostra Não disponível. Não infere causalidade nem regressão automática. Pontos coincidentes podem se sobrepor; a tabela mantém todos os registros. Os custos da carga simulada foram construídos com quantidade e horas, portanto suas relações não são evidência independente.

GET `/api/ferramentas/dispersao`: opções, eixos/unidades, pontos, contagens, correlação e snapshot assinado de consulta IA. Botão Consultar IA segue o componente compartilhado: prompt editável + filtros/dados/resultado, sem chamada antes do envio explícito. Clique no ponto filtra a tabela pelo ID. Mudanças invalidam resultados e consultas antigas; respostas obsoletas são descartadas. Sem Plotly, tabela continua disponível.

Testes: `tests/test_dispersao.py`, `tests/check_dispersao.cjs`, regressões de Pareto/Histograma/consulta IA.
