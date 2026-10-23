"""Aplica apenas a tabela aditiva de Afinidades, com backup e preservação verificada."""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.afinidades import DDL

with sqlite3.connect(DB_PATH) as conn:
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'afinidades'")]
    def state():
        # Conteúdo serializado em memória, sem expor dados ou credenciais.
        return {t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before=state()
    folder=DB_PATH.parent/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/('qualidade_antes_afinidades_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)
    assert state()==before,'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup':str(backup),'tabelas_preservadas':len(tables),'issues':len(before.get('issues',[])),'rncs':len(before.get('rncs',[])),'integridade':'ok'},ensure_ascii=False))
