import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, Depends, HTTPException

from app.db import get_connection

SESSION_TTL_HOURS = 8


def hash_password(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    criado_em = datetime.now(timezone.utc).isoformat()
    expira_em = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, criado_em, expira_em) VALUES (?, ?, ?, ?)",
            (token, user_id, criado_em, expira_em),
        )
        conn.commit()
    return token


def delete_session(token: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def get_current_user(session: str | None = Cookie(default=None)) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Não autenticado")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN usuarios u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.expira_em > ?",
            (session, datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        user = dict(row)
        if not user["ativo"]:
            raise HTTPException(status_code=401, detail="Usuário desativado")
        if empresa_desativada(conn, user["empresa_id"]):
            raise HTTPException(status_code=401, detail="Empresa desativada")
    return user


def empresa_desativada(conn, empresa_id) -> bool:
    if empresa_id is None:
        return False
    row = conn.execute("SELECT ativo FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    return row is not None and not row["ativo"]


def is_superuser(user: dict) -> bool:
    return user["papel"] == "admin" and user["empresa_id"] is None


def require_papel(*papeis):
    def dep(user: dict = Depends(get_current_user)):
        if user["papel"] not in papeis:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return user

    return dep


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "empresa_id": user["empresa_id"],
        "setor_id": user.get("setor_id"),
        "posicao": user.get("posicao", ""),
        "nome": user["nome"],
        "email": user["email"],
        "papel": user["papel"],
        "ativo": user["ativo"],
    }
