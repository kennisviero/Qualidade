"""Exemplo didático de versionamento + variantes nos requisitos do Liquidificador.

- Registra versões (R01 manual, R02 por mudança aprovada) em alguns requisitos.
- Cria variantes de tensão (127 V / 220 V) ligadas ao requisito base ESP-4.

Idempotente: ensaio (dry-run) sem argumentos; `--apply` grava após backup. Marca SIM-VER.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

from app.db import DB_PATH
from app.routers.requisitos import _snapshot_requisito

EMPRESA_ID = 4
USER_ID = 5
MARCA = "SIM-VER-20261024"
APPLY = "--apply" in sys.argv


def now():
    return datetime.now(timezone.utc).isoformat()


def run(conn):
    norma = conn.execute(
        "SELECT id FROM normas WHERE empresa_id=? AND (identificador_externo='ESP-LIQ-500' OR codigo='NORMA-0002') ORDER BY id LIMIT 1",
        (EMPRESA_ID,)).fetchone()
    if norma is None:
        raise SystemExit("Norma do liquidificador não encontrada (rode _popular_liquidificador_demo.py --apply antes).")
    norma_id = norma["id"]
    if conn.execute("SELECT 1 FROM requisito_versoes v JOIN requisitos r ON r.id=v.requisito_id WHERE r.empresa_id=? AND r.norma_id=?",
                    (EMPRESA_ID, norma_id)).fetchone():
        return {"status": "ja_populado", "marca": MARCA}
    reqs = {r["codigo_clausula"]: r["id"] for r in conn.execute(
        "SELECT id,codigo_clausula FROM requisitos WHERE empresa_id=? AND norma_id=?", (EMPRESA_ID, norma_id)).fetchall()}
    inst = now()
    versoes = 0
    # Versões em ESP-1 e ESP-3: R01 manual + R02 por mudança aprovada
    for clausula, desc in [("ESP-1", "Ajuste do valor-alvo de potência após ensaio"),
                           ("ESP-3", "Revisão do limite de ruído")]:
        rid = reqs.get(clausula)
        if not rid:
            continue
        _snapshot_requisito(conn, rid, "manual", USER_ID); versoes += 1
        cur = conn.execute(
            "INSERT INTO requisito_mudancas (empresa_id,requisito_id,descricao,situacao,solicitante_id,aprovador_id,decisao_obs,criado_em,decidido_em) "
            "VALUES (?,?,?,'aprovada',?,?,?,?,?)",
            (EMPRESA_ID, rid, f"{desc} ({MARCA})", USER_ID, USER_ID, "Aprovado (demo)", inst, inst))
        _snapshot_requisito(conn, rid, f"mudanca:{cur.lastrowid}", USER_ID); versoes += 1

    # Variantes de tensão ligadas ao ESP-4
    variantes = 0
    base = reqs.get("ESP-4")
    if base:
        for clausula, titulo, var in [("ESP-4a", "Tensão de alimentação 127 V", "127 V"),
                                      ("ESP-4b", "Tensão de alimentação 220 V", "220 V")]:
            if clausula in reqs:
                continue
            c = conn.execute(
                "INSERT INTO requisitos (empresa_id,norma_id,codigo_clausula,titulo,texto,categoria,obrigatoriedade,estado,prioridade,variante,ordem,criado_por_id,criado_em,atualizado_em) "
                "VALUES (?,?,?,?,?,'cliente','obrigatorio','ativo','must',?,?,?,?,?)",
                (EMPRESA_ID, norma_id, clausula, titulo, f"Variante de tensão ({MARCA}).", var, 90 + variantes, USER_ID, inst, inst))
            conn.execute(
                "INSERT INTO requisito_relacoes (empresa_id,origem_id,destino_id,tipo,observacao,criado_por_id,criado_em) VALUES (?,?,?,'variante_de',?,?,?)",
                (EMPRESA_ID, c.lastrowid, base, MARCA, USER_ID, inst))
            variantes += 1

    return {"status": "populado", "norma_id": norma_id, "versoes": versoes, "variantes": variantes, "marca": MARCA}


def main():
    if not APPLY:
        src = sqlite3.connect(DB_PATH); mem = sqlite3.connect(":memory:")
        src.backup(mem); src.close()
        mem.row_factory = sqlite3.Row; mem.execute("PRAGMA foreign_keys=ON")
        res = run(mem); mem.rollback(); mem.close()
        print(json.dumps({"ensaio": True, **res}, ensure_ascii=False))
        print("Ensaio apenas. Rode com --apply para gravar (faz backup antes).")
        return
    folder = DB_PATH.parent / "backups"; folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ("qualidade_antes_demo_versoes_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".db")
    with sqlite3.connect(DB_PATH) as s, sqlite3.connect(backup) as t:
        s.backup(t)
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON")
    try:
        res = run(conn)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.commit()
    except Exception:
        conn.rollback(); conn.close(); raise
    conn.close()
    print(json.dumps({"ensaio": False, "backup": str(backup), **res}, ensure_ascii=False))


if __name__ == "__main__":
    main()
