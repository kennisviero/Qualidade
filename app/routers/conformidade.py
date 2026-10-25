"""Rastreabilidade e conformidade (closed-loop) — submódulo Requisitos.

Avaliação de conformidade por requisito e matriz de cobertura (requisito × situação +
vínculos + lacunas), estilo gap-analysis. Os vínculos requisito↔alvo têm endpoints em
`requisitos.py`, mas a tabela é criada aqui (DDL único). Leitura aditiva: não altera
`enquadramento_normativo`/`requisito_violado`.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field

from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.routers.llm_acessos import scope
from app.security import SafeModel

router = APIRouter(prefix="/api/conformidade", tags=["conformidade"])

editor_dep = require_papel("admin", "editor")

SITUACOES = ("conforme", "nao_conforme", "nao_avaliado")
ALVOS = ("processo", "issue", "rnc", "acao", "familia", "grupo", "produto")

DDL = """CREATE TABLE IF NOT EXISTS requisito_vinculos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 requisito_id INTEGER NOT NULL REFERENCES requisitos(id) ON DELETE CASCADE,
 alvo_tipo TEXT NOT NULL,
 alvo_id INTEGER NOT NULL,
 observacao TEXT DEFAULT '',
 criado_por_id INTEGER REFERENCES usuarios(id),
 criado_em TEXT NOT NULL,
 UNIQUE(requisito_id, alvo_tipo, alvo_id)
);
CREATE TABLE IF NOT EXISTS requisito_conformidade (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 requisito_id INTEGER NOT NULL REFERENCES requisitos(id) ON DELETE CASCADE,
 processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
 situacao TEXT NOT NULL DEFAULT 'nao_avaliado',
 evidencia TEXT DEFAULT '',
 responsavel_id INTEGER REFERENCES usuarios(id),
 avaliado_em TEXT,
 criado_por_id INTEGER REFERENCES usuarios(id)
);
CREATE INDEX IF NOT EXISTS idx_conformidade_req ON requisito_conformidade(requisito_id);
CREATE INDEX IF NOT EXISTS idx_req_vinculos_alvo ON requisito_vinculos(alvo_tipo, alvo_id);
CREATE TRIGGER IF NOT EXISTS vinculos_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM requisito_vinculos WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS vinculos_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE requisito_vinculos SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS conformidade_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM requisito_conformidade WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS conformidade_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE requisito_conformidade SET responsavel_id=NULL WHERE responsavel_id=OLD.id;
 UPDATE requisito_conformidade SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
