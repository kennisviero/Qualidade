"""Backfill: justificativa (por que o requisito existe) vazia recebe o racional
padrão 'Requisito decorrente da norma {X}', já que todo requisito nasce de uma norma.
Com backup e preservação das demais tabelas. Idempotente (só toca justificativa vazia)."""
import json
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    outras = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
              if r[0] != "requisitos"]

    def state():
        return {t: conn.execute('SELECT * FROM "' + t.replace('"', '""') + '" ORDER BY rowid').fetchall() for t in outras}

    before = state()
    total = conn.execute("SELECT count(*) FROM requisitos").fetchone()[0]
    vazias = conn.execute("SELECT count(*) FROM requisitos WHERE COALESCE(justificativa,'')=''").fetchone()[0]
    folder = DB_PATH.parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('qualidade_antes_justif_backfill_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    conn.execute(
        "UPDATE requisitos SET justificativa = ("
        "  SELECT 'Requisito decorrente da norma ' || "
        "    CASE WHEN COALESCE(n.identificador_externo,'')<>'' THEN n.identificador_externo ELSE n.titulo END"
        "  FROM normas n WHERE n.id = requisitos.norma_id) "
        "WHERE COALESCE(justificativa,'') = '' "
        "  AND EXISTS (SELECT 1 FROM normas n WHERE n.id = requisitos.norma_id)"
    )
    assert state() == before, 'Conteúdo de outras tabelas alterado'
    assert conn.execute("SELECT count(*) FROM requisitos").fetchone()[0] == total, 'Linhas de requisitos perdidas'
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    restantes = conn.execute("SELECT count(*) FROM requisitos WHERE COALESCE(justificativa,'')=''").fetchone()[0]
    print(json.dumps({'backup': str(backup), 'requisitos': total, 'justif_vazia_antes': vazias,
                      'justif_vazia_depois': restantes, 'integridade': 'ok'}, ensure_ascii=False))
