import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa, criar_issue
from tests.test_pdm import _empresa_com_editor, _novo_usuario


def _norma_req(c, titulo="Norma RM"):
    n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": titulo, "criar_documento": False}).json()
    r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req", "codigo_clausula": "4.1"}).json()
    return n, r


def test_prioridade_moscow():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, _ = _norma_req(c)
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Crit", "prioridade": "must"}).json()
        assert r["prioridade"] == "must"
        assert c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "X", "prioridade": "xxx"}).status_code == 422
        assert len(c.get(f"/api/requisitos?norma_id={n['id']}&prioridade=must").json()) == 1


def test_atributo_schema_e_valores():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        n, r = _norma_req(c)
        # admin cria definições
        d_lista = c.post("/api/requisitos/atributos/defs", json={
            "chave": "risco", "rotulo": "Risco", "tipo": "lista", "opcoes": ["baixo", "alto"], "obrigatorio": True}).json()
        assert d_lista["tipo"] == "lista"
        assert c.post("/api/requisitos/atributos/defs", json={"chave": "risco", "rotulo": "dup"}).status_code == 409
        assert c.post("/api/requisitos/atributos/defs", json={"chave": "t", "rotulo": "T", "tipo": "zzz"}).status_code == 422
        assert c.post("/api/requisitos/atributos/defs", json={"chave": "l", "rotulo": "L", "tipo": "lista"}).status_code == 422
        # valor inválido (fora das opções) e obrigatório ausente
        assert c.put(f"/api/requisitos/{r['id']}/atributos", json={"valores": {str(d_lista["id"]): "medio"}}).status_code == 422
        assert c.put(f"/api/requisitos/{r['id']}/atributos", json={"valores": {}}).status_code == 422
        # valor válido
        ok = c.put(f"/api/requisitos/{r['id']}/atributos", json={"valores": {str(d_lista["id"]): "alto"}})
        assert ok.status_code == 200
        det = c.get(f"/api/requisitos/{r['id']}").json()
        attr = {a["chave"]: a["valor"] for a in det["atributos"]}
        assert attr["risco"] == "alto"


def test_atributo_defs_somente_admin():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        ed = _novo_usuario(c, eid, "editor")
        c.post("/api/auth/logout")
        login(c, ed, "senha")
        assert c.post("/api/requisitos/atributos/defs", json={"chave": "x", "rotulo": "X"}).status_code == 403
        assert c.get("/api/requisitos/atributos/defs").status_code == 200


def test_relacoes_requisito_requisito():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r1 = _norma_req(c)
        r2 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req2"}).json()
        rel = c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "deriva_de"})
        assert rel.status_code == 201
        assert c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r1["id"], "tipo": "refina"}).status_code == 422
        assert c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "deriva_de"}).status_code == 409
        assert c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": 999999, "tipo": "refina"}).status_code == 404
        assert len(c.get(f"/api/requisitos/{r1['id']}/relacoes").json()) == 1
        rid = rel.json()["id"]
        assert c.delete(f"/api/requisitos/{r1['id']}/relacoes/{rid}").status_code == 204


def test_vinculo_tipo_relacao():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        issue = criar_issue(c).json()
        v = c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"], "tipo_relacao": "verifica"})
        assert v.status_code == 201 and v.json()["tipo_relacao"] == "verifica"
        assert c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"], "tipo_relacao": "zzz"}).status_code == 422


def test_detalhe_enriquecido_para_rastreabilidade():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r1 = _norma_req(c)
        r2 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req2"}).json()
        c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "refina"})
        issue = criar_issue(c).json()
        c.post(f"/api/requisitos/{r1['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"]})
        d1 = c.get(f"/api/requisitos/{r1['id']}").json()
        assert d1["norma_codigo"] == n["codigo"]
        assert d1["relacoes"][0]["destino_id"] == r2["id"]
        assert d1["vinculos"][0]["alvo_label"]  # rótulo do alvo resolvido
        assert d1["relacoes_entrada"] == []
        d2 = c.get(f"/api/requisitos/{r2['id']}").json()
        assert d2["relacoes_entrada"][0]["origem_id"] == r1["id"]


