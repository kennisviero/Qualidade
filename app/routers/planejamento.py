"""PDPC e rede de atividades: fotografias de planejamento sem alterar os planos."""
import json
from math import isclose
from typing import ClassVar, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field
from app.auth import get_current_user, require_papel
from app.db import get_connection
from app.security import SafeModel
from app.routers.llm_acessos import scope
from app.routers.matriz import sources, generate as source_matrix
from app.services.ferramentas_ia import context, verify

TOOLS={'pdpc':('pdpc_diagramas','Processo Decisório — PDPC'),'setas':('setas_diagramas','Diagrama de Setas')}
DDL='\n'.join(f"""CREATE TABLE IF NOT EXISTS {table} (
 id INTEGER PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
 titulo TEXT NOT NULL, contexto TEXT NOT NULL, quadro_json TEXT NOT NULL,
 revisao INTEGER NOT NULL DEFAULT 1, criado_por_id INTEGER REFERENCES usuarios(id),
 atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER IF NOT EXISTS {table}_empresa_delete BEFORE DELETE ON empresas
BEGIN DELETE FROM {table} WHERE empresa_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS {table}_usuario_delete BEFORE DELETE ON usuarios
BEGIN UPDATE {table} SET criado_por_id=NULL WHERE criado_por_id=OLD.id; END;
""" for table,_ in TOOLS.values())

class StrictModel(SafeModel):
    model_config=ConfigDict(extra='forbid')

class Atividade(StrictModel):
    acao_id:int=Field(gt=0,strict=True)
    duracao_horas:float|None=Field(default=None,ge=0,le=1000000,allow_inf_nan=False)

class Alternativa(StrictModel):
    id:int=Field(gt=0,strict=True)
    descricao:str=Field(min_length=1,max_length=2000)
    decisao:Literal['pendente','viavel','inviavel']='pendente'
    justificativa:str=Field(default='',max_length=3000)

class Risco(StrictModel):
    id:int=Field(gt=0,strict=True)
    acao_id:int=Field(gt=0,strict=True)
    descricao:str=Field(min_length=1,max_length=2000)
    consequencia:str=Field(default='',max_length=2000)
    contramedidas:list[Alternativa]=Field(default_factory=list,max_length=5)

class Dependencia(StrictModel):
    de:int=Field(gt=0,strict=True)
    para:int=Field(gt=0,strict=True)
    justificativa:str=Field(min_length=1,max_length=3000)

class Planejamento(StrictModel):
    _sanitize_skip:ClassVar[frozenset]=frozenset({'snapshot'})
    titulo:str=Field(min_length=1,max_length=160)
    objetivo:str=Field(min_length=1,max_length=2000)
    snapshot:str=Field(min_length=1,max_length=1000000)
    assinatura:str=Field(pattern=r'^[a-f0-9]{64}$')
    atividades:list[Atividade]=Field(default_factory=list,max_length=60)
    riscos:list[Risco]=Field(default_factory=list,max_length=60)
    dependencias:list[Dependencia]=Field(default_factory=list,max_length=1800)
    revisao:int=Field(default=1,ge=1)

def pdpc_summary(activities,risks):
    alternatives=[c for r in risks for c in r['contramedidas']]
    covered={r['acao_id'] for r in risks}
    return dict(atividades=len(activities),riscos=len(risks),contramedidas=len(alternatives),
        acoes_sem_riscos_avaliados=[a['acao_id'] for a in activities if a['acao_id'] not in covered],
        riscos_sem_contramedida=[r['id'] for r in risks if not r['contramedidas']],
        riscos_sem_alternativa_viavel=[r['id'] for r in risks if not any(c['decisao']=='viavel' for c in r['contramedidas'])],
        alternativas_pendentes=sum(c['decisao']=='pendente' for c in alternatives),
        alternativas_viaveis=sum(c['decisao']=='viavel' for c in alternatives),
        alternativas_inviaveis=sum(c['decisao']=='inviavel' for c in alternatives))

