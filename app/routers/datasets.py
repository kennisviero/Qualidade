import csv
import json
from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import get_current_user, is_superuser, require_papel
from app.db import get_connection
from app.security import SafeModel

router = APIRouter(tags=["datasets"])

editor_dep = require_papel("admin", "editor")


class DatasetIn(SafeModel):
    nome: str
    tipo: str
    dados: list | dict


def row_to_dict(row):
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "nome": row["nome"],
        "tipo": row["tipo"],
        "dados": json.loads(row["dados"]),
        "criado_em": row["criado_em"],
    }


def owns(user, empresa_id):
    return is_superuser(user) or user["empresa_id"] == empresa_id


def check_project(conn, project_id, user):
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    if not owns(user, row["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row


def parse_csv(text, tipo):
    reader = csv.reader(StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []
    if tipo == "pareto":
        header = rows[0]
        cat_idx = 0
        freq_idx = 1 if len(header) > 1 else 0
        dados = []
        for r in rows[1:]:
            dados.append({"rotulo": r[cat_idx], "frequencia": float(r[freq_idx])})
        return dados
    if tipo == "dispersao":
        return [{"x": float(r[0]), "y": float(r[1])} for r in rows[1:]]
    if tipo == "controle":
        dados = []
        for r in rows[1:]:
            for cell in r:
                try:
                    dados.append(float(cell))
                except ValueError:
                    continue
        return dados
    return [dict(zip(rows[0], r)) for r in rows[1:]]


@router.get("/api/projects/{project_id}/datasets")
def list_datasets(project_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        check_project(conn, project_id, user)
        rows = conn.execute(
            "SELECT * FROM datasets WHERE project_id = ? ORDER BY id DESC", (project_id,)
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/api/projects/{project_id}/datasets", status_code=201)
def create_dataset(project_id: int, dataset: DatasetIn, user: dict = Depends(editor_dep)):
    criado_em = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        check_project(conn, project_id, user)
        cur = conn.execute(
            "INSERT INTO datasets (project_id, nome, tipo, dados, criado_em) VALUES (?, ?, ?, ?, ?)",
            (project_id, dataset.nome, dataset.tipo, json.dumps(dataset.dados), criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.post("/api/projects/{project_id}/datasets/csv", status_code=201)
def import_csv(
    project_id: int,
    file: UploadFile = File(...),
    nome: str = Form(...),
    tipo: str = Form(...),
    user: dict = Depends(editor_dep),
):
    with get_connection() as conn:
        check_project(conn, project_id, user)
    text = file.file.read().decode("utf-8-sig")
    dados = parse_csv(text, tipo)
    criado_em = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO datasets (project_id, nome, tipo, dados, criado_em) VALUES (?, ?, ?, ?, ?)",
            (project_id, nome, tipo, json.dumps(dados), criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")
        check_project(conn, row["project_id"], user)
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        conn.commit()
