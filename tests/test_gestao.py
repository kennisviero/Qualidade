from fastapi.testclient import TestClient

from app.main import app


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def test_processo_metadados_revisao_aprovacao():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa G")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        usuario = c.post(
            "/api/usuarios",
            json={"nome": "Resp", "email": "resp_g@x.com", "senha": "s", "papel": "editor", "empresa_id": empresa["id"]},
        ).json()

        r = c.post(
            "/api/processos",
            json={"setor_id": setor["id"], "nome": "P", "responsavel_id": usuario["id"], "aprovador_id": usuario["id"]},
        )
        assert r.status_code == 201
        p = r.json()
        assert p["responsavel_id"] == usuario["id"]
        assert p["status"] == "rascunho"
        assert p["criado_por_nome"] == "Superusuário"

        r = c.post(f"/api/processos/{p['id']}/revisoes", json={"sintaxe": "flowchart TD\n A-->B"})
        assert r.status_code == 201
        assert r.json()["numero"] == 2

        p = c.get(f"/api/processos/{p['id']}").json()
        assert p["status"] == "em_revisao"
        assert p["sintaxe"] == "flowchart TD\n A-->B"

        revs = c.get(f"/api/processos/{p['id']}/revisoes").json()
        assert len(revs) == 2

        p = c.post(f"/api/processos/{p['id']}/aprovar").json()
        assert p["status"] == "aprovado"
        assert p["aprovado_por_nome"] == "Superusuário"
        assert p["aprovacao_em"] is not None


def test_processo_status_invalido():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa I")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "P"}).json()
        r = c.put(f"/api/processos/{proc['id']}", json={"status": "invalido"})
        assert r.status_code == 422


def _proc_node(resp):
    return resp["arvore"]["filhos"][0]["filhos"][0]["filhos"][0]


def test_documentos_arvore_fluxo():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa H")
        setor = c.post("/api/setores", json={"nome": "Prod", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()

        r = c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": ""},
            files={"file": ("relatorio.txt", b"conteudo", "text/plain")},
        )
        assert r.status_code == 201

        resp = c.get(f"/api/processos/{proc['id']}/arvore").json()
        assert resp["pasta"] == "Empresa H/Prod/Proc"
        assert resp["arvore"]["nome"]  # raiz (Arquivos/temp)
        assert resp["arvore"]["filhos"][0]["nome"] == "Empresa H"
        assert resp["arvore"]["filhos"][0]["filhos"][0]["nome"] == "Prod"
        proc_node = _proc_node(resp)
        assert proc_node["nome"] == "Proc"
        assert [f["nome"] for f in proc_node["filhos"]] == ["relatorio.txt"]

        r = c.get(f"/api/processos/{proc['id']}/arquivo", params={"caminho": "relatorio.txt"})
        assert r.status_code == 200
        assert r.content == b"conteudo"

        assert c.delete(f"/api/processos/{proc['id']}/objetos", params={"caminho": "relatorio.txt"}).status_code == 204
        assert _proc_node(c.get(f"/api/processos/{proc['id']}/arvore").json())["filhos"] == []


def test_documentos_pastas_e_upload_subpasta():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa J")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()

        r = c.post(f"/api/processos/{proc['id']}/pastas", json={"nome": "Qualidade", "subpasta": ""})
        assert r.status_code == 201

        r = c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": "Qualidade"},
            files={"file": ("manual.pdf", b"%PDF", "application/pdf")},
        )
        assert r.status_code == 201

        proc_node = _proc_node(c.get(f"/api/processos/{proc['id']}/arvore").json())
        assert [f["nome"] for f in proc_node["filhos"]] == ["Qualidade"]
        assert proc_node["filhos"][0]["filhos"][0]["nome"] == "manual.pdf"

        # criar arquivo em branco
        r = c.post(f"/api/processos/{proc['id']}/arquivos/criar", json={"nome": "procedimento.txt", "subpasta": ""})
        assert r.status_code == 201
        assert c.get(f"/api/processos/{proc['id']}/arquivo", params={"caminho": "procedimento.txt"}).content == b""

        # excluir pasta recursiva
        assert c.delete(f"/api/processos/{proc['id']}/objetos", params={"caminho": "Qualidade"}).status_code == 204
        proc_node = _proc_node(c.get(f"/api/processos/{proc['id']}/arvore").json())
        assert [f["nome"] for f in proc_node["filhos"]] == ["procedimento.txt"]


def test_documentos_path_traversal_bloqueado():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa K")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()

        r = c.get(f"/api/processos/{proc['id']}/arquivo", params={"caminho": "../fora.txt"})
        assert r.status_code == 400
        r = c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": ".."},
            files={"file": ("x.txt", b"x", "text/plain")},
        )
        assert r.status_code == 400


def test_processo_cria_pasta_fisica():
    from app.docs import folder_for

    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa L")
        setor = c.post("/api/setores", json={"nome": "Prod", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()
        p = c.get(f"/api/processos/{proc['id']}").json()
        assert p["pasta"] == "Empresa L/Prod/Proc"
        assert folder_for(p["pasta"]).is_dir()


def test_excluir_processo_remove_pasta():
    from app.docs import folder_for

    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa M")
        setor = c.post("/api/setores", json={"nome": "Prod", "empresa_id": empresa["id"]}).json()
        proc = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc"}).json()
        p = c.get(f"/api/processos/{proc['id']}").json()
        folder = folder_for(p["pasta"])
        assert folder.is_dir()

        c.post(
            f"/api/processos/{proc['id']}/arquivos",
            data={"subpasta": ""},
            files={"file": ("x.txt", b"x", "text/plain")},
        )

        assert c.delete(f"/api/processos/{proc['id']}").status_code == 204
        assert c.get(f"/api/processos/{proc['id']}").status_code == 404
        assert not folder.exists()


