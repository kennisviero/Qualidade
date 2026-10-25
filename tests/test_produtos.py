import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa
from tests.test_pdm import _empresa_com_editor, _novo_usuario


def _familia(c, nome="Linha Branca"):
    return c.post("/api/produtos/familias", json={"nome": nome}).json()


def _hierarquia(c):
    f = _familia(c)
    g = c.post("/api/produtos/grupos", json={"familia_id": f["id"], "nome": "Liquidificadores"}).json()
    p = c.post("/api/produtos", json={"grupo_id": g["id"], "codigo": "LIQ-500", "nome": "ProMix 500"}).json()
    return f, g, p


def test_produtos_crud_e_arvore():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        f, g, p = _hierarquia(c)
        assert f["id"] and g["familia_id"] == f["id"] and p["grupo_id"] == g["id"]
        arv = c.get("/api/produtos/arvore").json()
        assert len(arv["familias"]) == 1
        assert arv["familias"][0]["grupos"][0]["produtos"][0]["nome"] == "ProMix 500"
        # update
        up = c.put(f"/api/produtos/{p['id']}", json={"nome": "ProMix 500 Plus"}).json()
        assert up["nome"] == "ProMix 500 Plus"
        # duplicado -> 409
        assert c.post("/api/produtos/familias", json={"nome": "Linha Branca"}).status_code == 409


def test_produtos_cascata_e_tenancy():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        f, g, p = _hierarquia(c)
        # excluir família remove grupos e produtos (cascata)
        assert c.delete(f"/api/produtos/familias/{f['id']}").status_code == 204
        assert c.get("/api/produtos/grupos").json() == []
        assert c.get("/api/produtos").json() == []
        # tenancy: outra empresa não vê nem edita
        f2, g2, p2 = _hierarquia(c)
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"PRD2 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get("/api/produtos").json() == []
        assert c.put(f"/api/produtos/{p2['id']}", json={"nome": "x"}).status_code == 404


def test_grupo_exige_familia_da_empresa():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        # família inexistente -> 404
        assert c.post("/api/produtos/grupos", json={"familia_id": 999999, "nome": "G"}).status_code == 404


def test_vincular_requisito_a_produto():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        f, g, p = _hierarquia(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "N", "criar_documento": False}).json()
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req"}).json()
        # vincula o requisito a família, grupo e produto
        for tipo, alvo in (("familia", f["id"]), ("grupo", g["id"]), ("produto", p["id"])):
            v = c.post(f"/api/requisitos/{r['id']}/vinculos", json={"alvo_tipo": tipo, "alvo_id": alvo, "tipo_relacao": "satisfaz"})
            assert v.status_code == 201, (tipo, v.text)
        # consulta reversa pelo produto
        rows = c.get(f"/api/requisitos/vinculos-por-alvo?alvo_tipo=produto&alvo_id={p['id']}").json()
        assert len(rows) == 1 and rows[0]["requisito_id"] == r["id"]
        # aparece na árvore de rastreabilidade com rótulo de produto
        arv = c.get(f"/api/requisitos/arvore?norma_id={n['id']}").json()
        labels = [v["alvo_label"] for req in arv["requisitos"] for v in req["vinculos"]]
        assert any("Produto:" in l for l in labels)
        assert any("Família:" in l for l in labels)


def test_vinculo_produto_de_outra_empresa_bloqueado():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "N", "criar_documento": False}).json()
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req"}).json()
        # produto de outra empresa
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"PRD3 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        f2, g2, p2 = _hierarquia(c)
        # superusuário no escopo da empresa do requisito tenta vincular ao produto alheio -> 403
        login(c, "admin", "admin")
        resp = c.post(f"/api/requisitos/{r['id']}/vinculos",
                      json={"alvo_tipo": "produto", "alvo_id": p2["id"], "empresa_id": eid})
        assert resp.status_code in (403, 404)
