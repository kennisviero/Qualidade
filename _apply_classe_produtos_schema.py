"""Cria as tabelas de Classe de requisito e de Produto (Família/Grupo/Produto) +
coluna requisitos.classe_id, com backup e preservação total do conteúdo anterior.
Aditivo e idempotente. Uso autorizado em base ativa."""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH
from app.routers.produtos import DDL as PROD_DDL
from app.routers.requisitos import CLASSES_DDL

NOVAS = ("requisito_classes", "produto_familias", "produto_grupos", "produtos")
ALTERADAS = ("requisitos",)

with sqlite3.connect(DB_PATH) as conn:
    existentes = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    preservar = [t for t in existentes if t not in NOVAS and t not in ALTERADAS]

    def state():
        return {t: conn.execute('SELECT * FROM "' + t.replace('"', '""') + '" ORDER BY rowid').fetchall() for t in preservar}

    before = state()
    reqn = conn.execute("SELECT count(*) FROM requisitos").fetchone()[0]
    folder = DB_PATH.parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('qualidade_antes_classe_produtos_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.executescript(CLASSES_DDL)
    conn.executescript(PROD_DDL)
    reqcols = [r[1] for r in conn.execute("PRAGMA table_info(requisitos)")]
    if "classe_id" not in reqcols:
        conn.execute("ALTER TABLE requisitos ADD COLUMN classe_id INTEGER REFERENCES requisito_classes(id)")
    assert state() == before, 'Conteúdo anterior alterado'
    assert conn.execute("SELECT count(*) FROM requisitos").fetchone()[0] == reqn, 'Linhas de requisitos perdidas'
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    final = [r[1] for r in conn.execute("PRAGMA table_info(requisitos)")]
    tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    print(json.dumps({'backup': str(backup), 'tabelas_preservadas': len(preservar), 'requisitos': reqn,
                      'classe_id_ok': 'classe_id' in final,
                      'tabelas_novas_ok': all(t in tabelas for t in NOVAS), 'integridade': 'ok'}, ensure_ascii=False))
