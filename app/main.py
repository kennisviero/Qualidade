from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import (
    auth,
    pareto,
    histograma,
    dispersao,
    afinidades,
    relacoes,
    matriz,
    planejamento,
    ferramentas_ia,
    llm_acessos,
    documentos_controlados,
    normas,
    requisitos,
    conformidade,
    produtos,
    datasets,
    documentos,
    empresas,
    issues,
    rncs,
    issue_limpeza,
    issue_selecao,
    processos,
    projects,
    setores,
    transcricao,
    usuarios,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.services.issue_triagem import start_worker
    stop, thread = start_worker()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)


app = FastAPI(title="7 Ferramentas da Qualidade", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path=='/' or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response

app.include_router(auth.router)
app.include_router(llm_acessos.router)
app.include_router(empresas.router)
app.include_router(usuarios.router)
app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(setores.router)
app.include_router(processos.router)
app.include_router(documentos.router)
app.include_router(issue_limpeza.router)
app.include_router(issue_selecao.router)
app.include_router(issues.router)
app.include_router(rncs.router)
app.include_router(pareto.router)
app.include_router(histograma.router)
app.include_router(dispersao.router)
app.include_router(afinidades.router)
app.include_router(relacoes.router)
app.include_router(matriz.router)
app.include_router(planejamento.pdpc_router)
app.include_router(planejamento.setas_router)
app.include_router(ferramentas_ia.router)
app.include_router(transcricao.router)
app.include_router(documentos_controlados.router)
app.include_router(normas.router)
app.include_router(requisitos.router)
app.include_router(conformidade.router)
app.include_router(produtos.router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
