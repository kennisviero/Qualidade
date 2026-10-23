import json
from copy import deepcopy
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from tests.test_pareto import seed
from tests.test_issues import login

ROOT='/api/ferramentas/relacoes'

def board(selected):
    ids=[r['id'] for r in selected['registros']]
    return dict(titulo='Influências',**selected['consulta_ia'],
        fatores=[dict(id=1,nome='Instrução',registros=ids[:1]),dict(id=2,nome='Ajustes',registros=ids[:2])],
        relacoes=[dict(origem=1,destino=2,tipo='hipotese',justificativa='Verificar se a instrução orienta os ajustes',evidencia='')])

def test_lifecycle_filters_snapshot_counts_and_tenancy():
    with TestClient(app) as c:
        assert c.get(ROOT).status_code==401
        eid,a,b,d=seed(c)
        selected=c.get(ROOT,params={'empresa_id':eid}).json()
        assert len(selected['registros'])==3 and all(not r['tem_rnc'] for r in selected['registros'])
        body=board(selected)
        prepared=c.post(ROOT+'/preparar',json=body)
        assert prepared.status_code==200,prepared.text
        result=prepared.json()
        assert [(f['entradas'],f['saidas']) for f in result['fatores']]==[(0,1),(1,0)]
        signed=json.loads(result['consulta_ia']['snapshot'])
        assert signed['ferramenta']=='relacoes' and signed['resultados']['relacoes']==body['relacoes']
        created=c.post(ROOT+'/diagramas',json=body)
        assert created.status_code==200,created.text
        saved=created.json();did=saved['id']
        assert c.get(ROOT+'/diagramas',params={'empresa_id':eid}).json()[0]['id']==did
        with get_connection() as conn:
            original=conn.execute('SELECT comportamento_observado FROM issues WHERE id=?',(d['id'],)).fetchone()[0]
            conn.execute("UPDATE issues SET comportamento_observado='Novo texto' WHERE id=?",(d['id'],));conn.commit()
        reopened=c.get(f'{ROOT}/diagramas/{did}').json()
        assert next(r for r in reopened['registros'] if r['id']==d['id'])['descricao']==original
        updated=c.put(f'{ROOT}/diagramas/{did}',json={**body,'revisao':1,'titulo':'Revisto'})
        assert updated.json()['revisao']==2
        assert c.put(f'{ROOT}/diagramas/{did}',json={**body,'revisao':1}).status_code==409
        rncs=c.get(ROOT,params={'empresa_id':eid,'base':'rncs'}).json()
        assert len(rncs['registros'])==2 and all(r['observacoes'] for r in rncs['registros'])
        assert c.post(ROOT+'/diagramas',json=board(rncs)).status_code==200
        assert c.put(f'{ROOT}/diagramas/{did}',json={**board(rncs),'revisao':2}).status_code==422
        assert c.get(ROOT,params={'empresa_id':eid,'categoria':'inexistente'}).json()['registros']==[]
        assert c.get(ROOT,params={'empresa_id':eid,'inicio':'2026-10-20','fim':'2026-10-10'}).status_code==422
        login(c,'carlos','carlos')
        assert c.get(ROOT,params={'empresa_id':eid}).status_code==403
        assert c.get(f'{ROOT}/diagramas/{did}').status_code==403
        assert c.post(ROOT+'/preparar',json=body).status_code==403
        login(c,'admin','admin')
        assert c.delete(f'/api/empresas/{eid}').status_code==204
        assert c.get(f'{ROOT}/diagramas/{did}').status_code==404


def test_invalid_edges_links_signature_and_cycles():
    with TestClient(app) as c:
        eid,*_=seed(c)
        body=board(c.get(ROOT,params={'empresa_id':eid}).json())
        variants=[]
        for changes in [dict(origem=999),dict(destino=1),dict(justificativa=' '),dict(tipo='evidenciada',evidencia=' '),dict(tipo='invalida')]:
            variant=deepcopy(body);variant['relacoes'][0].update(changes);variants.append(variant)
        variant=deepcopy(body);variant['relacoes']*=2;variants.append(variant)
        variant=deepcopy(body);variant['fatores'][0]['registros']=[999999];variants.append(variant)
        variant=deepcopy(body);variant['fatores'][1]['id']=1;variants.append(variant)
        variant=deepcopy(body);variant['fatores'][1]['nome']='instrução';variants.append(variant)
        for variant in variants:
            assert c.post(ROOT+'/preparar',json=variant).status_code==422,variant
        assert c.post(ROOT+'/preparar',json={**body,'assinatura':'0'*64}).status_code==409
        affinity=c.get('/api/ferramentas/afinidades',params={'empresa_id':eid}).json()
        assert c.post(ROOT+'/preparar',json={**body,**affinity['consulta_ia']}).status_code==409
        body['relacoes'][0].update(tipo='evidenciada',evidencia='Registro de ajuste a verificar pelo analista')
        body['relacoes'].append(dict(origem=2,destino=1,justificativa='Possível realimentação'))
        assert c.post(ROOT+'/preparar',json=body).status_code==200


def test_viewer_reads_but_cannot_write():
    with TestClient(app) as c:
        eid,*_=seed(c)
        body=board(c.get(ROOT,params={'empresa_id':eid}).json())
        did=c.post(ROOT+'/diagramas',json=body).json()['id']
        with get_connection() as conn:
            uid=conn.execute("SELECT id FROM usuarios WHERE email='admin'").fetchone()[0]
            conn.execute("UPDATE usuarios SET papel='visualizador',empresa_id=? WHERE id=?",(eid,uid));conn.commit()
        try:
            assert c.get(f'{ROOT}/diagramas/{did}').status_code==200
            assert c.post(ROOT+'/diagramas',json=body).status_code==403
            assert c.put(f'{ROOT}/diagramas/{did}',json=body).status_code==403
        finally:
            with get_connection() as conn:
                conn.execute("UPDATE usuarios SET papel='admin',empresa_id=NULL WHERE id=?",(uid,));conn.commit()
