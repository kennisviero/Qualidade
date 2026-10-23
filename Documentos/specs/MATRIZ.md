# Diagrama de Matriz — problemas/fatores × ações

Disponível em **Ferramentas → 6-Diagrama de Matriz**. Compara problemas e fatores da investigação com ações reais dos planos. A matriz registra avaliações qualitativas do usuário; não determina causa raiz, prioridade ou eficácia automaticamente.

## Contextos

- **Uma RNC:** uma RNC da empresa selecionada, seus fatos preservados na emissão, investigação e ações vinculadas ao seu plano.
- **Geral:** de duas a vinte RNCs da mesma empresa. Cada linha identifica suas RNCs de origem; cada ação identifica a RNC dona do plano. Cruzamentos entre RNCs são propostas desta análise, sem transferir ações nem alterar planos.

Os filtros compartilham opções e critérios da base RNC do Pareto: período por detecção/emissão, dados simulados e dimensões contextuais. Clique em **Filtrar RNCs**, selecione os registros e gere a matriz. Os filtros ajudam a escolher a população; a fotografia gerada contém exatamente as RNCs selecionadas. Mudanças posteriores nos filtros não alteram a matriz já carregada.

## Interação

1. Confira **Registros de origem**. A linha inicial de cada RNC usa o comportamento observado no snapshot da emissão. Relatos acima de 2.000 caracteres recebem uma prévia identificada na linha; o texto integral permanece na origem e no snapshot. As colunas são ações existentes vinculadas simultaneamente à RNC e à sua Issue.
2. Edite as linhas ou adicione hipóteses/fatores, indicando RNCs de origem. Um fator marcado como evidenciado exige referência textual de evidência; a declaração é do usuário.
3. Selecione as ações consideradas nas colunas. A exclusão de uma coluna retira suas avaliações após confirmação.
4. Clique no cruzamento e escolha **Não avaliada**, **Nenhuma**, **Fraca**, **Média** ou **Forte**. Toda avaliação diferente de Não avaliada exige justificativa, inclusive Nenhuma. Evidência do cruzamento é opcional.
5. Clique em **Aplicar cruzamento**. Salvar e consultar IA exigem aplicar ou cancelar a edição pendente.
6. Revise os indicadores e salve manualmente. Reabra a matriz pelo seletor de matrizes salvas do contexto.

Uma linha sem relação positiva indicada pode continuar com avaliação pendente. O indicador “sem cobertura após avaliação completa” exige todas as células da linha avaliadas e nenhuma relação positiva. Sem colunas, não se conclui cobertura ausente. Ações excluídas aparecem separadamente das ações consideradas sem relação indicada. Não há pesos numéricos ou ranking automático.

## IA

Segue o componente compartilhado `ferramentas_ia.js`: **Consultar IA** prepara uma fotografia assinada da matriz atual, abre instruções editáveis, seleção de acesso e prévia dos dados. Somente **Enviar à IA** chama o provedor. O prompt distingue Uma RNC de Geral e pede identificação das origens, confronto com as ações, análise das justificativas, lacunas e perguntas de investigação.

A resposta aparece na janela e não altera automaticamente a matriz ou as RNCs. A resposta não é persistida na matriz. A revisão e a aplicação de sugestões são manuais. A fotografia contém fatos, observações, investigação, ações, linhas, células, justificativas e indicadores, vinculados à empresa e ao usuário. Implementação e testes não fazem chamadas reais ao provedor.

## Persistência e acesso

Tabela própria `matrizes`, com título, contexto, JSON da fotografia, autor, empresa, revisão e atualização. Admin/editor salvam; usuários autenticados da empresa consultam e exploram temporariamente. Superusuário escolhe uma empresa. Validação de origem e assinatura impede inserir ações de outra seleção ou alterar os dados fonte. A edição de uma matriz salva preserva empresa, contexto e seleção de RNCs; revisão desatualizada recebe 409.

Uma fotografia salva não sincroniza automaticamente alterações futuras das RNCs/ações. Gere outra matriz para obter fontes atualizadas. Limites: 20 RNCs, 40 linhas, 60 ações e 2.400 cruzamentos; seleções acima do limite de ações são rejeitadas, sem corte silencioso.

## API

- `GET /api/ferramentas/matriz/fontes`: filtros e RNCs disponíveis.
- `GET /api/ferramentas/matriz?empresa_id=…&contexto=rnc|geral&rnc_ids=…`: fotografia inicial assinada.
- `POST /api/ferramentas/matriz/preparar`: valida edição e assina a fotografia atual para IA, sem gravação.
- `GET/POST /api/ferramentas/matriz/diagramas`: lista por empresa/contexto ou salva.
- `GET/PUT /api/ferramentas/matriz/diagramas/{id}`: consulta ou atualiza com controle de revisão.

Não executa transições, aprovações ou gravações em Issues, RNCs ou ações. A aplicação de schema na base existente usa `_apply_matriz_schema.py`, com backup SQLite, comparação de todas as linhas anteriores, integridade e FKs.