def test_arvore_de_rastreabilidade():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r1 = _norma_req(c)
        r2 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req2"}).json()
        c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "depende", "observacao": "obs rel"})
        issue = criar_issue(c).json()
        c.post(f"/api/requisitos/{r1['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"], "observacao": "obs vinc"})
        c.post("/api/conformidade", json={"requisito_id": r1["id"], "situacao": "conforme"})
        c.post(f"/api/requisitos/{r1['id']}/mudancas", json={"descricao": "mudar algo"})
        a = c.get(f"/api/requisitos/arvore?norma_id={n['id']}").json()
        assert a["norma"]["codigo"] == n["codigo"]
        assert len(a["requisitos"]) == 2
        r1t = [x for x in a["requisitos"] if x["id"] == r1["id"]][0]
        assert r1t["situacao"] == "conforme"
        assert r1t["vinculos"][0]["alvo_label"]
        assert r1t["vinculos"][0]["id"] and r1t["vinculos"][0]["observacao"] == "obs vinc"
        assert r1t["relacoes"][0]["destino_id"] == r2["id"]
        assert r1t["relacoes"][0]["id"] and r1t["relacoes"][0]["observacao"] == "obs rel"
        assert len(r1t["mudancas"]) == 1 and r1t["mudancas"][0]["situacao"] == "proposta"
        # norma de outra empresa / sem login
        assert c.get("/api/requisitos/arvore?norma_id=999999").status_code == 404


def test_classes_por_norma():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        na = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "NA", "criar_documento": False}).json()
        nb = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "NB", "criar_documento": False}).json()
        cl = c.post("/api/requisitos/classes", json={"norma_id": na["id"], "codigo": "8", "nome": "Operação"})
        assert cl.status_code == 201
        clid = cl.json()["id"]
        assert len(c.get(f"/api/requisitos/classes?norma_id={na['id']}").json()) == 1
        # requisito com classe da própria norma -> ok; classe da outra norma -> 422
        r = c.post("/api/requisitos", json={"norma_id": na["id"], "titulo": "R", "classe_id": clid}).json()
        assert r["classe_id"] == clid
        assert c.post("/api/requisitos", json={"norma_id": nb["id"], "titulo": "X", "classe_id": clid}).status_code == 422
        # árvore agrupa/expõe classe
        arv = c.get(f"/api/requisitos/arvore?norma_id={na['id']}").json()
        assert any(x["nome"] == "Operação" for x in arv["classes"])
        rt = [x for x in arv["requisitos"] if x["id"] == r["id"]][0]
        assert rt["classe_id"] == clid and rt["classe_nome"] == "Operação"
        # excluir a classe solta o requisito (classe_id -> NULL)
        assert c.delete(f"/api/requisitos/classes/{clid}").status_code == 204
        assert c.get(f"/api/requisitos/{r['id']}").json()["classe_id"] is None


def test_fonte_justificativa_requisito():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "N", "criar_documento": False}).json()
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req",
                                            "fonte": "ISO 9001 §8.5", "justificativa": "exigência do cliente"}).json()
        assert r["fonte"] == "ISO 9001 §8.5" and r["justificativa"] == "exigência do cliente"
        upd = c.put(f"/api/requisitos/{r['id']}", json={"fonte": "Lei 14.133", "justificativa": "requisito legal"}).json()
        assert upd["fonte"] == "Lei 14.133" and upd["justificativa"] == "requisito legal"
        # valores preservados ao editar outro campo
        upd2 = c.put(f"/api/requisitos/{r['id']}", json={"titulo": "Req 2"}).json()
        assert upd2["fonte"] == "Lei 14.133" and upd2["justificativa"] == "requisito legal"


