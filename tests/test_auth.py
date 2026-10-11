from fastapi.testclient import TestClient

from app.main import app


def login(c, email, senha):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def test_login_superuser():
    with TestClient(app) as c:
        r = login(c, "admin", "admin")
        assert r.status_code == 200
        assert r.json()["papel"] == "admin"
        assert c.get("/api/auth/me").json()["email"] == "admin"


def test_login_senha_errada():
    with TestClient(app) as c:
        assert login(c, "admin", "errada").status_code == 401


def test_rotas_sem_autenticacao():
    with TestClient(app) as c:
        assert c.get("/api/projects").status_code == 401
        assert c.get("/api/issues").status_code == 401
        assert c.get("/api/issues/stats").status_code == 401
        assert c.get("/api/empresas").status_code == 401


def test_visualizador_nao_escreve():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa A")["id"]
        r = c.post(
            "/api/usuarios",
            json={"nome": "V", "email": "v@x.com", "senha": "senha", "papel": "visualizador", "empresa_id": eid},
        )
        assert r.status_code == 201
        c.post("/api/auth/logout")
        login(c, "v@x.com", "senha")
        assert c.get("/api/projects").status_code == 200
        assert c.post("/api/projects", json={"nome": "P"}).status_code == 403


def test_isolamento_entre_empresas():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        ea = criar_empresa(c, "Empresa A")["id"]
        eb = criar_empresa(c, "Empresa B")["id"]
        c.post("/api/usuarios", json={"nome": "UA", "email": "ua@x.com", "senha": "s", "papel": "admin", "empresa_id": ea})
        c.post("/api/usuarios", json={"nome": "UB", "email": "ub@x.com", "senha": "s", "papel": "admin", "empresa_id": eb})
        c.post("/api/auth/logout")

        login(c, "ua@x.com", "s")
        pa = c.post("/api/projects", json={"nome": "PA"}).json()
        assert [p["id"] for p in c.get("/api/projects").json()] == [pa["id"]]
        c.post("/api/auth/logout")

        login(c, "ub@x.com", "s")
        assert c.get("/api/projects").json() == []
        assert c.get(f"/api/projects/{pa['id']}").status_code == 403
