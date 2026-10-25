"""Catálogo de Normas e Regulamentos (submódulo Requisitos) — 1º consumidor do PDM.

Captura e organização de normas/regulamentos de fontes diversas, por empresa. O
documento (PDF) da norma vive no motor de PDM (`documentos_controlados`), versionado;
a norma referencia esse documento por `documento_id`. Nada aqui altera módulos existentes.
"""
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ConfigDict, Field

from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.docs import save_file
from app.routers.documentos_controlados import _audit, _rev_folder, create_documento_interno, doc_to_dict, sync_norma_status
from app.routers.llm_acessos import scope
from app.security import SafeModel

router = APIRouter(prefix="/api/normas", tags=["normas"])

editor_dep = require_papel("admin", "editor")

TIPOS_FONTE = ("norma_tecnica", "regulamento_legal", "requisito_contratual",
               "requisito_cliente", "politica_interna", "outro")
STATUS = ("vigente", "em_revisao", "obsoleta")

DDL = """CREATE TABLE IF NOT EXISTS normas (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 codigo TEXT NOT NULL,
 tipo_fonte TEXT NOT NULL DEFAULT 'outro',
 titulo TEXT NOT NULL,
 identificador_externo TEXT DEFAULT '',
 emissor TEXT DEFAULT '',
 edicao_versao TEXT DEFAULT '',
 data_publicacao TEXT DEFAULT '',
 data_vigencia TEXT DEFAULT '',
 status TEXT NOT NULL DEFAULT 'vigente',
 escopo TEXT DEFAULT '',
 observacoes TEXT DEFAULT '',
 documento_id INTEGER REFERENCES documentos_controlados(id) ON DELETE SET NULL,
 criado_por_id INTEGER REFERENCES usuarios(id),
 criado_em TEXT NOT NULL,
 atualizado_em TEXT,
 UNIQUE(empresa_id, codigo)
);
CREATE TRIGGER IF NOT EXISTS normas_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM normas WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS normas_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE normas SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
"""


class NormaIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    tipo_fonte: str = "outro"
    titulo: str = Field(min_length=1, max_length=200)
    identificador_externo: str = Field(default="", max_length=200)
    emissor: str = Field(default="", max_length=200)
    edicao_versao: str = Field(default="", max_length=120)
    data_publicacao: str = Field(default="", max_length=40)
    data_vigencia: str = Field(default="", max_length=40)
    status: str = "vigente"
    escopo: str = Field(default="", max_length=3000)
    observacoes: str = Field(default="", max_length=3000)
    criar_documento: bool = True


class NormaUpdate(SafeModel):
    model_config = ConfigDict(extra="forbid")
    tipo_fonte: str | None = None
    titulo: str | None = Field(default=None, max_length=200)
    identificador_externo: str | None = Field(default=None, max_length=200)
    emissor: str | None = Field(default=None, max_length=200)
    edicao_versao: str | None = Field(default=None, max_length=120)
    data_publicacao: str | None = Field(default=None, max_length=40)
    data_vigencia: str | None = Field(default=None, max_length=40)
    status: str | None = None
    escopo: str | None = Field(default=None, max_length=3000)
    observacoes: str | None = Field(default=None, max_length=3000)


def now():
    return datetime.now(timezone.utc).isoformat()


def _next_codigo(conn, empresa_id):
    rows = conn.execute("SELECT codigo FROM normas WHERE empresa_id=?", (empresa_id,)).fetchall()
    maxn = 0
    for r in rows:
        m = re.fullmatch(r"NORMA-(\d+)", r["codigo"] or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"NORMA-{maxn + 1:04d}"


def norma_to_dict(conn, row):
    d = dict(row)
    nome = conn.execute("SELECT nome FROM usuarios WHERE id=?", (d.get("criado_por_id"),)).fetchone() if d.get("criado_por_id") else None
    d["criado_por_nome"] = nome["nome"] if nome else None
    d["documento"] = None
    if d.get("documento_id"):
        doc = conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (d["documento_id"],)).fetchone()
        if doc:
            d["documento"] = doc_to_dict(conn, doc)
    return d


