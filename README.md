# Qualidade — Gestão da Qualidade em Ciclo Fechado (Issues + PDCA)

Aplicação web para registrar, tratar e analisar **issues** (não conformidades, defeitos, ocorrências) com ciclo fechado **PDCA** — Captura → Contenção → Investigação → Ação → Análise — baseada em TQM / ISO 9001.

Stack: Python + FastAPI + SQLite (backend) e HTML5/CSS3/JS + Plotly.js (frontend).

## Requisitos

- Python 3.10+

## Instalação

```powershell
cd C:\Produttare\Qualidade
pip install -r requirements.txt
```

## Executar

```powershell
uvicorn app.main:app --reload
```

Acesse `http://localhost:8000`. Documentação da API em `http://localhost:8000/docs`. Ou duplo clique em `iniciar.bat`.

## Acesso

- **Superusuário inicial:** email `admin` / senha `admin` (criado no primeiro start).
- Papéis: `admin` (gerencia empresa/usuários), `editor` (cria/edita processos, issues, ações), `visualizador` (somente leitura).
- Multi-tenant: cada empresa é isolada; usuários pertencem a uma empresa (hierarquia Empresa → Setor → Usuário).

## Módulos (menu lateral)

1. **Empresas** (admin) — CRUD de tenants.
2. **Setores** — cadastro por empresa.
3. **Processos** — cadastro por empresa + **gestão do processo** (guardião, aprovador, status, revisões, aprovação) + **documentos do processo** (explorador de arquivos em `Vault/{empresa}/{setor}/{processo}/`).
4. **Usuários** (admin) — CRUD de usuários com papel e posição.
5. **Issues** — ciclo PDCA em 5 abas:
   - **1. Captura (Plan):** tipo, severidade, etapa de captura, setor, processo, descrição (com transcrição TXT/PDF/DOCX), origem, produto, norma, reincidência, anexos.
   - **2. Contenção (Plan/Do):** Bloqueio de Lote (rastreabilidade, identificação, localização, responsabilidade) + decisão de investigar a causa (Ishikawa e/ou 5 Porquês).
   - **3. Investigação (Do):** Ishikawa (6Ms) + 5 Porquês → causa raiz.
   - **4. Ação (Check/Act):** plano 5W2H (geração automática a partir do Ishikawa), Kanban de tarefas, finalização com resultado + nota 1–5.
   - **5. Análise (Check):** Pareto automático por dimensão e tendência de criação vs finalização (Plotly).

## Testes

```powershell
python -m pytest -q   # 54 testes passando
```

## Estrutura

- `app/main.py` — aplicação FastAPI, serve estáticos e monta rotas (lifespan roda `init_db`)
- `app/db.py` — schema SQLite + migração (issues) + seed admin
- `app/auth.py` — hash bcrypt, sessão por cookie, papéis
- `app/docs.py` — pastas físicas de documentos + helpers de arquivo (`Vault/`)
- `app/calculations.py` — `pareto()` (usado pela aba Análise)
- `app/routers/` — auth, empresas, usuarios, setores, processos, issues, transcricao
- `app/static/` — frontend SPA (index.html, CSS, JS)
- `Vault/` — repositório físico de arquivos (configurável via `QUALIDADE_DOCS`)