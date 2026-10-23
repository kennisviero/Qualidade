"""Smoke da base/servidor ativos: somente SELECT/PRAGMA e HTTP GET local.

Não importa app, inicializa lifespan, efetua login/logout ou grava dados de negócio.
Respostas e sessões nunca são persistidas nas evidências.
"""
import json
import os
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

ROOT=Path(__file__).resolve().parent.parent
FOLDER=Path(os.environ['QA_EVIDENCE_DIR'])
DB=Path(os.environ['QA_ACTIVE_DB']).resolve()
ORIGIN='http://127.0.0.1:8000'
results=[]

def check(name,action):
    started=time.monotonic()
    try:
        detail=action()
        item=dict(name=name,status='passed',detail=detail)
    except Exception as error:
        # Do not log response bodies, request cookies or raw database rows.
        safe=str(error) if isinstance(error,AssertionError) else type(error).__name__
        item=dict(name=name,status='failed',detail=safe)
    item['seconds']=round(time.monotonic()-started,3)
    results.append(item)
    print(json.dumps(item,ensure_ascii=False),flush=True)
    return item['status']=='passed'

def require(condition,message):
    if not condition:raise AssertionError(message)

def connect():
    conn=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True,timeout=5)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    return conn

def get(client,path,params=None):
    url=ORIGIN+path
    parts=urlsplit(url)
    require(parts.scheme=='http' and parts.hostname=='127.0.0.1' and parts.port==8000,'Destino fora da origem autorizada')
    response=client.get(url,params=params)
    require(response.status_code==200,f'GET {path}: HTTP {response.status_code}, esperado 200')
    return response.json() if path.startswith('/api/') else response.text

def sql_integrity():
    with connect() as conn:
        require(conn.execute('PRAGMA integrity_check').fetchall()[0][0]=='ok','integrity_check não retornou ok')
        require(not conn.execute('PRAGMA foreign_key_check').fetchall(),'foreign_key_check identificou inconsistência')
        return {'integrity':'ok','foreign_keys':'ok','mode':'ro/query_only'}

def session():
    with connect() as conn:
        rows=conn.execute('SELECT s.token,u.id,u.empresa_id,u.papel FROM sessions s JOIN usuarios u ON u.id=s.user_id LEFT JOIN empresas e ON e.id=u.empresa_id WHERE s.expira_em>? AND u.ativo=1 AND (u.empresa_id IS NULL OR e.ativo=1) ORDER BY (u.papel="admin" AND u.empresa_id IS NULL) DESC,s.criado_em DESC', (datetime.now(timezone.utc).isoformat(),)).fetchall()
    require(bool(rows),'Sem sessão existente válida; login não executado para preservar somente leitura')
    return dict(rows[0])

def same_rows(client,path,table,company=None,params=None):
    data=get(client,path,params)
    require(isinstance(data,list),f'{path}: lista esperada')
    with connect() as conn:
        sql=f'SELECT * FROM {table}'
        rows={r['id']:dict(r) for r in conn.execute(sql+(' WHERE empresa_id=?' if company is not None else ''),(company,) if company is not None else ())}
        expected=set(rows)
    id_key='rnc_id' if table=='rncs' else 'id'
    require({r[id_key] for r in data}==expected,f'{path}: IDs API diferem do banco consultado (ou alteração concorrente)')
    fields={'issues':['codigo','empresa_id','status','comportamento_observado'],
            'rncs':['codigo','empresa_id','status','issue_id'],
            'usuarios':['nome','empresa_id','papel'],
            'setores':['nome','empresa_id'],'processos':['nome','empresa_id']}.get(table,[])
    for item in data:
        raw=rows[item[id_key]]
        for field in fields:
            key='rnc_'+field if table=='rncs' else field
            require(item.get(key)==raw[field],f'{path}: campo {key} diverge do banco (ou alteração concorrente)')
    return {'records':len(data),'ids_and_fields_match_database':True}

