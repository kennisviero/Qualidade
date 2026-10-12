# Ferramentas da qualidade

Guia prático para registro, investigação e tratamento de Issues e RNCs. Edição: 12/10/2026.

Este guia reúne dez ferramentas: sete ferramentas básicas, adotando o fluxograma como a sétima, e três ferramentas de gestão e planejamento. A ASQ registra variações na lista básica, incluindo estratificação ou gráfico de sequência no lugar do fluxograma. Os exemplos abaixo são didáticos e simulados; não representam os dados da aplicação.

## Como escolher a ferramenta

| Necessidade | Ferramenta indicada | Resultado esperado |
| --- | --- | --- |
| Coletar ocorrências de modo consistente | Folha de verificação | Dados comparáveis |
| Priorizar categorias de problemas | Pareto | Ordem de atenção |
| Examinar distribuição de medidas | Histograma | Perfil da variação |
| Explorar relação entre duas medidas | Dispersão | Hipótese de associação |
| Acompanhar estabilidade no tempo | Carta de controle | Sinais de variação especial |
| Entender etapas e decisões | Fluxograma | Mapa do processo |
| Organizar hipóteses de causas | Ishikawa | Hipóteses para testar |
| Organizar relatos e ideias | Afinidades | Grupos temáticos |
| Desdobrar objetivo em ações | Árvore | Estrutura do plano |
| Relacionar requisitos e ações | Matriz | Vínculos e lacunas |

## 1. Folha de verificação

**Finalidade:** registrar observações em um formulário padronizado, usando categorias e marcações ou contagens. É um instrumento de coleta de dados, diferente de um checklist que apenas confirma execução de atividades.

**Quando usar:** na captura de Issues, em inspeções repetitivas ou quando faltam dados comparáveis para investigar uma RNC.

**Dados necessários:** definição operacional do defeito, unidade observada, período, categoria, local, turno e quantidade inspecionada. Definir se uma unidade pode ter mais de um defeito e como evitar contagem duplicada.

**Exemplo Issues/RNCs:** durante cinco dias, registrar por turno falhas de embalagem, etiqueta e dimensão. Anotar também o total de peças inspecionadas. As Issues recebem evidências rastreáveis, e a RNC pode comparar taxas entre turnos, em vez de comparar somente quantidades brutas.

**Cuidado:** campos ambíguos produzem classificações inconsistentes. Testar o formulário com quem coleta os dados antes de ampliar o uso.

## 2. Diagrama de Pareto

**Finalidade:** ordenar categorias pelo tamanho de sua contribuição, com barras decrescentes e percentual acumulado. Ajuda a definir onde concentrar esforço.

**Quando usar:** quando existem vários tipos de Issues ou causas confirmadas e é necessário escolher prioridades por frequência, custo, tempo perdido ou outro indicador definido.

**Dados necessários:** categorias consistentes, período comum e uma medida somável. Escolher uma unidade por análise; não somar horas, reais e quantidades no mesmo eixo.

**Exemplo Issues/RNCs:** em 100 ocorrências simuladas, etiqueta representa 45, embalagem 30, dimensão 15 e outros 10. As duas primeiras categorias somam 75% das ocorrências. A equipe prioriza sua investigação e verifica separadamente os riscos de baixa frequência e alto impacto.

**Cuidado:** a relação 80/20 não é uma exigência matemática. Frequência alta não comprova causa raiz e não substitui avaliação de segurança ou criticidade.

## 3. Histograma

**Finalidade:** mostrar a distribuição de uma variável numérica em intervalos, evidenciando concentração, dispersão, assimetria e possíveis grupos distintos.

**Quando usar:** para compreender medidas de produto, tempo de atendimento ou duração de tratamento, antes de escolher testes ou ações.

**Dados necessários:** medidas individuais na mesma unidade, método de medição e amostra representativa. Registrar condições de coleta e definir intervalos adequados à resolução dos dados.

**Exemplo Issues/RNCs:** reunir o tempo, em horas, entre detecção e contenção de 60 Issues. Um grupo concentrado em até duas horas e outro acima de oito horas sugere separar os dados por turno ou tipo de ocorrência para investigar diferenças.

**Cuidado:** o histograma não preserva a ordem temporal. Pode esconder mudanças ocorridas durante a coleta; não permite concluir estabilidade do processo sozinho.

## 4. Diagrama de dispersão

**Finalidade:** explorar uma possível associação entre duas variáveis numéricas, representando cada par como um ponto.

**Quando usar:** para testar visualmente hipóteses de relação entre condições do processo e intensidade do problema.

**Dados necessários:** pares de medidas correspondentes à mesma unidade ou ao mesmo intervalo, unidades claras e condições de coleta. Dados de momentos ou lotes diferentes não devem ser emparelhados arbitrariamente.

