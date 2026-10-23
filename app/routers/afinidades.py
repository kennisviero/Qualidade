"""Quadros de afinidades preservam os relatos e não alteram Issues ou RNCs."""
import json
from datetime import date
from typing import ClassVar, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.security import SafeModel
from app.routers.pareto import analysis
from app.routers.llm_acessos import scope
from app.services.ferramentas_ia import context, verify

router = APIRouter(prefix='/api/ferramentas/afinidades', tags=['afinidades'])
DDL = """CREATE TABLE IF NOT EXISTS afinidades (
 id INTEGER PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
 titulo TEXT NOT NULL, base TEXT NOT NULL, quadro_json TEXT NOT NULL,
 revisao INTEGER NOT NULL DEFAULT 1, criado_por_id INTEGER REFERENCES usuarios(id),
 atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER IF NOT EXISTS afinidades_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM afinidades WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS afinidades_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE afinidades SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
"""


class Grupo(SafeModel):
    nome: str = Field(min_length=1, max_length=120)
    registros: list[int] = Field(default_factory=list, max_length=2000)


class Quadro(SafeModel):
    _sanitize_skip: ClassVar[frozenset] = frozenset({'snapshot'})
    titulo: str = Field(min_length=1, max_length=160)
    snapshot: str = Field(max_length=1000000)
    assinatura: str = Field(pattern=r'^[a-f0-9]{64}$')
    grupos: list[Grupo] = Field(default_factory=list, max_length=100)
    revisao: int = Field(default=1, ge=1)


def prepare(body, user):
    data = verify(body.snapshot, body.assinatura)
    if not data or data.get('ferramenta') != 'afinidades':
        raise HTTPException(409, 'Recarregue os cartões da análise.')
    company = scope(user, data['empresa_id'])
    if data['usuario_id'] != user['id']:
        raise HTTPException(403, 'Reabra a análise na sua sessão.')
    if not body.titulo.strip() or any(not g.nome.strip() for g in body.grupos):
        raise HTTPException(422, 'Informe o título e os nomes dos grupos.')
    records = data['resultados']['registros']
    allowed = {r['id'] for r in records}
    assigned = [rid for g in body.grupos for rid in g.registros]
    if len(assigned) != len(set(assigned)) or not set(assigned) <= allowed:
        raise HTTPException(422, 'Cada cartão deve pertencer a um único grupo e à base carregada.')
    names = [g.nome.strip().casefold() for g in body.grupos]
    if len(names) != len(set(names)):
        raise HTTPException(422, 'Use nomes diferentes para os grupos.')
    result = dict(titulo=body.titulo.strip(), base=data['resultados']['base'], registros=records,
                  grupos=[g.model_dump() for g in body.grupos],
                  sem_grupo=sorted(allowed-set(assigned)), parametros=data['parametros'])
    return company, result


@router.get('')
def candidates(base: Literal['issues','rncs']='issues', empresa_id: int|None=None,
               data_referencia: Literal['detectado_em','criado_em','emitida_em']='detectado_em',
               inicio: date|None=None, fim: date|None=None,
               simulados: Literal['todos','somente','excluir']='todos',
               categoria: str='', impacto: str='', ambiente: str='', local: str='',
               status: str='', pessoa: str='', envolvidos: str='', classificacao: str='',
               user: dict=Depends(get_current_user)):
    company = scope(user, empresa_id)
    filters = dict(base=base, empresa_id=company, data_referencia=data_referencia, inicio=inicio, fim=fim,
                   simulados=simulados, categoria=categoria, impacto=impacto, ambiente=ambiente,
                   local=local, status=status, pessoa=pessoa, envolvidos=envolvidos, classificacao=classificacao)
    selected = analysis(**filters, user=user)
    records = selected['registros']
    # Observações ampliam o relato da RNC sem substituir os fatos da emissão.
    with get_connection() as conn:
        for r in records:
            if base == 'rncs':
                source = conn.execute('SELECT fatos_snapshot_json FROM rncs WHERE id=?', (r['id'],)).fetchone()
                facts = json.loads(source['fatos_snapshot_json'] or '{}')
                row = conn.execute('SELECT * FROM rnc_observacoes WHERE rnc_id=?', (r['id'],)).fetchone()
                r['observacoes'] = dict(row) if row else {}
            else:
                facts = dict(conn.execute('SELECT * FROM issues WHERE id=?', (r['id'],)).fetchone())
            r['esperado'] = facts.get('comportamento_esperado') or ''
            r['evidencias'] = facts.get('evidencias_objetivas') or ''
    result = dict(base=base, registros=records, grupos=[], sem_data=selected['sem_data'])
    return {**result, 'opcoes':selected['opcoes'], 'consulta_ia':context('afinidades',company,user,filters,result)}


@router.post('/preparar')
def preview(body: Quadro, user: dict=Depends(get_current_user)):
    company, result = prepare(body,user)
    return {**result, 'consulta_ia':context('afinidades',company,user,result['parametros'],result)}


@router.get('/diagramas')
def listing(empresa_id: int|None=None, base: Literal['issues','rncs']='issues', user: dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,titulo,base,revisao,atualizado_em FROM afinidades WHERE empresa_id=? AND base=? ORDER BY id DESC',(company,base))]


@router.get('/diagramas/{diagram_id}')
def detail(diagram_id: int, user: dict=Depends(get_current_user)):
    with get_connection() as conn:
        row=conn.execute('SELECT * FROM afinidades WHERE id=?',(diagram_id,)).fetchone()
    if not row: raise HTTPException(404,'Diagrama não encontrado.')
    company=scope(user,row['empresa_id'])
    result=json.loads(row['quadro_json'])
    return {**result,'id':row['id'],'revisao':row['revisao'],
            'consulta_ia':context('afinidades',company,user,result['parametros'],result)}


@router.post('/diagramas')
def create(body: Quadro, user: dict=Depends(require_papel('admin','editor'))):
    company,result=prepare(body,user)
    with get_connection() as conn:
        cursor=conn.execute('INSERT INTO afinidades (empresa_id,titulo,base,quadro_json,criado_por_id) VALUES (?,?,?,?,?)',
            (company,result['titulo'],result['base'],json.dumps(result,ensure_ascii=False,default=str),user['id']))
        diagram_id=cursor.lastrowid
        conn.commit()
    return detail(diagram_id,user)


@router.put('/diagramas/{diagram_id}')
def update(diagram_id: int, body: Quadro, user: dict=Depends(require_papel('admin','editor'))):
    existing=detail(diagram_id,user)
    company,result=prepare(body,user)
    if result['base']!=existing['base'] or company!=json.loads(existing['consulta_ia']['snapshot'])['empresa_id']:
        raise HTTPException(422,'A base e a empresa do diagrama devem ser preservadas.')
    with get_connection() as conn:
        cursor=conn.execute('UPDATE afinidades SET titulo=?,quadro_json=?,revisao=revisao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND revisao=?',
            (result['titulo'],json.dumps(result,ensure_ascii=False,default=str),diagram_id,company,body.revisao))
        if not cursor.rowcount: raise HTTPException(409,'O diagrama foi alterado. Reabra antes de salvar.')
        conn.commit()
    return detail(diagram_id,user)
