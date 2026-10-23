"""Matriz problema/fator × ação, separada das RNCs e dos planos originais."""
import json
from datetime import date
from typing import ClassVar, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field
from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.security import SafeModel
from app.routers.llm_acessos import scope
from app.routers.pareto import analysis
from app.services.ferramentas_ia import context, verify

router=APIRouter(prefix='/api/ferramentas/matriz',tags=['matriz'])
DDL="""CREATE TABLE IF NOT EXISTS matrizes (
 id INTEGER PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
 titulo TEXT NOT NULL, contexto TEXT NOT NULL, quadro_json TEXT NOT NULL,
 revisao INTEGER NOT NULL DEFAULT 1, criado_por_id INTEGER REFERENCES usuarios(id),
 atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER IF NOT EXISTS matrizes_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM matrizes WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS matrizes_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE matrizes SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
"""

class Linha(SafeModel):
    model_config=ConfigDict(extra='forbid')
    id:int=Field(gt=0)
    nome:str=Field(min_length=1,max_length=2000)
    rnc_ids:list[int]=Field(min_length=1,max_length=20)
    situacao:Literal['problema','hipotese','fator_evidenciado']='problema'
    evidencia:str=Field(default='',max_length=3000)

class Celula(SafeModel):
    model_config=ConfigDict(extra='forbid')
    linha_id:int=Field(gt=0)
    acao_id:int=Field(gt=0)
    intensidade:Literal['nao_avaliada','nenhuma','fraca','media','forte']='nao_avaliada'
    justificativa:str=Field(default='',max_length=3000)
    evidencia:str=Field(default='',max_length=3000)

class Quadro(SafeModel):
    model_config=ConfigDict(extra='forbid')
    _sanitize_skip:ClassVar[frozenset]=frozenset({'snapshot'})
    titulo:str=Field(min_length=1,max_length=160)
    snapshot:str=Field(min_length=1,max_length=1000000)
    assinatura:str=Field(pattern=r'^[a-f0-9]{64}$')
    linhas:list[Linha]=Field(min_length=1,max_length=40)
    colunas:list[int]=Field(default_factory=list,max_length=60)
    celulas:list[Celula]=Field(default_factory=list,max_length=2400)
    revisao:int=Field(default=1,ge=1)

def diagnostics(lines,columns,cells,actions):
    assessed=[c for c in cells if c['intensidade']!='nao_avaliada']
    positive=[c for c in assessed if c['intensidade'] in ('fraca','media','forte')]
    covered={c['linha_id'] for c in positive};linked={c['acao_id'] for c in positive}
    pending=[l['id'] for l in lines if sum(c['linha_id']==l['id'] for c in assessed)<len(columns)]
    return dict(cruzamentos=len(lines)*len(columns),avaliados=len(assessed),
        nao_avaliados=len(lines)*len(columns)-len(assessed),
        linhas_sem_relacao_indicada=[l['id'] for l in lines if l['id'] not in covered],
        linhas_com_avaliacao_pendente=pending,
        linhas_sem_cobertura_apos_avaliacao=[l['id'] for l in lines if columns and l['id'] not in covered and l['id'] not in pending],
        acoes_sem_relacao_indicada=[a for a in columns if a not in linked],
        acoes_fora_matriz=[a['id'] for a in actions if a['id'] not in columns])

