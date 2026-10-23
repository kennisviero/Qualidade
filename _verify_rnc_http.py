"""Reproduz encerramento via HTTP real em cópia temporária da base ativa."""
import os,sys,tempfile,sqlite3,subprocess,time,json
from pathlib import Path
import httpx

root=Path(__file__).resolve().parent
folder=Path(tempfile.mkdtemp(prefix='qualidade_rnc_http_'))
database=folder/'qualidade.db'
with sqlite3.connect(root/'data/qualidade.db') as source,sqlite3.connect(database) as target:source.backup(target)
os.environ['QUALIDADE_DB']=str(database)
os.environ['QUALIDADE_DOCS']=str(folder/'Vault')
from app.db import init_db,get_connection
from app.auth import hash_password
init_db()
with get_connection() as conn:
    conn.execute("UPDATE usuarios SET senha_hash=? WHERE id IN (SELECT encerramento_aprovador_id FROM rncs) OR email='admin'",(hash_password('verificacao-local'),))
    rnc=conn.execute('SELECT * FROM rncs ORDER BY id LIMIT 1').fetchone()
    reviewer=conn.execute('SELECT email FROM usuarios WHERE id=?',(rnc['encerramento_aprovador_id'],)).fetchone()[0]
    rid=rnc['id'];eid=rnc['empresa_id'];issue_id=rnc['issue_id'];approver=rnc['encerramento_aprovador_id']
    conn.execute("UPDATE rncs SET status='emitida',encerramento_aprovado_em=NULL,encerramento_aprovado_por_id=NULL WHERE id=?",(rid,))
    conn.execute("UPDATE acoes SET status='backlog' WHERE rnc_id=?",(rid,))
base='http://127.0.0.1:8765'
log=open(folder/'server.log','w',encoding='utf-8')
process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765'],cwd=root,env=os.environ.copy(),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
    for attempt in range(60):
        try:
            if httpx.get(base+'/openapi.json',timeout=1).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(.2)
    with httpx.Client(base_url=base,timeout=10) as client:
        assert client.post('/api/auth/login',json={'email':'admin','senha':'verificacao-local'}).status_code==200
        body={'confirmar':True,'encerramento_aprovador_id':approver,'encerramento_conclusao':'','licoes_aprendidas':''}
        response=client.post(f'/api/rncs/{rid}/encerrar',json=body)
        print('Admin global com aprovador da empresa:',response.status_code,response.json().get('detail','concluída'))
        assert response.status_code==200,response.text
        assert response.json()['rnc_encerramento_aprovador_id']==approver
        assert response.json()['rnc_encerramento_aprovado_por_id']!=approver
        client.post('/api/auth/logout')
        assert client.post('/api/auth/login',json={'email':reviewer,'senha':'verificacao-local'}).status_code==200
        response=client.post(f'/api/rncs/{rid}/encerrar',json=body)
        assert response.status_code==200,response.text
        assert response.json()['rnc_status']=='concluida'
        cards=client.get('/api/issues/kanban',params={'empresa_id':eid}).json()
        own=[a for a in cards if a['rnc_id']==rid]
        assert own and all(a['status']=='finalizada' for a in own)
        print('Após encerramento HTTP:',[(a['id'],a['status'],a['rnc_status']) for a in own])
        assert client.put(f'/api/rncs/{rid}',json={'resumo':'bloqueio'}).status_code==409
        assert client.put(f"/api/issues/{issue_id}/acoes/{own[0]['id']}/status",json={'status':'backlog'}).status_code==409
        response=client.post(f'/api/rncs/{rid}/reabrir',json={'confirmar':True,'motivo':'Verificação em cópia temporária'})
        assert response.status_code==200,response.text
        assert response.json()['acoes'] and all(a['status']=='em_andamento' for a in response.json()['acoes'])
        reopened_cards=client.get('/api/issues/kanban',params={'empresa_id':eid}).json()
        assert all(a['status']=='em_andamento' for a in reopened_cards if a['rnc_id']==rid)
        print('Após reativação HTTP: cartões em em_andamento')
        assert client.put(f'/api/rncs/{rid}',json={'resumo':'Reaberta'}).status_code==200
        assert client.put(f"/api/issues/{issue_id}/acoes/{own[0]['id']}/status",json={'status':'backlog'}).status_code==200
        print('Bloqueio, reativação e movimentação após reabrir: OK')
    print('Base ativa preservada; teste em cópia temporária.')
finally:
    process.terminate();process.wait(timeout=10);log.close()
