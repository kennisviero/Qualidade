"""Cria classes para as normas existentes e encaixa os requisitos nelas.
- ISO 9001: capítulos 4..10; requisito vai pela parte inteira da cláusula (8.5.1 -> cap 8).
- Especificação de produto (cláusulas ESP-*): classes temáticas por palavra-chave do título.
Idempotente (não duplica classes nem reatribui requisito já classificado). Com backup."""
import json
import re
import sqlite3
from datetime import datetime, timezone
from app.db import DB_PATH

ISO_CAPS = {"4": "Contexto da organização", "5": "Liderança", "6": "Planejamento",
            "7": "Apoio", "8": "Operação", "9": "Avaliação de desempenho", "10": "Melhoria"}
ESP_CLASSES = [("DES", "Desempenho"), ("ELE", "Elétrica"), ("SEG", "Segurança"), ("ACU", "Acústica"), ("GER", "Geral")]


def esp_classe(titulo):
    t = (titulo or "").lower()
    if any(k in t for k in ("potência", "potencia", "capacidade", "velocidade")):
        return "Desempenho"
    if any(k in t for k in ("tensão", "tensao", "alimentação", "alimentacao", "127", "220", "elétr", "eletr")):
        return "Elétrica"
    if any(k in t for k in ("segurança", "seguranca", "trava", "intertrav")):
        return "Segurança"
    if any(k in t for k in ("ruído", "ruido", "acúst", "acust", "som")):
        return "Acústica"
    return "Geral"


now = datetime.now(timezone.utc).isoformat()
with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    # backup
    folder = DB_PATH.parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('qualidade_antes_classes_demo_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.db')
    with sqlite3.connect(backup) as target:
        conn.backup(target)

    reqn_before = conn.execute("SELECT count(*) FROM requisitos").fetchone()[0]
    criadas = atribuidos = 0

    def ensure_classe(empresa_id, norma_id, codigo, nome, ordem):
        global criadas
        row = conn.execute("SELECT id FROM requisito_classes WHERE norma_id=? AND nome=?", (norma_id, nome)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO requisito_classes (empresa_id,norma_id,codigo,nome,ordem,criado_em) VALUES (?,?,?,?,?,?)",
            (empresa_id, norma_id, codigo, nome, ordem, now))
        criadas += 1
        return cur.lastrowid

    for n in conn.execute("SELECT id,empresa_id,codigo,titulo,identificador_externo FROM normas").fetchall():
        reqs = conn.execute("SELECT id,codigo_clausula,titulo,classe_id FROM requisitos WHERE norma_id=?", (n["id"],)).fetchall()
        if not reqs:
            continue
        ident = (n["identificador_externo"] or "")
        is_iso = ident.upper().startswith("ISO 9001") or "9001" in ident
        if is_iso:
            # cria os capítulos presentes entre os requisitos
            prefixos = []
            for r in reqs:
                m = re.match(r"\s*(\d+)", r["codigo_clausula"] or "")
                if m and m.group(1) not in prefixos:
                    prefixos.append(m.group(1))
            ids = {}
            for p in sorted(prefixos, key=lambda x: int(x)):
                ids[p] = ensure_classe(n["empresa_id"], n["id"], p, ISO_CAPS.get(p, f"Capítulo {p}"), int(p))
            for r in reqs:
                if r["classe_id"] is not None:
                    continue
                m = re.match(r"\s*(\d+)", r["codigo_clausula"] or "")
                cid = ids.get(m.group(1)) if m else None
                if cid:
                    conn.execute("UPDATE requisitos SET classe_id=? WHERE id=?", (cid, r["id"]))
                    atribuidos += 1
        else:
            nome_por_id = {}
            for i, (cod, nome) in enumerate(ESP_CLASSES, start=1):
                nome_por_id[nome] = ensure_classe(n["empresa_id"], n["id"], cod, nome, i)
            for r in reqs:
                if r["classe_id"] is not None:
                    continue
                cid = nome_por_id[esp_classe(r["titulo"])]
                conn.execute("UPDATE requisitos SET classe_id=? WHERE id=?", (cid, r["id"]))
                atribuidos += 1

    # remove classes ESP vazias (ex.: 'Geral' sem requisito) para não poluir
    conn.execute("DELETE FROM requisito_classes WHERE id NOT IN (SELECT DISTINCT classe_id FROM requisitos WHERE classe_id IS NOT NULL)")
    assert conn.execute("SELECT count(*) FROM requisitos").fetchone()[0] == reqn_before, 'Linhas de requisitos perdidas'
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    total_classes = conn.execute("SELECT count(*) FROM requisito_classes").fetchone()[0]
    sem_classe = conn.execute("SELECT count(*) FROM requisitos WHERE classe_id IS NULL").fetchone()[0]
    print(json.dumps({'backup': str(backup), 'classes_criadas': criadas, 'requisitos_atribuidos': atribuidos,
                      'total_classes': total_classes, 'requisitos_sem_classe': sem_classe, 'integridade': 'ok'}, ensure_ascii=False))