def network(activities,edges):
    """CPM início/fim relativo em horas; vínculos término→início sem defasagem."""
    ids=[a['acao_id'] for a in activities];nodes=set(ids)
    predecessors={i:[] for i in ids};successors={i:[] for i in ids};seen=set()
    for edge in edges:
        pair=edge['de'],edge['para']
        if pair in seen or pair[0]==pair[1] or not set(pair)<=nodes:
            raise HTTPException(422,'Dependência duplicada, autorreferente ou fora das atividades selecionadas.')
        if not edge['justificativa'].strip():raise HTTPException(422,'Justifique cada dependência.')
        seen.add(pair);predecessors[pair[1]].append(pair[0]);successors[pair[0]].append(pair[1])
    degree={i:len(predecessors[i]) for i in ids};queue=sorted(i for i in ids if not degree[i]);order=[];levels={i:0 for i in ids}
    while queue:
        current=queue.pop(0);order.append(current)
        for following in successors[current]:
            levels[following]=max(levels[following],levels[current]+1);degree[following]-=1
            if not degree[following]:queue.append(following)
    if len(order)!=len(ids):raise HTTPException(422,'As dependências formam um ciclo. Remova o ciclo antes de calcular ou salvar.')
    missing=[a['acao_id'] for a in activities if a['duracao_horas'] is None]
    result=dict(atividades=len(ids),dependencias=len(edges),ordem=order,niveis=levels,
        duracoes_ausentes=missing,completo=bool(ids) and not missing,duracao_total_horas=None,
        cronograma=[],atividades_criticas=[],dependencias_criticas=[])
    if not result['completo']:return result
    durations={a['acao_id']:a['duracao_horas'] for a in activities};start={};end={}
    for i in order:
        start[i]=max((end[p] for p in predecessors[i]),default=0);end[i]=start[i]+durations[i]
    total=max(end.values());late_start={};late_end={}
    for i in reversed(order):
        late_end[i]=min((late_start[s] for s in successors[i]),default=total);late_start[i]=late_end[i]-durations[i]
    critical=[i for i in order if isclose(late_start[i],start[i],rel_tol=0,abs_tol=1e-7)]
    result.update(duracao_total_horas=round(total,6),atividades_criticas=critical,
        dependencias_criticas=[dict(de=a,para=b) for a,b in seen if a in critical and b in critical and isclose(end[a],start[b],rel_tol=0,abs_tol=1e-7)],
        cronograma=[dict(acao_id=i,duracao_horas=durations[i],inicio_cedo=round(start[i],6),fim_cedo=round(end[i],6),
            inicio_tarde=round(late_start[i],6),fim_tarde=round(late_end[i],6),folga_horas=round(max(0,late_start[i]-start[i]),6),critica=i in critical) for i in order])
    return result

def prepare(tool,body,user):
    data=verify(body.snapshot,body.assinatura)
    if not data or data.get('ferramenta')!=tool:raise HTTPException(409,'Gere ou reabra o diagrama desta ferramenta.')
    company=scope(user,data['empresa_id'])
    if data['usuario_id']!=user['id']:raise HTTPException(403,'Reabra o diagrama na sua própria sessão.')
    source=data['resultados'];allowed={a['id'] for a in source['acoes']}
    activities=[a.model_dump() for a in body.atividades];ids=[a['acao_id'] for a in activities]
    if len(set(ids))!=len(ids) or not set(ids)<=allowed:raise HTTPException(422,'Selecione ações da fotografia sem repetições.')
    if not body.titulo.strip() or not body.objetivo.strip():raise HTTPException(422,'Informe título e objetivo.')
    risks=[r.model_dump() for r in body.riscos];edges=[e.model_dump() for e in body.dependencias]
    if tool=='pdpc':
        if edges or any(a['duracao_horas'] is not None for a in activities):raise HTTPException(422,'Dependências e durações pertencem ao Diagrama de Setas.')
        if len({r['id'] for r in risks})!=len(risks):raise HTTPException(422,'Identificadores de riscos duplicados.')
        for risk in risks:
            if risk['acao_id'] not in ids or not risk['descricao'].strip():raise HTTPException(422,'Cada risco precisa de descrição e ação selecionada válida.')
            alternatives=risk['contramedidas']
            if len({a['id'] for a in alternatives})!=len(alternatives):raise HTTPException(422,'Identificadores de contramedidas duplicados no risco.')
            for alternative in alternatives:
                if not alternative['descricao'].strip():raise HTTPException(422,'Descreva cada contramedida.')
                if alternative['decisao']!='pendente' and not alternative['justificativa'].strip():raise HTTPException(422,'Justifique a viabilidade ou inviabilidade da contramedida.')
        summary=pdpc_summary(activities,risks)
    else:
        if risks:raise HTTPException(422,'Riscos e contramedidas pertencem ao PDPC.')
        summary=network(activities,edges)
    result=dict(titulo=body.titulo.strip(),objetivo=body.objetivo.strip(),contexto=source['contexto'],
        registros=source['registros'],acoes=source['acoes'],parametros=data['parametros'],
        atividades=activities,riscos=risks,dependencias=edges,resumo=summary)
    return company,result

