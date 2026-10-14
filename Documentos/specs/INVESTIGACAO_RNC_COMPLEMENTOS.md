# Complementos da investigação da RNC

Implementados em 2026-10-12. Todos os novos campos são opcionais.

Na aba Investigação, os blocos adicionais registram mudanças anteriores à ocorrência (descrição, data/hora e configurações anterior/atual), abrangência (itens afetados e verificados sem falha), falha de detecção (controle esperado e motivo), síntese (hipóteses confirmadas/descartadas/inconclusivas, conclusão técnica e limitações/pendências) e revisão (usuário, data/hora, parecer e observações).

Cada teste ganha resultado esperado, critério de decisão, quantidade de repetições, equipamento/configuração, amostra e seleção de arquivos de evidência da própria RNC. Replicações, quando informadas, são inteiros positivos. Datas, parecer e usuários da empresa são validados no backend.

Persistência: coluna existente `rncs.investigacao_json`, chave `complementos`; campos dos testes em `hipoteses[].testes[]`. Não é necessária migração física do schema nem atualização de registros históricos. Registros existentes sem essas chaves continuam legíveis e editáveis. Campos de metodologias, notas, observação e hipóteses existentes permanecem.

Os dados são gravados pelo botão Salvar registro. Upload de evidência atualiza as opções dos testes sem descartar rascunhos. Exclusão de evidência remove seus vínculos nos testes na mesma transação; se a exclusão física falhar, arquivo e dados são preservados pelo fluxo existente.

Parecer é um registro editável de revisão, sem novo bloqueio de aprovação ou mudança do ciclo de vida da RNC.

## Etapas da investigação

A aba 3 contém três subabas: 3.1 — Início · Etapa 1 (todo o formulário anterior preservado), 3.2 — 5 Porquês · Etapa 2 e 3.3 — Ishikawa · Etapa 3. A navegação entre elas mantém os rascunhos em memória; Salvar registro em qualquer subaba grava as três etapas e mantém a subaba selecionada.

5 Porquês registra problema, sequência numerada de perguntas/respostas/evidências e conclusão. Inicia com cinco perguntas e permite incluir até vinte. Ishikawa registra efeito, causas potenciais em Método, Máquina, Material, Mão de obra, Medição e Meio ambiente, e conclusão. Ambos permanecem editáveis sem dependência do seletor de metodologias da Etapa 1.

Os novos dados são próprios da RNC, em `rncs.investigacao_json.etapa_porques` e `etapa_ishikawa`; não usam os dados legados da Issue, nem exigem migração ou alteração da base ativa. A API valida a estrutura e preserva as regras existentes de papel, empresa e RNC não concluída.
