"""Consulta de Pareto sem modificar registros operacionais."""
import json
import math
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.calculations import pareto
from app.db import get_connection
from app.routers.issues import _empresa_scope

router = APIRouter(prefix='/api/ferramentas/pareto', tags=['pareto'])
TZ = timezone(timedelta(hours=-3))
LABELS = {'baixo':'Baixo','medio':'Médio','alto':'Alto','critico':'Crítico',
    'producao':'Produção','homologacao':'Homologação','campo':'Campo','linha':'Linha','outro':'Outro',
    'cadastrada':'Cadastrada','em_tratamento':'Em tratamento','fechada':'Fechada',
    'emitida':'Emitida','concluida':'Concluída','reaberta':'Reaberta','maior':'Maior','menor':'Menor'}
DIMENSIONS = ('categoria','impacto','ambiente','local','status','pessoa','envolvidos')

def norm(value):
    s = unicodedata.normalize('NFKD', str(value or '').strip())
    return ' '.join(''.join(ch for ch in s if not unicodedata.combining(ch)).casefold().split())

def local_date(value):
    if not value:return None
    try:
        parsed = datetime.fromisoformat(value)
        return (parsed.astimezone(TZ) if parsed.tzinfo else parsed).date()
    except (TypeError, ValueError):return None

def records(conn, base, empresa_id):
    users = {r['id']:r['nome'] for r in conn.execute('SELECT id,nome FROM usuarios')}
    issues = conn.execute('SELECT * FROM issues'+(' WHERE empresa_id=?' if empresa_id is not None else ''),
        (empresa_id,) if empresa_id is not None else ()).fetchall()
    rncs = {r['issue_id']:dict(r) for r in conn.execute('SELECT * FROM rncs'+(' WHERE empresa_id=?' if empresa_id is not None else ''),
        (empresa_id,) if empresa_id is not None else ())}
    observations = {r['rnc_id']:dict(r) for r in conn.execute('SELECT o.* FROM rnc_observacoes o JOIN rncs r ON r.id=o.rnc_id'+
        (' WHERE r.empresa_id=?' if empresa_id is not None else ''),(empresa_id,) if empresa_id is not None else ())}
    result=[]
    for row in issues:
        issue=dict(row);rnc=rncs.get(issue['id'])
        # Elegibilidade fixa, aplicada antes das opções e de qualquer filtro.
        if base=='issues' and (issue['status'] not in ('cadastrada','em_tratamento') or issue['finalizado_em'] or rnc):continue
        if base=='rncs' and not rnc:continue
        facts=json.loads(rnc['fatos_snapshot_json'] or '{}') if base=='rncs' else issue
        observation=observations.get(rnc['id'],{}) if base=='rncs' else {}
        uid=(rnc['responsavel_id'] or rnc['lider_investigacao_id']) if base=='rncs' else (issue['autor_registro_id'] or issue['criado_por_id'])
        simulation_text=' '.join(str(facts.get(k) or '') for k in ('codigo_erro','comportamento_observado','evidencias_objetivas'))
        result.append(dict(id=rnc['id'] if base=='rncs' else issue['id'],issue_id=issue['id'],empresa_id=issue['empresa_id'],
            codigo=rnc['codigo'] if base=='rncs' else issue['codigo'],issue_codigo=issue['codigo'],
            descricao=facts.get('comportamento_observado') or '',categoria=facts.get('o_que') or '',
            impacto=rnc['impacto'] if base=='rncs' else issue['impacto'],ambiente=rnc['ambiente'] if base=='rncs' else issue['ambiente'],
            local=(observation.get('localizacao') or facts.get('onde') or '') if base=='rncs' else issue['onde'],
            status=rnc['status'] if base=='rncs' else issue['status'],classificacao=rnc['criticidade'] if base=='rncs' else '',
            envolvidos=facts.get('envolvidos_afetados') or '',pessoa=str(uid) if uid else '',pessoa_nome=users.get(uid,'Não informado'),
            detectado_em=facts.get('detectado_em') or '',criado_em=issue['criado_em'],emitida_em=rnc['emitida_em'] if rnc else '',
            tem_rnc=bool(rnc),simulado=('simulado' in norm(simulation_text) or 'sim-ferr-' in norm(simulation_text)),
            quantidade=observation.get('quantidade_afetada'),horas=observation.get('horas_perdidas'),
            prejuizo=observation.get('prejuizo_financeiro'),unidade=observation.get('unidade_quantidade') or '',moeda=observation.get('moeda') or ''))
    return result

def label(key,value):
    return LABELS.get(norm(value),str(value).strip()) if value else 'Não informado'

