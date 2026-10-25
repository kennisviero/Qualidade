"""Popula um exemplo didático do módulo Requisitos e Normas na base ativa.

Cria, para a empresa alvo (padrão: 4 "Empresa teste"): uma Norma ISO 9001:2015 com
documento controlado (PDM) aprovado, esquema de atributos, requisitos/cláusulas com
prioridade e atributos, relações requisito↔requisito, vínculos a processo/Issue e
avaliações de conformidade (mix conforme/não conforme/não avaliado + lacunas).

Idempotente: ensaio (dry-run) sem argumentos; `--apply` grava após backup. Tudo é
marcado com SIM-REQ para rastreio/remoção. Preserva todo o conteúdo anterior.
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
MARCA = "SIM-REQ-20261024"
APPLY = "--apply" in sys.argv


def now():
    return datetime.now(timezone.utc).isoformat()


REQUISITOS = [
    # (clausula, titulo, categoria, obrigatoriedade, prioridade)
    ("4.1", "Compreensão da organização e do seu contexto", "normativo", "obrigatorio", "should"),
    ("5.1", "Liderança e comprometimento", "normativo", "obrigatorio", "must"),
    ("7.1.5", "Recursos de monitoramento e medição", "normativo", "obrigatorio", "should"),
    ("8.5.1", "Controle da produção e da prestação de serviço", "normativo", "obrigatorio", "must"),
    ("9.2", "Auditoria interna", "normativo", "recomendado", "could"),
    ("10.2", "Não conformidade e ação corretiva", "normativo", "obrigatorio", "must"),
]
ATRIBUTOS = [
    ("risco", "Risco", "lista", ["baixo", "medio", "alto"], 0),
    ("verificacao", "Método de verificação", "texto", [], 0),
]


def run(conn):
    if conn.execute("SELECT id FROM normas WHERE empresa_id=? AND observacoes LIKE ?",
                    (EMPRESA_ID, f"%{MARCA}%")).fetchone():
        return {"status": "ja_populado", "marca": MARCA}
    emp = conn.execute("SELECT razao_social FROM empresas WHERE id=?", (EMPRESA_ID,)).fetchone()
    if emp is None:
        raise SystemExit(f"Empresa {EMPRESA_ID} não encontrada")
    empresa_nome = emp["razao_social"]
    inst = now()

    # 1) Documento controlado (PDM) + aprovação da R1
    doc_id = create_documento_interno(conn, EMPRESA_ID, "ISO 9001:2015 — Sistema de Gestão da Qualidade",
                                      "norma", USER_ID, empresa_nome=empresa_nome)
    rev = conn.execute("SELECT id,numero FROM documento_revisoes WHERE documento_id=? ORDER BY numero", (doc_id,)).fetchone()
    conn.execute("UPDATE documento_revisoes SET estado='aprovada',descricao_mudanca=?,texto_extraido=?,origem_texto='digital',aprovado_por_id=?,aprovacao_em=? WHERE id=?",
                 ("Emissão inicial (demo)", "Texto didático da norma ISO 9001:2015 (" + MARCA + ").", USER_ID, inst, rev["id"]))
    conn.execute("UPDATE documentos_controlados SET estado='aprovado',revisao_atual_id=?,aprovador_id=?,atualizado_em=? WHERE id=?",
                 (rev["id"], USER_ID, inst, doc_id))

    # 2) Norma
    codigo = norma_next_codigo(conn, EMPRESA_ID)
    cur = conn.execute(
        "INSERT INTO normas (empresa_id,codigo,tipo_fonte,titulo,identificador_externo,emissor,edicao_versao,"
        "data_publicacao,data_vigencia,status,escopo,observacoes,documento_id,criado_por_id,criado_em,atualizado_em) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (EMPRESA_ID, codigo, "norma_tecnica", "ISO 9001:2015", "ISO 9001:2015", "ISO", "2015",
         "2015-09-15", "2015-09-15", "vigente", "Sistema de gestão da qualidade — requisitos.",
         f"Exemplo didático ({MARCA})", doc_id, USER_ID, inst, inst))
    norma_id = cur.lastrowid

    # 3) Esquema de atributos (IREB)
    defs = {}
    for ordem, (chave, rotulo, tipo, opcoes, obr) in enumerate(ATRIBUTOS):
        try:
            d = conn.execute(
                "INSERT INTO requisito_atributo_defs (empresa_id,chave,rotulo,tipo,opcoes,obrigatorio,ordem,ativo,criado_em) "
                "VALUES (?,?,?,?,?,?,?,1,?)",
                (EMPRESA_ID, chave, rotulo, tipo, json.dumps(opcoes, ensure_ascii=False), obr, ordem, inst))
            defs[chave] = d.lastrowid
        except sqlite3.IntegrityError:
            defs[chave] = conn.execute("SELECT id FROM requisito_atributo_defs WHERE empresa_id=? AND chave=?", (EMPRESA_ID, chave)).fetchone()["id"]

    # 4) Requisitos
    req_ids = {}
    for ordem, (clausula, titulo, cat, obr, prio) in enumerate(REQUISITOS):
        c = conn.execute(
            "INSERT INTO requisitos (empresa_id,norma_id,codigo_clausula,titulo,texto,categoria,obrigatoriedade,estado,prioridade,ordem,criado_por_id,criado_em,atualizado_em) "
            "VALUES (?,?,?,?,?,?,?,'ativo',?,?,?,?,?)",
            (EMPRESA_ID, norma_id, clausula, titulo, f"Requisito da cláusula {clausula} ({MARCA}).", cat, obr, prio, ordem, USER_ID, inst, inst))
        req_ids[clausula] = c.lastrowid

    # 5) Valores de atributo (em alguns requisitos)
    conn.execute("INSERT INTO requisito_atributo_valores (requisito_id,def_id,valor) VALUES (?,?,?)",
                 (req_ids["8.5.1"], defs["risco"], "alto"))
    conn.execute("INSERT INTO requisito_atributo_valores (requisito_id,def_id,valor) VALUES (?,?,?)",
                 (req_ids["9.2"], defs["verificacao"], "Auditoria interna anual"))

    # 6) Relações requisito↔requisito
    for origem, destino, tipo in [("10.2", "8.5.1", "depende"), ("9.2", "10.2", "refina")]:
        conn.execute(
            "INSERT INTO requisito_relacoes (empresa_id,origem_id,destino_id,tipo,observacao,criado_por_id,criado_em) VALUES (?,?,?,?,?,?,?)",
            (EMPRESA_ID, req_ids[origem], req_ids[destino], tipo, MARCA, USER_ID, inst))

    # 7) Vínculos a processo e Issues reais da empresa
    proc = conn.execute("SELECT id FROM processos WHERE empresa_id=? ORDER BY id LIMIT 1", (EMPRESA_ID,)).fetchone()
    issues = conn.execute("SELECT id FROM issues WHERE empresa_id=? ORDER BY id LIMIT 2", (EMPRESA_ID,)).fetchall()
    vincs = 0
    if proc:
        conn.execute("INSERT INTO requisito_vinculos (empresa_id,requisito_id,alvo_tipo,alvo_id,tipo_relacao,observacao,criado_por_id,criado_em) VALUES (?,?,?,?,?,?,?,?)",
                     (EMPRESA_ID, req_ids["8.5.1"], "processo", proc["id"], "satisfaz", MARCA, USER_ID, inst)); vincs += 1
    if issues:
        conn.execute("INSERT INTO requisito_vinculos (empresa_id,requisito_id,alvo_tipo,alvo_id,tipo_relacao,observacao,criado_por_id,criado_em) VALUES (?,?,?,?,?,?,?,?)",
                     (EMPRESA_ID, req_ids["10.2"], "issue", issues[0]["id"], "verifica", MARCA, USER_ID, inst)); vincs += 1

    # 8) Conformidade (mix conforme / não conforme / não avaliado deixa lacunas)
    for clausula, situacao, evid in [("4.1", "conforme", "Contexto documentado e revisado."),
                                     ("5.1", "conforme", "Política e papéis definidos."),
                                     ("8.5.1", "nao_conforme", "Instrução de trabalho desatualizada."),
                                     ("10.2", "conforme", "Procedimento de ação corretiva em uso.")]:
        conn.execute("INSERT INTO requisito_conformidade (empresa_id,requisito_id,processo_id,situacao,evidencia,responsavel_id,avaliado_em,criado_por_id) VALUES (?,?,?,?,?,?,?,?)",
                     (EMPRESA_ID, req_ids[clausula], None, situacao, evid, USER_ID, inst, USER_ID))

    return {"status": "populado", "empresa_id": EMPRESA_ID, "norma": codigo, "documento_id": doc_id,
            "requisitos": len(req_ids), "atributos_def": len(defs), "relacoes": 2, "vinculos": vincs,
            "conformidade": 4, "marca": MARCA}


def main():
    if not APPLY:
        # Ensaio em memória: carrega a base numa cópia e roda sem gravar nada.
        src = sqlite3.connect(DB_PATH)
        mem = sqlite3.connect(":memory:")
        src.backup(mem); src.close()
        mem.row_factory = sqlite3.Row
        mem.execute("PRAGMA foreign_keys=ON")
        res = run(mem)
        mem.rollback(); mem.close()
        print(json.dumps({"ensaio": True, **res}, ensure_ascii=False))
        print("Ensaio apenas. Rode com --apply para gravar (faz backup antes).")
        return
    # Backup antes de gravar
    folder = DB_PATH.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ("qualidade_antes_demo_requisitos_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".db")
    with sqlite3.connect(DB_PATH) as s, sqlite3.connect(backup) as t:
        s.backup(t)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
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
