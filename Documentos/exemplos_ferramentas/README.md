# Base simulada para ferramentas da qualidade

Carga de 14/10/2026 na Empresa teste. Todas as informações novas são simuladas para exercícios; não representam resultados reais. Foram preservados os 37 registros de Issue e a RNC existentes.

Foram criadas 40 Issues (ISSUE-0038 a ISSUE-0077). As primeiras 30 originaram RNC-2026-002 a RNC-2026-031; suas Issues estão fechadas conforme a regra vigente de emissão. As últimas dez permanecem abertas, cinco cadastradas e cinco em tratamento. Toda nova RNC desta carga tem uma nova Issue de origem.

Cada RNC possui observações quantitativas, hipótese com teste proposto, uma ação 5W2H e uma pendência de avaliação de eficácia. As ações estão distribuídas pelas cinco raias. As RNCs permanecem emitidas; não se registraram aprovações ou encerramentos em nome de usuários. Carlos é o único usuário da empresa disponível, portanto os responsáveis usam seu cadastro; equipes e turnos do exercício são identificações textuais simuladas.

## Dados para exercícios

`amostras_simuladas.json` relaciona os códigos da Issue/RNC a lotes, categorias, turnos, quantidades inspecionadas/não conformes, temperatura de selagem (°C), tempo de contenção (h) e cinco comprimentos individuais (mm). As mesmas contagens e medições constam nas evidências textuais das Issues e nas observações das RNCs. Não há anexos físicos de evidência nesta carga.

- Folha de verificação: uma unidade com categoria principal única; total inspecionado e não conformes por lote. O conjunto só contém ocorrências; não permite estimar a frequência geral da empresa.
- Pareto: usar as 30 RNCs simuladas, com 12 de etiqueta, 8 de selagem, 5 de dimensão, 3 de atraso e 2 de material. Separar contagem de ocorrências, unidades afetadas e custo.
- Histograma: analisar tempos de contenção; para comprimentos, separar produto e categoria antes de agrupar.
- Dispersão: explorar temperatura versus proporção não conforme nos lotes de selagem. A relação é sintética e não comprova causalidade.
- Carta p: os primeiros 30 lotes (`serie_controle=true`) formam uma série didática cronológica, com denominador variável e mudança construída após o lote 20. Usar os primeiros 20 para estudar a referência e os seguintes para monitoramento; verificar hipóteses e comparabilidade. Não usar os limites como especificação ou prova real de eficácia. `fase` é apenas a fase da simulação, sem execução real de uma ação.
- Fluxograma: mapear detecção, segregação, registro, emissão, investigação, plano e avaliação pendente.
- Ishikawa: usar as hipóteses dos registros, testar e registrar evidências antes de concluir causas.
- Afinidades: agrupar descrições e relatos preservando o vínculo com cada código.
- Árvore: desdobrar redução de falhas em controles de arquivos, selagem, dispositivos e passagem de turno.
- Matriz: relacionar hipóteses/causas validadas a ações e critérios de aceite; o banco não recebeu uma nova ferramenta gráfica.

## Reprodução e proteção

`_popular_ferramentas.py` sem argumentos ensaia numa cópia em memória. `--apply` faz backup e grava em uma transação, verificando integridade, vínculos e preservação dos registros anteriores. O identificador `SIM-FERR-20261014` impede executar a mesma carga novamente. A emissão utiliza o serviço existente, que vincula RNC/Issue, preserva fatos e cria ação no Backlog; a carga distribui apenas suas próprias ações nas raias.

Backup anterior à carga: `data/backups/qualidade_antes_ferramentas_20261014T125345103801Z.db`.
