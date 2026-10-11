from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, is_superuser, require_papel
from app.db import DOCS_DIR, get_connection
from app.docs import build_pasta, delete_path, ensure_pasta
from app.security import SafeModel

router = APIRouter(prefix="/api/processos", tags=["processos"])

editor_dep = require_papel("admin", "editor")

STATUSES = ("rascunho", "em_revisao", "aprovado")


class ProcessoIn(SafeModel):
    _sanitize_skip = frozenset({"sintaxe"})
    empresa_id: int | None = None
    setor_id: int | None = None
    nome: str
    descricao: str = ""
    sintaxe: str = ""
    ativo: str = ""
    responsavel_id: int | None = None
    aprovador_id: int | None = None


class ProcessoUpdate(SafeModel):
    nome: str | None = None
    setor_id: int | None = None
    descricao: str | None = None
    ativo: str | None = None
    responsavel_id: int | None = None
    aprovador_id: int | None = None
    status: str | None = None


class RevisaoIn(SafeModel):
    _sanitize_skip = frozenset({"sintaxe"})
    sintaxe: str


def now():
    return datetime.now(timezone.utc).isoformat()


def user_nome(conn, user_id):
    if user_id is None:
        return None
    row = conn.execute("SELECT nome FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    return row["nome"] if row else None


def row_to_dict(conn, row):
    d = dict(row)
    d["responsavel_nome"] = user_nome(conn, d.get("responsavel_id"))
    d["aprovador_nome"] = user_nome(conn, d.get("aprovador_id"))
    d["criado_por_nome"] = user_nome(conn, d.get("criado_por_id"))
    d["setor_nome"] = None
    if d.get("setor_id"):
        srow = conn.execute("SELECT nome FROM setores WHERE id = ?", (d["setor_id"],)).fetchone()
        if srow:
            d["setor_nome"] = srow["nome"]
    rev = conn.execute(
        "SELECT * FROM revisoes WHERE processo_id = ? ORDER BY numero DESC LIMIT 1", (d["id"],)
    ).fetchone()
    if rev:
        d["revisao_em"] = rev["revisao_em"]
        d["revisado_por_nome"] = user_nome(conn, rev["revisado_por_id"])
        d["aprovacao_em"] = rev["aprovacao_em"]
        d["aprovado_por_nome"] = user_nome(conn, rev["aprovado_por_id"])
    else:
        d["revisao_em"] = None
        d["revisado_por_nome"] = None
        d["aprovacao_em"] = None
        d["aprovado_por_nome"] = None
    return d


def rev_to_dict(conn, r):
    d = dict(r)
    d["revisado_por_nome"] = user_nome(conn, r["revisado_por_id"])
    d["aprovado_por_nome"] = user_nome(conn, r["aprovado_por_id"])
    return d


def check_setor_empresa(conn, setor_id, empresa_id):
    if setor_id is None:
        return None
    srow = conn.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
    if srow is None or srow["empresa_id"] != empresa_id:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    return srow


def check_user_empresa(conn, user_id, empresa_id, label):
    if user_id is None:
        return
    urow = conn.execute("SELECT empresa_id FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    if urow is None or urow["empresa_id"] != empresa_id:
        raise HTTPException(status_code=422, detail=f"{label} invalido para a empresa do processo")


def fetch_processo(conn, processo_id, user):
    row = conn.execute("SELECT * FROM processos WHERE id = ?", (processo_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    if not (is_superuser(user) or user["empresa_id"] == row["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row


@router.get("")
def list_processos(
    empresa_id: int | None = None,
    setor_id: int | None = None,
    user: dict = Depends(get_current_user),
):
    with get_connection() as conn:
        if is_superuser(user):
            if setor_id is not None:
                rows = conn.execute(
                    "SELECT * FROM processos WHERE setor_id = ? ORDER BY nome", (setor_id,)
                ).fetchall()
            elif empresa_id is not None:
                rows = conn.execute(
                    "SELECT * FROM processos WHERE empresa_id = ? ORDER BY nome", (empresa_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM processos ORDER BY nome").fetchall()
        else:
            if setor_id is not None:
                rows = conn.execute(
                    "SELECT * FROM processos WHERE empresa_id = ? AND setor_id = ? ORDER BY nome",
                    (user["empresa_id"], setor_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM processos WHERE empresa_id = ? ORDER BY nome",
                    (user["empresa_id"],),
                ).fetchall()
        result = [row_to_dict(conn, r) for r in rows]
    return result


@router.post("", status_code=201)
def create_processo(processo: ProcessoIn, user: dict = Depends(editor_dep)):
    criado_em = now()
    with get_connection() as conn:
        if not is_superuser(user):
            empresa_id = user["empresa_id"]
        else:
            empresa_id = processo.empresa_id
            if empresa_id is None and processo.setor_id is not None:
                srow = conn.execute(
                    "SELECT empresa_id FROM setores WHERE id = ?", (processo.setor_id,)
                ).fetchone()
                if srow is None:
                    raise HTTPException(status_code=404, detail="Setor não encontrado")
                empresa_id = srow["empresa_id"]
        if empresa_id is None:
            raise HTTPException(status_code=400, detail="Informe a empresa (ou o setor) do processo")
        empresa = conn.execute(
            "SELECT razao_social FROM empresas WHERE id = ?", (empresa_id,)
        ).fetchone()
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        setor_nome = ""
        if processo.setor_id is not None:
            srow = check_setor_empresa(conn, processo.setor_id, empresa_id)
            setor_nome = srow["nome"]
        check_user_empresa(conn, processo.responsavel_id, empresa_id, "Responsavel")
        check_user_empresa(conn, processo.aprovador_id, empresa_id, "Aprovador")
        existing = conn.execute(
            "SELECT id FROM processos WHERE empresa_id = ? AND nome = ?",
            (empresa_id, processo.nome),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Já existe um processo com este nome nesta empresa")
        pasta = build_pasta(empresa["razao_social"], setor_nome, processo.nome)
        ensure_pasta(pasta)
        cur = conn.execute(
            "INSERT INTO processos (empresa_id, setor_id, nome, descricao, sintaxe, ativo, criado_por_id, "
            "responsavel_id, aprovador_id, status, pasta, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'rascunho', ?, ?, ?)",
            (
                empresa_id,
                processo.setor_id,
                processo.nome,
                processo.descricao,
                processo.sintaxe,
                processo.ativo,
                user["id"],
                processo.responsavel_id,
                processo.aprovador_id,
                pasta,
                criado_em,
                criado_em,
            ),
        )
        pid = cur.lastrowid
        conn.execute(
            "INSERT INTO revisoes (processo_id, numero, sintaxe, revisado_por_id, criado_em, revisao_em) "
            "VALUES (?, 1, ?, ?, ?, ?)",
            (pid, processo.sintaxe, user["id"], criado_em, criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM processos WHERE id = ?", (pid,)).fetchone()
        result = row_to_dict(conn, row)
    return result


@router.get("/{processo_id}")
def get_processo(processo_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        row = fetch_processo(conn, processo_id, user)
        result = row_to_dict(conn, row)
    return result


@router.put("/{processo_id}")
def update_processo(processo_id: int, processo: ProcessoUpdate, user: dict = Depends(editor_dep)):
    atualizado_em = now()
    with get_connection() as conn:
        row = fetch_processo(conn, processo_id, user)
        nome = processo.nome if processo.nome is not None else row["nome"]
        descricao = processo.descricao if processo.descricao is not None else row["descricao"]
        ativo = processo.ativo if processo.ativo is not None else row["ativo"]
        responsavel_id = processo.responsavel_id if processo.responsavel_id is not None else row["responsavel_id"]
        aprovador_id = processo.aprovador_id if processo.aprovador_id is not None else row["aprovador_id"]
        status = processo.status if processo.status is not None else row["status"]
        setor_id = processo.setor_id if processo.setor_id is not None else row["setor_id"]
        if status not in STATUSES:
            raise HTTPException(status_code=422, detail="Status inválido")
        if setor_id is not None:
            check_setor_empresa(conn, setor_id, row["empresa_id"])
        check_user_empresa(conn, responsavel_id, row["empresa_id"], "Responsavel")
        check_user_empresa(conn, aprovador_id, row["empresa_id"], "Aprovador")
        conn.execute(
            "UPDATE processos SET nome = ?, setor_id = ?, descricao = ?, ativo = ?, responsavel_id = ?, aprovador_id = ?, "
            "status = ?, atualizado_em = ? WHERE id = ?",
            (nome, setor_id, descricao, ativo, responsavel_id, aprovador_id, status, atualizado_em, processo_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM processos WHERE id = ?", (processo_id,)).fetchone()
        result = row_to_dict(conn, row)
    return result


@router.get("/{processo_id}/revisoes")
def list_revisoes(processo_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        fetch_processo(conn, processo_id, user)
        rows = conn.execute(
            "SELECT * FROM revisoes WHERE processo_id = ? ORDER BY numero", (processo_id,)
        ).fetchall()
        result = [rev_to_dict(conn, r) for r in rows]
    return result


@router.post("/{processo_id}/revisoes", status_code=201)
def create_revisao(processo_id: int, revisao: RevisaoIn, user: dict = Depends(editor_dep)):
    criado_em = now()
    with get_connection() as conn:
        fetch_processo(conn, processo_id, user)
        maxnum = conn.execute(
            "SELECT COALESCE(MAX(numero), 0) FROM revisoes WHERE processo_id = ?", (processo_id,)
        ).fetchone()[0]
        numero = maxnum + 1
        cur = conn.execute(
            "INSERT INTO revisoes (processo_id, numero, sintaxe, revisado_por_id, criado_em, revisao_em) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (processo_id, numero, revisao.sintaxe, user["id"], criado_em, criado_em),
        )
        conn.execute(
            "UPDATE processos SET sintaxe = ?, status = 'em_revisao', atualizado_em = ? WHERE id = ?",
            (revisao.sintaxe, criado_em, processo_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM revisoes WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = rev_to_dict(conn, row)
    return result


@router.post("/{processo_id}/aprovar")
def aprovar_processo(processo_id: int, user: dict = Depends(editor_dep)):
    aprovacao_em = now()
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        if processo["aprovador_id"] is not None and processo["aprovador_id"] != user["id"] and not is_superuser(user):
            raise HTTPException(status_code=403, detail="Somente o aprovador definido pode aprovar este processo")
        rev = conn.execute(
            "SELECT id FROM revisoes WHERE processo_id = ? ORDER BY numero DESC LIMIT 1", (processo_id,)
        ).fetchone()
        if rev is None:
            raise HTTPException(status_code=400, detail="Processo sem revisão")
        conn.execute(
            "UPDATE revisoes SET aprovado_por_id = ?, aprovacao_em = ? WHERE id = ?",
            (user["id"], aprovacao_em, rev["id"]),
        )
        conn.execute(
            "UPDATE processos SET status = 'aprovado', atualizado_em = ? WHERE id = ?",
            (aprovacao_em, processo_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM processos WHERE id = ?", (processo_id,)).fetchone()
        result = row_to_dict(conn, row)
    return result


@router.delete("/{processo_id}", status_code=204)
def delete_processo(processo_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_processo(conn, processo_id, user)
        pasta = row["pasta"] or ""
        conn.execute("DELETE FROM processos WHERE id = ?", (processo_id,))
        conn.commit()
    if pasta:
        try:
            delete_path(DOCS_DIR, pasta)
        except (ValueError, FileNotFoundError):
            pass