@router.get('/fontes')
def sources(empresa_id:int|None=None,data_referencia:Literal['detectado_em','emitida_em']='detectado_em',
    inicio:date|None=None,fim:date|None=None,simulados:Literal['todos','somente','excluir']='todos',
    categoria:str='',impacto:str='',ambiente:str='',local:str='',status:str='',pessoa:str='',envolvidos:str='',classificacao:str='',
    user:dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    filters=dict(empresa_id=company,data_referencia=data_referencia,inicio=inicio,fim=fim,simulados=simulados,
        categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,envolvidos=envolvidos,classificacao=classificacao)
    selected=analysis(base='rncs',**filters,user=user)
    return dict(registros=selected['registros'],opcoes=selected['opcoes'],sem_data=selected['sem_data'])

@router.get('')
def generate(empresa_id:int|None=None,contexto:Literal['rnc','geral']='rnc',rnc_ids:str='',user:dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    try:ids=[int(x) for x in rnc_ids.split(',') if x.strip()]
    except ValueError:raise HTTPException(422,'Selecione RNCs válidas.') from None
    if not ids or len(ids)>20 or len(set(ids))!=len(ids) or any(i<=0 for i in ids):
        raise HTTPException(422,'Selecione de 1 a 20 RNCs sem repetição.')
    if contexto=='rnc' and len(ids)!=1 or contexto=='geral' and len(ids)<2:
        raise HTTPException(422,'Uma RNC exige um registro; Geral exige pelo menos duas RNCs.')
    records=[];actions=[];lines=[]
    with get_connection() as conn:
        for rid in ids:
            row=conn.execute('SELECT * FROM rncs WHERE id=? AND empresa_id=?',(rid,company)).fetchone()
            if not row:raise HTTPException(404,'RNC não encontrada na empresa selecionada.')
            facts=json.loads(row['fatos_snapshot_json'] or '{}')
            observation=conn.execute('SELECT * FROM rnc_observacoes WHERE rnc_id=?',(rid,)).fetchone()
            records.append(dict(id=rid,codigo=row['codigo'],issue_id=row['issue_id'],issue_codigo=facts.get('codigo',''),
                status=row['status'],resumo=row['resumo'],fatos=facts,observacao=dict(observation) if observation else {},
                investigacao=json.loads(row['investigacao_json'] or '{}')))
            description=facts.get('comportamento_observado') or row['codigo']
            if len(description)>2000:
                description=description[:1900]+'… (relato completo em Registros de origem)'
            lines.append(dict(id=rid,nome=description,rnc_ids=[rid],situacao='problema',evidencia=''))
            for action in conn.execute('SELECT * FROM acoes WHERE rnc_id=? AND issue_id=? ORDER BY ordem,id',(rid,row['issue_id'])):
                item=dict(action);item['rnc_codigo']=row['codigo'];actions.append(item)
    if len(actions)>60:raise HTTPException(422,'A seleção tem mais de 60 ações. Reduza a quantidade de RNCs.')
    columns=[a['id'] for a in actions]
    params=dict(empresa_id=company,contexto=contexto,rnc_ids=ids)
    result=dict(titulo='Matriz de uma RNC' if contexto=='rnc' else 'Matriz geral de RNCs',contexto=contexto,
        registros=records,acoes=actions,linhas=lines,colunas=columns,celulas=[],parametros=params,
        resumo=diagnostics(lines,columns,[],actions))
    return {**result,'consulta_ia':context('matriz',company,user,params,result)}

def prepare(body,user):
    data=verify(body.snapshot,body.assinatura)
    if not data or data.get('ferramenta')!='matriz':raise HTTPException(409,'Recarregue ou reabra a matriz.')
    company=scope(user,data['empresa_id'])
    if data['usuario_id']!=user['id']:raise HTTPException(403,'Reabra a matriz na sua sessão.')
    source=data['resultados'];allowed={r['id'] for r in source['registros']};actions={a['id'] for a in source['acoes']}
    if not body.titulo.strip():raise HTTPException(422,'Informe o título da análise.')
    lines=[l.model_dump() for l in body.linhas];line_ids={l['id'] for l in lines}
    if len(line_ids)!=len(lines):raise HTTPException(422,'Identificadores de linhas duplicados.')
    for line in lines:
        line['nome']=line['nome'].strip()
        if not line['nome'] or not set(line['rnc_ids'])<=allowed or len(set(line['rnc_ids']))!=len(line['rnc_ids']):
            raise HTTPException(422,'Cada linha precisa de descrição e RNCs de origem válidas, sem repetição.')
        if line['situacao']=='fator_evidenciado' and not line['evidencia'].strip():
            raise HTTPException(422,'Descreva a evidência do fator indicado como evidenciado.')
    if len(set(body.colunas))!=len(body.colunas) or not set(body.colunas)<=actions:
        raise HTTPException(422,'Selecione ações do plano carregado, sem repetição.')
    pairs=set();cells=[]
    for cell in body.celulas:
        pair=(cell.linha_id,cell.acao_id)
        if cell.linha_id not in line_ids or cell.acao_id not in body.colunas or pair in pairs:
            raise HTTPException(422,'Cruzamento inválido ou duplicado.')
        pairs.add(pair)
        if cell.intensidade!='nao_avaliada' and not cell.justificativa.strip():
            raise HTTPException(422,'Justifique cada cruzamento avaliado, inclusive quando não houver relação.')
        cells.append(cell.model_dump())
    result=dict(titulo=body.titulo.strip(),contexto=source['contexto'],registros=source['registros'],acoes=source['acoes'],
        linhas=lines,colunas=body.colunas,celulas=cells,parametros=data['parametros'],
        resumo=diagnostics(lines,body.colunas,cells,source['acoes']))
    return company,result

@router.post('/preparar')
def preview(body:Quadro,user:dict=Depends(get_current_user)):
    company,result=prepare(body,user)
    return {**result,'consulta_ia':context('matriz',company,user,result['parametros'],result)}

@router.get('/diagramas')
def listing(empresa_id:int|None=None,contexto:Literal['rnc','geral']='rnc',user:dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,titulo,contexto,revisao,atualizado_em FROM matrizes WHERE empresa_id=? AND contexto=? ORDER BY id DESC',(company,contexto))]

@router.get('/diagramas/{diagram_id}')
def detail(diagram_id:int,user:dict=Depends(get_current_user)):
    with get_connection() as conn:row=conn.execute('SELECT * FROM matrizes WHERE id=?',(diagram_id,)).fetchone()
    if not row:raise HTTPException(404,'Matriz não encontrada.')
    company=scope(user,row['empresa_id']);result=json.loads(row['quadro_json'])
    return {**result,'id':row['id'],'revisao':row['revisao'],'consulta_ia':context('matriz',company,user,result['parametros'],result)}

@router.post('/diagramas')
def create(body:Quadro,user:dict=Depends(require_papel('admin','editor'))):
    company,result=prepare(body,user)
    with get_connection() as conn:
        cursor=conn.execute('INSERT INTO matrizes (empresa_id,titulo,contexto,quadro_json,criado_por_id) VALUES (?,?,?,?,?)',
            (company,result['titulo'],result['contexto'],json.dumps(result,ensure_ascii=False,default=str),user['id']))
        diagram_id=cursor.lastrowid;conn.commit()
    return detail(diagram_id,user)

@router.put('/diagramas/{diagram_id}')
def update(diagram_id:int,body:Quadro,user:dict=Depends(require_papel('admin','editor'))):
    existing=detail(diagram_id,user);company,result=prepare(body,user)
    if company!=json.loads(existing['consulta_ia']['snapshot'])['empresa_id'] or result['contexto']!=existing['contexto'] or result['parametros']['rnc_ids']!=existing['parametros']['rnc_ids']:
        raise HTTPException(422,'Preserve a empresa, o contexto e a seleção de RNCs da matriz salva.')
    with get_connection() as conn:
        cursor=conn.execute('UPDATE matrizes SET titulo=?,quadro_json=?,revisao=revisao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND revisao=?',
            (result['titulo'],json.dumps(result,ensure_ascii=False,default=str),diagram_id,company,body.revisao))
        if not cursor.rowcount:raise HTTPException(409,'Matriz alterada por outra gravação. Reabra antes de salvar.')
        conn.commit()
    return detail(diagram_id,user)
