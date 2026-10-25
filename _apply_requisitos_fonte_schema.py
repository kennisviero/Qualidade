"""Item 1 (Grady §2.2.2 rastreabilidade vertical): colunas `requisitos.fonte` e
`requisitos.justificativa` (rationale), com backup e preservação total do conteúdo.

Aditivo e idempotente. Uso autorizado em base ativa.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH

ALTERADAS = ("requisitos",)  # ganha colunas (conteúdo preservado, schema muda)

with sqlite3.connect(DB_PATH) as conn:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
              if r[0] not in ALTERADAS]

    def state():
        return {t: conn.execute('SELECT * FROM "' + t.replace('"', '""') + '" ORDER BY rowid').fetchall() for t in tables}

    before = state()
    reqn_before = conn.execute('SELECT count(*) FROM requisitos').fetchone()[0]
    folder = DB_PATH.parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('qualidade_antes_requisitos_fonte_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    reqcols = [r[1] for r in conn.execute("PRAGMA table_info(requisitos)")]
    for c in ('fonte', 'justificativa'):
        if c not in reqcols:
            conn.execute(f"ALTER TABLE requisitos ADD COLUMN {c} TEXT DEFAULT ''")
    assert state() == before, 'Conteúdo anterior alterado'
    assert conn.execute('SELECT count(*) FROM requisitos').fetchone()[0] == reqn_before, 'Linhas de requisitos perdidas'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    final = [r[1] for r in conn.execute('PRAGMA table_info(requisitos)')]
    print(json.dumps({'backup': str(backup), 'tabelas_preservadas': len(tables),
                      'requisitos': reqn_before,
                      'fonte_ok': 'fonte' in final, 'justificativa_ok': 'justificativa' in final,
                      'integridade': 'ok'}, ensure_ascii=False))
