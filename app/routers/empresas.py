from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import is_superuser, require_papel
from app.db import DOCS_DIR, get_connection
from app.docs import delete_path, sanitize
from app.security import SafeModel

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


class EmpresaIn(SafeModel):
    razao_social: str
    cnpj: str = ""


class EmpresaUpdate(SafeModel):
    razao_social: str | None = None
    cnpj: str | None = None
    ativo: int | None = None


def row_to_dict(row):
    return {
        "id": row["id"],
        "razao_social": row["razao_social"],
        "cnpj": row["cnpj"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def _can_access(user, empresa_id):
    return is_superuser(user) or user["empresa_id"] == empresa_id


@router.get("")
def list_empresas(user: dict = Depends(require_papel("admin"))):
    with get_connection() as conn:
        if is_superuser(user):
            rows = conn.execute("SELECT * FROM empresas ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM empresas WHERE id = ?", (user["empresa_id"],)
            ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
def create_empresa(empresa: EmpresaIn, user: dict = Depends(require_papel("admin"))):
    if not is_superuser(user):
        raise HTTPException(status_code=403, detail="Apenas o superusuário cria empresas")
    criado_em = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO empresas (razao_social, cnpj, ativo, criado_em) VALUES (?, ?, 1, ?)",
            (empresa.razao_social, empresa.cnpj, criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM empresas WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.get("/{empresa_id}")
def get_empresa(empresa_id: int, user: dict = Depends(require_papel("admin"))):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not _can_access(user, empresa_id):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row_to_dict(row)


@router.put("/{empresa_id}")
def update_empresa(empresa_id: int, empresa: EmpresaUpdate, user: dict = Depends(require_papel("admin"))):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if not _can_access(user, empresa_id):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        razao = empresa.razao_social if empresa.razao_social is not None else row["razao_social"]
        cnpj = empresa.cnpj if empresa.cnpj is not None else row["cnpj"]
        ativo = empresa.ativo if empresa.ativo is not None else row["ativo"]
        conn.execute(
            "UPDATE empresas SET razao_social = ?, cnpj = ?, ativo = ? WHERE id = ?",
            (razao, cnpj, ativo, empresa_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    return row_to_dict(row)


@router.delete("/{empresa_id}", status_code=204)
def delete_empresa(empresa_id: int, user: dict = Depends(require_papel("admin"))):
    if not is_superuser(user):
        raise HTTPException(status_code=403, detail="Apenas o superusuário exclui empresas")
    with get_connection() as conn:
        row = conn.execute("SELECT razao_social FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        razao = row["razao_social"]
        conn.execute("DELETE FROM empresas WHERE id = ?", (empresa_id,))
        conn.commit()
    try:
        delete_path(DOCS_DIR, sanitize(razao))
    except (ValueError, FileNotFoundError):
        pass
