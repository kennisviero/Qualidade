"""Pares numéricos da mesma Issue/RNC, com filtros e consulta IA compartilhados."""
import json
import math
import statistics
from datetime import date,datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from app.auth import get_current_user
from app.db import get_connection
from app.routers.pareto import analysis,norm,TZ
from app.routers.histograma import METRICS,elapsed
from app.services.ferramentas_ia import context

router=APIRouter(prefix='/api/ferramentas/dispersao',tags=['dispersao'])
Metric=Literal['idade_dias','registro_horas','emissao_horas','contencao_horas','horas','quantidade','prejuizo']

def correlation(points):
    if len(points)<2:return None
    xs=[p['x'] for p in points];ys=[p['y'] for p in points]
    if min(xs)==max(xs) or min(ys)==max(ys):return None
    return max(-1,min(1,statistics.correlation(xs,ys)))

@router.get('')
def scatter(base:Literal['issues','rncs']='issues',empresa_id:int|None=None,
    data_referencia:Literal['detectado_em','criado_em','emitida_em']='detectado_em',inicio:date|None=None,fim:date|None=None,
    simulados:Literal['todos','somente','excluir']='todos',categoria:str='',impacto:str='',ambiente:str='',local:str='',
    status:str='',pessoa:str='',envolvidos:str='',classificacao:str='',
    eixo_x:Metric='idade_dias',eixo_y:Metric|None=None,unidade:str='',moeda:str='',user:dict=Depends(get_current_user)):
    allowed=['idade_dias','registro_horas'] if base=='issues' else ['idade_dias','emissao_horas','contencao_horas','horas','quantidade','prejuizo']
    eixo_y=eixo_y or ('registro_horas' if base=='issues' else 'horas')
    if eixo_x not in allowed or eixo_y not in allowed:raise HTTPException(422,'Escolha medidas disponíveis para a base selecionada.')
    if eixo_x==eixo_y:raise HTTPException(422,'Selecione medidas diferentes para os eixos X e Y.')
    selected=analysis(base=base,empresa_id=empresa_id,data_referencia=data_referencia,inicio=inicio,fim=fim,simulados=simulados,
        categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,envolvidos=envolvidos,classificacao=classificacao,user=user)
    axes=(eixo_x,eixo_y);generated=datetime.now(TZ).isoformat();containment={}
    if 'contencao_horas' in axes:
        with get_connection() as conn:
            for r in selected['registros']:
                row=conn.execute('SELECT contencao_em,data_conclusao_contencao FROM rncs WHERE id=?',(r['id'],)).fetchone()
                containment[r['id']]=(row['contencao_em'] or row['data_conclusao_contencao']) if row else ''
    candidates=[]
    for r in selected['registros']:
        if 'quantidade' in axes and unidade and norm(r['unidade'])!=norm(unidade):continue
        if 'prejuizo' in axes and moeda and norm(r['moeda'])!=norm(moeda):continue
        candidates.append(r)
    def value(r,metric):
        if metric=='idade_dias':return elapsed(r['emitida_em'] if base=='rncs' else r['criado_em'],generated,86400)
        if metric=='registro_horas':return elapsed(r['detectado_em'],r['criado_em'],3600)
        if metric=='emissao_horas':return elapsed(r['detectado_em'],r['emitida_em'],3600)
        if metric=='contencao_horas':return elapsed(r['detectado_em'],containment.get(r['id']),3600)
        if metric in ('quantidade','prejuizo') and not r['unidade' if metric=='quantidade' else 'moeda'].strip():return None
        return r[metric]
    points=[];missing=0;invalid=0
    for r in candidates:
        x,y=value(r,eixo_x),value(r,eixo_y)
        if x is None or y is None:missing+=1;continue
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in (x,y)):invalid+=1;continue
        points.append({**r,'x':x,'y':y})
    for metric,key in [('quantidade','unidade'),('prejuizo','moeda')]:
        if metric in axes and len({norm(p[key]) for p in points})>1:
            raise HTTPException(422,'Selecione uma única unidade ou moeda para cada medida comparável.')
    def axis(metric):
        unit=METRICS[metric][1] or next((p['unidade' if metric=='quantidade' else 'moeda'] for p in points),'')
        return dict(medida=metric,rotulo=METRICS[metric][0],unidade=unit)
    r=correlation(points)
    result=dict(base=base,eixo_x=axis(eixo_x),eixo_y=axis(eixo_y),pontos=points,registros=points,
        opcoes=selected['opcoes'],medidas=[dict(valor=k,rotulo=METRICS[k][0]) for k in allowed],
        selecionados=len(candidates),incluidos=len(points),sem_par=missing,invalidos=invalid,sem_data=selected['sem_data'],
        correlacao=r,gerado_em=generated,aviso='Correlação não comprova causalidade. Valores simulados podem ter relações construídas na geração dos exemplos.')
    company=json.loads(selected['consulta_ia']['snapshot'])['empresa_id']
    parameters=dict(base=base,empresa_id=company,data_referencia=data_referencia,inicio=inicio,fim=fim,simulados=simulados,
        categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,envolvidos=envolvidos,
        classificacao=classificacao,eixo_x=eixo_x,eixo_y=eixo_y,unidade=unidade,moeda=moeda)
    result['consulta_ia']=context('dispersao',company,user,parameters,{k:v for k,v in result.items() if k not in ('opcoes','medidas','pontos')})
    return result
