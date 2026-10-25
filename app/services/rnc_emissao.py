import json
from fastapi import HTTPException


def emitir_rnc_transacao(conn, issue_id, body, user):
    # Imports locais evitam ciclo; mesmas regras do endpoint original.
    from app.routers.issues import (
        RNC_CRITICIDADES, RNC_ORIGENS, RNC_DISPOSICOES, RNC_METODOLOGIAS,
        now, fetch_issue, _validar_cadastro_inicial, IssueUpdate,
        _validar_usuario_empresa, _next_rnc_codigo,
    )
    if body.criticidade and body.criticidade not in RNC_CRITICIDADES:
        raise HTTPException(status_code=422, detail="Classificacao da RNC invalida")
    if body.origem_gatilho and body.origem_gatilho not in RNC_ORIGENS:
        raise HTTPException(status_code=422, detail="Origem do gatilho da RNC invalida")
    if body.disposicao_inicial and body.disposicao_inicial not in RNC_DISPOSICOES:
        raise HTTPException(status_code=422, detail="Disposicao inicial invalida")
    if body.metodologia and body.metodologia not in RNC_METODOLOGIAS:
        raise HTTPException(status_code=422, detail="Metodologia de analise invalida")
    equipe = list(dict.fromkeys(body.equipe_investigacao or []))
    emitida_em = now()
    row = fetch_issue(conn, issue_id, user)
    if conn.execute("SELECT id FROM rncs WHERE issue_id = ?", (issue_id,)).fetchone():
        raise HTTPException(status_code=409, detail="A RNC desta Issue ja foi emitida")
    _validar_cadastro_inicial(IssueUpdate(), conn, row["empresa_id"], row)
    for campo, user_id in (
        ("Lider da investigacao", body.lider_investigacao_id),
        ("Responsavel pela contencao", body.contencao_responsavel_id),
        ("Auditor da eficacia", body.auditor_eficacia_id),
    ):
        _validar_usuario_empresa(conn, user_id, row["empresa_id"], campo)
    for user_id in equipe:
        _validar_usuario_empresa(conn, user_id, row["empresa_id"], "Membro da equipe de investigacao")
    rnc_codigo = _next_rnc_codigo(conn, row["empresa_id"])
    values = body.model_dump()
    values["equipe_investigacao"] = json.dumps(equipe)
    for field, value in values.items():
        if isinstance(value, str):
            values[field] = value.strip()
    values.update(issue_id=issue_id, empresa_id=row["empresa_id"], codigo=rnc_codigo,
                  emitida_por_id=user["id"], emitida_em=emitida_em)
    from app.services.rnc_schema import facts
    values.update(fatos_snapshot_json=json.dumps(facts(row),ensure_ascii=False),
                  metodologias_json=json.dumps([body.metodologia] if body.metodologia else []),
                  impacto=row['impacto'] or '',ambiente=row['ambiente'] or '',
                  fatos_preservados_em=emitida_em,fatos_snapshot_origem='emissao',atualizado_em=emitida_em,
                  acao_contencao_imediata=row['acao_emergencial'] or '',
                  emitente_id=user['id'] if user['empresa_id']==row['empresa_id'] else None)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO rncs ({columns}) VALUES ({placeholders})", tuple(values.values()))
    rnc_id=conn.execute('SELECT id FROM rncs WHERE issue_id=?',(issue_id,)).fetchone()[0]
    # Copia os vínculos de requisito/norma da Issue para a RNC (mesma transação).
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='requisito_vinculos'").fetchone():
        conn.execute(
            "INSERT OR IGNORE INTO requisito_vinculos "
            "(empresa_id, requisito_id, alvo_tipo, alvo_id, tipo_relacao, observacao, criado_por_id, criado_em) "
            "SELECT empresa_id, requisito_id, 'rnc', ?, tipo_relacao, observacao, ?, ? "
            "FROM requisito_vinculos WHERE alvo_tipo='issue' AND alvo_id=?",
            (rnc_id, user["id"], emitida_em, issue_id),
        )
    conn.execute(
        "INSERT INTO acoes (issue_id, descricao, responsavel_id, prazo_limite, status, ordem, rnc_id) "
        "VALUES (?, ?, ?, ?, 'backlog', ?, ?)",
        (issue_id, f"Tratar {rnc_codigo}: {row['comportamento_observado'] or row['codigo']}",
         body.lider_investigacao_id, body.prazo_analise,
         conn.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM acoes WHERE issue_id=?", (issue_id,)).fetchone()[0],rnc_id),
    )
    conn.execute("UPDATE issues SET status = 'fechada', finalizado_em = COALESCE(finalizado_em, ?), "
                 "finalizado_por_id = COALESCE(finalizado_por_id, ?), atualizado_em = ? WHERE id = ?",
                 (emitida_em, user["id"], emitida_em, issue_id))
    return dict(conn.execute("SELECT * FROM rncs WHERE issue_id=?", (issue_id,)).fetchone())