"""


class ConformidadeIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    requisito_id: int
    processo_id: int | None = None
    situacao: str = "nao_avaliado"
    evidencia: str = Field(default="", max_length=3000)
    responsavel_id: int | None = None


def now():
    return datetime.now(timezone.utc).isoformat()


def alvo_empresa(conn, alvo_tipo, alvo_id):
    """empresa_id do alvo de vínculo, ou None se não existir."""
    if alvo_tipo == "processo":
        r = conn.execute("SELECT empresa_id FROM processos WHERE id=?", (alvo_id,)).fetchone()
    elif alvo_tipo == "issue":
        r = conn.execute("SELECT empresa_id FROM issues WHERE id=?", (alvo_id,)).fetchone()
    elif alvo_tipo == "rnc":
        r = conn.execute("SELECT empresa_id FROM rncs WHERE id=?", (alvo_id,)).fetchone()
    elif alvo_tipo == "acao":
        r = conn.execute(
            "SELECT i.empresa_id FROM acoes a JOIN issues i ON i.id=a.issue_id WHERE a.id=?", (alvo_id,)
        ).fetchone()
    elif alvo_tipo == "familia":
        r = conn.execute("SELECT empresa_id FROM produto_familias WHERE id=?", (alvo_id,)).fetchone()
    elif alvo_tipo == "grupo":
        r = conn.execute("SELECT empresa_id FROM produto_grupos WHERE id=?", (alvo_id,)).fetchone()
    elif alvo_tipo == "produto":
        r = conn.execute("SELECT empresa_id FROM produtos WHERE id=?", (alvo_id,)).fetchone()
    else:
        return None
    return r["empresa_id"] if r else None


def _requisito_da_empresa(conn, requisito_id, company):
    r = conn.execute("SELECT id FROM requisitos WHERE id=? AND empresa_id=?", (requisito_id, company)).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Requisito não encontrado")


@router.post("", status_code=201)
def set_conformidade(body: ConformidadeIn, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    if body.situacao not in SITUACOES:
        raise HTTPException(status_code=422, detail="Situação inválida")
    instante = now()
    with get_connection() as conn:
        _requisito_da_empresa(conn, body.requisito_id, company)
        if body.processo_id is not None:
            p = conn.execute("SELECT empresa_id FROM processos WHERE id=?", (body.processo_id,)).fetchone()
            if p is None or p["empresa_id"] != company:
                raise HTTPException(status_code=422, detail="Processo inválido para a empresa")
        if body.responsavel_id is not None:
            u = conn.execute("SELECT empresa_id FROM usuarios WHERE id=?", (body.responsavel_id,)).fetchone()
            if u is None or u["empresa_id"] != company:
                raise HTTPException(status_code=422, detail="Responsável inválido para a empresa")
        existing = conn.execute(
            "SELECT id FROM requisito_conformidade WHERE requisito_id=? AND IFNULL(processo_id,0)=IFNULL(?,0)",
            (body.requisito_id, body.processo_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE requisito_conformidade SET situacao=?,evidencia=?,responsavel_id=?,avaliado_em=? WHERE id=?",
                (body.situacao, body.evidencia, body.responsavel_id, instante, existing["id"]),
            )
            rid = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO requisito_conformidade (empresa_id,requisito_id,processo_id,situacao,evidencia,responsavel_id,avaliado_em,criado_por_id) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (company, body.requisito_id, body.processo_id, body.situacao, body.evidencia,
                 body.responsavel_id, instante, user["id"]),
            )
            rid = cur.lastrowid
        conn.commit()
        return dict(conn.execute("SELECT * FROM requisito_conformidade WHERE id=?", (rid,)).fetchone())


def _matriz(conn, company, norma_id):
    reqs = conn.execute(
        "SELECT * FROM requisitos WHERE empresa_id=? AND norma_id=? ORDER BY ordem,id", (company, norma_id)
    ).fetchall()
    linhas = []
    sem_vinculo, nao_avaliados, nao_conformes = [], [], []
    conformes = 0
    for r in reqs:
        conf = conn.execute(
            "SELECT situacao,evidencia,responsavel_id FROM requisito_conformidade WHERE requisito_id=? AND processo_id IS NULL",
            (r["id"],),
        ).fetchone()
        situacao = conf["situacao"] if conf else "nao_avaliado"
        vinc = conn.execute(
            "SELECT alvo_tipo, COUNT(*) n FROM requisito_vinculos WHERE requisito_id=? GROUP BY alvo_tipo",
            (r["id"],),
        ).fetchall()
        vdict = {v["alvo_tipo"]: v["n"] for v in vinc}
        total_vinc = sum(vdict.values())
        if total_vinc == 0:
            sem_vinculo.append(r["id"])
        if situacao == "nao_avaliado":
            nao_avaliados.append(r["id"])
        elif situacao == "nao_conforme":
            nao_conformes.append(r["id"])
        elif situacao == "conforme":
            conformes += 1
        linhas.append(dict(id=r["id"], codigo_clausula=r["codigo_clausula"], titulo=r["titulo"],
                           categoria=r["categoria"], obrigatoriedade=r["obrigatoriedade"], estado=r["estado"],
                           prioridade=(r["prioridade"] or ""),
                           situacao=situacao, evidencia=(conf["evidencia"] if conf else ""),
                           vinculos=vdict, total_vinculos=total_vinc))
    resumo = dict(total=len(reqs), conformes=conformes, nao_conformes=len(nao_conformes),
                  nao_avaliados=len(nao_avaliados), sem_vinculo=len(sem_vinculo))
    lacunas = dict(sem_vinculo=sem_vinculo, nao_avaliados=nao_avaliados, nao_conformes=nao_conformes)
    return dict(norma_id=norma_id, requisitos=linhas, resumo=resumo, lacunas=lacunas)


@router.get("/matriz")
def matriz(norma_id: int, empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        n = conn.execute("SELECT id FROM normas WHERE id=? AND empresa_id=?", (norma_id, company)).fetchone()
        if n is None:
            raise HTTPException(status_code=404, detail="Norma não encontrada")
        return _matriz(conn, company, norma_id)


class PrepararIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    norma_id: int


@router.post("/matriz/preparar")
def preparar_ia(body: PrepararIn, user: dict = Depends(get_current_user)):
    """Monta a matriz de cobertura + snapshot assinado para a Consulta IA (análise de lacunas)."""
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        n = conn.execute("SELECT id FROM normas WHERE id=? AND empresa_id=?", (body.norma_id, company)).fetchone()
        if n is None:
            raise HTTPException(status_code=404, detail="Norma não encontrada")
        result = _matriz(conn, company, body.norma_id)
    from app.services.ferramentas_ia import context
    result["consulta_ia"] = context("conformidade", company, user, {"norma_id": body.norma_id}, result)
    return result
