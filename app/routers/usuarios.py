from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, hash_password, is_superuser, public_user, require_papel
from app.db import get_connection
from app.security import SafeModel

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

PAPEIS = ("admin", "editor", "visualizador")
POSICOES = ("Presidente", "Diretoria", "Gerente", "Supervisor", "Encarregado", "Colaborador")


class UsuarioIn(SafeModel):
    _sanitize_skip = frozenset({"senha"})
    nome: str
    email: str
    senha: str
    papel: str = "editor"
    empresa_id: int | None = None
    setor_id: int | None = None
    posicao: str = ""


class UsuarioUpdate(SafeModel):
    _sanitize_skip = frozenset({"senha"})
    nome: str | None = None
    email: str | None = None
    senha: str | None = None
    papel: str | None = None
    ativo: int | None = None
    setor_id: int | None = None
    posicao: str | None = None


def row_to_dict(conn, row):
    d = public_user(dict(row))
    setor_nome = None
    if d.get("setor_id"):
        s = conn.execute("SELECT nome FROM setores WHERE id = ?", (d["setor_id"],)).fetchone()
        setor_nome = s["nome"] if s else None
    d["setor_nome"] = setor_nome
    return d


def _can_access(user, target_empresa_id):
    if is_superuser(user):
        return True
    return target_empresa_id == user["empresa_id"]


def _resolve_setor(conn, setor_id, user):
    row = conn.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    if not (is_superuser(user) or row["empresa_id"] == user["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row


def _valida_posicao(posicao):
    if posicao and posicao not in POSICOES:
        raise HTTPException(status_code=422, detail="Posição inválida")


@router.get("")
def list_usuarios(user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        if is_superuser(user):
            rows = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM usuarios WHERE empresa_id = ?", (user["empresa_id"],)
            ).fetchall()
    return [row_to_dict(conn, r) for r in rows]


@router.post("", status_code=201)
def create_usuario(usuario: UsuarioIn, user: dict = Depends(require_papel("admin"))):
    if usuario.papel not in PAPEIS:
        raise HTTPException(status_code=422, detail="Papel inválido")
    _valida_posicao(usuario.posicao)
    if not is_superuser(user):
        usuario.empresa_id = user["empresa_id"]
    criado_em = datetime.now(timezone.utc).isoformat()
    senha_hash = hash_password(usuario.senha)
    with get_connection() as conn:
        empresa_id = usuario.empresa_id
        if usuario.setor_id is not None:
            setor = _resolve_setor(conn, usuario.setor_id, user)
            empresa_id = setor["empresa_id"]
        if empresa_id is not None:
            empresa = conn.execute(
                "SELECT id FROM empresas WHERE id = ?", (empresa_id,)
            ).fetchone()
            if empresa is None:
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
        cur = conn.execute(
            "INSERT INTO usuarios (empresa_id, setor_id, posicao, nome, email, senha_hash, papel, ativo, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (empresa_id, usuario.setor_id, usuario.posicao, usuario.nome, usuario.email,
             senha_hash, usuario.papel, criado_em),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(conn, row)


@router.put("/{usuario_id}")
def update_usuario(usuario_id: int, usuario: UsuarioUpdate, user: dict = Depends(require_papel("admin"))):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if not _can_access(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        if usuario.papel is not None and usuario.papel not in PAPEIS:
            raise HTTPException(status_code=422, detail="Papel inválido")
        _valida_posicao(usuario.posicao)
        nome = usuario.nome if usuario.nome is not None else row["nome"]
        email = usuario.email if usuario.email is not None else row["email"]
        senha_hash = hash_password(usuario.senha) if usuario.senha else row["senha_hash"]
        papel = usuario.papel if usuario.papel is not None else row["papel"]
        ativo = usuario.ativo if usuario.ativo is not None else row["ativo"]
        setor_id = row["setor_id"]
        empresa_id = row["empresa_id"]
        if usuario.setor_id is not None:
            setor = _resolve_setor(conn, usuario.setor_id, user)
            setor_id = setor["id"]
            empresa_id = setor["empresa_id"]
        posicao = usuario.posicao if usuario.posicao is not None else row["posicao"]
        conn.execute(
            "UPDATE usuarios SET nome = ?, email = ?, senha_hash = ?, papel = ?, ativo = ?, "
            "setor_id = ?, posicao = ?, empresa_id = ? WHERE id = ?",
            (nome, email, senha_hash, papel, ativo, setor_id, posicao, empresa_id, usuario_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return row_to_dict(conn, row)


@router.delete("/{usuario_id}", status_code=204)
def delete_usuario(usuario_id: int, user: dict = Depends(require_papel("admin"))):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if not _can_access(user, row["empresa_id"]):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
