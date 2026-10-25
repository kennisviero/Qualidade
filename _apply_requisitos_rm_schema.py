"""Fase A IREB: tabelas de atributos/relações + colunas `requisitos.prioridade` e
`requisito_vinculos.tipo_relacao`, com backup e preservação total do conteúdo anterior.

Requer PDM, Normas, Requisitos e Conformidade já aplicados. Uso autorizado em base ativa.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.requisitos import DDL

NOVAS = ("requisito_atributo_defs", "requisito_atributo_valores", "requisito_relacoes")
ALTERADAS = ("requisitos", "requisito_vinculos")  # ganham coluna (conteúdo preservado, schema muda)

with sqlite3.connect(DB_PATH) as conn:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
              if r[0] not in NOVAS and r[0] not in ALTERADAS]
    def state():
        return {t: conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before = state()
    folder = DB_PATH.parent/'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder/('qualidade_antes_requisitos_rm_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(DDL)  # cria as 3 tabelas novas (IF NOT EXISTS)
    reqcols = [r[1] for r in conn.execute("PRAGMA table_info(requisitos)")]
    if 'prioridade' not in reqcols:
        conn.execute("ALTER TABLE requisitos ADD COLUMN prioridade TEXT DEFAULT ''")
    vcols = [r[1] for r in conn.execute("PRAGMA table_info(requisito_vinculos)")]
    if 'tipo_relacao' not in vcols:
        conn.execute("ALTER TABLE requisito_vinculos ADD COLUMN tipo_relacao TEXT DEFAULT 'satisfaz'")
    assert state() == before, 'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    # nenhuma linha perdida nas tabelas alteradas
    reqn = conn.execute('SELECT count(*) FROM requisitos').fetchone()[0]
    vn = conn.execute('SELECT count(*) FROM requisito_vinculos').fetchone()[0]
    print(json.dumps({'backup': str(backup), 'tabelas_preservadas': len(tables),
        'requisitos': reqn, 'requisito_vinculos': vn,
        'prioridade_ok': 'prioridade' in [r[1] for r in conn.execute('PRAGMA table_info(requisitos)')],
        'tipo_relacao_ok': 'tipo_relacao' in [r[1] for r in conn.execute('PRAGMA table_info(requisito_vinculos)')],
        'integridade': 'ok'}, ensure_ascii=False))