def test_clonar_requisitos():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        a = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "Origem", "criar_documento": False}).json()
        b = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "Destino", "criar_documento": False}).json()
        c.post("/api/requisitos", json={"norma_id": a["id"], "titulo": "R1", "codigo_clausula": "1.1",
                                        "prioridade": "must", "fonte": "F1", "justificativa": "J1"})
        c.post("/api/requisitos", json={"norma_id": a["id"], "titulo": "R2", "codigo_clausula": "1.2"})
        res = c.post("/api/requisitos/clonar", json={"origem_norma_id": a["id"], "destino_norma_id": b["id"]})
        assert res.status_code == 201 and res.json()["criados"] == 2
        dest = c.get(f"/api/requisitos?norma_id={b['id']}").json()
        assert len(dest) == 2
        r1 = [x for x in dest if x["codigo_clausula"] == "1.1"][0]
        assert r1["prioridade"] == "must" and r1["fonte"] == "F1" and r1["justificativa"] == "J1"
        # mesma norma -> 422
        assert c.post("/api/requisitos/clonar", json={"origem_norma_id": a["id"], "destino_norma_id": a["id"]}).status_code == 422


def test_semear_qualidade_atributos():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        # editor (não admin) não pode semear (admin only)
        editor = _novo_usuario(c, eid, "editor")
        c.post("/api/auth/logout")
        login(c, editor, "senha")
        assert c.post(f"/api/requisitos/atributos/defs/semear-qualidade?empresa_id={eid}", json={}).status_code == 403
        login(c, "admin", "admin")
        r1 = c.post(f"/api/requisitos/atributos/defs/semear-qualidade?empresa_id={eid}", json={})
        assert r1.status_code == 201 and r1.json()["criados"] == 6
        # idempotente
        assert c.post(f"/api/requisitos/atributos/defs/semear-qualidade?empresa_id={eid}", json={}).json()["criados"] == 0
        defs = c.get(f"/api/requisitos/atributos/defs?empresa_id={eid}").json()
        chaves = {d["chave"] for d in defs}
        assert {"req_verificavel", "req_mensuravel", "req_rastreavel"} <= chaves


def test_auditoria_e_export_rastreabilidade():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "NA",
                                        "identificador_externo": "ISO 9999", "criar_documento": False}).json()
        # requisito criado sem fonte herda a norma; demais lacunas permanecem
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Sem nada", "codigo_clausula": "9.1"}).json()
        assert r["fonte"] == "ISO 9999"  # fonte veio da norma
        assert r["justificativa"] == "Requisito decorrente da norma ISO 9999"  # justificativa veio da norma
        aud = c.get(f"/api/requisitos/auditoria?norma_id={n['id']}").json()
        assert aud["resumo"]["total"] == 1
        assert aud["resumo"]["sem_fonte"] == 0 and aud["resumo"]["sem_justificativa"] == 0  # herdados da norma
        assert aud["resumo"]["sem_vinculo"] == 1 and aud["resumo"]["sem_verificacao"] == 1
        # se fonte/justificativa forem esvaziadas manualmente, a auditoria volta a sinalizar
        c.put(f"/api/requisitos/{r['id']}", json={"fonte": "", "justificativa": ""})
        aud2 = c.get(f"/api/requisitos/auditoria?norma_id={n['id']}").json()["resumo"]
        assert aud2["sem_fonte"] == 1 and aud2["sem_justificativa"] == 1
        # export CSV
        exp = c.get(f"/api/requisitos/rastreabilidade-export?norma_id={n['id']}")
        assert exp.status_code == 200 and "text/csv" in exp.headers["content-type"]
        texto = exp.content.decode("utf-8-sig")
        assert "Norma" in texto and "9.1" in texto


def test_vinculos_por_alvo_issue_e_rnc():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        issue = criar_issue(c).json()
        # vincula o requisito à Issue com tipo 'viola'
        v = c.post(f"/api/requisitos/{r['id']}/vinculos",
                   json={"alvo_tipo": "issue", "alvo_id": issue["id"], "tipo_relacao": "viola"})
        assert v.status_code == 201 and v.json()["tipo_relacao"] == "viola"
        rows = c.get(f"/api/requisitos/vinculos-por-alvo?alvo_tipo=issue&alvo_id={issue['id']}").json()
        assert len(rows) == 1
        assert rows[0]["requisito_id"] == r["id"]
        assert rows[0]["norma_codigo"] == n["codigo"] and rows[0]["norma_id"] == n["id"]
        # alvo_tipo inválido -> 422
        assert c.get(f"/api/requisitos/vinculos-por-alvo?alvo_tipo=xxx&alvo_id={issue['id']}").status_code == 422
        # tenancy: outra empresa não enxerga o alvo
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"RM2 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get(f"/api/requisitos/vinculos-por-alvo?alvo_tipo=issue&alvo_id={issue['id']}").status_code == 404


