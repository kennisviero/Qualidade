"""Diagramas de relações preservam os relatos e não alteram Issues ou RNCs."""
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

router = APIRouter(prefix='/api/ferramentas/relacoes', tags=['relacoes'])
DDL = """CREATE TABLE IF NOT EXISTS relacoes (
 id INTEGER PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
 titulo TEXT NOT NULL, base TEXT NOT NULL, quadro_json TEXT NOT NULL,
 revisao INTEGER NOT NULL DEFAULT 1, criado_por_id INTEGER REFERENCES usuarios(id),
 atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER IF NOT EXISTS relacoes_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM relacoes WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS relacoes_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE relacoes SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
"""


class Fator(SafeModel):
    id: int = Field(gt=0)
    nome: str = Field(min_length=1, max_length=160)
    registros: list[int] = Field(default_factory=list, max_length=2000)


class Relacao(SafeModel):
    origem: int = Field(gt=0)
    destino: int = Field(gt=0)
    tipo: Literal['hipotese','evidenciada'] = 'hipotese'
    justificativa: str = Field(min_length=1, max_length=3000)
    evidencia: str = Field(default='', max_length=3000)


class Quadro(SafeModel):
    _sanitize_skip: ClassVar[frozenset] = frozenset({'snapshot'})
    titulo: str = Field(min_length=1, max_length=160)
    snapshot: str = Field(max_length=1000000)
    assinatura: str = Field(pattern=r'^[a-f0-9]{64}$')
    fatores: list[Fator] = Field(default_factory=list, max_length=40)
    relacoes: list[Relacao] = Field(default_factory=list, max_length=200)
    revisao: int = Field(default=1, ge=1)


def prepare(body, user):
    data = verify(body.snapshot, body.assinatura)
    if not data or data.get('ferramenta') != 'relacoes':
        raise HTTPException(409, 'Recarregue os registros da análise.')
    company = scope(user, data['empresa_id'])
    if data['usuario_id'] != user['id']:
        raise HTTPException(403, 'Reabra a análise na sua sessão.')
    if not body.titulo.strip() or any(not f.nome.strip() for f in body.fatores):
        raise HTTPException(422, 'Informe o título e os nomes dos fatores.')
    records = data['resultados']['registros']
    allowed = {r['id'] for r in records}
    ids = [f.id for f in body.fatores]
    names = [f.nome.strip().casefold() for f in body.fatores]
    if len(ids)!=len(set(ids)) or len(names)!=len(set(names)):
        raise HTTPException(422, 'Cada fator deve ter identificação e nome únicos.')
    if any(not set(f.registros)<=allowed or len(f.registros)!=len(set(f.registros)) for f in body.fatores):
        raise HTTPException(422, 'Vincule somente registros da base carregada, sem duplicatas no fator.')
    edges=set()
    for edge in body.relacoes:
        pair=(edge.origem,edge.destino)
        if edge.origem not in ids or edge.destino not in ids or edge.origem==edge.destino:
            raise HTTPException(422, 'Cada seta deve conectar dois fatores diferentes do quadro.')
        if pair in edges:
            raise HTTPException(422, 'Já existe uma relação nessa direção entre os fatores.')
        edges.add(pair)
        if not edge.justificativa.strip():
            raise HTTPException(422, 'Justifique cada relação de influência.')
        if edge.tipo=='evidenciada' and not edge.evidencia.strip():
            raise HTTPException(422, 'Descreva a evidência para uma relação sustentada por evidência.')
    factors=[dict(id=f.id,nome=f.nome.strip(),registros=f.registros,
                  entradas=sum(e.destino==f.id for e in body.relacoes),
                  saidas=sum(e.origem==f.id for e in body.relacoes)) for f in body.fatores]
    result=dict(titulo=body.titulo.strip(),base=data['resultados']['base'],registros=records,
                fatores=factors,relacoes=[e.model_dump() for e in body.relacoes],parametros=data['parametros'],
                aviso='Setas expressam influências propostas pelo usuário. Evidências declaradas precisam de avaliação; contagens não comprovam causa raiz nem prioridade.')
    return company,result


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
    result = dict(base=base, registros=records, fatores=[], relacoes=[], sem_data=selected['sem_data'])
    return {**result, 'opcoes':selected['opcoes'], 'consulta_ia':context('relacoes',company,user,filters,result)}


@router.post('/preparar')
def preview(body: Quadro, user: dict=Depends(get_current_user)):
    company, result = prepare(body,user)
    return {**result, 'consulta_ia':context('relacoes',company,user,result['parametros'],result)}


@router.get('/diagramas')
def listing(empresa_id: int|None=None, base: Literal['issues','rncs']='issues', user: dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,titulo,base,revisao,atualizado_em FROM relacoes WHERE empresa_id=? AND base=? ORDER BY id DESC',(company,base))]


@router.get('/diagramas/{diagram_id}')
def detail(diagram_id: int, user: dict=Depends(get_current_user)):
    with get_connection() as conn:
        row=conn.execute('SELECT * FROM relacoes WHERE id=?',(diagram_id,)).fetchone()
    if not row: raise HTTPException(404,'Diagrama não encontrado.')
    company=scope(user,row['empresa_id'])
    result=json.loads(row['quadro_json'])
    return {**result,'id':row['id'],'revisao':row['revisao'],
            'consulta_ia':context('relacoes',company,user,result['parametros'],result)}


@router.post('/diagramas')
def create(body: Quadro, user: dict=Depends(require_papel('admin','editor'))):
    company,result=prepare(body,user)
    with get_connection() as conn:
        cursor=conn.execute('INSERT INTO relacoes (empresa_id,titulo,base,quadro_json,criado_por_id) VALUES (?,?,?,?,?)',
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
        cursor=conn.execute('UPDATE relacoes SET titulo=?,quadro_json=?,revisao=revisao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND revisao=?',
            (result['titulo'],json.dumps(result,ensure_ascii=False,default=str),diagram_id,company,body.revisao))
        if not cursor.rowcount: raise HTTPException(409,'O diagrama foi alterado. Reabra antes de salvar.')
        conn.commit()
    return detail(diagram_id,user)
