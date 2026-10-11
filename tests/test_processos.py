from fastapi.testclient import TestClient

from app.main import app


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def test_fluxo_setor_processo_sintaxe():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa X")

        r = c.post("/api/setores", json={"nome": "Produção", "empresa_id": empresa["id"]})
        assert r.status_code == 201
        setor = r.json()
        assert setor["nome"] == "Produção"

        assert c.get(f"/api/setores?empresa_id={empresa['id']}").status_code == 200

        r = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Expedição"})
        assert r.status_code == 201
        processo = r.json()

        sintaxe = "flowchart TD\n    A[Início] --> B[Fim]"
        r = c.post(f"/api/processos/{processo['id']}/revisoes", json={"sintaxe": sintaxe})
        assert r.status_code == 201
        assert r.json()["sintaxe"] == sintaxe

        assert c.get(f"/api/processos/{processo['id']}").json()["sintaxe"] == sintaxe

        assert c.delete(f"/api/processos/{processo['id']}").status_code == 204
        assert c.get(f"/api/processos/{processo['id']}").status_code == 404


def test_isolamento_fluxo_entre_empresas():
    with TestClient(app) as c:
        login(c)
        ea = criar_empresa(c, "Empresa A")["id"]
        eb = criar_empresa(c, "Empresa B")["id"]
        c.post("/api/usuarios", json={"nome": "UA", "email": "fluxo_ua@x.com", "senha": "s", "papel": "admin", "empresa_id": ea})
        c.post("/api/usuarios", json={"nome": "UB", "email": "fluxo_ub@x.com", "senha": "s", "papel": "admin", "empresa_id": eb})
        c.post("/api/auth/logout")

        login(c, "fluxo_ua@x.com", "s")
        setor_a = c.post("/api/setores", json={"nome": "S A"}).json()
        proc_a = c.post("/api/processos", json={"setor_id": setor_a["id"], "nome": "P A"}).json()
        assert len(c.get("/api/processos").json()) == 1
        c.post("/api/auth/logout")

        login(c, "fluxo_ub@x.com", "s")
        assert c.get("/api/processos").json() == []
        assert c.get(f"/api/processos/{proc_a['id']}").status_code == 403
        assert c.delete(f"/api/setores/{setor_a['id']}").status_code == 403


def test_processo_primary_key_unico():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa PK")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()
        r = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"})
        assert r.status_code == 409

        # mesmo nome em outro setor da MESMA empresa -> continua duplicado (chave = empresa + nome)
        setor2 = c.post("/api/setores", json={"nome": "S2", "empresa_id": empresa["id"]}).json()
        r2 = c.post("/api/processos", json={"setor_id": setor2["id"], "nome": "Proc"})
        assert r2.status_code == 409

        # mesmo nome em OUTRA empresa -> OK
        empresa2 = criar_empresa(c, "Empresa PK2")
        r3 = c.post("/api/processos", json={"empresa_id": empresa2["id"], "nome": "Proc"})
        assert r3.status_code == 201


def test_delete_empresa_cascateia_setores():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa C")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "P"}).json()
        assert c.get(f"/api/processos/{proc['id']}").status_code == 200

        assert c.delete(f"/api/empresas/{empresa['id']}").status_code == 204

        assert c.get(f"/api/processos/{proc['id']}").status_code == 404
