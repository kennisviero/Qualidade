"""Verifica o critério: empresa(1) -> setor(n) e empresa(1) -> processo(n).

Confirma que:
- setor SEM empresa -> rejeitado (NOT NULL).
- processo SEM empresa -> rejeitado (NOT NULL).
- (empresa, processo) é primary key -> duplicata rejeitada (setor é campo, não chave).
"""
from fastapi.testclient import TestClient

from app.main import app


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def test_setor_exige_empresa():
    """setor SEM empresa_id é rejeitado."""
    with TestClient(app) as c:
        login(c)
        r = c.post("/api/setores", json={"nome": "SemEmpresa"})
        assert r.status_code in (400, 422)


def test_processo_exige_empresa():
    """processo SEM empresa_id é rejeitado."""
    with TestClient(app) as c:
        login(c)
        r = c.post("/api/processos", json={"nome": "SemEmpresa"})
        assert r.status_code in (400, 422)


def test_primary_key_empresa_processo():
    """(empresa, processo) é único — setor não faz parte da chave (409)."""
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa PK1")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()
        r = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"})
        assert r.status_code == 409

        # mesmo nome em outro setor da MESMA empresa = duplicado (setor não é chave)
        setor2 = c.post("/api/setores", json={"nome": "S2", "empresa_id": empresa["id"]}).json()
        r2 = c.post("/api/processos", json={"setor_id": setor2["id"], "nome": "Proc"})
        assert r2.status_code == 409

        # mesmo nome em empresa diferente = OK
        empresa2 = criar_empresa(c, "Empresa PK2")
        r3 = c.post("/api/processos", json={"empresa_id": empresa2["id"], "nome": "Proc"})
        assert r3.status_code == 201


def test_primary_key_ishikawa():
    """Ishikawa standalone foi removido — verifica que a tabela/endpoints não existem mais."""
    with TestClient(app) as c:
        login(c)
        assert c.post("/api/ishikawas", json={"setor_id": 1, "nome": "I"}).status_code == 404


def test_cascata_empresa_setor_processo():
    """Excluir empresa cascataia setores e processos (FK ON DELETE CASCADE)."""
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa Cascata")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "P"}).json()

        assert c.delete(f"/api/empresas/{empresa['id']}").status_code == 204
        assert c.get(f"/api/processos/{proc['id']}").status_code == 404
