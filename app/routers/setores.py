from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, is_superuser, require_papel
from app.db import DOCS_DIR, get_connection
from app.docs import delete_path, sanitize
from app.security import SafeModel

router = APIRouter(prefix="/api/setores", tags=["setores"])

editor_dep = require_papel("admin", "editor")


class SetorIn(SafeModel):
    nome: str
    empresa_id: int | None = None


class SetorUpdate(SafeModel):
    nome: str | None = None


def row_to_dict(row):
    return {
        "id": row["id"],
        "empresa_id": row["empresa_id"],
        "nome": row["nome"],
        "criado_em": row["criado_em"],
    }


def owns(user, empresa_id):
    return is_superuser(user) or user["empresa_id"] == empresa_id


@router.get("")
def list_setores(empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        if is_superuser(user):
            if empresa_id is None:
                rows = conn.execute("SELECT * FROM setores ORDER BY nome").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM setores WHERE empresa_id = ? ORDER BY nome", (empresa_id,)
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM setores WHERE empresa_id = ? ORDER BY nome",
                (user["empresa_id"],),
            ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
def create_setor(setor: SetorIn, user: dict = Depends(editor_dep)):
    if not is_superuser(user):
        setor.empresa_id = user["empresa_id"]
    if setor.empresa_id is None:
        raise HTTPException(status_code=400, detail="Informe a empresa")
    if not owns(user, setor.empresa_id):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    criado_em = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        empresa = conn.execute(
            "SELECT id FROM empresas WHERE id = ?", (setor.empresa_id,)
        ).fetchone()
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        cur = conn.execute(
            "INSERT INTO setores (empresa_id, nome, criado_em) VALUES (?, ?, ?)",
            (setor.empresa_id, setor.nome, criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM setores WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.put("/{setor_id}")
def update_setor(setor_id: int, setor: SetorUpdate, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Setor não encontrado")
        if not owns(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        nome = setor.nome if setor.nome is not None else row["nome"]
        conn.execute("UPDATE setores SET nome = ? WHERE id = ?", (nome, setor_id))
        conn.commit()
        row = conn.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
    return row_to_dict(row)


@router.delete("/{setor_id}", status_code=204)
def delete_setor(setor_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT s.id, s.nome, s.empresa_id, e.razao_social AS empresa_nome "
            "FROM setores s JOIN empresas e ON e.id = s.empresa_id WHERE s.id = ?",
            (setor_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Setor não encontrado")
        if not owns(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        pasta = f"{sanitize(row['empresa_nome'])}/{sanitize(row['nome'])}"
        conn.execute("DELETE FROM setores WHERE id = ?", (setor_id,))
        conn.commit()
    try:
        delete_path(DOCS_DIR, pasta)
    except (ValueError, FileNotFoundError):
        pass
