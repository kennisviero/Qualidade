"""Change request + impacto econômico: tabela `requisito_mudancas` e colunas
`custo_atual`/`custo_projetado`/`volume` em `requisitos`. Backup + preservação total.

Requer o schema de Requisitos já aplicado. Uso autorizado em base ativa.
"""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.requisitos import DDL

with sqlite3.connect(DB_PATH) as conn:
    novas = ("requisito_mudancas", "requisito_versoes")
    alteradas = ("requisitos",)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
              if r[0] not in novas and r[0] not in alteradas]
    def state():
        return {t: conn.execute('SELECT * FROM "'+t.replace('"','""')+'" ORDER BY rowid').fetchall() for t in tables}
    before = state()
    folder = DB_PATH.parent/'backups'; folder.mkdir(parents=True, exist_ok=True)
    backup = folder/('qualidade_antes_mud_impacto_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.db')
    with sqlite3.connect(backup) as t:
        conn.backup(t)
    conn.executescript(DDL)  # cria requisito_mudancas e requisito_versoes (IF NOT EXISTS)
    rcols = [r[1] for r in conn.execute("PRAGMA table_info(requisitos)")]
    for col in ("custo_atual", "custo_projetado", "volume"):
        if col not in rcols:
            conn.execute(f"ALTER TABLE requisitos ADD COLUMN {col} REAL")
    if "variante" not in rcols:
        conn.execute("ALTER TABLE requisitos ADD COLUMN variante TEXT DEFAULT ''")
    assert state() == before, 'Conteúdo anterior alterado'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    print(json.dumps({'backup': str(backup), 'tabelas_preservadas': len(tables),
        'requisito_mudancas': conn.execute('SELECT count(*) FROM requisito_mudancas').fetchone()[0],
        'colunas_custo': [c for c in ('custo_atual','custo_projetado','volume') if c in [r[1] for r in conn.execute('PRAGMA table_info(requisitos)')]],
        'integridade': 'ok'}, ensure_ascii=False))
