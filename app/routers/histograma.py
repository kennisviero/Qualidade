"""Histograma de medidas estruturadas, com os filtros e elegibilidade do Pareto."""
import bisect
import math
import statistics
from datetime import date, datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_user
from app.db import get_connection
from app.routers.pareto import analysis, norm, TZ

router=APIRouter(prefix='/api/ferramentas/histograma',tags=['histograma'])
METRICS={
    'idade_dias':('Tempo desde o cadastro / emissão','dias'),
    'registro_horas':('Tempo da detecção ao cadastro','horas'),
    'emissao_horas':('Tempo da detecção à emissão','horas'),
    'contencao_horas':('Tempo da detecção à contenção','horas'),
    'horas':('Horas perdidas','horas'),
    'quantidade':('Quantidade afetada',''),
    'prejuizo':('Prejuízo financeiro',''),
}

def instant(value):
    if not value or ('T' not in value and ' ' not in value):return None
    try:
        parsed=datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)
    except (TypeError,ValueError):return None

def elapsed(start,end,divisor):
    a,b=instant(start),instant(end)
    return (b-a).total_seconds()/divisor if a and b else None

def distribution(values,classes=None):
    if not values:return [],dict(n=0,minimo=None,maximo=None,media=None,mediana=None,desvio_padrao=None)
    lo,hi=min(values),max(values)
    count=classes or min(50,math.ceil(math.log2(len(values)))+1)
    if lo==hi:
        count=1
        width=max(1,abs(lo)*0.1)
        lo,hi=max(0,lo-width/2),lo+width/2
    width=(hi-lo)/count
    edges=[lo+i*width for i in range(count)]+[hi]
    bins=[dict(indice=i,inicio=edges[i],fim=edges[i+1],frequencia=0,percentual=0,inclui_fim=i==count-1) for i in range(count)]
    for value in values:
        index=min(count-1,max(0,bisect.bisect_right(edges,value)-1))
        bins[index]['frequencia']+=1
    for item in bins:item['percentual']=item['frequencia']/len(values)*100
    stats=dict(n=len(values),minimo=min(values),maximo=max(values),media=statistics.mean(values),
        mediana=statistics.median(values),desvio_padrao=statistics.stdev(values) if len(values)>1 else None)
    return bins,stats

@router.get('')
def histogram(base:Literal['issues','rncs']='issues',empresa_id:int|None=None,
    data_referencia:Literal['detectado_em','criado_em','emitida_em']='detectado_em',inicio:date|None=None,fim:date|None=None,
    simulados:Literal['todos','somente','excluir']='todos',categoria:str='',impacto:str='',ambiente:str='',local:str='',
    status:str='',pessoa:str='',envolvidos:str='',classificacao:str='',
    medida:Literal['idade_dias','registro_horas','emissao_horas','contencao_horas','horas','quantidade','prejuizo']='idade_dias',
    classes:int|None=Query(default=None,ge=1,le=50),unidade:str='',moeda:str='',user:dict=Depends(get_current_user)):
    allowed=['idade_dias','registro_horas'] if base=='issues' else ['idade_dias','emissao_horas','contencao_horas','horas','quantidade','prejuizo']
    if medida not in allowed:raise HTTPException(422,'Escolha uma medida disponível para a base selecionada.')
    selected=analysis(base=base,empresa_id=empresa_id,data_referencia=data_referencia,inicio=inicio,fim=fim,
        simulados=simulados,categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,
        envolvidos=envolvidos,classificacao=classificacao,user=user)
    generated=datetime.now(TZ)
    with get_connection() as conn:
        containment={}
        if base=='rncs' and medida=='contencao_horas':
            # Apenas IDs já autorizados e selecionados, sem ler outras empresas.
            for record in selected['registros']:
                row=conn.execute('SELECT contencao_em,data_conclusao_contencao FROM rncs WHERE id=?',(record['id'],)).fetchone()
                containment[record['id']]=(row['contencao_em'] or row['data_conclusao_contencao']) if row else ''
    filtered=[]
    for record in selected['registros']:
        if medida=='quantidade' and unidade and norm(record['unidade'])!=norm(unidade):continue
        if medida=='prejuizo' and moeda and norm(record['moeda'])!=norm(moeda):continue
        filtered.append(record)
    valid=[];missing=0;invalid=0
    for record in filtered:
        if medida=='idade_dias':value=elapsed(record['emitida_em'] if base=='rncs' else record['criado_em'],generated.isoformat(),86400)
        elif medida=='registro_horas':value=elapsed(record['detectado_em'],record['criado_em'],3600)
        elif medida=='emissao_horas':value=elapsed(record['detectado_em'],record['emitida_em'],3600)
        elif medida=='contencao_horas':value=elapsed(record['detectado_em'],containment.get(record['id']),3600)
        else:value=record[medida]
        if value is None or (medida in ('quantidade','prejuizo') and not record['unidade' if medida=='quantidade' else 'moeda'].strip()):missing+=1;continue
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:invalid+=1;continue
        valid.append({**record,'valor':value})
    unitkey='unidade' if medida=='quantidade' else 'moeda'
    if medida in ('quantidade','prejuizo') and len({norm(r[unitkey]) for r in valid})>1:
        raise HTTPException(422,'Selecione uma única unidade ou moeda para comparar medidas compatíveis.')
    bins,stats=distribution([r['valor'] for r in valid],classes)
    for record in valid:
        record['intervalo']=next(item['indice'] for item in bins if item['inicio']<=record['valor'] and (record['valor']<item['fim'] or item['inclui_fim'] and record['valor']<=item['fim']))
    unit=METRICS[medida][1] or next((r[unitkey] for r in valid),'')
    result=dict(base=base,medida=medida,rotulo=METRICS[medida][0],unidade=unit,opcoes=selected['opcoes'],
        medidas=[dict(valor=k,rotulo=METRICS[k][0]) for k in allowed],intervalos=bins,estatisticas=stats,registros=valid,
        selecionados=len(filtered),incluidos=len(valid),sem_medida=missing,invalidos=invalid,sem_data=selected['sem_data'],gerado_em=generated.isoformat())
    from app.services.ferramentas_ia import context
    import json
    company=json.loads(selected['consulta_ia']['snapshot'])['empresa_id']
    parameters=dict(base=base,empresa_id=company,data_referencia=data_referencia,inicio=inicio,fim=fim,simulados=simulados,
        categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,envolvidos=envolvidos,
        classificacao=classificacao,medida=medida,classes=classes,unidade=unidade,moeda=moeda)
    result['consulta_ia']=context('histograma',company,user,parameters,{k:v for k,v in result.items() if k not in ('opcoes','medidas')})
    return result
