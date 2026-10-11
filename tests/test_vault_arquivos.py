"""Testes de verificação dos arquivos dos Processos e das Issues.

Confirma que o armazenamento está em Vault, que a árvore mostra a hierarquia
completa (Vault → Empresa → Setor → entidade → arquivos/subpastas) e que excluir
a entidade remove a pasta física.
"""
from fastapi.testclient import TestClient

from app.db import DOCS_DIR
from app.docs import folder_for
from app.main import app


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def _dentro_do_vault(pasta):
    return folder_for(pasta).is_relative_to(DOCS_DIR)


def test_fluxo_arquivos_completo():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa Vault F")
        setor = c.post("/api/setores", json={"nome": "Prod", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "ProcVault"}).json()

        pasta = proc["pasta"]
        assert pasta == "Empresa Vault F/Prod/ProcVault"
        assert _dentro_do_vault(pasta)
        assert folder_for(pasta).is_dir()

        c.post(f"/api/processos/{proc['id']}/pastas", json={"nome": "Sub", "subpasta": ""})
        c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": "Sub"},
            files={"file": ("doc.txt", b"conteudo", "text/plain")},
        )
        c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": ""},
            files={"file": ("raiz.txt", b"r", "text/plain")},
        )

        resp = c.get(f"/api/processos/{proc['id']}/arvore").json()
        assert resp["pasta"] == pasta
        arvore = resp["arvore"]
        assert arvore["nome"] == DOCS_DIR.name
        assert arvore["filhos"][0]["nome"] == "Empresa Vault F"
        assert arvore["filhos"][0]["filhos"][0]["nome"] == "Prod"
        proc_node = arvore["filhos"][0]["filhos"][0]["filhos"][0]
        assert proc_node["nome"] == "ProcVault"
        assert sorted(f["nome"] for f in proc_node["filhos"]) == ["Sub", "raiz.txt"]
        sub_node = next(f for f in proc_node["filhos"] if f["nome"] == "Sub")
        assert sub_node["filhos"][0]["nome"] == "doc.txt"

        r = c.get(f"/api/processos/{proc['id']}/arquivo", params={"caminho": "Sub/doc.txt"})
        assert r.status_code == 200
        assert r.content == b"conteudo"

        r = c.get(f"/api/processos/{proc['id']}/arquivo", params={"caminho": "raiz.txt"})
        assert r.status_code == 200
        assert r.content == b"r"

        assert c.delete(f"/api/processos/{proc['id']}/objetos", params={"caminho": "Sub/doc.txt"}).status_code == 204
        assert c.delete(f"/api/processos/{proc['id']}/objetos", params={"caminho": "raiz.txt"}).status_code == 204
        assert c.delete(f"/api/processos/{proc['id']}").status_code == 204
        assert not folder_for(pasta).exists()
