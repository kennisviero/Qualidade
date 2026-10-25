"""Exemplo didático de PRODUTO: especificação de um Liquidificador, com requisitos
e atributos preenchidos (valor-alvo, risco, método de verificação).

Idempotente: ensaio (dry-run) sem argumentos; `--apply` grava após backup.
Marca SIM-LIQ para rastreio/remoção. Preserva todo o conteúdo anterior.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

from app.db import DB_PATH
from app.routers.documentos_controlados import create_documento_interno
from app.routers.normas import _next_codigo as norma_next_codigo

EMPRESA_ID = 4
USER_ID = 5
MARCA = "SIM-LIQ-20261024"
APPLY = "--apply" in sys.argv


def now():
    return datetime.now(timezone.utc).isoformat()


# Atributos (schema por empresa). Chaves reaproveitadas se já existirem.
ATRIBUTOS = [
    ("risco", "Risco", "lista", ["baixo", "medio", "alto"], 0),
    ("verificacao", "Método de verificação", "texto", [], 0),
    ("valor_alvo", "Valor-alvo / especificação", "texto", [], 0),
    ("tolerancia", "Tolerância", "texto", [], 0),
]

# (clausula, titulo, categoria, obrigatoriedade, prioridade, {atributos}, conformidade, evidencia)
REQS = [
    ("ESP-1", "Potência do motor", "cliente", "obrigatorio", "must",
     {"valor_alvo": "500 W", "tolerancia": "± 5%", "risco": "alto", "verificacao": "Ensaio de bancada (wattímetro)"},
     "conforme", "Medido 498 W em 3 amostras."),
    ("ESP-2", "Capacidade do copo", "cliente", "obrigatorio", "should",
     {"valor_alvo": "1,5 L", "tolerancia": "± 0,05 L"}, None, None),
    ("ESP-3", "Nível de ruído", "cliente", "recomendado", "should",
     {"valor_alvo": "<= 80 dB(A)", "verificacao": "Medição acústica (NBR)", "risco": "medio"},
     "nao_conforme", "Medido 84 dB(A) na velocidade máxima."),
    ("ESP-4", "Tensão de alimentação", "cliente", "obrigatorio", "must",
     {"valor_alvo": "127/220 V (bivolt)"}, None, None),
    ("ESP-5", "Segurança: trava de tampa (intertravamento)", "legal", "obrigatorio", "must",
     {"risco": "alto", "verificacao": "Inspeção funcional + ensaio de intertravamento", "valor_alvo": "não liga sem tampa"},
     "conforme", "Intertravamento validado conforme norma de segurança."),
    ("ESP-6", "Velocidades", "cliente", "informativo", "could",
     {"valor_alvo": "3 + função pulsar"}, None, None),
]


def _def_ids(conn, inst):
    defs = {}
    for ordem, (chave, rotulo, tipo, opcoes, obr) in enumerate(ATRIBUTOS):
        row = conn.execute("SELECT id FROM requisito_atributo_defs WHERE empresa_id=? AND chave=?", (EMPRESA_ID, chave)).fetchone()
        if row:
            defs[chave] = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO requisito_atributo_defs (empresa_id,chave,rotulo,tipo,opcoes,obrigatorio,ordem,ativo,criado_em) "
                "VALUES (?,?,?,?,?,?,?,1,?)",
                (EMPRESA_ID, chave, rotulo, tipo, json.dumps(opcoes, ensure_ascii=False), obr, ordem, inst))
            defs[chave] = cur.lastrowid
    return defs


def run(conn):
    if conn.execute("SELECT id FROM normas WHERE empresa_id=? AND observacoes LIKE ?",
                    (EMPRESA_ID, f"%{MARCA}%")).fetchone():
        return {"status": "ja_populado", "marca": MARCA}
    emp = conn.execute("SELECT razao_social FROM empresas WHERE id=?", (EMPRESA_ID,)).fetchone()
    if emp is None:
        raise SystemExit(f"Empresa {EMPRESA_ID} não encontrada")
    inst = now()
    defs = _def_ids(conn, inst)

    # Documento controlado (PDM) da especificação do produto
    doc_id = create_documento_interno(conn, EMPRESA_ID, "Especificação do Liquidificador ProMix 500",
                                      "outro", USER_ID, empresa_nome=emp["razao_social"])
    rev = conn.execute("SELECT id FROM documento_revisoes WHERE documento_id=? ORDER BY numero", (doc_id,)).fetchone()
    conn.execute("UPDATE documento_revisoes SET estado='aprovada',descricao_mudanca=?,aprovado_por_id=?,aprovacao_em=? WHERE id=?",
                 ("Especificação inicial do produto (demo)", USER_ID, inst, rev["id"]))
    conn.execute("UPDATE documentos_controlados SET estado='aprovado',revisao_atual_id=?,aprovador_id=?,atualizado_em=? WHERE id=?",
                 (rev["id"], USER_ID, inst, doc_id))

    # Norma/Especificação (fonte: requisito de cliente)
    codigo = norma_next_codigo(conn, EMPRESA_ID)
    cur = conn.execute(
        "INSERT INTO normas (empresa_id,codigo,tipo_fonte,titulo,identificador_externo,emissor,edicao_versao,"
        "data_publicacao,data_vigencia,status,escopo,observacoes,documento_id,criado_por_id,criado_em,atualizado_em) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (EMPRESA_ID, codigo, "requisito_cliente", "Especificação — Liquidificador ProMix 500", "ESP-LIQ-500",
         "Engenharia de Produto", "Rev. A", "", "", "vigente",
         "Requisitos do produto liquidificador (motor, copo, ruído, tensão, segurança).",
         f"Exemplo didático de produto ({MARCA})", doc_id, USER_ID, inst, inst))
    norma_id = cur.lastrowid

    req_ids = {}
    for ordem, (clausula, titulo, cat, obr, prio, atrs, situ, evid) in enumerate(REQS):
        c = conn.execute(
            "INSERT INTO requisitos (empresa_id,norma_id,codigo_clausula,titulo,texto,categoria,obrigatoriedade,estado,prioridade,ordem,criado_por_id,criado_em,atualizado_em) "
            "VALUES (?,?,?,?,?,?,?,'ativo',?,?,?,?,?)",
            (EMPRESA_ID, norma_id, clausula, titulo, f"Requisito de produto do liquidificador ({MARCA}).", cat, obr, prio, ordem, USER_ID, inst, inst))
        rid = c.lastrowid
        req_ids[clausula] = rid
        for chave, valor in atrs.items():
            conn.execute("INSERT INTO requisito_atributo_valores (requisito_id,def_id,valor) VALUES (?,?,?)",
                         (rid, defs[chave], valor))
        if situ:
            conn.execute("INSERT INTO requisito_conformidade (empresa_id,requisito_id,processo_id,situacao,evidencia,responsavel_id,avaliado_em,criado_por_id) VALUES (?,?,?,?,?,?,?,?)",
                         (EMPRESA_ID, rid, None, situ, evid, USER_ID, inst, USER_ID))

    # Relação: ruído depende da potência do motor
    conn.execute("INSERT INTO requisito_relacoes (empresa_id,origem_id,destino_id,tipo,observacao,criado_por_id,criado_em) VALUES (?,?,?,?,?,?,?)",
                 (EMPRESA_ID, req_ids["ESP-3"], req_ids["ESP-1"], "depende", MARCA, USER_ID, inst))

    # Vínculo de rastreabilidade: segurança -> um processo real da empresa
    proc = conn.execute("SELECT id FROM processos WHERE empresa_id=? ORDER BY id LIMIT 1", (EMPRESA_ID,)).fetchone()
    vincs = 0
    if proc:
        conn.execute("INSERT INTO requisito_vinculos (empresa_id,requisito_id,alvo_tipo,alvo_id,tipo_relacao,observacao,criado_por_id,criado_em) VALUES (?,?,?,?,?,?,?,?)",
                     (EMPRESA_ID, req_ids["ESP-5"], "processo", proc["id"], "satisfaz", MARCA, USER_ID, inst)); vincs += 1

    return {"status": "populado", "empresa_id": EMPRESA_ID, "norma": codigo, "documento_id": doc_id,
            "requisitos": len(req_ids), "atributos_def": len(defs), "conformidade": 3, "relacoes": 1,
            "vinculos": vincs, "marca": MARCA}


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
    backup = folder / ("qualidade_antes_demo_liquidificador_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".db")
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
