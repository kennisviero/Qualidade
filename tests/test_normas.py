import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa
from tests.test_pdm import _empresa_com_editor, _novo_usuario


def test_norma_cria_com_documento():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={
            "tipo_fonte": "norma_tecnica", "titulo": "ISO 9001", "identificador_externo": "ISO 9001:2015",
            "emissor": "ISO", "edicao_versao": "2015", "status": "vigente"}).json()
        assert n["codigo"] == "NORMA-0001"
        assert n["tipo_fonte"] == "norma_tecnica"
        assert n["documento"] is not None and n["documento"]["tipo"] == "norma"


def test_norma_sem_documento():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "regulamento_legal", "titulo": "Lei 14.133",
                                        "criar_documento": False}).json()
        assert n["documento"] is None


def test_norma_filtros_e_update():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "Norma A",
                                    "emissor": "ABNT", "criar_documento": False})
        n2 = c.post("/api/normas", json={"tipo_fonte": "regulamento_legal", "titulo": "Norma B",
                                         "emissor": "Gov", "criar_documento": False}).json()
        assert len(c.get("/api/normas?tipo_fonte=norma_tecnica").json()) == 1
        assert len(c.get("/api/normas?emissor=ABNT").json()) == 1
        assert len(c.get("/api/normas?q=Norma B").json()) == 1
        upd = c.put(f"/api/normas/{n2['id']}", json={"status": "obsoleta"}).json()
        assert upd["status"] == "obsoleta"
        assert len(c.get("/api/normas?status=obsoleta").json()) == 1


def test_norma_validacoes():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        assert c.post("/api/normas", json={"tipo_fonte": "xxx", "titulo": "N", "criar_documento": False}).status_code == 422
        assert c.post("/api/normas", json={"tipo_fonte": "outro", "titulo": "N", "status": "xxx", "criar_documento": False}).status_code == 422


def test_norma_visualizador_sem_escrita():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        vis = _novo_usuario(c, eid, "visualizador")
        c.post("/api/auth/logout")
        login(c, vis, "senha")
        assert c.post("/api/normas", json={"tipo_fonte": "outro", "titulo": "N", "criar_documento": False}).status_code == 403
        assert c.get("/api/normas").status_code == 200


def test_norma_documento_fonte():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "ISO 9001"}).json()
        info = c.get(f"/api/normas/{n['id']}/documento").json()
        assert info["documento_id"] is not None
        assert info["revisao"]["fonte"] == "cadastrado"
        # link (Google Docs)
        lk = c.post(f"/api/normas/{n['id']}/documento/link", json={"url": "https://docs.google.com/document/d/x/edit"})
        assert lk.status_code == 201 and lk.json()["fonte"] == "link"
        assert c.post(f"/api/normas/{n['id']}/documento/link", json={"url": "ftp://x"}).status_code == 422
        # arquivo (upload)
        up = c.post(f"/api/normas/{n['id']}/documento/arquivo",
                    files={"file": ("norma.txt", b"conteudo", "text/plain")})
        assert up.status_code == 201 and up.json()["fonte"] == "arquivo" and up.json()["tem_arquivo"] is True


def test_norma_aparece_no_kanban_de_documentos():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "regulamento_legal", "titulo": "Lei 14.133",
                                        "identificador_externo": "Lei 14.133/2021"}).json()
        docs = c.get(f"/api/pdm/documentos?empresa_id={eid}").json()
        vinc = [d for d in docs if d.get("norma_codigo") == n["codigo"]]
        assert len(vinc) == 1
        assert vinc[0]["norma_tipo_fonte"] == "regulamento_legal"
        assert vinc[0]["norma_ident"] == "Lei 14.133/2021"


def test_status_norma_segue_documento():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "ISO X"}).json()
        did = n["documento"]["id"]
        assert n["status"] == "em_revisao"  # documento nasce em backlog
        c.post(f"/api/pdm/documentos/{did}/aprovar")
        assert c.get(f"/api/normas/{n['id']}").json()["status"] == "vigente"
        c.post(f"/api/pdm/documentos/{did}/obsoletar")
        assert c.get(f"/api/normas/{n['id']}").json()["status"] == "obsoleta"
        c.post(f"/api/pdm/documentos/{did}/reativar")
        assert c.get(f"/api/normas/{n['id']}").json()["status"] == "em_revisao"


def test_norma_tenancy():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        nid = c.post("/api/normas", json={"tipo_fonte": "outro", "titulo": "N priv", "criar_documento": False}).json()["id"]
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"NOR2 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get(f"/api/normas/{nid}").status_code == 404
        assert c.get("/api/normas").json() == []
        c.post("/api/auth/logout")
        assert c.get("/api/normas").status_code == 401
