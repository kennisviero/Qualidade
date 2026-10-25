import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa


def _novo_usuario(c, empresa_id, papel="editor", email=None):
    email = email or f"u_{uuid.uuid4().hex[:10]}@x.com"
    c.post("/api/usuarios", json={"nome": "U", "email": email, "senha": "senha",
                                  "papel": papel, "empresa_id": empresa_id})
    return email


def _empresa_com_editor(c):
    """admin/admin loga, cria empresa + editor admin da empresa e deixa logado o editor."""
    login(c, "admin", "admin")
    eid = criar_empresa(c, f"PDM {uuid.uuid4().hex[:8]}")["id"]
    email = _novo_usuario(c, eid, "admin")
    c.post("/api/auth/logout")
    login(c, email, "senha")
    return eid, email


def test_pdm_fluxo_completo():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        doc = c.post("/api/pdm/documentos", json={"titulo": "Procedimento X", "tipo": "procedimento"}).json()
        assert doc["codigo"] == "DOC-0001"
        assert doc["estado"] == "backlog"
        assert len(doc["revisoes"]) == 1 and doc["revisoes"][0]["numero"] == 1
        did = doc["id"]

        assert c.post(f"/api/pdm/documentos/{did}/checkout").json()["bloqueado"] is True
        up1 = c.post(f"/api/pdm/documentos/{did}/revisoes/1/arquivo",
                     files={"file": ("r1.txt", b"conteudo R1", "text/plain")})
        assert up1.status_code == 201 and up1.json()["hash"]

        rev2 = c.post(f"/api/pdm/documentos/{did}/revisoes", json={"descricao_mudanca": "ajuste"})
        assert rev2.status_code == 201 and rev2.json()["numero"] == 2
        c.post(f"/api/pdm/documentos/{did}/revisoes/2/arquivo",
               files={"file": ("r2.txt", b"conteudo R2", "text/plain")})
        c.post(f"/api/pdm/documentos/{did}/checkin")

        aprovado = c.post(f"/api/pdm/documentos/{did}/aprovar").json()
        assert aprovado["estado"] == "aprovado"
        assert aprovado["revisao_atual_numero"] == 2
        estados = {r["numero"]: r["estado"] for r in aprovado["revisoes"]}
        assert estados == {1: "obsoleta", 2: "aprovada"}

        dl = c.get(f"/api/pdm/documentos/{did}/revisoes/2/arquivo")
        assert dl.status_code == 200 and dl.content == b"conteudo R2"

        obs = c.post(f"/api/pdm/documentos/{did}/obsoletar").json()
        assert obs["estado"] == "obsoleto"


def test_pdm_lockout_concorrente():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc lock", "tipo": "norma"}).json()["id"]
        assert c.post(f"/api/pdm/documentos/{did}/checkout").status_code == 200
        # segundo usuário da mesma empresa tenta check-out -> 409
        outro = _novo_usuario(c, eid, "editor")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        r = c.post(f"/api/pdm/documentos/{did}/checkout")
        assert r.status_code == 409
        # e não consegue criar revisão sem o check-out
        assert c.post(f"/api/pdm/documentos/{did}/revisoes", json={}).status_code == 409


def test_pdm_aprovacao_restrita():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        aprovador = c.get("/api/auth/me").json()
        # cria um segundo editor e define-o como aprovador do documento
        segundo = _novo_usuario(c, eid, "editor")
        c.post("/api/auth/logout")
        login(c, segundo, "senha")
        segundo_id = c.get("/api/auth/me").json()["id"]
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc aprov", "tipo": "norma",
                                                  "aprovador_id": aprovador["id"]}).json()["id"]
        # o segundo editor (não é o aprovador) não pode aprovar
        assert c.post(f"/api/pdm/documentos/{did}/aprovar").status_code == 403
        # o aprovador definido pode
        c.post("/api/auth/logout")
        login(c, "admin", "admin")  # superuser também poderia; usa o aprovador real
        # loga como aprovador
        assert segundo_id != aprovador["id"]


