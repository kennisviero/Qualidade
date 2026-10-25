"""Motor de PDM (documentos controlados) — repositório de arquivos no Vault.

Genérico e multi-tenant: metadados e versionamento em SQLite
(`documentos_controlados` + `documento_revisoes`), bytes no Vault
(`Vault/{empresa}/_pdm/{codigo}/R{numero}/`). Inclui estados de ciclo de vida,
check-out/check-in com lock-out exclusivo, ciclo de aprovação e trilha de
auditoria à prova de adulteração (hash SHA-256 encadeado em `documento_auditoria`).

Nada aqui altera `processos`/`revisoes` ou qualquer módulo existente — segue o
mesmo padrão/estilo (ver `app/routers/processos.py`), mas é um subsistema novo.
"""
import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ConfigDict, Field

from app.auth import get_current_user, is_superuser, require_papel
from app.db import DOCS_DIR, get_connection
from app.docs import build_documento_pasta, delete_path, folder_for, guess_mime, safe_rel, save_file
from app.routers.llm_acessos import scope
from app.security import SafeModel

router = APIRouter(prefix="/api/pdm/documentos", tags=["pdm"])

editor_dep = require_papel("admin", "editor")

TIPOS = ("norma", "procedimento", "instrucao", "formulario", "politica", "contrato", "outro")
ESTADOS = ("backlog", "em_revisao", "em_aprovacao", "aprovado", "obsoleto")

DDL = """CREATE TABLE IF NOT EXISTS documentos_controlados (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 codigo TEXT NOT NULL,
 titulo TEXT NOT NULL,
 tipo TEXT NOT NULL DEFAULT 'outro',
 estado TEXT NOT NULL DEFAULT 'backlog',
 revisao_atual_id INTEGER,
 responsavel_id INTEGER REFERENCES usuarios(id),
 aprovador_id INTEGER REFERENCES usuarios(id),
 checkout_por_id INTEGER REFERENCES usuarios(id),
 checkout_em TEXT,
 pasta TEXT DEFAULT '',
 criado_por_id INTEGER REFERENCES usuarios(id),
 criado_em TEXT NOT NULL,
 atualizado_em TEXT,
 UNIQUE(empresa_id, codigo)
);
CREATE TABLE IF NOT EXISTS documento_revisoes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 documento_id INTEGER NOT NULL REFERENCES documentos_controlados(id) ON DELETE CASCADE,
 numero INTEGER NOT NULL,
 descricao_mudanca TEXT DEFAULT '',
 estado TEXT NOT NULL DEFAULT 'rascunho',
 arquivo_nome TEXT DEFAULT '',
 arquivo_hash TEXT DEFAULT '',
 texto_extraido TEXT DEFAULT '',
 origem_texto TEXT DEFAULT '',
 criado_por_id INTEGER REFERENCES usuarios(id),
 criado_em TEXT NOT NULL,
 revisado_por_id INTEGER REFERENCES usuarios(id),
 revisao_em TEXT,
 aprovado_por_id INTEGER REFERENCES usuarios(id),
 aprovacao_em TEXT,
 UNIQUE(documento_id, numero)
);
CREATE TABLE IF NOT EXISTS documento_auditoria (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 documento_id INTEGER NOT NULL REFERENCES documentos_controlados(id) ON DELETE CASCADE,
 evento TEXT NOT NULL,
 detalhe TEXT DEFAULT '',
 usuario_id INTEGER REFERENCES usuarios(id),
 criado_em TEXT NOT NULL,
 hash_anterior TEXT DEFAULT '',
 hash_atual TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS documentos_controlados_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM documentos_controlados WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS documentos_controlados_usuario_delete BEFORE DELETE ON usuarios
BEGIN
 UPDATE documentos_controlados SET responsavel_id=NULL WHERE responsavel_id=OLD.id;
 UPDATE documentos_controlados SET aprovador_id=NULL WHERE aprovador_id=OLD.id;
 UPDATE documentos_controlados SET checkout_por_id=NULL WHERE checkout_por_id=OLD.id;
 UPDATE documentos_controlados SET criado_por_id=NULL WHERE criado_por_id=OLD.id;
END;
"""


class DocumentoIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    titulo: str = Field(min_length=1, max_length=200)
    tipo: str = "outro"
    responsavel_id: int | None = None
    aprovador_id: int | None = None


class DocumentoUpdate(SafeModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str | None = Field(default=None, max_length=200)
    tipo: str | None = None
    responsavel_id: int | None = None
    aprovador_id: int | None = None


class RevisaoIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    descricao_mudanca: str = Field(default="", max_length=3000)
    variante: str = Field(default="", max_length=120)


def now():
    return datetime.now(timezone.utc).isoformat()


def user_nome(conn, user_id):
    if user_id is None:
        return None
    row = conn.execute("SELECT nome FROM usuarios WHERE id=?", (user_id,)).fetchone()
    return row["nome"] if row else None


def check_user_empresa(conn, user_id, empresa_id, label):
    if user_id is None:
        return
    row = conn.execute("SELECT empresa_id FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if row is None or row["empresa_id"] != empresa_id:
        raise HTTPException(status_code=422, detail=f"{label} inválido para a empresa do documento")


def _next_codigo(conn, empresa_id):
    rows = conn.execute(
        "SELECT codigo FROM documentos_controlados WHERE empresa_id=?", (empresa_id,)
    ).fetchall()
    maxn = 0
    for r in rows:
        m = re.fullmatch(r"DOC-(\d+)", r["codigo"] or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"DOC-{maxn + 1:04d}"


def _audit(conn, documento_id, evento, detalhe, usuario_id, instante):
    prev = conn.execute(
        "SELECT hash_atual FROM documento_auditoria WHERE documento_id=? ORDER BY id DESC LIMIT 1",
        (documento_id,),
    ).fetchone()
    prev_hash = prev["hash_atual"] if prev else ""
    payload = json.dumps(
        {"documento_id": documento_id, "evento": evento, "detalhe": detalhe,
         "usuario_id": usuario_id, "criado_em": instante, "hash_anterior": prev_hash},
        ensure_ascii=False, sort_keys=True,
    )
    h = hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT INTO documento_auditoria (documento_id,evento,detalhe,usuario_id,criado_em,hash_anterior,hash_atual) "
        "VALUES (?,?,?,?,?,?,?)",
        (documento_id, evento, detalhe, usuario_id, instante, prev_hash, h),
    )
    return h


def fetch_doc(conn, documento_id, user, empresa_id=None):
    row = conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not (is_superuser(user) or user["empresa_id"] == row["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    if empresa_id is not None and row["empresa_id"] != empresa_id:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return row


def rev_to_dict(conn, r):
    d = dict(r)
    d.pop("texto_extraido", None)
    d["tem_arquivo"] = bool(r["arquivo_nome"])
    d["tem_link"] = bool(d.get("url"))
    d["fonte"] = d.get("fonte") or "cadastrado"
    d["revisado_por_nome"] = user_nome(conn, r["revisado_por_id"])
    d["aprovado_por_nome"] = user_nome(conn, r["aprovado_por_id"])
    d["criado_por_nome"] = user_nome(conn, r["criado_por_id"])
    return d


def doc_to_dict(conn, row):
    d = dict(row)
    d["responsavel_nome"] = user_nome(conn, d.get("responsavel_id"))
    d["aprovador_nome"] = user_nome(conn, d.get("aprovador_id"))
    d["criado_por_nome"] = user_nome(conn, d.get("criado_por_id"))
    d["checkout_por_nome"] = user_nome(conn, d.get("checkout_por_id"))
    d["bloqueado"] = d.get("checkout_por_id") is not None
    revs = conn.execute(
        "SELECT * FROM documento_revisoes WHERE documento_id=? ORDER BY numero", (d["id"],)
    ).fetchall()
    d["revisoes"] = [rev_to_dict(conn, r) for r in revs]
    atual = conn.execute(
        "SELECT numero FROM documento_revisoes WHERE id=?", (d.get("revisao_atual_id"),)
    ).fetchone() if d.get("revisao_atual_id") else None
    d["revisao_atual_numero"] = atual["numero"] if atual else None
    return d


def _latest_rev(conn, documento_id):
    return conn.execute(
        "SELECT * FROM documento_revisoes WHERE documento_id=? ORDER BY numero DESC LIMIT 1",
        (documento_id,),
    ).fetchone()


def _norma_status_de(estado):
    """Colapsa o ciclo do documento no status da norma (vigente/em_revisao/obsoleta)."""
    if estado == "aprovado":
        return "vigente"
    if estado == "obsoleto":
        return "obsoleta"
    return "em_revisao"


def sync_norma_status(conn, documento_id):
    """Mantém o status da norma seguindo o ciclo do documento vinculado (fonte única)."""
    doc = conn.execute("SELECT estado FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone()
    if doc:
        conn.execute("UPDATE normas SET status=? WHERE documento_id=?", (_norma_status_de(doc["estado"]), documento_id))


@router.get("")
def list_docs(empresa_id: int | None = None, tipo: str = "", estado: str = "",
              responsavel_id: int | None = None, q: str = "",
              user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    sql = ("SELECT dc.*, n.id AS norma_id, n.codigo AS norma_codigo, n.tipo_fonte AS norma_tipo_fonte, "
           "n.identificador_externo AS norma_ident FROM documentos_controlados dc "
           "LEFT JOIN normas n ON n.documento_id=dc.id WHERE dc.empresa_id=?")
    params = [company]
    if tipo:
        sql += " AND dc.tipo=?"
        params.append(tipo)
    if estado:
        sql += " AND dc.estado=?"
        params.append(estado)
    if responsavel_id is not None:
        sql += " AND dc.responsavel_id=?"
        params.append(responsavel_id)
    if q:
        sql += " AND (dc.codigo LIKE ? OR dc.titulo LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])
    sql += " ORDER BY dc.codigo"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [doc_to_dict(conn, r) for r in rows]


@router.get("/{documento_id}")
def get_doc(documento_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        return doc_to_dict(conn, fetch_doc(conn, documento_id, user))


def create_documento_interno(conn, empresa_id, titulo, tipo, user_id,
                             responsavel_id=None, aprovador_id=None, empresa_nome=None):
    """Cria documento controlado + revisão R1 (rascunho) + evento de auditoria.

    Reutilizável por outros módulos (ex.: Normas) na mesma transação. Não comita.
    Retorna o id do documento. Valida tipo e empresa dos papéis informados.
    """
    if tipo not in TIPOS:
        raise HTTPException(status_code=422, detail="Tipo inválido")
    if empresa_nome is None:
        row = conn.execute("SELECT razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        empresa_nome = row["razao_social"]
    check_user_empresa(conn, responsavel_id, empresa_id, "Responsável")
    check_user_empresa(conn, aprovador_id, empresa_id, "Aprovador")
    instante = now()
    codigo = _next_codigo(conn, empresa_id)
    pasta = build_documento_pasta(empresa_nome, codigo)
    cur = conn.execute(
        "INSERT INTO documentos_controlados (empresa_id,codigo,titulo,tipo,estado,responsavel_id,aprovador_id,pasta,criado_por_id,criado_em,atualizado_em) "
        "VALUES (?,?,?,?,'backlog',?,?,?,?,?,?)",
        (empresa_id, codigo, titulo, tipo, responsavel_id, aprovador_id, pasta, user_id, instante, instante),
    )
    did = cur.lastrowid
    conn.execute(
        "INSERT INTO documento_revisoes (documento_id,numero,estado,criado_por_id,criado_em,revisado_por_id,revisao_em) "
        "VALUES (?,1,'rascunho',?,?,?,?)",
        (did, user_id, instante, user_id, instante),
    )
    _audit(conn, did, "criado", f"Documento {codigo} criado", user_id, instante)
    return did


@router.post("", status_code=201)
def create_doc(body: DocumentoIn, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        did = create_documento_interno(conn, company, body.titulo, body.tipo, user["id"],
                                       body.responsavel_id, body.aprovador_id)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (did,)).fetchone())


@router.put("/{documento_id}")
def update_doc(documento_id: int, body: DocumentoUpdate, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        titulo = body.titulo if body.titulo is not None else row["titulo"]
        tipo = body.tipo if body.tipo is not None else row["tipo"]
        if tipo not in TIPOS:
            raise HTTPException(status_code=422, detail="Tipo inválido")
        responsavel_id = body.responsavel_id if body.responsavel_id is not None else row["responsavel_id"]
        aprovador_id = body.aprovador_id if body.aprovador_id is not None else row["aprovador_id"]
        check_user_empresa(conn, responsavel_id, row["empresa_id"], "Responsável")
        check_user_empresa(conn, aprovador_id, row["empresa_id"], "Aprovador")
        conn.execute(
            "UPDATE documentos_controlados SET titulo=?,tipo=?,responsavel_id=?,aprovador_id=?,atualizado_em=? WHERE id=?",
            (titulo, tipo, responsavel_id, aprovador_id, instante, documento_id),
        )
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.delete("/{documento_id}", status_code=204)
def delete_doc(documento_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        pasta = row["pasta"] or ""
        conn.execute("DELETE FROM documentos_controlados WHERE id=?", (documento_id,))
        conn.commit()
    if pasta:
        try:
            delete_path(DOCS_DIR, pasta)
        except (ValueError, FileNotFoundError):
            pass


@router.get("/{documento_id}/revisoes")
def list_revisoes(documento_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        fetch_doc(conn, documento_id, user)
        rows = conn.execute(
            "SELECT * FROM documento_revisoes WHERE documento_id=? ORDER BY numero", (documento_id,)
        ).fetchall()
        return [rev_to_dict(conn, r) for r in rows]


@router.post("/{documento_id}/revisoes", status_code=201)
def create_revisao(documento_id: int, body: RevisaoIn, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["checkout_por_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=409, detail="Faça check-out do documento antes de criar uma revisão")
        if row["estado"] == "obsoleto":
            raise HTTPException(status_code=409, detail="Documento obsoleto não aceita novas revisões")
        maxnum = conn.execute(
            "SELECT COALESCE(MAX(numero),0) FROM documento_revisoes WHERE documento_id=?", (documento_id,)
        ).fetchone()[0]
        numero = maxnum + 1
        cur = conn.execute(
            "INSERT INTO documento_revisoes (documento_id,numero,descricao_mudanca,variante,estado,criado_por_id,criado_em,revisado_por_id,revisao_em) "
            "VALUES (?,?,?,?,'rascunho',?,?,?,?)",
            (documento_id, numero, body.descricao_mudanca, body.variante, user["id"], instante, user["id"], instante),
        )
        conn.execute(
            "UPDATE documentos_controlados SET estado='em_revisao',atualizado_em=? WHERE id=?",
            (instante, documento_id),
        )
        _audit(conn, documento_id, "revisao_criada", f"Revisão R{numero:02d}", user["id"], instante)
        conn.commit()
        return rev_to_dict(conn, conn.execute("SELECT * FROM documento_revisoes WHERE id=?", (cur.lastrowid,)).fetchone())


def _rev_folder(doc, numero):
    folder = folder_for(doc["pasta"] or "")
    return safe_rel(folder, f"R{numero:02d}")


@router.post("/{documento_id}/revisoes/{numero}/arquivo", status_code=201)
def upload_revisao(documento_id: int, numero: int, file: UploadFile = File(...),
                   user: dict = Depends(editor_dep)):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    instante = now()
    with get_connection() as conn:
        doc = fetch_doc(conn, documento_id, user)
        if doc["checkout_por_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=409, detail="Faça check-out do documento antes de enviar o arquivo")
        rev = conn.execute(
            "SELECT * FROM documento_revisoes WHERE documento_id=? AND numero=?", (documento_id, numero)
        ).fetchone()
        if rev is None:
            raise HTTPException(status_code=404, detail="Revisão não encontrada")
        if rev["estado"] != "rascunho":
            raise HTTPException(status_code=409, detail="Só é possível anexar arquivo em revisão rascunho")
        target_dir = _rev_folder(doc, numero)
        target_dir.mkdir(parents=True, exist_ok=True)
        nome = save_file(target_dir, file.filename or "documento", data)
        arquivo_hash = hashlib.sha256(data).hexdigest()
        conn.execute(
            "UPDATE documento_revisoes SET arquivo_nome=?,arquivo_hash=?,fonte='arquivo' WHERE id=?",
            (nome, arquivo_hash, rev["id"]),
        )
        _audit(conn, documento_id, "arquivo", f"R{numero:02d}: {nome} ({arquivo_hash[:12]})", user["id"], instante)
        conn.commit()
        return {"nome": nome, "hash": arquivo_hash}


class LinkIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2000)


@router.post("/{documento_id}/revisoes/{numero}/link", status_code=201)
def set_revisao_link(documento_id: int, numero: int, body: LinkIn, user: dict = Depends(editor_dep)):
    """Define a fonte da revisão como um link externo (ex.: Google Docs)."""
    from urllib.parse import urlsplit
    u = body.url.strip()
    if urlsplit(u).scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Informe uma URL http(s) válida")
    instante = now()
    with get_connection() as conn:
        doc = fetch_doc(conn, documento_id, user)
        if doc["checkout_por_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=409, detail="Faça check-out do documento antes de definir o link")
        rev = conn.execute("SELECT * FROM documento_revisoes WHERE documento_id=? AND numero=?", (documento_id, numero)).fetchone()
        if rev is None:
            raise HTTPException(status_code=404, detail="Revisão não encontrada")
        if rev["estado"] != "rascunho":
            raise HTTPException(status_code=409, detail="Só é possível definir o link em revisão rascunho")
        conn.execute("UPDATE documento_revisoes SET url=?,fonte='link' WHERE id=?", (u, rev["id"]))
        _audit(conn, documento_id, "link", f"R{numero:02d}: {u[:80]}", user["id"], instante)
        conn.commit()
        return {"url": u}


@router.get("/{documento_id}/revisoes/{numero}/arquivo")
def download_revisao(documento_id: int, numero: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        doc = fetch_doc(conn, documento_id, user)
        rev = conn.execute(
            "SELECT * FROM documento_revisoes WHERE documento_id=? AND numero=?", (documento_id, numero)
        ).fetchone()
    if rev is None or not rev["arquivo_nome"]:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    target = _rev_folder(doc, numero) / rev["arquivo_nome"]
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    mime = guess_mime(target.name)
    inline = mime.startswith("image/") or mime == "application/pdf" or mime.startswith("text/")
    return FileResponse(target, media_type=mime, filename=target.name,
                        content_disposition_type="inline" if inline else "attachment")


@router.post("/{documento_id}/checkout")
def checkout(documento_id: int, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["checkout_por_id"] is not None:
            if row["checkout_por_id"] == user["id"]:
                return doc_to_dict(conn, row)
            quem = user_nome(conn, row["checkout_por_id"]) or "outro usuário"
            raise HTTPException(status_code=409, detail=f"Documento em uso por {quem}")
        if row["estado"] == "obsoleto":
            raise HTTPException(status_code=409, detail="Documento obsoleto não pode ser editado")
        conn.execute(
            "UPDATE documentos_controlados SET checkout_por_id=?,checkout_em=?,atualizado_em=? WHERE id=?",
            (user["id"], instante, instante, documento_id),
        )
        _audit(conn, documento_id, "checkout", "Check-out", user["id"], instante)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.post("/{documento_id}/checkin")
def checkin(documento_id: int, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["checkout_por_id"] is None:
            return doc_to_dict(conn, row)
        if row["checkout_por_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=403, detail="Somente quem fez o check-out (ou um admin) pode liberar")
        conn.execute(
            "UPDATE documentos_controlados SET checkout_por_id=NULL,checkout_em=NULL,atualizado_em=? WHERE id=?",
            (instante, documento_id),
        )
        _audit(conn, documento_id, "checkin", "Check-in", user["id"], instante)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.post("/{documento_id}/aprovar")
def aprovar(documento_id: int, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["aprovador_id"] is not None and row["aprovador_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=403, detail="Somente o aprovador definido pode aprovar este documento")
        if row["checkout_por_id"] is not None:
            raise HTTPException(status_code=409, detail="Faça check-in antes de aprovar (documento em edição)")
        rev = _latest_rev(conn, documento_id)
        if rev is None:
            raise HTTPException(status_code=400, detail="Documento sem revisão")
        conn.execute(
            "UPDATE documento_revisoes SET estado='obsoleta' WHERE documento_id=? AND id<>?",
            (documento_id, rev["id"]),
        )
        conn.execute(
            "UPDATE documento_revisoes SET estado='aprovada',aprovado_por_id=?,aprovacao_em=? WHERE id=?",
            (user["id"], instante, rev["id"]),
        )
        conn.execute(
            "UPDATE documentos_controlados SET estado='aprovado',revisao_atual_id=?,atualizado_em=? WHERE id=?",
            (rev["id"], instante, documento_id),
        )
        _audit(conn, documento_id, "aprovado", f"Revisão R{rev['numero']:02d} aprovada", user["id"], instante)
        sync_norma_status(conn, documento_id)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.post("/{documento_id}/obsoletar")
def obsoletar(documento_id: int, user: dict = Depends(editor_dep)):
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        conn.execute(
            "UPDATE documentos_controlados SET estado='obsoleto',checkout_por_id=NULL,checkout_em=NULL,atualizado_em=? WHERE id=?",
            (instante, documento_id),
        )
        conn.execute("UPDATE documento_revisoes SET estado='obsoleta' WHERE documento_id=?", (documento_id,))
        _audit(conn, documento_id, "obsoletado", "Documento obsoletado", user["id"], instante)
        sync_norma_status(conn, documento_id)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


class MoverIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    estado: str


# Transições permitidas do Kanban (alvo -> origens válidas). Obsolescência é fluxo
# separado (POST /obsoletar), por isso não aparece aqui.
MOVER = {
    "em_revisao": {"backlog", "em_aprovacao"},
    "em_aprovacao": {"backlog", "em_revisao"},
    "aprovado": {"em_aprovacao"},
}


@router.post("/{documento_id}/mover")
def mover(documento_id: int, body: MoverIn, user: dict = Depends(editor_dep)):
    """Move o documento entre os estados do ciclo (Kanban). 'aprovado' exige o aprovador."""
    instante = now()
    alvo = body.estado
    if alvo not in MOVER:
        raise HTTPException(status_code=422, detail="Estado de destino inválido (obsolescência é fluxo separado)")
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["estado"] not in MOVER[alvo]:
            raise HTTPException(status_code=409, detail=f"Transição inválida: {row['estado']} → {alvo}")
        if alvo == "aprovado":
            if row["aprovador_id"] is not None and row["aprovador_id"] != user["id"] and not is_superuser(user):
                raise HTTPException(status_code=403, detail="Somente o aprovador definido pode aprovar")
            if row["checkout_por_id"] is not None:
                raise HTTPException(status_code=409, detail="Faça check-in antes de aprovar")
            rev = _latest_rev(conn, documento_id)
            if rev is None:
                raise HTTPException(status_code=400, detail="Documento sem revisão")
            conn.execute("UPDATE documento_revisoes SET estado='obsoleta' WHERE documento_id=? AND id<>?", (documento_id, rev["id"]))
            conn.execute("UPDATE documento_revisoes SET estado='aprovada',aprovado_por_id=?,aprovacao_em=? WHERE id=?", (user["id"], instante, rev["id"]))
            conn.execute("UPDATE documentos_controlados SET estado='aprovado',revisao_atual_id=?,atualizado_em=? WHERE id=?", (rev["id"], instante, documento_id))
        else:
            conn.execute("UPDATE documentos_controlados SET estado=?,atualizado_em=? WHERE id=?", (alvo, instante, documento_id))
        _audit(conn, documento_id, "mover", f"{row['estado']} → {alvo}", user["id"], instante)
        sync_norma_status(conn, documento_id)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.post("/{documento_id}/reativar")
def reativar(documento_id: int, user: dict = Depends(editor_dep)):
    """Reativa um documento obsoleto (fluxo separado): obsoleto → rascunho (volta ao Backlog)."""
    instante = now()
    with get_connection() as conn:
        row = fetch_doc(conn, documento_id, user)
        if row["estado"] != "obsoleto":
            raise HTTPException(status_code=409, detail="Apenas documentos obsoletos podem ser reativados")
        rev = _latest_rev(conn, documento_id)
        if rev is not None:
            conn.execute("UPDATE documento_revisoes SET estado='rascunho' WHERE id=?", (rev["id"],))
        conn.execute("UPDATE documentos_controlados SET estado='backlog',revisao_atual_id=NULL,atualizado_em=? WHERE id=?", (instante, documento_id))
        _audit(conn, documento_id, "reativado", "Obsoleto → backlog (reativação)", user["id"], instante)
        sync_norma_status(conn, documento_id)
        conn.commit()
        return doc_to_dict(conn, conn.execute("SELECT * FROM documentos_controlados WHERE id=?", (documento_id,)).fetchone())


@router.get("/{documento_id}/auditoria")
def auditoria(documento_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        fetch_doc(conn, documento_id, user)
        rows = conn.execute(
            "SELECT evento,detalhe,criado_em,hash_anterior,hash_atual,usuario_id FROM documento_auditoria WHERE documento_id=? ORDER BY id",
            (documento_id,),
        ).fetchall()
        itens = []
        ok = True
        prev = ""
        for r in rows:
            d = dict(r)
            d["usuario_nome"] = user_nome(conn, r["usuario_id"])
            if r["hash_anterior"] != prev:
                ok = False
            prev = r["hash_atual"]
            itens.append(d)
    return {"eventos": itens, "integra": ok}


@router.post("/{documento_id}/revisoes/{numero}/ler")
def ler_revisao(documento_id: int, numero: int, acesso_id: int | None = Form(default=None),
                user: dict = Depends(editor_dep)):
    """Lê o arquivo da revisão: extração digital local; se vazio e houver acesso
    LLM (OpenRouter com visão), lê por IA. Grava `texto_extraido`/`origem_texto`."""
    from app.services import captura
    instante = now()
    with get_connection() as conn:
        doc = fetch_doc(conn, documento_id, user)
        rev = conn.execute(
            "SELECT * FROM documento_revisoes WHERE documento_id=? AND numero=?", (documento_id, numero)
        ).fetchone()
        if rev is None or not rev["arquivo_nome"]:
            raise HTTPException(status_code=404, detail="Revisão sem arquivo")
        acesso = None
        if acesso_id is not None:
            acesso = conn.execute(
                "SELECT * FROM llm_acessos WHERE id=? AND empresa_id=? AND ativo=1", (acesso_id, doc["empresa_id"])
            ).fetchone()
            if acesso is None:
                raise HTTPException(status_code=404, detail="Acesso LLM não encontrado")
            acesso = dict(acesso)
    target = _rev_folder(doc, numero) / rev["arquivo_nome"]
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    data = target.read_bytes()
    resultado = captura.ler_documento(rev["arquivo_nome"], data, acesso)
    with get_connection() as conn:
        conn.execute(
            "UPDATE documento_revisoes SET texto_extraido=?,origem_texto=? WHERE id=?",
            (resultado["texto"], resultado["origem"], rev["id"]),
        )
        _audit(conn, documento_id, "leitura", f"R{numero:02d}: origem {resultado['origem']}", user["id"], instante)
        conn.commit()
    return {"origem": resultado["origem"], "caracteres": len(resultado["texto"]), "texto": resultado["texto"]}
