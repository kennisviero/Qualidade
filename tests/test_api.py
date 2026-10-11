from fastapi.testclient import TestClient

from app.main import app


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def test_fluxo_projeto_dataset():
    with TestClient(app) as c:
        login(c)
        empresa = c.post("/api/empresas", json={"razao_social": "Empresa X"}).json()

        r = c.post("/api/projects", json={"nome": "Projeto X", "descricao": "teste", "empresa_id": empresa["id"]})
        assert r.status_code == 201
        pid = r.json()["id"]

        assert c.get("/api/projects").status_code == 200

        r = c.post(
            f"/api/projects/{pid}/datasets",
            json={"nome": "ds1", "tipo": "pareto", "dados": [{"rotulo": "A", "frequencia": 5}]},
        )
        assert r.status_code == 201

        assert c.delete(f"/api/projects/{pid}").status_code == 204


def test_issue_analise_endpoints():
    with TestClient(app) as c:
        login(c)
        assert c.get("/api/issues/stats").status_code == 200
        assert c.get("/api/issues/trends").status_code == 200


def test_projeto_nao_encontrado():
    with TestClient(app) as c:
        login(c)
        assert c.get("/api/projects/9999").status_code == 404