@router.get('')
def analysis(base:Literal['issues','rncs']='issues',empresa_id:int|None=None,
    data_referencia:Literal['detectado_em','criado_em','emitida_em']='detectado_em',
    inicio:date|None=None,fim:date|None=None,
    simulados:Literal['todos','somente','excluir']='todos',vinculo:Literal['todos','com','sem']='todos',
    categoria:str='',impacto:str='',ambiente:str='',local:str='',status:str='',pessoa:str='',envolvidos:str='',classificacao:str='',
    agrupar:Literal['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao']='categoria',
    medida:Literal['registros','quantidade','horas','prejuizo']='registros',unidade:str='',moeda:str='',
    user:dict=Depends(get_current_user)):
    scope=_empresa_scope(user,empresa_id)
    if inicio and fim and inicio>fim:raise HTTPException(422,'A data inicial deve ser anterior ou igual à final.')
    if base=='issues' and (medida!='registros' or agrupar=='classificacao' or data_referencia=='emitida_em' or classificacao):
        raise HTTPException(422,'Esta medida, classificação ou data de emissão está disponível somente para RNCs.')
    if base=='rncs' and (vinculo!='todos' or data_referencia=='criado_em'):
        raise HTTPException(422,'Use os filtros e datas próprios de RNCs.')
    with get_connection() as conn:items=records(conn,base,scope)
    options={}
    for key in (*DIMENSIONS,'classificacao','unidade','moeda'):
        choices={}
        for r in items:
            value=r[key];canonical=norm(value)
            if canonical:choices[canonical]=dict(valor=canonical,rotulo=r['pessoa_nome'] if key=='pessoa' else label(key,value))
        options[key]=sorted(choices.values(),key=lambda x:norm(x['rotulo']))
    filters=dict(categoria=categoria,impacto=impacto,ambiente=ambiente,local=local,status=status,pessoa=pessoa,envolvidos=envolvidos,classificacao=classificacao)
    filtered=[];date_missing=0
    for r in items:
        if any(value and norm(r[key])!=norm(value) for key,value in filters.items()):continue
        if simulados=='somente' and not r['simulado'] or simulados=='excluir' and r['simulado']:continue
        if vinculo=='com' and not r['tem_rnc'] or vinculo=='sem' and r['tem_rnc']:continue
        if inicio or fim:
            d=local_date(r[data_referencia])
            if d is None:date_missing+=1;continue
            if inicio and d<inicio or fim and d>fim:continue
        if medida=='quantidade' and unidade and norm(r['unidade'])!=norm(unidade):continue
        if medida=='prejuizo' and moeda and norm(r['moeda'])!=norm(moeda):continue
        filtered.append(r)
    valid=[];missing=0
    for r in filtered:
        value=1 if medida=='registros' else r[medida]
        if value is None or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            missing+=1;continue
        if medida in ('quantidade','prejuizo') and not r['unidade' if medida=='quantidade' else 'moeda'].strip():
            missing+=1;continue
        valid.append({**r,'contribuicao':value})
    unit_key='unidade' if medida=='quantidade' else 'moeda'
    if medida in ('quantidade','prejuizo') and len({norm(r[unit_key]) for r in valid})>1:
        raise HTTPException(422,'Selecione uma única unidade ou moeda para somar valores comparáveis.')
    totals=defaultdict(float);names={}
    for r in valid:
        key=norm(r[agrupar]) or '__ausente__'
        r['grupo']=key;names[key]=r['pessoa_nome'] if agrupar=='pessoa' else label(agrupar,r[agrupar]);totals[key]+=r['contribuicao']
    ordered=sorted(totals,key=lambda key:(-totals[key],key))
    chart=pareto([dict(rotulo=names[key],frequencia=totals[key]) for key in ordered])
    for item,key in zip(chart['itens'],ordered):item['chave']=key
    unit='registros' if medida=='registros' else 'horas' if medida=='horas' else next((r[unit_key] for r in valid),'')
    result=dict(base=base,opcoes=options,dados=chart,unidade=unit,registros=valid,
        selecionados=len(filtered),incluidos=len(valid),sem_medida=missing,sem_data=date_missing,
        categoria_origem='Campo O que aconteceu da Issue; nas RNCs, fatos preservados na emissão.')
    from app.services.ferramentas_ia import context
    parameters=dict(base=base,empresa_id=scope,data_referencia=data_referencia,inicio=inicio,fim=fim,simulados=simulados,
        vinculo=vinculo,**filters,agrupar=agrupar,medida=medida,unidade=unidade,moeda=moeda)
    result['consulta_ia']=context('pareto',scope,user,parameters,{k:v for k,v in result.items() if k!='opcoes'})
    return result
