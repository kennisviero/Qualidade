# Operação — Gestão da Qualidade (Issues + PDCA)

Guia operacional da aplicação. Stack: FastAPI + SQLite (backend), HTML/CSS/JS + Plotly.js (frontend).

## 1. Pré-requisitos

- Python 3.10+
- Acesso à internet na primeira execução (CDN Plotly.js no frontend)

## 2. Instalação

```powershell
cd C:\Produttare\Qualidade
pip install -r requirements.txt
```

## 3. Executar o servidor

```powershell
cd C:\Produttare\Qualidade
uvicorn app.main:app --reload
```

| URL | Descrição |
|-----|-----------|
| `http://localhost:8000` | Interface web |
| `http://localhost:8000/docs` | Swagger (documentação interativa da API) |

Para outra porta: `uvicorn app.main:app --reload --port 8080`.

## 4. Banco de Dados

- Arquivo: `C:\Produttare\Qualidade\data\qualidade.db` (criado automaticamente no primeiro start).
- Para usar outro caminho, defina a variável de ambiente `QUALIDADE_DB` antes de iniciar:

```powershell
$env:QUALIDADE_DB = "C:\outro\qualidade.db"
uvicorn app.main:app --reload
```

## 5. Fluxo de operação no frontend

1. **Login** — entre com `admin` / `admin` (superusuário) ou usuário criado.
2. **Configurar tenants (admin)** — crie empresas em "Empresas", setores em "Setores", processos em "Processos" e usuários em "Usuários" (papéis `admin`/`editor`/`visualizador`).
3. **Processos** — além do cadastro (Empresa → Processo, setor como campo), permite a **gestão do processo** (guardião, aprovador, status, histórico de revisões, aprovação) e os **documentos do processo** (árvore de arquivos).
4. **Issues** — ciclo fechado PDCA com 5 abas (Captura, Contenção, Investigação, Ação, Análise) + Kanban de tarefas e anexos por issue.

### Gestão do processo

Ao clicar em um processo na lista "Processos", o painel "Gestão do processo" permite:

- Definir o **guardião (responsável)** e o **aprovador final** (usuários cadastrados) e o **status**.
- Ver as datas e responsáveis de **criação**, **revisão** e **aprovação** (preenchidas automaticamente).
- O **histórico de revisões** (sintaxe de cada versão) fica listado no painel (botão "Ver" mostra a sintaxe).
- **"Aprovar"** registra a aprovação da revisão atual (data + responsável) e marca o processo como `aprovado`.

### Documentos (no módulo Processos)

