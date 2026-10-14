# Ferramentas → 2-Histograma

Menu Ferramentas numerado: 1-Pareto e 2-Histograma. Histograma representa a distribuição de uma medida numérica por registro em intervalos de mesma largura, em ordem crescente. Não contém ordenação por frequência nem percentual acumulado.

Reutiliza a consulta autenticada e os filtros de Pareto: empresa, base Issues/RNCs, período, categoria, impacto, ambiente, local, status, pessoa, envolvidos, simulados e classificação da RNC. Issues elegíveis exclusivamente cadastradas/em tratamento, sem finalização e sem RNC. RNCs usam os fatos preservados e observações próprias. A ferramenta não escreve na base.

Medidas de Issues: idade desde cadastro (dias) e detecção → cadastro (horas). Medidas de RNCs: idade desde emissão (dias), detecção → emissão (horas), detecção → contenção (horas), horas perdidas, quantidade afetada e prejuízo. Idade calculada no instante único informado em `gerado_em`. Datas sem timezone usam UTC−03:00; tempos exigem data e hora completas. Contenção usa `contencao_em`, com fallback para `data_conclusao_contencao`. Dados negativos/inválidos e ausentes são contados separadamente e excluídos da distribuição; zero informado é válido. Não extrai medições de textos livres nem inventa valores.

Quantidade afetada e prejuízo exigem unidade/moeda comparável: formulário exige seleção; backend rejeita combinações heterogêneas. Medidas são valores individuais por registro, sem somar categorias como no Pareto.

Intervalos automáticos pela regra de Sturges (ceil(log2(n))+1, máximo 50), ou número informado de 1 a 50. Valores todos iguais recebem um único intervalo. Início incluído, fim excluído; último inclui o máximo. Valores sem arredondamento para atribuição; rótulos exibem até seis casas. Frequências somam exatamente a amostra válida. Estatísticas: tamanho da amostra, mínimo, máximo, média, mediana e desvio padrão amostral (somente n≥2).

`GET /api/ferramentas/histograma`. Gráfico com barras contíguas, tabela de intervalos/frequência/percentual e detalhamento por clique. Mudanças de base/empresa limpam filtros/resultados; mudanças de filtros invalidam resultados; respostas obsoletas descartadas. Tabelas disponíveis mesmo sem Plotly.

Testes: `tests/test_histograma.py`, `tests/check_histograma.cjs` e regressão `tests/test_pareto.py` / `tests/check_pareto.cjs`.