def test_emissao_rnc_copia_vinculos_da_issue():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        issue = criar_issue(c).json()
        c.post(f"/api/requisitos/{r['id']}/vinculos",
               json={"alvo_tipo": "issue", "alvo_id": issue["id"], "tipo_relacao": "viola", "observacao": "clausula 4.1"})
        rnc_id = c.post(f"/api/issues/{issue['id']}/emitir-rnc", json={}).json()["rnc_id"]
        rows = c.get(f"/api/requisitos/vinculos-por-alvo?alvo_tipo=rnc&alvo_id={rnc_id}").json()
        assert len(rows) == 1
        assert rows[0]["requisito_id"] == r["id"]
        assert rows[0]["tipo_relacao"] == "viola" and rows[0]["observacao"] == "clausula 4.1"
        assert rows[0]["norma_codigo"] == n["codigo"]


def test_rastreabilidade_editar_observacao():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        n, r1 = _norma_req(c)
        r2 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req2"}).json()
        rel = c.post(f"/api/requisitos/{r1['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "depende"}).json()
        issue = criar_issue(c).json()
        vinc = c.post(f"/api/requisitos/{r1['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"]}).json()
        # editar observação da relação e do vínculo
        assert c.put(f"/api/requisitos/{r1['id']}/relacoes/{rel['id']}", json={"observacao": "revisar depois"}).status_code == 200
        assert c.put(f"/api/requisitos/{r1['id']}/vinculos/{vinc['id']}", json={"observacao": "evidência X"}).status_code == 200
        a = c.get(f"/api/requisitos/arvore?norma_id={n['id']}").json()
        r1t = [x for x in a["requisitos"] if x["id"] == r1["id"]][0]
        assert r1t["relacoes"][0]["observacao"] == "revisar depois"
        assert r1t["vinculos"][0]["observacao"] == "evidência X"
        # id inexistente / de outro requisito -> 404
        assert c.put(f"/api/requisitos/{r1['id']}/relacoes/999999", json={"observacao": "x"}).status_code == 404
        assert c.put(f"/api/requisitos/{r2['id']}/vinculos/{vinc['id']}", json={"observacao": "x"}).status_code == 404
        # visualizador não edita
        vis = _novo_usuario(c, eid, "visualizador")
        c.post("/api/auth/logout")
        login(c, vis, "senha")
        assert c.put(f"/api/requisitos/{r1['id']}/relacoes/{rel['id']}", json={"observacao": "no"}).status_code == 403
        assert c.put(f"/api/requisitos/{r1['id']}/vinculos/{vinc['id']}", json={"observacao": "no"}).status_code == 403


def test_change_request():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        m = c.post(f"/api/requisitos/{r['id']}/mudancas", json={"descricao": "Reduzir custo de descarte"})
        assert m.status_code == 201 and m.json()["situacao"] == "proposta"
        mid = m.json()["id"]
        assert len(c.get(f"/api/requisitos/{r['id']}/mudancas").json()) == 1
        dec = c.post(f"/api/requisitos/{r['id']}/mudancas/{mid}/decidir", json={"situacao": "aprovada", "decisao_obs": "ok"})
        assert dec.status_code == 200 and dec.json()["situacao"] == "aprovada"
        # decidir de novo -> 422; situação inválida -> 422
        assert c.post(f"/api/requisitos/{r['id']}/mudancas/{mid}/decidir", json={"situacao": "rejeitada"}).status_code == 422
        m2 = c.post(f"/api/requisitos/{r['id']}/mudancas", json={"descricao": "x"}).json()
        assert c.post(f"/api/requisitos/{r['id']}/mudancas/{m2['id']}/decidir", json={"situacao": "xxx"}).status_code == 422


