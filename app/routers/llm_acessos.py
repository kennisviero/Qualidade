import sqlite3
from datetime import datetime, timezone
from typing import ClassVar
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator

from app.auth import is_superuser, require_papel
from app.db import get_connection
from app.security import SafeModel

router = APIRouter(prefix='/api/configuracao/llm', tags=['configuracao'])
admin = require_papel('admin')


class AcessoIn(SafeModel):
    _sanitize_skip: ClassVar[frozenset] = frozenset({'api_key'})
    empresa_id: int | None = None
    nome: str = Field(min_length=1, max_length=120)
    provedor: str = Field(min_length=1, max_length=120)
    modelo: str = Field(min_length=1, max_length=200)
    url_base: str = Field(min_length=1, max_length=1000)
    api_key: str = Field(default='', max_length=8192, repr=False)
    ativo: bool = True

    @field_validator('nome', 'provedor', 'modelo', 'url_base')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Campo obrigatório')
        return value

    @field_validator('url_base')
    @classmethod
    def valid_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Informe uma URL HTTP/HTTPS sem credenciais, parâmetros ou fragmentos')
        return value.rstrip('/')


def scope(user, empresa_id):
    if not is_superuser(user):
        if not user['empresa_id'] or (empresa_id is not None and empresa_id != user['empresa_id']):
            raise HTTPException(403, 'Permissão insuficiente')
        return user['empresa_id']
    if empresa_id is None:
        raise HTTPException(422, 'Selecione uma empresa')
    return empresa_id


def public(row):
    result = dict(row)
    result['chave_configurada'] = bool(result.pop('api_key'))
    result['ativo'] = bool(result['ativo'])
    return result


def fetch(conn, access_id, user):
    row = conn.execute('SELECT * FROM llm_acessos WHERE id=?', (access_id,)).fetchone()
    if not row or (not is_superuser(user) and row['empresa_id'] != user['empresa_id']):
        raise HTTPException(404, 'Acesso não encontrado')
    return row


@router.get('')
def list_access(empresa_id: int | None = None, user: dict = Depends(admin)):
    eid = scope(user, empresa_id)
    with get_connection() as conn:
        return [public(r) for r in conn.execute('SELECT * FROM llm_acessos WHERE empresa_id=? ORDER BY nome,id', (eid,))]


@router.get('/{access_id}')
def get_access(access_id: int, user: dict = Depends(admin)):
    with get_connection() as conn:
        return public(fetch(conn, access_id, user))


@router.post('', status_code=201)
def create_access(body: AcessoIn, user: dict = Depends(admin)):
    eid = scope(user, body.empresa_id)
    if not body.api_key.strip():
        raise HTTPException(422, 'Informe a chave de API')
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if not conn.execute('SELECT id FROM empresas WHERE id=?', (eid,)).fetchone():
            raise HTTPException(404, 'Empresa não encontrada')
        try:
            cur = conn.execute('INSERT INTO llm_acessos (empresa_id,nome,provedor,modelo,url_base,api_key,ativo,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?)',
                (eid, body.nome, body.provedor, body.modelo, body.url_base, body.api_key, int(body.ativo), now, now))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Já existe um acesso com esse nome na empresa')
        return public(fetch(conn, cur.lastrowid, user))


@router.put('/{access_id}')
def update_access(access_id: int, body: AcessoIn, user: dict = Depends(admin)):
    with get_connection() as conn:
        row = fetch(conn, access_id, user)
        if body.empresa_id is not None and body.empresa_id != row['empresa_id']:
            raise HTTPException(422, 'A empresa do acesso não pode ser alterada')
        try:
            conn.execute('UPDATE llm_acessos SET nome=?,provedor=?,modelo=?,url_base=?,api_key=?,ativo=?,atualizado_em=? WHERE id=?',
                (body.nome, body.provedor, body.modelo, body.url_base, body.api_key if body.api_key.strip() else row['api_key'], int(body.ativo), datetime.now(timezone.utc).isoformat(), access_id))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Já existe um acesso com esse nome na empresa')
        return public(fetch(conn, access_id, user))


@router.delete('/{access_id}', status_code=204)
def delete_access(access_id: int, user: dict = Depends(admin)):
    with get_connection() as conn:
        fetch(conn, access_id, user)
        conn.execute('DELETE FROM llm_acessos WHERE id=?', (access_id,))
