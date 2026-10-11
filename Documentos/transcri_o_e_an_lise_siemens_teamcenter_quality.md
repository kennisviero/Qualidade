# Transcrição e Análise Detalhada do Vídeo: Siemens Teamcenter Quality

## 1. Visão Geral da Solução Siemens Digital Enterprise (00:00 - 04:02)

* **Integração e Visão Holística:** O sistema unifica o controlo de qualidade desde a fase de engenharia de design até à execução no chão de fábrica e melhoria contínua. Integra funcionalidades do antigo *Compliance Hub* diretamente no Teamcenter, assegurando que todos os processos e auditorias fiquem centralizados numa única plataforma. Permite verificar se os operadores no fabrico possuem as qualificações e formações válidas para executar determinados trabalhos.
* **Planeamento da Qualidade (*Quality Planning*):**
  * **APQP (*Program Planning*):** Permite aos clientes definir marcos (*milestones*), fases de projeto e gerir o cronograma de lançamento de produtos com base em critérios de qualidade e mitigação de risco atempada.
  * **FMEA (*Failure Mode and Effects Analysis*):** Realiza a análise de risco sobre o modelo virtual do produto, permitindo ajustar o design e corrigir falhas antes do fabrico físico.
  * **Plano de Inspeção (*Inspection Plan*):** Como nem todos os erros podem ser eliminados na fase de design por questões de custo/eficiência, o plano de inspeção define controlos no chão de fábrica para conter defeitos e evitar que cheguem ao cliente.
* **Garantia da Qualidade (*Quality Assurance*):**
  * A recolha de dados de qualidade no chão de fábrica é feita através do *Opcenter Execution* ou *Opcenter Quality Control*.
  * Qualquer desvio detetado no processo de execução é automaticamente enviado para a Gestão de Não-Conformidades (*Issue Management*) do Teamcenter Quality.
* **Melhoria Contínua (*Continuous Improvement*):**
  * **Gestão Centralizada de Problemas:** Qualquer colaborador de qualquer departamento tem permissão para registar um problema (*issue*), ativando notificações e fluxos de distribuição automáticos.
  * **Resolução de Problemas (*Problem Solving*):** Permite conduzir análises de causa-raiz para problemas específicos e determinar Ações Corretivas e Preventivas (CAPA).
  * **Ações de Qualidade:** Módulo de acompanhamento com ciclos de alerta e escalamento automático caso os prazos definidos não sejam cumpridos.
* **Análise da Qualidade (*Quality Analytics*):** Acompanhamento de dados através das pesquisas padrão do Teamcenter ou através da ferramenta avançada *Teamcenter Reporting and Analytics*.

---

## 2. Roadmap de Produto e Atualizações Técnicas (04:03 - 06:30)

* **Estatuto dos Módulos (Plano de Desenvolvimento 2018–2023):**
  * **Módulos Lançados:** *Quality Action Management*, *APQP Program Management*, *Problem Solving & Quality Issue Management*, *Control and Inspection Plan* e *FMEA*.
  * **Módulos Futuros:** *Supplier Quality* (portal para APQP e resolução de problemas com fornecedores), *Audit/Assessment & EHS*, *Training & Qualification* e *Gage Management*. Os primeiros protótipos/incubações surgem no ano seguinte, com o lançamento final previsto para o fim de 2022.
* **Compatibilidade e Padrão RPN (Active Workspace 5.2 / Teamcenter 13.2):**
  * **Requisito Rigoroso de Versão:** No Teamcenter Quality, a versão do *Active Workspace* (ex.: 5.2) tem obrigatoriamente de corresponder à versão do *Teamcenter* (ex.: 13.2), não permitindo cruzamento de versões anteriores.
  * **Cálculo de RPN no FMEA:** A partir da versão 5.2, foi reintroduzida a funcionalidade de análise por RPN (*Risk Priority Number*), correspondente ao padrão clássico da indústria automóvel (IATF 16949). A versão anterior suportava apenas a nova metodologia combinada VDA/AIAG. Esta adição permite aplicar o módulo de FMEA a qualquer setor industrial que continue a utilizar a abordagem RPN.

---

## 3. Campanha SLT_043_014 e Setores-Alvo (06:31 - 08:06)

* **Identificação da Campanha:** `SLT_043_014_GBL` (*Closed Loop Quality Management for Design to Manufacturing_MI*). O apresentador aconselha a consulta inicial do documento *Campaign Introduction* para obter o mapa do material disponível.
* **Indústrias-Alvo:** Automóvel & Transportes, Energia, Produtos de Consumo & Retalho, Marítimo, Aeroespacial & Defesa, Maquinaria Industrial, Dispositivos Médicos e Farmacêutica.
* **Perfil de Empresa:** Apesar da documentação indicar foco em grandes contas, na prática a solução é aplicada com sucesso em médias e pequenas empresas.

---

## 4. Acelerador Teamcenter Quality para Dispositivos Médicos (08:07 - 10:37)

Desenvolvido em parceria com a unidade de negócio ES/MC, este acelerador foi concebido exclusivamente para os requisitos do setor médico (não pode ser instalado *plug-and-play* noutros setores sem adaptação).

* **Fase I (Concluída):**
  * **Âmbito:** Módulos de Não-Conformidades/Reclamações (*Complaint Management*), Resolução de Problemas e PPAP de Clientes.
  * **Custo & Casos:** Custo fixo de implementação de **$130k** para dois módulos. Primeira implementação concluída com sucesso na empresa **Mach Medical**.