- O card "Documentos do processo" mostra a **árvore** da pasta física `C:\Produttare\Qualidade\Vault\{empresa}\{setor}\{processo}\` (raiz = pasta do processo; com subpastas).
- **Nova pasta** / **Criar arquivo**: cria na pasta selecionada (ou na raiz se nada estiver selecionado).
- **Enviar**: arraste arquivo(s) do Windows Explorer para dentro de uma pasta da árvore (ou na própria árvore).
- **Abrir**: duplo clique no arquivo (PDF/imagem/texto abrem no navegador; demais baixam).
- **Excluir**: selecione o item e pressione **Delete** (pasta pede confirmação e exclui recursivamente).
- Configure outro local com a variável `QUALIDADE_DOCS`.

### Módulo Issues (registro e tratamento, ciclo PDCA)

1. **1. Captura (Plan)** — registrar a issue: setor, processo, tipo, severidade, etapa de captura, descrição (com transcrição de TXT/PDF/DOCX), data, origem (interno/externo), produto, norma e reincidência.
2. **2. Contenção (Plan/Do)** — bloqueio de lote: rastreabilidade temporal (último OK, alarme, margem), identificação (SKU/PN, lote, ordem de produção, série), localização e responsabilidade (operador, inspetor, motivo). Decisão "Investigar a causa?" (SIM marca ≥1 ferramenta: Ishikawa e/ou 5 Porquês).
3. **3. Investigação (Do)** — análise de causa raiz: Ishikawa (6Ms com nomes customizáveis + "Gerar") e/ou **5 Porquês** (numerados; se ambos marcados, cada porquê usa um item distinto do Ishikawa). Salva `causa_raiz`.
4. **4. Ação (Check/Act)** — plano de ação 5W2H (`descricao`, `por_que`, `onde`, `como`, `quanto`, responsável, prazo, observação). "Gerar ações do Ishikawa" cria uma ação por causa. Login na aba de Investigação. Sair do backlog define `data_inicio`. **Finalizar** exige todas as tarefas `finalizada` + `resultado_alcancado` + `nota_atingimento` (1–5).
5. **5. Análise (Check)** — Pareto automático por dimensão (status, tipo, severidade, origem, produto, setor) e tendência de criação vs finalização (Plotly).

Abaixo da issue, **Documentos da issue** (anexos em `Vault\{empresa}\{codigo}\`) e o **Kanban de tarefas** (quadro global da empresa, drag-and-drop).

## 6. API (resumo)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET / POST | `/api/empresas` | Listar / criar empresas |
| PUT / DELETE | `/api/empresas/{id}` | Editar / excluir empresa |
| GET / POST | `/api/usuarios` | Listar / criar usuários (administrador) |
| PUT / DELETE | `/api/usuarios/{id}` | Editar / excluir usuário |
| GET / POST | `/api/setores` | Listar / criar setores (por empresa) |
| PUT / DELETE | `/api/setores/{id}` | Editar / excluir setor |
| GET / POST | `/api/processos` | Listar / criar processos |
| GET / PUT / DELETE | `/api/processos/{id}` | Detalhe / editar (nome, descrição, guardião, aprovador, status) / excluir |
| GET / POST | `/api/processos/{id}/revisoes` | Histórico / criar revisão |
| POST | `/api/processos/{id}/aprovar` | Aprovar a revisão atual |
| GET | `/api/processos/{id}/arvore` | Árvore de arquivos/pastas do processo |
| POST | `/api/processos/{id}/arquivos` | Enviar arquivo (`file`, `subpasta`) |
| POST | `/api/processos/{id}/arquivos/criar` | Criar arquivo em branco (`nome`, `subpasta`) |
| POST | `/api/processos/{id}/pastas` | Criar subpasta (`nome`, `subpasta`) |
| GET | `/api/processos/{id}/arquivo?caminho=…` | Abrir/baixar arquivo |
| DELETE | `/api/processos/{id}/objetos?caminho=…` | Excluir arquivo/pasta (recursivo) |
| GET / POST | `/api/issues` | Listar / criar issues |
| GET / PUT / DELETE | `/api/issues/{id}` | Detalhe / editar / excluir issue |
| GET | `/api/issues/kanban` | Tarefas no quadro da empresa |
| GET | `/api/issues/stats` | Pareto por dimensão |
| GET | `/api/issues/trends` | Tendência de criação vs finalização |
| PUT | `/api/issues/{id}/porques` | Salvar 5 Porquês + `causa_raiz` |
| GET / POST | `/api/issues/{id}/acoes` | Listar / criar ação 5W2H |
| PUT / DELETE | `/api/issues/{id}/acoes/{acao_id}` | Editar / excluir ação |
| PUT | `/api/issues/{id}/acoes/{acao_id}/status` | Mudar status (kanban; sai do backlog define `data_inicio`) |
| POST | `/api/issues/{id}/finalizar` | Finalizar issue (exige tarefas finalizadas + nota 1–5) |
| POST | `/api/issues/{id}/ishikawa` | Vincular Ishikawa |
| PUT | `/api/issues/{id}/ishikawa` | Atualizar Ishikawa vinculado |
| GET / POST | `/api/issues/{id}/acoes` … | Ações |
| GET | `/api/issues/{id}/arvore` | Árvore de anexos da issue |
| POST | `/api/issues/{id}/arquivos` · `/arquivos/criar` · `/pastas` | Enviar / criar arquivo / criar pasta |
| GET | `/api/issues/{id}/arquivo?caminho=…` | Abrir/baixar anexo |
| DELETE | `/api/issues/{id}/objetos?caminho=…` | Excluir anexo |
| POST | `/api/transcricao` | Transcrever TXT/PDF/DOCX → texto |

## 7. Testes

```powershell
cd C:\Produttare\Qualidade
python -m pytest -q
```

## 8. Solução de problemas

| Sintoma | Causa provável / ação |
|---------|------------------------|
| Gráfico não renderiza | Sem internet (CDN Plotly). Verifique conectividade ou baixe a lib localmente |
| `ModuleNotFoundError: fastapi` | Rode `pip install -r requirements.txt` |
| Porta em uso | Use `--port 8080` (ou outra) |
| Dados "sumiram" | Verifique se a variável `QUALIDADE_DB` aponta para o arquivo esperado |

## 9. Estrutura de arquivos

```
C:\Produttare\Qualidade\
  PRD.md
  README.md
  OPERACAO.md
  requirements.txt
  app/
    main.py            # FastAPI + serve estáticos
    db.py              # SQLite + schema
    docs.py            # pastas físicas + arquivos
    calculations.py    # pareto() (usado em /api/issues/stats)
    routers/           # auth, empresas, usuarios, setores, processos, issues, transcricao
    static/            # index.html, css/, js/
  data/qualidade.db    # gerado em runtime
  Vault/             # arquivos (empresa/setor/processo)
  tests/
```