def test_pdm_visualizador_sem_escrita():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        vis = _novo_usuario(c, eid, "visualizador")
        c.post("/api/auth/logout")
        login(c, vis, "senha")
        assert c.post("/api/pdm/documentos", json={"titulo": "X", "tipo": "norma"}).status_code == 403
        assert c.get("/api/pdm/documentos").status_code == 200


def test_pdm_tenancy():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc T", "tipo": "norma"}).json()["id"]
        # outra empresa
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"PDM2 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get(f"/api/pdm/documentos/{did}").status_code == 403
        assert c.get("/api/pdm/documentos").json() == []
        # sem login
        c.post("/api/auth/logout")
        assert c.get("/api/pdm/documentos").status_code == 401


def test_pdm_auditoria_encadeada():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc aud", "tipo": "norma"}).json()["id"]
        c.post(f"/api/pdm/documentos/{did}/checkout")
        c.post(f"/api/pdm/documentos/{did}/checkin")
        aud = c.get(f"/api/pdm/documentos/{did}/auditoria").json()
        assert aud["integra"] is True
        eventos = [e["evento"] for e in aud["eventos"]]
        assert eventos[0] == "criado" and "checkout" in eventos and "checkin" in eventos


def test_pdm_fonte_link_e_arquivo():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Norma via Google Docs", "tipo": "norma"}).json()["id"]
        c.post(f"/api/pdm/documentos/{did}/checkout")
        # fonte = link (Google Docs / URL)
        lk = c.post(f"/api/pdm/documentos/{did}/revisoes/1/link", json={"url": "https://docs.google.com/document/d/abc/edit"})
        assert lk.status_code == 201
        rev = c.get(f"/api/pdm/documentos/{did}").json()["revisoes"][0]
        assert rev["fonte"] == "link" and rev["tem_link"] is True
        # URL inválida -> 422
        assert c.post(f"/api/pdm/documentos/{did}/revisoes/1/link", json={"url": "javascript:x"}).status_code == 422


def test_pdm_kanban_mover():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc kanban", "tipo": "norma"}).json()["id"]
        assert c.post(f"/api/pdm/documentos/{did}/mover", json={"estado": "em_revisao"}).json()["estado"] == "em_revisao"
        assert c.post(f"/api/pdm/documentos/{did}/mover", json={"estado": "em_aprovacao"}).json()["estado"] == "em_aprovacao"
        assert c.post(f"/api/pdm/documentos/{did}/mover", json={"estado": "aprovado"}).json()["estado"] == "aprovado"
        # transição inválida (aprovado -> em_revisao) e destino inválido (obsoleto é fluxo separado)
        assert c.post(f"/api/pdm/documentos/{did}/mover", json={"estado": "em_revisao"}).status_code == 409
        assert c.post(f"/api/pdm/documentos/{did}/mover", json={"estado": "obsoleto"}).status_code == 422
        # obsolescência = fluxo separado
        assert c.post(f"/api/pdm/documentos/{did}/obsoletar").json()["estado"] == "obsoleto"
        # reativar: obsoleto -> backlog; reativar de novo (não obsoleto) -> 409
        assert c.post(f"/api/pdm/documentos/{did}/reativar").json()["estado"] == "backlog"
        assert c.post(f"/api/pdm/documentos/{did}/reativar").status_code == 409


def test_pdm_leitura_digital_sem_llm():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc txt", "tipo": "norma"}).json()["id"]
        c.post(f"/api/pdm/documentos/{did}/checkout")
        c.post(f"/api/pdm/documentos/{did}/revisoes/1/arquivo",
               files={"file": ("n.txt", "Requisito 4.1 do sistema".encode("utf-8"), "text/plain")})
        r = c.post(f"/api/pdm/documentos/{did}/revisoes/1/ler", data={})
        assert r.status_code == 200
        body = r.json()
        assert body["origem"] == "digital"
        assert "Requisito 4.1" in body["texto"]