def main():
    check('SQL.integridade_e_FKs',sql_integrity)
    selected={}
    def existing_session():
        selected.update(session())
        return {'existing_session':True,'authentication_writes':False}
    if not check('HTTP.sessao_existente',existing_session):return
    with httpx.Client(timeout=20,follow_redirects=False,trust_env=False,cookies={'session':selected['token']}) as client:
        check('HTTP.pagina',lambda:{'html':bool(get(client,'/'))})
        def identity():
            user=get(client,'/api/auth/me')
            require(user['id']==selected['id'],'Sessão/servidor não corresponde ao banco ativo selecionado')
            return {'identity_matches_database':True}
        if not check('HTTP.identidade',identity):return
        global_user=selected['papel']=='admin' and selected['empresa_id'] is None
        with connect() as conn:
            companies=[r[0] for r in conn.execute('SELECT id FROM empresas ORDER BY id')] if global_user else [selected['empresa_id']]
        def company_list():
            response=client.get(ORIGIN+'/api/empresas')
            if selected['papel']!='admin':
                require(response.status_code==403,'Lista empresas deveria exigir admin')
                return {'permission_denied_expected':True}
            require(response.status_code==200,'GET empresas falhou')
            require({r['id'] for r in response.json()}==set(companies),'Empresas API diferem do banco ou alteração concorrente')
            return {'companies':len(companies),'ids_match_database':True}
        check('HTTP.empresas',company_list)
        check('HTTP.usuarios',lambda:same_rows(client,'/api/usuarios','usuarios',None if global_user else selected['empresa_id']))
        for eid in companies:
            prefix=f'empresa_{eid}'
            params={'empresa_id':eid}
            for path,table in [('/api/issues','issues'),('/api/rncs','rncs'),('/api/setores','setores'),('/api/processos','processos')]:
                check(prefix+path,lambda p=path,t=table:same_rows(client,p,t,eid,params))
            for path in ['/api/issues/kpis','/api/issues/stats','/api/issues/trends','/api/issues/kanban']:
                check(prefix+path,lambda p=path:{'response_type':type(get(client,p,params)).__name__})
            for base in ['issues','rncs']:
                with connect() as conn:
                    if base=='issues':
                        expected={r[0] for r in conn.execute("SELECT i.id FROM issues i WHERE i.empresa_id=? AND i.status IN ('cadastrada','em_tratamento') AND (i.finalizado_em IS NULL OR i.finalizado_em='') AND NOT EXISTS(SELECT 1 FROM rncs r WHERE r.issue_id=i.id)",(eid,))}
                    else:expected={r[0] for r in conn.execute('SELECT id FROM rncs WHERE empresa_id=?',(eid,))}
                query={**params,'base':base}
                for tool in ['pareto','histograma','dispersao','afinidades','relacoes']:
                    def tool_check(tool=tool,query=query,expected=expected,base=base):
                        data=get(client,'/api/ferramentas/'+tool,query)
                        require(data['base']==base,'Ferramenta retornou base diferente')
                        records=data.get('registros',data.get('pontos',[]))
                        require(all(r.get('empresa_id',eid)==eid for r in records),'Ferramenta retornou registro de outra empresa')
                        require({r['id'] for r in records}<=expected,'Ferramenta retornou registro inelegível ou banco mudou durante execução')
                        if tool in ['pareto','afinidades','relacoes']:
                            require({r['id'] for r in records}==expected,'Ferramenta omitiu registros ou banco mudou durante execução')
                        return {'base':base,'records':len(records),'eligible_records':len(expected)}
                    check(prefix+'.'+base+'.'+tool,tool_check)
                for tool in ['afinidades','relacoes']:
                    check(prefix+'.'+base+'.'+tool+'.salvos',lambda tool=tool,query=query:saved(client,tool,eid,base,query))
            check(prefix+'.matriz.fontes',lambda:matrix_sources(client,eid))
            with connect() as conn:matrix_ids=[r[0] for r in conn.execute('SELECT id FROM rncs WHERE empresa_id=? ORDER BY id LIMIT 2',(eid,))]
            if matrix_ids:check(prefix+'.matriz.rnc',lambda:matrix_generate(client,eid,matrix_ids[:1],'rnc'))
            if len(matrix_ids)>=2:check(prefix+'.matriz.geral',lambda:matrix_generate(client,eid,matrix_ids,'geral'))
            for mode in ['rnc','geral']:
                check(prefix+'.matriz.salvas.'+mode,lambda mode=mode:matrix_saved(client,eid,mode))

def matrix_sources(client,eid):
    data=get(client,'/api/ferramentas/matriz/fontes',{'empresa_id':eid})
    with connect() as conn:expected={r[0] for r in conn.execute('SELECT id FROM rncs WHERE empresa_id=?',(eid,))}
    require({r['id'] for r in data['registros']}==expected,'Fontes matriz divergem do banco ou alteração concorrente')
    return {'sources':len(expected),'ids_match_database':True}

def matrix_generate(client,eid,ids,mode):
    data=get(client,'/api/ferramentas/matriz',{'empresa_id':eid,'contexto':mode,'rnc_ids':','.join(map(str,ids))})
    require(data['contexto']==mode and {r['id'] for r in data['registros']}==set(ids),'Contexto/seleção matriz divergente')
    with connect() as conn:
        expected={r[0] for r in conn.execute('SELECT id FROM acoes WHERE rnc_id IN ('+','.join('?' for _ in ids)+')',ids)}
    require({a['id'] for a in data['acoes']}==expected,'Ações matriz divergem dos planos ou alteração concorrente')
    require(data['celulas']==[] and data['resumo']['avaliados']==0,'Matriz gerada deveria iniciar sem avaliações')
    return {'context':mode,'rncs':len(ids),'actions':len(expected),'assessed':0}

def matrix_saved(client,eid,mode):
    data=get(client,'/api/ferramentas/matriz/diagramas',{'empresa_id':eid,'contexto':mode})
    with connect() as conn:expected={r[0] for r in conn.execute('SELECT id FROM matrizes WHERE empresa_id=? AND contexto=?',(eid,mode))}
    require({r['id'] for r in data}==expected,'Matrizes salvas divergem do banco ou alteração concorrente')
    return {'saved_matrices':len(data),'ids_match_database':True}

def saved(client,tool,eid,base,query):
    data=get(client,'/api/ferramentas/'+tool+'/diagramas',query)
    with connect() as conn:expected={r[0] for r in conn.execute(f'SELECT id FROM {tool} WHERE empresa_id=? AND base=?',(eid,base))}
    require({r['id'] for r in data}==expected,'Diagramas salvos diferem do banco ou alteração concorrente')
    return {'saved_diagrams':len(data),'ids_match_database':True}

try:main()
except Exception as error:check('infraestrutura',lambda:(_ for _ in ()).throw(error))
finally:
    failures=sum(r['status']=='failed' for r in results)
    suite=ET.Element('testsuite',name='live-readonly',tests=str(len(results)),failures=str(failures))
    for result in results:
        case=ET.SubElement(suite,'testcase',name=result['name'],classname='live_readonly',time=str(result['seconds']))
        if result['status']=='failed':ET.SubElement(case,'failure',message=str(result['detail']))
    ET.ElementTree(suite).write(FOLDER/'live-readonly.xml',encoding='utf-8',xml_declaration=True)
    (FOLDER/'live-readonly.json').write_text(json.dumps({'readonly':True,'origin':ORIGIN,'cases':results,'failures':failures,'concurrent_changes_possible':True},ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(1 if failures else 0)