**Exemplo Issues/RNCs:** para cada lote, relacionar temperatura de operação e percentual de peças rejeitadas. Uma tendência crescente orienta um teste controlado na investigação da RNC, considerando material, máquina e velocidade como possíveis fatores adicionais.

**Cuidado:** associação não demonstra causalidade. Ausência de tendência linear também não elimina relações não lineares ou efeitos de variáveis não observadas.

## 5. Carta de controle

**Finalidade:** acompanhar uma estatística do processo no tempo, com linha central e limites de controle calculados. Ajuda a distinguir variação comum de sinais compatíveis com causas especiais.

**Quando usar:** no acompanhamento de um processo repetitivo, na identificação de mudanças e na verificação sustentada da eficácia de ações corretivas.

**Dados necessários:** série temporal, definição de amostragem, tamanho das amostras ou subgrupos e tipo de dado. Escolher uma carta apropriada: por exemplo, I-MR para medidas individuais ou p para proporção de unidades não conformes, respeitando suas hipóteses.

**Exemplo Issues/RNCs:** acompanhar semanalmente a proporção de unidades com etiqueta incorreta, registrando o número inspecionado em cada semana. Após uma ação da RNC, observar se há mudança sustentada com as regras de interpretação definidas previamente.

**Cuidado:** limites de controle não são limites de especificação. Um processo estável ainda pode não atender ao requisito. Não recalcular limites a cada sinal para fazer o problema desaparecer; avaliar comparabilidade, volume produzido e mudanças de processo.

## 6. Fluxograma

**Finalidade:** representar a sequência de atividades, decisões, entradas e saídas de um processo para tornar seu funcionamento compreensível.

**Quando usar:** ao investigar falhas de passagem entre equipes, aprovações, retrabalho, atrasos ou diferenças entre o procedimento e a prática.

**Dados necessários:** etapas reais, responsáveis, critérios das decisões, documentos utilizados, exceções e pontos de retorno. Validar o desenho com quem executa o trabalho.

**Exemplo Issues/RNCs:** mapear detecção, registro da Issue, contenção, análise de elegibilidade, aprovação da emissão da RNC, investigação, plano e verificação de eficácia. Identificar em qual passagem uma evidência deixa de chegar ao responsável e incluir uma ação verificável no plano.

**Cuidado:** distinguir processo atual de processo proposto. Um desenho idealizado pode ocultar a origem do desvio. Este exemplo descreve um fluxo de gestão, sem afirmar que todas as etapas já estejam implementadas no sistema.

## 7. Diagrama de Ishikawa

**Finalidade:** organizar causas possíveis e subcausas em torno de um efeito claramente definido. Também conhecido como diagrama de causa e efeito ou espinha de peixe.

**Quando usar:** na investigação da RNC, especialmente quando a equipe precisa explorar várias linhas de explicação antes de testar hipóteses.

**Dados necessários:** descrição objetiva do efeito, observações do processo, evidências disponíveis e participação de pessoas que conheçam a operação. As categorias podem seguir os 6Ms ou ser adaptadas ao contexto.

**Exemplo Issues/RNCs:** para o efeito “etiqueta com código de outro produto”, organizar hipóteses em método, sistema, material e pessoas: arquivo antigo, seleção manual, mistura de rolos e instrução ambígua. Para cada hipótese, definir teste, responsável, prazo e evidência esperada na investigação.

**Cuidado:** o diagrama reúne hipóteses; não comprova causas. Confirmar ou rejeitar cada hipótese com evidências, evitando atribuir culpa a pessoas sem análise do processo.

## 8. Diagrama de afinidades

**Finalidade:** agrupar muitos relatos, ideias ou observações por semelhança de significado, permitindo reconhecer temas recorrentes.

**Quando usar:** após entrevistas, brainstorming ou leitura de descrições de Issues, quando o material é qualitativo e ainda não há categorias claras.

**Dados necessários:** registros curtos, com uma ideia por item, mantendo o vínculo com a origem. A equipe agrupa por afinidade e só depois nomeia os grupos.

**Exemplo Issues/RNCs:** reunir 40 relatos simulados de dificuldade operacional e formar grupos como instruções ambíguas, acesso à informação e passagem de turno. Os grupos ajudam a planejar coleta adicional e a definir categorias para futuras Issues.

**Cuidado:** afinidade semântica não mede frequência real nem demonstra causalidade. Preservar relatos divergentes e evitar que um participante imponha os grupos antecipadamente.

## 9. Diagrama de árvore

**Finalidade:** desdobrar um objetivo amplo em níveis sucessivos de meios, entregas ou tarefas, tornando o planejamento executável.

**Quando usar:** após definir o problema e a direção da solução, para estruturar o plano de ação de uma RNC e verificar se as ações cobrem o objetivo.

**Dados necessários:** objetivo mensurável, restrições, entregas necessárias e conhecimento das atividades. Nos níveis finais, definir responsável, prazo, recursos e critério de aceite.

