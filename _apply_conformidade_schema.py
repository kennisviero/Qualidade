"""Adiciona `requisito_vinculos` e `requisito_conformidade` com backup e preservação total.

Requer PDM, Normas e Requisitos já aplicados. Uso autorizado em base ativa.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.conformidade import DDL

with sqlite3.connect(DB_PATH) as conn:
    novas = ('requisito_vinculos', 'requisito_conformidade')
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") if r[0] not in novas]
    def state():
        return {t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before=state()
    folder=DB_PATH.parent/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/('qualidade_antes_conformidade_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)
    assert state()==before,'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup':str(backup),'tabelas_preservadas':len(tables),
        'requisito_vinculos':conn.execute('SELECT count(*) FROM requisito_vinculos').fetchone()[0],
        'requisito_conformidade':conn.execute('SELECT count(*) FROM requisito_conformidade').fetchone()[0],
        'integridade':'ok'},ensure_ascii=False))
