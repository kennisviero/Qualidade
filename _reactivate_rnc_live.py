"""Reativa a RNC-2026-001 no servidor ativo após backup SQLite."""
import sqlite3,time
from datetime import datetime,timezone
import httpx
from app.db import DB_PATH,get_connection

base='http://127.0.0.1:8000'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
with get_connection() as conn:
    row=conn.execute("SELECT id,codigo,status FROM rncs WHERE codigo='RNC-2026-001'").fetchone()
    assert row is not None
    rid=row['id']
    session=conn.execute("SELECT s.token FROM sessions s JOIN usuarios u ON u.id=s.user_id WHERE u.papel='admin' AND u.empresa_id IS NULL AND u.ativo=1 AND s.expira_em>? ORDER BY s.criado_em DESC LIMIT 1",(datetime.now(timezone.utc).isoformat(),)).fetchone()
    assert session is not None,'Não há sessão administrativa vigente para verificar a reativação'
    token=session['token']
with httpx.Client(base_url=base,timeout=20) as client:
    for attempt in range(40):
        try:
            schema=client.get('/openapi.json').json()['components']['schemas']['ReaberturaIn']
            if 'motivo' not in schema.get('required',[]):break
        except (httpx.HTTPError,KeyError,ValueError):pass
        time.sleep(.25)
    assert 'motivo' not in schema.get('required',[]),'Servidor ainda executa a validação antiga da reativação'
    client.cookies.set('session',token)
    me=client.get('/api/auth/me');assert me.status_code==200,me.text
    detail=client.get(f'/api/rncs/{rid}');assert detail.status_code==200,detail.text
    before=detail.json();print('Antes:',before['rnc_status'],[(a['id'],a['status']) for a in before['acoes']])
    if before['rnc_status'] in ('concluida','fechada'):
        folder=DB_PATH.parent/'backups';folder.mkdir(parents=True,exist_ok=True)
        backup=folder/f'qualidade_antes_reativacao_rnc_{stamp}.db'
        with sqlite3.connect(DB_PATH) as source,sqlite3.connect(backup) as target:source.backup(target)
        print('Backup:',backup)
        response=client.post(f'/api/rncs/{rid}/reabrir',json={'confirmar':True})
        assert response.status_code==200,response.text
    result=client.get(f'/api/rncs/{rid}');assert result.status_code==200,result.text
    record=result.json();assert record['rnc_status']=='reaberta',record['rnc_status']
    assert record['acoes'] and all(a['status']=='em_andamento' for a in record['acoes'])
    cards=client.get('/api/issues/kanban',params={'empresa_id':record['rnc_empresa_id']}).json()
    own=[a for a in cards if a['rnc_id']==rid]
    assert own and all(a['status']=='em_andamento' and a['rnc_status']=='reaberta' for a in own)
    print('Depois:',record['rnc_status'],[(a['id'],a['status'],a['rnc_status']) for a in own])
    with get_connection() as conn:
        print('Gravação na base:',dict(conn.execute('SELECT id,status FROM rncs WHERE id=?',(rid,)).fetchone()),[dict(a) for a in conn.execute('SELECT id,status FROM acoes WHERE rnc_id=?',(rid,))])
