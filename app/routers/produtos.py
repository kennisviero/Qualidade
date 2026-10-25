"""Hierarquia de produto (Família → Grupo → Produto), por empresa.

Master data aditivo: não altera módulos existentes. Requisitos ligam-se a qualquer
nível reusando `requisito_vinculos` (alvo_tipo familia/grupo/produto).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field

from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.routers.llm_acessos import scope
from app.security import SafeModel

router = APIRouter(prefix="/api/produtos", tags=["produtos"])
editor_dep = require_papel("admin", "editor")

DDL = """CREATE TABLE IF NOT EXISTS produto_familias (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 nome TEXT NOT NULL,
 descricao TEXT DEFAULT '',
 ordem INTEGER DEFAULT 0,
 criado_em TEXT NOT NULL,
 UNIQUE(empresa_id, nome)
);
CREATE TABLE IF NOT EXISTS produto_grupos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 familia_id INTEGER NOT NULL REFERENCES produto_familias(id) ON DELETE CASCADE,
 nome TEXT NOT NULL,
 descricao TEXT DEFAULT '',
 ordem INTEGER DEFAULT 0,
 criado_em TEXT NOT NULL,
 UNIQUE(familia_id, nome)
);
CREATE TABLE IF NOT EXISTS produtos (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 grupo_id INTEGER NOT NULL REFERENCES produto_grupos(id) ON DELETE CASCADE,
 codigo TEXT DEFAULT '',
 nome TEXT NOT NULL,
 descricao TEXT DEFAULT '',
 ordem INTEGER DEFAULT 0,
 criado_em TEXT NOT NULL,
 UNIQUE(grupo_id, nome)
);
CREATE INDEX IF NOT EXISTS idx_prod_grupos_familia ON produto_grupos(familia_id);
CREATE INDEX IF NOT EXISTS idx_produtos_grupo ON produtos(grupo_id);
CREATE TRIGGER IF NOT EXISTS prod_familias_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM produto_familias WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS prod_grupos_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM produto_grupos WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS produtos_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM produtos WHERE empresa_id=OLD.id; END;
"""


def now():
    return datetime.now(timezone.utc).isoformat()


class FamiliaIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(default="", max_length=2000)
    ordem: int = 0


class GrupoIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    familia_id: int
    nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(default="", max_length=2000)
    ordem: int = 0


class ProdutoIn(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    grupo_id: int
    codigo: str = Field(default="", max_length=60)
    nome: str = Field(min_length=1, max_length=200)
    descricao: str = Field(default="", max_length=2000)
    ordem: int = 0


class NomeUpdate(SafeModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int | None = None
    nome: str | None = Field(default=None, max_length=200)
    codigo: str | None = Field(default=None, max_length=60)
    descricao: str | None = Field(default=None, max_length=2000)
    ordem: int | None = None


def _familia_da_empresa(conn, familia_id, company):
    r = conn.execute("SELECT id FROM produto_familias WHERE id=? AND empresa_id=?", (familia_id, company)).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Família não encontrada")


def _grupo_da_empresa(conn, grupo_id, company):
    r = conn.execute("SELECT id FROM produto_grupos WHERE id=? AND empresa_id=?", (grupo_id, company)).fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")


# --- Árvore completa ---
@router.get("/arvore")
def arvore(empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        fam = [dict(r) for r in conn.execute(
            "SELECT * FROM produto_familias WHERE empresa_id=? ORDER BY ordem,id", (company,)).fetchall()]
        grp = [dict(r) for r in conn.execute(
            "SELECT * FROM produto_grupos WHERE empresa_id=? ORDER BY ordem,id", (company,)).fetchall()]
        prod = [dict(r) for r in conn.execute(
            "SELECT * FROM produtos WHERE empresa_id=? ORDER BY ordem,id", (company,)).fetchall()]
        for g in grp:
            g["produtos"] = [p for p in prod if p["grupo_id"] == g["id"]]
        for f in fam:
            f["grupos"] = [g for g in grp if g["familia_id"] == f["id"]]
    return {"familias": fam}


# --- Famílias ---
@router.get("/familias")
def list_familias(empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM produto_familias WHERE empresa_id=? ORDER BY ordem,id", (company,)).fetchall()]


@router.post("/familias", status_code=201)
def create_familia(body: FamiliaIn, user: dict = Depends(editor_dep)):
    import sqlite3
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO produto_familias (empresa_id,nome,descricao,ordem,criado_em) VALUES (?,?,?,?,?)",
                (company, body.nome, body.descricao, body.ordem, now()))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Família já existe")
        conn.commit()
        return dict(conn.execute("SELECT * FROM produto_familias WHERE id=?", (cur.lastrowid,)).fetchone())


@router.put("/familias/{familia_id}")
def update_familia(familia_id: int, body: NomeUpdate, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM produto_familias WHERE id=? AND empresa_id=?", (familia_id, company)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Família não encontrada")
        nome = body.nome if body.nome is not None else row["nome"]
        descricao = body.descricao if body.descricao is not None else row["descricao"]
        ordem = body.ordem if body.ordem is not None else row["ordem"]
        conn.execute("UPDATE produto_familias SET nome=?,descricao=?,ordem=? WHERE id=?", (nome, descricao, ordem, familia_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM produto_familias WHERE id=?", (familia_id,)).fetchone())


@router.delete("/familias/{familia_id}", status_code=204)
def delete_familia(familia_id: int, empresa_id: int | None = None, user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        _familia_da_empresa(conn, familia_id, company)
        conn.execute("DELETE FROM produto_familias WHERE id=?", (familia_id,))
        conn.commit()


# --- Grupos ---
@router.get("/grupos")
def list_grupos(familia_id: int | None = None, empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    sql = "SELECT * FROM produto_grupos WHERE empresa_id=?"
    params = [company]
    if familia_id is not None:
        sql += " AND familia_id=?"
        params.append(familia_id)
    sql += " ORDER BY ordem,id"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


@router.post("/grupos", status_code=201)
def create_grupo(body: GrupoIn, user: dict = Depends(editor_dep)):
    import sqlite3
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        _familia_da_empresa(conn, body.familia_id, company)
        try:
            cur = conn.execute(
                "INSERT INTO produto_grupos (empresa_id,familia_id,nome,descricao,ordem,criado_em) VALUES (?,?,?,?,?,?)",
                (company, body.familia_id, body.nome, body.descricao, body.ordem, now()))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Grupo já existe nesta família")
        conn.commit()
        return dict(conn.execute("SELECT * FROM produto_grupos WHERE id=?", (cur.lastrowid,)).fetchone())


@router.put("/grupos/{grupo_id}")
def update_grupo(grupo_id: int, body: NomeUpdate, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM produto_grupos WHERE id=? AND empresa_id=?", (grupo_id, company)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Grupo não encontrado")
        nome = body.nome if body.nome is not None else row["nome"]
        descricao = body.descricao if body.descricao is not None else row["descricao"]
        ordem = body.ordem if body.ordem is not None else row["ordem"]
        conn.execute("UPDATE produto_grupos SET nome=?,descricao=?,ordem=? WHERE id=?", (nome, descricao, ordem, grupo_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM produto_grupos WHERE id=?", (grupo_id,)).fetchone())


@router.delete("/grupos/{grupo_id}", status_code=204)
def delete_grupo(grupo_id: int, empresa_id: int | None = None, user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        _grupo_da_empresa(conn, grupo_id, company)
        conn.execute("DELETE FROM produto_grupos WHERE id=?", (grupo_id,))
        conn.commit()


# --- Produtos ---
@router.get("")
def list_produtos(grupo_id: int | None = None, empresa_id: int | None = None, user: dict = Depends(get_current_user)):
    company = scope(user, empresa_id)
    sql = "SELECT * FROM produtos WHERE empresa_id=?"
    params = [company]
    if grupo_id is not None:
        sql += " AND grupo_id=?"
        params.append(grupo_id)
    sql += " ORDER BY ordem,id"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


@router.post("", status_code=201)
def create_produto(body: ProdutoIn, user: dict = Depends(editor_dep)):
    import sqlite3
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        _grupo_da_empresa(conn, body.grupo_id, company)
        try:
            cur = conn.execute(
                "INSERT INTO produtos (empresa_id,grupo_id,codigo,nome,descricao,ordem,criado_em) VALUES (?,?,?,?,?,?,?)",
                (company, body.grupo_id, body.codigo, body.nome, body.descricao, body.ordem, now()))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Produto já existe neste grupo")
        conn.commit()
        return dict(conn.execute("SELECT * FROM produtos WHERE id=?", (cur.lastrowid,)).fetchone())


@router.put("/{produto_id}")
def update_produto(produto_id: int, body: NomeUpdate, user: dict = Depends(editor_dep)):
    company = scope(user, body.empresa_id)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM produtos WHERE id=? AND empresa_id=?", (produto_id, company)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        nome = body.nome if body.nome is not None else row["nome"]
        codigo = body.codigo if body.codigo is not None else row["codigo"]
        descricao = body.descricao if body.descricao is not None else row["descricao"]
        ordem = body.ordem if body.ordem is not None else row["ordem"]
        conn.execute("UPDATE produtos SET codigo=?,nome=?,descricao=?,ordem=? WHERE id=?", (codigo, nome, descricao, ordem, produto_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM produtos WHERE id=?", (produto_id,)).fetchone())


@router.delete("/{produto_id}", status_code=204)
def delete_produto(produto_id: int, empresa_id: int | None = None, user: dict = Depends(editor_dep)):
    company = scope(user, empresa_id)
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM produtos WHERE id=? AND empresa_id=?", (produto_id, company)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        conn.execute("DELETE FROM produtos WHERE id=?", (produto_id,))
        conn.commit()