**Exemplo Issues/RNCs:** desdobrar “reduzir erros de etiqueta” em controlar arquivos, validar impressão e capacitar operadores. Controlar arquivos se divide em revisão aprovada, retirada de versões antigas e teste de acesso. As tarefas finais alimentam a matriz 5W2H da RNC.

**Cuidado:** uma lista de tarefas só é útil se cada ramo contribuir para o objetivo. Verificar suficiência do conjunto e dependências entre ações; a árvore não calcula cronograma sozinha.

## 10. Diagrama de matriz

**Finalidade:** mostrar relações entre dois ou mais conjuntos de informações, como requisitos, causas, ações e responsáveis. Pode indicar presença, intensidade ou natureza do vínculo.

**Quando usar:** para verificar cobertura do plano, explicitar responsabilidades e encontrar requisitos ou causas confirmadas sem ação correspondente.

**Dados necessários:** listas claras de elementos e uma legenda comum para os vínculos. Se forem usadas pontuações, definir previamente critérios e significado da escala.

**Exemplo Issues/RNCs:** colocar causas confirmadas nas linhas e ações propostas nas colunas. Marcar relação forte, média ou ausente. Uma causa sem relação com nenhuma ação sinaliza uma lacuna; uma ação sem relação com qualquer causa exige justificativa.

**Cuidado:** diagrama de matriz não é automaticamente matriz de priorização. Para escolher alternativas com pesos e notas, é necessário definir um método de decisão e testar a sensibilidade dos resultados.

## Gráficos estatísticos e diagramas de planejamento

| Grupo | Ferramentas deste guia | Pergunta principal |
| --- | --- | --- |
| Análise quantitativa | Pareto, histograma, dispersão e carta de controle | O que os dados mostram? |
| Coleta estruturada | Folha de verificação | Como obter dados confiáveis? |
| Processo e investigação | Fluxograma e Ishikawa | Como o trabalho ocorre e quais causas testar? |
| Gestão e planejamento | Afinidades, árvore e matriz | Como organizar informações e estruturar o plano? |

Os gráficos quantitativos dependem de medidas e contagens confiáveis. Pareto descreve contribuições por categoria; histograma descreve distribuição; dispersão explora associações; carta de controle examina comportamento temporal. Cada um responde a uma pergunta diferente.

Os diagramas de planejamento organizam conhecimento e decisões, podendo utilizar dados qualitativos. Eles não substituem evidências estatísticas. Da mesma forma, um gráfico não define sozinho quem executará uma ação, qual seu prazo ou como sua eficácia será avaliada.

## Sequência sugerida de aplicação

1. **Delimitar a ocorrência:** registrar na Issue o esperado, o observado, quando, onde, impacto e evidências. Aplicar contenção conforme o risco, sem aguardar toda a análise.
2. **Entender e coletar:** desenhar o fluxograma do processo real e preparar a folha de verificação. Usar afinidades quando os relatos ainda estiverem dispersos.
3. **Priorizar:** construir Pareto com indicador e período definidos. Estratificar os dados por turno, produto, equipe ou ambiente quando pertinente, sem perder o denominador das taxas.
4. **Investigar:** usar histograma para distribuição, dispersão para associações e Ishikawa para estruturar hipóteses. Na RNC, registrar testes e conclusões sustentados por evidência.
5. **Planejar:** desdobrar soluções na árvore, verificar cobertura na matriz e detalhar ações em 5W2H com responsáveis, prazos e critérios de aceite.
6. **Executar e avaliar:** acompanhar ações e coletar dados comparáveis antes e depois. Quando houver processo repetitivo e amostragem adequada, usar carta de controle para monitorar estabilidade e mudança sustentada.
7. **Padronizar e acompanhar:** documentar o resultado, revisar instruções, comunicar a equipe e manter o acompanhamento de recorrências. Concluir a RNC conforme critérios de eficácia e aprovação definidos pela organização.

A sequência é uma orientação, não uma obrigação de usar todas as ferramentas. Escolher as necessárias à pergunta e aos dados disponíveis. Exemplos e aplicações deste guia são adaptações didáticas ao contexto de Issues/RNCs.

## Referências da ASQ

Referências consultadas em 12/10/2026. As explicações são paráfrases e aplicações próprias, sem reprodução extensa das fontes.

- [Catálogo de ferramentas da qualidade](https://asq.org/quality-resources/quality-tools)
- [Sete ferramentas básicas da qualidade](https://asq.org/quality-resources/seven-basic-quality-tools)
- [Sete ferramentas de gestão e planejamento](https://asq.org/quality-resources/new-management-planning-tools)
- [Folha de verificação](https://asq.org/quality-resources/check-sheet)
- [Carta de controle](https://asq.org/quality-resources/control-chart)

