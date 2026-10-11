from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, is_superuser, require_papel
from app.db import get_connection
from app.security import SafeModel

router = APIRouter(prefix="/api/projects", tags=["projects"])

editor_dep = require_papel("admin", "editor")


class ProjectIn(SafeModel):
    nome: str
    descricao: str = ""
    empresa_id: int | None = None


class ProjectUpdate(SafeModel):
    nome: str | None = None
    descricao: str | None = None


def row_to_dict(row):
    return {
        "id": row["id"],
        "empresa_id": row["empresa_id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "criado_em": row["criado_em"],
    }


def owns(user, empresa_id):
    return is_superuser(user) or user["empresa_id"] == empresa_id


@router.get("")
def list_projects(user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        if is_superuser(user):
            rows = conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM projects WHERE empresa_id = ? ORDER BY id DESC",
                (user["empresa_id"],),
            ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
def create_project(project: ProjectIn, user: dict = Depends(editor_dep)):
    if not is_superuser(user):
        project.empresa_id = user["empresa_id"]
    if project.empresa_id is None:
        raise HTTPException(status_code=400, detail="Informe a empresa")
    criado_em = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        empresa = conn.execute(
            "SELECT id FROM empresas WHERE id = ?", (project.empresa_id,)
        ).fetchone()
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        cur = conn.execute(
            "INSERT INTO projects (empresa_id, nome, descricao, criado_em) VALUES (?, ?, ?, ?)",
            (project.empresa_id, project.nome, project.descricao, criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.get("/{project_id}")
def get_project(project_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    if not owns(user, row["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row_to_dict(row)


@router.put("/{project_id}")
def update_project(project_id: int, project: ProjectUpdate, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
        if not owns(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        nome = project.nome if project.nome is not None else row["nome"]
        descricao = project.descricao if project.descricao is not None else row["descricao"]
        conn.execute(
            "UPDATE projects SET nome = ?, descricao = ? WHERE id = ?",
            (nome, descricao, project_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_dict(row)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
        if not owns(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
