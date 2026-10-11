from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import (
    create_session,
    delete_session,
    empresa_desativada,
    get_current_user,
    public_user,
    verify_password,
)
from app.db import get_connection
from app.security import SafeModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(SafeModel):
    _sanitize_skip = frozenset({"senha"})
    email: str
    senha: str


@router.post("/login")
def login(body: LoginIn, response: Response):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (body.email,)
        ).fetchone()
        if row is None or not verify_password(body.senha, row["senha_hash"]):
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        if not row["ativo"]:
            raise HTTPException(status_code=401, detail="Usuário desativado")
        if empresa_desativada(conn, row["empresa_id"]):
            raise HTTPException(status_code=401, detail="Empresa desativada")
    token = create_session(row["id"])
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return public_user(dict(row))


@router.post("/logout")
def logout(response: Response, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        conn.commit()
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return public_user(user)
