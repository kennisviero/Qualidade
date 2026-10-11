# PRD — Gestão da Qualidade (Issues + PDCA)

> PRD completo e detalhado: `Documentos/PRD.md`. Este arquivo é o resumo executivo.

App web para registrar/tratar/analisar **issues** (não conformidades, defeitos, ocorrências) em **ciclo fechado PDCA** — Captura → Contenção → Investigação → Ação → Análise — baseado em TQM / ISO 9001 (ação corretiva). Multi-tenant por **empresa** + login por usuário.

## Stack

- Backend: **Python + FastAPI + Uvicorn** · Banco: **SQLite** (`data/qualidade.db`) · Senha: `bcrypt`
- Frontend: SPA estática (HTML/CSS/JS + **Plotly.js**), servida pelo FastAPI em `/`

## Módulos (menu)

1. **Empresas** (admin) — CRUD de tenants.
2. **Setores** — Empresa(1)→Setor(n).
3. **Processos** — Empresa(1)→Processo(n) + **gestão** (guardião/aprovador/status/revisões/aprovação) + **documentos** (árvore em `Vault/{empresa}/{setor}/{processo}`).
4. **Usuários** (admin) — papéis `admin`/`editor`/`visualizador`, `posicao`, vínculo a setor.
5. **Issues** — ciclo PDCA em 5 abas:

| Aba | PDCA | Conteúdo |
|-----|------|----------|
| 1. Captura | Plan | setor, processo, tipo, severidade, etapa de captura, descrição (+transcrição TXT/PDF/DOCX), origem, produto, norma, reincidência, status, anexos |
| 2. Contenção | Plan/Do | Bloqueio de Lote (rastreabilidade/identificação/localização/responsabilidade) + decisão de investigar causa (Ishikawa/5 Porquês) |
| 3. Investigação | Do | Ishikawa 6Ms + 5 Porquês → `causa_raiz` |
| 4. Ação | Check/Act | Ações 5W2H (geração automática do Ishikawa), kanban global, finalização com nota 1–5 |
| 5. Análise | Check | Pareto por dimensão (`/api/issues/stats`) + tendência criação vs finalização (`/api/issues/trends`) |

## API principal

- `/api/{empresas,setores,processos,usuarios}`, `/api/issues` (CRUD + `ishikawa`/`porques`/`acoes`/`kanban`/`stats`/`trends`/`finalizar` + anexos), `/api/transcricao`.
- Acesso: `editor+` para escrita; `visualizador` 403; isolamento por `empresa_id`.

## Testes

```powershell
python -m pytest -q   # 54 testes passando
```

Reset = apagar `data/qualidade.db` + limpar `Vault/`. Seed: `admin`/`admin` (superusuário) e `carlos`/`carlos` (admin empresa 1).