* **Fase II (Em Curso):**
  * **Âmbito:** FMEA de Processo (*P-FMEA*), Planos de Controlo e Inspeção, Integração com *Opcenter Quality Control* (inspeção em processo), PPAP de Fornecedores e APQP.
  * **Prazo:** Conclusão prevista para o final do ano, seguida da implementação da Fase II na Mach Medical.
* **Fase III (Futuro):**
  * **Âmbito:** Gestão de Peças (*Part Management*), Gestão de Mudanças (*Change Management*), Auditorias, Formação e D-FMEA.
  * **Visão:** Conexão ao *Teamcenter Medical Device Accelerator* e ao *Execution Core*, completando o ciclo CLM (*Closed Loop Manufacturing*).

---

## 5. Metodologia de Implantação e Estimativa de Custos/Horas (10:38 - 13:27)

* **Ajuste Metodológico:** A implantação segue o processo *Advantage* (Validação, Configuração Iterativa/Verificação e Implantação). A grande alteração no Teamcenter Quality é introduzir os especialistas (*SMEs*) e utilizadores-chave logo no início do desenvolvimento da configuração, reduzindo o tempo total do projeto.
* **Uso da GDN (*Global Delivery Network*):** Recomenda-se o uso da GDN para as tarefas de configuração por razões de eficiência de custos em comparação com arquitetos locais nas Américas, exceto em projetos com restrições militares/governamentais (ITAR / DoD).
* **Matriz de Estimativa de Serviços (Exemplo de Projeto Padrão - GDLS):**

| Fase / Tarefa de Implementação | Perfil / Responsável | Carga Horária Estimada |
| :--- | :--- | :--- |
| **Project Management** | SPM | **88 horas** |
| **Preparation** | SA | **40 horas** |
| **VSD Workshop** | SA | **48 horas** |
| **Specification (Configuration Workbooks)** | SA | **48 horas** |
| **Configuration** | PA (GDN) | **160 horas** |
| **Configuration Support** | SA | **40 horas** |
| **Maturity Reviews** | SA | **80 horas** |
| **Deployment & Acceptance** | SA | **40 horas** |
| **TOTAL (1 Módulo Padrão)** | — | **~600 horas (~$150k)** |

*Nota:* Tarefas como Instalação/Upgrade, Integração, Migração, Formação e Adoção pertencem a outros departamentos e devem ser adicionadas a este total para a estimativa global do projeto.

---

## 6. Proposta de Valor: Aceleradores vs. Implementação Padrão (13:28 - 18:10)

### Comparativo Económico e de Prazos
* **Custo de Implementação:** O Acelerador oferece **2 módulos por $130k** (incluindo instalação). Na abordagem padrão, 1 módulo requer ~600 horas (~$150k), o que significa que 2 módulos custariam cerca de **$300k**.
* **Tempo de Implantação:** Na Mach Medical, a Fase I (2 módulos) demorou **1,5 a 2 meses** com o Acelerador. A mesma implementação na abordagem padrão demoraria cerca de **6 meses**.
* **Redução de Risco:** O Acelerador força o cliente a seguir as melhores práticas pré-configuradas do setor em vez de tentar criar soluções personalizadas de raiz.

### Matriz de Segmentação de Clientes

| Característica | Aceleradores (*Accelerators*) | Implementação Padrão (*Standard Implementation*) |
| :--- | :--- | :--- |
| **Perfil de Cliente** | Pequenas e médias empresas; Clientes que estão a iniciar do zero no Teamcenter. | Grandes empresas (ex.: Honeywell, Dana) com instâncias Teamcenter já consolidadas. |
| **Adoção de Processos** | Dispostos a aceitar os processos padrão e melhores práticas da indústria. | Possuem processos internos e configurações proprietárias muito específicas. |
| **Nível de Configuração** | Configurações mínimas (alteração de rótulos, atributos adicionais, pequenos ajustes de workflow). | Configuração total para adaptar o Teamcenter Quality às estruturas e objetos existentes. |
| **Argumento Principal** | Implementação ultra-rápida e custo significativamente reduzido. | Integração perfeita num ecossistema complexo preexistente (Engenharia + Fabrico + Qualidade). |

---

## 7. Recomendações Estratégicas, Debate e Recursos (18:11 - 22:18)

* **Recomendação para Unidades de Negócio (BUs):** Criar aceleradores para outras indústrias aproveitando a base técnica do acelerador de dispositivos médicos. A construção de novos aceleradores requer verbas de financiamento (*funding*).
* **Sessão de Pergunta e Resposta Durante a Reunião:**
  * **PM Mehta (19:40):** Questiona como deve proceder a equipa de Aeroespacial & Defesa (A&D) se quiser desenvolver um acelerador equivalente (devem contactar Barry Chapman?).
  * **Len Carlton (19:53):** Esclarece que se deve contactar primeiro o Tony e envolver a *Global Practice Team* (liderada por Martin e Marco). A equipa global avalia as oportunidades entre as Américas e a Europa para avançar. Caso a equipa global não tenha verba, a própria Unidade de Negócio pode financiar o desenvolvimento, à semelhança do investimento feito por Prakash e Rob nos setores de High-Tech/Semicondutores e Dispositivos Médicos.
* **Lista de Contactos e Hiperligações:**
  * **Responsável:** Marco Langbein (MOM Quality) — E-mail: `Marco.Langbein@siemens.com` | Tel.: `+1 (781) 382-5567`.
  * **Recursos Disponíveis:** Ligações na apresentação para a página da Campanha, canais do Teams (*Tc Q Accelerator for MDS* e *Teamcenter Quality*) e vídeo demonstrativo de produto de 15 minutos (no Highspot / YouTube).