def make_router(tool):
    table,label=TOOLS[tool];router=APIRouter(prefix=f'/api/ferramentas/{tool}',tags=[tool])
    router.add_api_route('/fontes',sources,methods=['GET'])

    @router.get('')
    def generate(empresa_id:int|None=None,contexto:Literal['rnc','geral']='rnc',rnc_ids:str='',user:dict=Depends(get_current_user)):
        source=source_matrix(empresa_id,contexto,rnc_ids,user)
        activities=[dict(acao_id=a['id'],duracao_horas=None) for a in source['acoes']]
        result=dict(titulo=f'{label} — '+('uma RNC' if contexto=='rnc' else 'geral'),objetivo='Executar os planos de ação selecionados.',
            contexto=contexto,registros=source['registros'],acoes=source['acoes'],parametros=source['parametros'],
            atividades=activities,riscos=[],dependencias=[],resumo=pdpc_summary(activities,[]) if tool=='pdpc' else network(activities,[]))
        return {**result,'consulta_ia':context(tool,source['parametros']['empresa_id'],user,result['parametros'],result)}

    @router.post('/preparar')
    def preview(body:Planejamento,user:dict=Depends(get_current_user)):
        company,result=prepare(tool,body,user)
        return {**result,'consulta_ia':context(tool,company,user,result['parametros'],result)}

    @router.get('/diagramas')
    def listing(empresa_id:int|None=None,contexto:Literal['rnc','geral']='rnc',user:dict=Depends(get_current_user)):
        company=scope(user,empresa_id)
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(f'SELECT id,titulo,contexto,revisao,atualizado_em FROM {table} WHERE empresa_id=? AND contexto=? ORDER BY id DESC',(company,contexto))]

    @router.get('/diagramas/{diagram_id}')
    def detail(diagram_id:int,user:dict=Depends(get_current_user)):
        with get_connection() as conn:row=conn.execute(f'SELECT * FROM {table} WHERE id=?',(diagram_id,)).fetchone()
        if not row:raise HTTPException(404,'Diagrama não encontrado.')
        company=scope(user,row['empresa_id']);result=json.loads(row['quadro_json'])
        return {**result,'id':row['id'],'revisao':row['revisao'],'consulta_ia':context(tool,company,user,result['parametros'],result)}

    @router.post('/diagramas')
    def create(body:Planejamento,user:dict=Depends(require_papel('admin','editor'))):
        company,result=prepare(tool,body,user)
        with get_connection() as conn:
            cursor=conn.execute(f'INSERT INTO {table} (empresa_id,titulo,contexto,quadro_json,criado_por_id) VALUES (?,?,?,?,?)',
                (company,result['titulo'],result['contexto'],json.dumps(result,ensure_ascii=False,default=str),user['id']))
            diagram_id=cursor.lastrowid;conn.commit()
        return detail(diagram_id,user)

    @router.put('/diagramas/{diagram_id}')
    def update(diagram_id:int,body:Planejamento,user:dict=Depends(require_papel('admin','editor'))):
        existing=detail(diagram_id,user);company,result=prepare(tool,body,user)
        original=json.loads(existing['consulta_ia']['snapshot'])
        if company!=original['empresa_id'] or result['contexto']!=existing['contexto'] or result['parametros']['rnc_ids']!=existing['parametros']['rnc_ids']:
            raise HTTPException(422,'Preserve empresa, contexto e seleção de RNCs do diagrama salvo.')
        with get_connection() as conn:
            cursor=conn.execute(f'UPDATE {table} SET titulo=?,quadro_json=?,revisao=revisao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND revisao=?',
                (result['titulo'],json.dumps(result,ensure_ascii=False,default=str),diagram_id,company,body.revisao))
            if not cursor.rowcount:raise HTTPException(409,'Diagrama alterado por outra gravação. Reabra antes de salvar.')
            conn.commit()
        return detail(diagram_id,user)
    return router

pdpc_router=make_router('pdpc')
setas_router=make_router('setas')
