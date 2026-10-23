import json
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from tests.test_pareto import seed
from tests.test_issues import login

ROOT='/api/ferramentas/afinidades'

def test_board_lifecycle_snapshot_validation_and_tenancy():
    with TestClient(app) as c:
        assert c.get(ROOT).status_code==401
        eid,a,b,d=seed(c)
        selected=c.get(ROOT,params={'empresa_id':eid}).json()
        assert len(selected['registros'])==3
        assert all(not r['tem_rnc'] for r in selected['registros'])
        ids=[r['id'] for r in selected['registros']]
        body=dict(titulo='Temas',**selected['consulta_ia'],grupos=[dict(nome='Instruções',registros=ids[:2])])
        preview=c.post(ROOT+'/preparar',json=body)
        assert preview.status_code==200,preview.text
        data=json.loads(preview.json()['consulta_ia']['snapshot'])
        assert data['resultados']['grupos']==body['grupos']
        assert data['resultados']['sem_grupo']==ids[2:]
        created=c.post(ROOT+'/diagramas',json=body)
        assert created.status_code==200,created.text
        saved=created.json();did=saved['id']
        assert c.get(ROOT+'/diagramas',params={'empresa_id':eid}).json()[0]['id']==did
        with get_connection() as conn:
            original=conn.execute('SELECT comportamento_observado FROM issues WHERE id=?',(ids[0],)).fetchone()[0]
            conn.execute("UPDATE issues SET comportamento_observado='Relato novo' WHERE id=?",(ids[0],));conn.commit()
        reopened=c.get(f'{ROOT}/diagramas/{did}').json()
        assert reopened['registros'][0]['descricao']==original
        update={**body,'titulo':'Temas revisados','revisao':1}
        assert c.put(f'{ROOT}/diagramas/{did}',json=update).json()['revisao']==2
        assert c.put(f'{ROOT}/diagramas/{did}',json=update).status_code==409
        for groups in [[dict(nome='X',registros=[ids[0],ids[0]])],[dict(nome='X',registros=[999999])],[dict(nome=' ',registros=[])],[dict(nome='X'),dict(nome='x')]]:
            assert c.post(ROOT+'/preparar',json={**body,'grupos':groups}).status_code==422
        assert c.post(ROOT+'/preparar',json={**body,'assinatura':'0'*64}).status_code==409
        rncs=c.get(ROOT,params={'empresa_id':eid,'base':'rncs'}).json()
        assert len(rncs['registros'])==2
        assert all(r['observacoes'] and r['issue_id'] in [a['id'],b['id']] for r in rncs['registros'])
        assert c.get(ROOT,params={'empresa_id':eid,'inicio':'2026-10-20','fim':'2026-10-10'}).status_code==422
        assert c.get(ROOT,params={'empresa_id':eid,'categoria':'inexistente'}).json()['registros']==[]
        login(c,'carlos','carlos')
        assert c.get(ROOT,params={'empresa_id':eid}).status_code==403
        assert c.get(f'{ROOT}/diagramas/{did}').status_code==403
        assert c.post(ROOT+'/preparar',json=body).status_code==403
        login(c,'admin','admin')
        # O novo vínculo não bloqueia a exclusão já existente de empresas.
        assert c.delete(f'/api/empresas/{eid}').status_code==204
        assert c.get(f'{ROOT}/diagramas/{did}').status_code==404


def test_viewer_cannot_save_or_update():
    with TestClient(app) as c:
        eid,*_=seed(c)
        selected=c.get(ROOT,params={'empresa_id':eid}).json()
        body=dict(titulo='Teste',**selected['consulta_ia'],grupos=[])
        saved=c.post(ROOT+'/diagramas',json=body).json()
        with get_connection() as conn:
            uid=conn.execute("SELECT id FROM usuarios WHERE email='admin'").fetchone()[0]
            conn.execute("UPDATE usuarios SET papel='visualizador',empresa_id=? WHERE id=?",(eid,uid));conn.commit()
        try:
            assert c.get(f"{ROOT}/diagramas/{saved['id']}").status_code==200
            assert c.post(ROOT+'/diagramas',json=body).status_code==403
            assert c.put(f"{ROOT}/diagramas/{saved['id']}",json=body).status_code==403
        finally:
            with get_connection() as conn:
                conn.execute("UPDATE usuarios SET papel='admin',empresa_id=NULL WHERE id=?",(uid,));conn.commit()
