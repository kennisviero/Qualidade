"""Adiciona as tabelas do PDM (documentos controlados) com backup e preservação total.

Uso autorizado em base ativa: cria backup em data/backups e aplica o DDL aditivo,
verificando que nenhum conteúdo anterior mudou e a integridade/FKs continuam ok.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.documentos_controlados import DDL

with sqlite3.connect(DB_PATH) as conn:
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('documentos_controlados','documento_revisoes','documento_auditoria')")]
    def state():
        return {t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before=state()
    folder=DB_PATH.parent/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/('qualidade_antes_pdm_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)
    assert state()==before,'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup':str(backup),'tabelas_preservadas':len(tables),
        'issues':len(before.get('issues',[])),'rncs':len(before.get('rncs',[])),'acoes':len(before.get('acoes',[])),
        'documentos_controlados':conn.execute('SELECT count(*) FROM documentos_controlados').fetchone()[0],
        'integridade':'ok'},ensure_ascii=False))