def test_impacto_economico():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "Nimp", "criar_documento": False}).json()
        r1 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Descarte",
                                             "custo_atual": 150, "custo_projetado": 50, "volume": 1000000}).json()
        c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Sem dados"})  # economia None
        d = c.get(f"/api/requisitos/impacto?norma_id={n['id']}").json()
        assert d["resumo"]["economia_total"] == 100000000.0
        assert d["resumo"]["requisitos_com_dados"] == 1
        assert d["requisitos"][0]["economia"] == 100000000.0  # ordenado por economia desc
        assert d["requisitos"][-1]["economia"] is None
        # recalcula ao alterar volume
        c.put(f"/api/requisitos/{r1['id']}", json={"volume": 2000000})
        d2 = c.get(f"/api/requisitos/impacto?norma_id={n['id']}").json()
        assert d2["resumo"]["economia_total"] == 200000000.0


def test_versionamento_e_variante():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        # variante
        upd = c.put(f"/api/requisitos/{r['id']}", json={"variante": "127V"}).json()
        assert upd["variante"] == "127V"
        # relação variante_de
        r2 = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Base"}).json()
        assert c.post(f"/api/requisitos/{r['id']}/relacoes", json={"destino_id": r2["id"], "tipo": "variante_de"}).status_code == 201
        # versão manual
        assert c.post(f"/api/requisitos/{r['id']}/versoes").status_code == 201
        vs = c.get(f"/api/requisitos/{r['id']}/versoes").json()
        assert len(vs) == 1 and vs[0]["numero"] == 1 and vs[0]["snapshot"]["variante"] == "127V"
        # snapshot automático ao aprovar mudança
        m = c.post(f"/api/requisitos/{r['id']}/mudancas", json={"descricao": "muda"}).json()
        c.post(f"/api/requisitos/{r['id']}/mudancas/{m['id']}/decidir", json={"situacao": "aprovada"})
        vs2 = c.get(f"/api/requisitos/{r['id']}/versoes").json()
        assert len(vs2) == 2 and vs2[0]["origem"].startswith("mudanca:")


def test_consulta_variantes():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, base = _norma_req(c)
        v = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Tensão 127V", "variante": "127V"}).json()
        c.post(f"/api/requisitos/{v['id']}/relacoes", json={"destino_id": base["id"], "tipo": "variante_de"})
        solta = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "BR", "variante": "BR"}).json()
        d = c.get(f"/api/requisitos/variantes?norma_id={n['id']}").json()
        assert len(d["grupos"]) == 1
        g = d["grupos"][0]
        assert g["base"]["id"] == base["id"]
        assert g["variantes"][0]["id"] == v["id"] and g["variantes"][0]["variante"] == "127V"
        assert any(s["id"] == solta["id"] for s in d["soltas"])  # variante com label, sem base


def test_arvore_de_versionamento():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        c.post(f"/api/requisitos/{r['id']}/versoes")  # R01 manual
        m = c.post(f"/api/requisitos/{r['id']}/mudancas", json={"descricao": "x"}).json()
        c.post(f"/api/requisitos/{r['id']}/mudancas/{m['id']}/decidir", json={"situacao": "aprovada"})  # R02 auto
        d = c.get(f"/api/requisitos/versoes-arvore?norma_id={n['id']}").json()
        assert d["norma"]["codigo"] == n["codigo"]
        rt = [x for x in d["requisitos"] if x["id"] == r["id"]][0]
        nums = [v["numero"] for v in rt["versoes"]]
        assert nums == [2, 1]  # ordem desc
        assert any(v["origem"].startswith("mudanca:") for v in rt["versoes"])


def test_exportar_ainda_funciona():
    # regressão: a rota /{req_id} não pode capturar /exportar
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, _ = _norma_req(c)
        exp = c.get(f"/api/requisitos/exportar?norma_id={n['id']}&formato=csv")
        assert exp.status_code == 200
