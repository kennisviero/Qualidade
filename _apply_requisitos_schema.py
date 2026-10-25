"""Adiciona a tabela `requisitos` e a coluna `documento_revisoes.variante` com backup e preservação total.

Requer PDM e Normas já aplicados. Uso autorizado em base ativa.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.requisitos import DDL

with sqlite3.connect(DB_PATH) as conn:
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'requisitos'")]
    def state():
        return {t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before=state()
    folder=DB_PATH.parent/'backups'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/('qualidade_antes_requisitos_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)
    revcols=[r[1] for r in conn.execute("PRAGMA table_info(documento_revisoes)")]
    if revcols and 'variante' not in revcols:
        conn.execute("ALTER TABLE documento_revisoes ADD COLUMN variante TEXT DEFAULT ''")
    # a adição de coluna altera o schema de documento_revisoes; conteúdo preservado (valores default '').
    before.pop('documento_revisoes', None)
    after={t:conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables if t!='documento_revisoes'}
    assert after==before,'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup':str(backup),'tabelas_preservadas':len(tables),
        'requisitos':conn.execute('SELECT count(*) FROM requisitos').fetchone()[0],
        'variante_adicionada':'variante' in [r[1] for r in conn.execute('PRAGMA table_info(documento_revisoes)')],
        'integridade':'ok'},ensure_ascii=False))