def fetch_norma(conn, norma_id, company):
    row = conn.execute("SELECT * FROM normas WHERE id=? AND empresa_id=?", (norma_id, company)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Norma não encontrada")
    return row


@router.get("")
def list_normas(empresa_id: int | None = None, tipo_fonte: str = "", status: str = "",
                emissor: str = "", q: str = "", user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    sql = "SELECT * FROM normas WHERE empresa_id=?"
    params = [company]
    if tipo_fonte:
        sql += " AND tipo_fonte=?"
        params.append(tipo_fonte)
    if status:
        sql += " AND status=?"
        params.append(status)
    if emissor:
        sql += " AND emissor LIKE ?"
        params.append(f"%{emissor}%")
    if q:
        sql += " AND (codigo LIKE ? OR titulo LIKE ? OR identificador_externo LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY codigo"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [norma_to_dict(conn, r) for r in rows]


@router.get("/{norma_id}")
def get_norma(norma_id: int, empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        return norma_to_dict(conn, fetch_norma(conn, norma_id, company))


@router.post("", status_code=201)
def create_norma(body: NormaIn, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    if body.tipo_fonte not in TIPOS_FONTE:
        raise HTTPException(status_code=422, detail="Tipo de fonte inválido")
    if body.status not in STATUS:
        raise HTTPException(status_code=422, detail="Status inválido")
    instante = now()
    with get_connection() as conn:
        if conn.execute("SELECT id FROM empresas WHERE id=?", (company,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        documento_id = None
        if body.criar_documento:
            documento_id = create_documento_interno(
                conn, company, body.titulo, "norma", user["id"])
        codigo = _next_codigo(conn, company)
        cur = conn.execute(
            "INSERT INTO normas (empresa_id,codigo,tipo_fonte,titulo,identificador_externo,emissor,edicao_versao,"
            "data_publicacao,data_vigencia,status,escopo,observacoes,documento_id,criado_por_id,criado_em,atualizado_em) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (company, codigo, body.tipo_fonte, body.titulo, body.identificador_externo, body.emissor,
             body.edicao_versao, body.data_publicacao, body.data_vigencia, body.status, body.escopo,
             body.observacoes, documento_id, user["id"], instante, instante),
        )
        if documento_id:
            sync_norma_status(conn, documento_id)  # status segue o ciclo do documento
        conn.commit()
        return norma_to_dict(conn, conn.execute("SELECT * FROM normas WHERE id=?", (cur.lastrowid,)).fetchone())


@router.put("/{norma_id}")
def update_norma(norma_id: int, body: NormaUpdate, empresa_id: int | None = None,
                 user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    instante = now()
    with get_connection() as conn:
        row = fetch_norma(conn, norma_id, company)
        tipo_fonte = body.tipo_fonte if body.tipo_fonte is not None else row["tipo_fonte"]
        status = body.status if body.status is not None else row["status"]
        if tipo_fonte not in TIPOS_FONTE:
            raise HTTPException(status_code=422, detail="Tipo de fonte inválido")
        if status not in STATUS:
            raise HTTPException(status_code=422, detail="Status inválido")
        campos = dict(
            tipo_fonte=tipo_fonte,
            titulo=body.titulo if body.titulo is not None else row["titulo"],
            identificador_externo=body.identificador_externo if body.identificador_externo is not None else row["identificador_externo"],
            emissor=body.emissor if body.emissor is not None else row["emissor"],
            edicao_versao=body.edicao_versao if body.edicao_versao is not None else row["edicao_versao"],
            data_publicacao=body.data_publicacao if body.data_publicacao is not None else row["data_publicacao"],
            data_vigencia=body.data_vigencia if body.data_vigencia is not None else row["data_vigencia"],
            status=status,
            escopo=body.escopo if body.escopo is not None else row["escopo"],
            observacoes=body.observacoes if body.observacoes is not None else row["observacoes"],
        )
        conn.execute(
            "UPDATE normas SET tipo_fonte=?,titulo=?,identificador_externo=?,emissor=?,edicao_versao=?,"
            "data_publicacao=?,data_vigencia=?,status=?,escopo=?,observacoes=?,atualizado_em=? WHERE id=?",
            (*campos.values(), instante, norma_id),
        )
        conn.commit()
        return norma_to_dict(conn, conn.execute("SELECT * FROM normas WHERE id=?", (norma_id,)).fetchone())


@router.delete("/{norma_id}", status_code=204)
def delete_norma(norma_id: int, empresa_id: int | None = None, user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        fetch_norma(conn, norma_id, company)
        conn.execute("DELETE FROM normas WHERE id=?", (norma_id,))
        conn.commit()


# --- Documento da norma (a norma é um documento controlado; fonte PDF/DOCX/link/cadastrado) ---

def _ensure_doc(conn, norma, user_id):
    if norma["documento_id"]:
        doc = conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (norma["documento_id"],)).fetchone()
        if doc:
            return doc
    did = create_documento_interno(conn, norma["empresa_id"], norma["titulo"], "norma", user_id)
    conn.execute("UPDATE normas SET documento_id=?,atualizado_em=? WHERE id=?", (did, now(), norma["id"]))
    return conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (did,)).fetchone()


def _latest_rev(conn, doc_id):
    return conn.execute("SELECT * FROM documento_revisoes WHERE documento_id=? ORDER BY numero DESC LIMIT 1", (doc_id,)).fetchone()


def _rev_public(doc, rev):
    return dict(numero=rev["numero"], estado=rev["estado"], fonte=(rev["fonte"] or "cadastrado"),
                url=(rev["url"] or ""), arquivo_nome=(rev["arquivo_nome"] or ""),
                tem_arquivo=bool(rev["arquivo_nome"]), tem_link=bool(rev["url"]), documento_id=doc["id"])


@router.get("/{norma_id}/documento")
def get_documento(norma_id: int, empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        norma = fetch_norma(conn, norma_id, company)
        if not norma["documento_id"]:
            return {"documento_id": None}
        doc = conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (norma["documento_id"],)).fetchone()
        if doc is None:
            return {"documento_id": None}
        rev = _latest_rev(conn, doc["id"])
        out = {"documento_id": doc["id"], "codigo": doc["codigo"], "estado": doc["estado"]}
        if rev:
            out["revisao"] = _rev_public(doc, rev)
        return out


@router.post("/{norma_id}/documento/arquivo", status_code=201)
def set_documento_arquivo(norma_id: int, empresa_id: int | None = Form(default=None),
                          file: UploadFile = File(...), user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    with get_connection() as conn:
        norma = fetch_norma(conn, norma_id, company)
        doc = _ensure_doc(conn, norma, user["id"])
        rev = _latest_rev(conn, doc["id"])
        target = _rev_folder(doc, rev["numero"])
        target.mkdir(parents=True, exist_ok=True)
        nome = save_file(target, file.filename or "documento", data)
        h = hashlib.sha256(data).hexdigest()
        conn.execute("UPDATE documento_revisoes SET arquivo_nome=?,arquivo_hash=?,fonte='arquivo' WHERE id=?", (nome, h, rev["id"]))
        _audit(conn, doc["id"], "arquivo", f"Norma {norma['codigo']}: {nome}", user["id"], now())
        conn.commit()
        return _rev_public(doc, conn.execute("SELECT * FROM documento_revisoes WHERE id=?", (rev["id"],)).fetchone())


class DocLinkIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    url: str = Field(min_length=1, max_length=2000)


@router.post("/{norma_id}/documento/link", status_code=201)
def set_documento_link(norma_id: int, body: DocLinkIn, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    u = body.url.strip()
    if urlsplit(u).scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Informe uma URL http(s) válida")
    with get_connection() as conn:
        norma = fetch_norma(conn, norma_id, company)
        doc = _ensure_doc(conn, norma, user["id"])
        rev = _latest_rev(conn, doc["id"])
        conn.execute("UPDATE documento_revisoes SET url=?,fonte='link' WHERE id=?", (u, rev["id"]))
        _audit(conn, doc["id"], "link", f"Norma {norma['codigo']}: {u[:80]}", user["id"], now())
        conn.commit()
        return _rev_public(doc, conn.execute("SELECT * FROM documento_revisoes WHERE id=?", (rev["id"],)).fetchone())
