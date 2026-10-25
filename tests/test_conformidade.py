import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa, criar_issue
from tests.test_pdm import _empresa_com_editor, _novo_usuario


def _norma_req(c):
    n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "Norma C", "criar_documento": False}).json()
    r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req", "codigo_clausula": "4.1"}).json()
    return n, r


def test_vinculo_issue_e_processo():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        issue = criar_issue(c).json()
        proc = c.post("/api/processos", json={"nome": f"Proc {uuid.uuid4().hex[:6]}"}).json()
        v1 = c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"]})
        assert v1.status_code == 201
        v2 = c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "processo", "alvo_id": proc["id"]})
        assert v2.status_code == 201
        # duplicado -> 409
        assert c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue["id"]}).status_code == 409
        assert len(c.get(f"/api/requisitos/{r['id']}/vinculos").json()) == 2
        # alvo inexistente -> 404
        assert c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": 999999}).status_code == 404
        # remover
        vid = v1.json()["id"]
        assert c.delete(f"/api/requisitos/{r['id']}/vinculos/{vid}").status_code == 204


def test_vinculo_alvo_outra_empresa_bloqueado():
    with TestClient(app) as c:
        eid1, email1 = _empresa_com_editor(c)
        n, r = _norma_req(c)
        # empresa 2 com uma issue
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"CONF2 {uuid.uuid4().hex[:8]}")["id"]
        e2 = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, e2, "senha")
        issue2 = criar_issue(c).json()
        # volta para empresa 1 e tenta vincular à issue da empresa 2
        c.post("/api/auth/logout")
        login(c, email1, "senha")
        rr = c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": "issue", "alvo_id": issue2["id"]})
        assert rr.status_code == 403


def test_conformidade_e_matriz():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        # sem avaliação nem vínculo: aparece nas lacunas
        m0 = c.get(f"/api/conformidade/matriz?norma_id={n['id']}").json()
        assert m0["resumo"]["total"] == 1
        assert r["id"] in m0["lacunas"]["sem_vinculo"]
        assert r["id"] in m0["lacunas"]["nao_avaliados"]
        # avaliar conforme
        assert c.post("/api/conformidade", json={"requisito_id": r["id"], "situacao": "conforme", "evidencia": "ok"}).status_code == 201
        m1 = c.get(f"/api/conformidade/matriz?norma_id={n['id']}").json()
        assert m1["requisitos"][0]["situacao"] == "conforme"
        assert m1["resumo"]["conformes"] == 1
        assert r["id"] not in m1["lacunas"]["nao_avaliados"]
        # situação inválida
        assert c.post("/api/conformidade", json={"requisito_id": r["id"], "situacao": "xxx"}).status_code == 422


def test_conformidade_tenancy():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n, r = _norma_req(c)
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"CONF3 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get(f"/api/conformidade/matriz?norma_id={n['id']}").status_code == 404
        c.post("/api/auth/logout")
        assert c.get(f"/api/conformidade/matriz?norma_id={n['id']}").status_code == 401
