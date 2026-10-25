"""Adiciona a tabela `normas` com backup e preservação total das linhas anteriores.

Requer o schema do PDM já aplicado (FK `normas.documento_id` → documentos_controlados).
Uso autorizado em base ativa: backup em data/backups + DDL aditivo + verificação.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.normas import DDL

with sqlite3.connect(DB_PATH) as conn:
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'normas'")]
    def state():
        return {t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before=state()
    folder=DB_PATH.parent/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/('qualidade_antes_normas_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)
    assert state()==before,'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup':str(backup),'tabelas_preservadas':len(tables),
        'issues':len(before.get('issues',[])),'rncs':len(before.get('rncs',[])),
        'normas':conn.execute('SELECT count(*) FROM normas').fetchone()[0],'integridade':'ok'},ensure_ascii=False))
