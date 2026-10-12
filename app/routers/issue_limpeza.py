import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.auth import is_superuser, require_papel
from app.db import DB_PATH, get_connection
from app.security import SafeModel

router = APIRouter(prefix="/api/issues/limpeza", tags=["issues"])
admin_dep = require_papel("admin")


class LimpezaIn(SafeModel):
    empresa_id: int | None = None
    escopo: Literal["fechadas", "todas"] = "fechadas"
    confirmar: bool = False
    revisao: str


def empresa_limpeza(conn, user, empresa_id):
    if not is_superuser(user):
        if empresa_id is not None and empresa_id != user["empresa_id"]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        empresa_id = user["empresa_id"]
    if empresa_id is None:
        raise HTTPException(status_code=422, detail="Selecione uma empresa para limpar as Issues")
    if not conn.execute("SELECT id FROM empresas WHERE id = ?", (empresa_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa_id


def resumo_limpeza(conn, empresa_id, escopo):
    query = "SELECT i.*, (SELECT COUNT(*) FROM acoes WHERE issue_id = i.id) AS total_acoes "
    query += "FROM issues i WHERE i.empresa_id = ? AND NOT EXISTS (SELECT 1 FROM rncs WHERE issue_id = i.id) "
    if escopo == "fechadas":
        query += "AND i.status = 'fechada' "
    query += "ORDER BY i.id"
    rows = conn.execute(query, (empresa_id,)).fetchall()
    snapshot = json.dumps([dict(r) for r in rows], sort_keys=True, ensure_ascii=False)
    revision = hashlib.sha256((str(empresa_id) + escopo + snapshot).encode()).hexdigest()
    protected = conn.execute("SELECT COUNT(*) FROM issues i WHERE empresa_id = ? "
                             "AND EXISTS (SELECT 1 FROM rncs WHERE issue_id = i.id)", (empresa_id,)).fetchone()[0]
    summary = {"empresa_id": empresa_id, "escopo": escopo, "issues": len(rows),
               "acoes": sum(r["total_acoes"] for r in rows), "vinculadas_rnc_preservadas": protected,
               "revisao": revision}
    return rows, summary


@router.get("")
def preview_limpeza(empresa_id: int | None = None, escopo: Literal["fechadas", "todas"] = "fechadas",
                    user: dict = Depends(admin_dep)):
    with get_connection() as conn:
        empresa_id = empresa_limpeza(conn, user, empresa_id)
        return resumo_limpeza(conn, empresa_id, escopo)[1]


@router.post("")
def limpar_issues(body: LimpezaIn, user: dict = Depends(admin_dep)):
    if not body.confirmar:
        raise HTTPException(status_code=422, detail="Confirme a limpeza dos registros selecionados")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        empresa_id = empresa_limpeza(conn, user, body.empresa_id)
        rows, summary = resumo_limpeza(conn, empresa_id, body.escopo)
        if body.revisao != summary["revisao"]:
            raise HTTPException(status_code=409, detail="A base mudou. Atualize o resumo antes de confirmar a limpeza")
        if not rows:
            return {**summary, "removidas": 0, "backup": None}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = DB_PATH.parent / "backups" / f"qualidade_antes_limpeza_issues_{stamp}_{uuid.uuid4().hex[:8]}.db"
        backup.parent.mkdir(parents=True, exist_ok=True)
        with get_connection() as source, sqlite3.connect(backup) as target:
            source.backup(target)
        for row in rows:
            conn.execute("DELETE FROM acoes WHERE issue_id = ?", (row["id"],))
            if row["ishikawa_id"]:
                conn.execute("DELETE FROM ishikawas WHERE id = ? AND NOT EXISTS "
                             "(SELECT 1 FROM issues WHERE ishikawa_id = ? AND id <> ?)",
                             (row["ishikawa_id"], row["ishikawa_id"], row["id"]))
            conn.execute("DELETE FROM issues WHERE id = ?", (row["id"],))
        conn.commit()
        return {**summary, "removidas": len(rows), "backup": backup.name}
