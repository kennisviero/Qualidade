import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_issues import login, criar_empresa
from tests.test_pdm import _empresa_com_editor, _novo_usuario


def _norma(c, titulo="Norma X"):
    return c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": titulo, "criar_documento": False}).json()


def test_requisito_crud_e_tenancy():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = _norma(c)
        r = c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req 4.1",
                                            "codigo_clausula": "4.1", "categoria": "normativo"}).json()
        assert r["codigo_clausula"] == "4.1" and r["estado"] == "ativo"
        upd = c.put(f"/api/requisitos/{r['id']}", json={"estado": "revogado"}).json()
        assert upd["estado"] == "revogado"
        assert len(c.get(f"/api/requisitos?norma_id={n['id']}").json()) == 1
        # outra empresa não enxerga
        login(c, "admin", "admin")
        eid2 = criar_empresa(c, f"REQ2 {uuid.uuid4().hex[:8]}")["id"]
        outro = _novo_usuario(c, eid2, "admin")
        c.post("/api/auth/logout")
        login(c, outro, "senha")
        assert c.get(f"/api/requisitos?norma_id={n['id']}").status_code == 404  # norma de outra empresa
        c.post("/api/auth/logout")
        assert c.get(f"/api/requisitos?norma_id={n['id']}").status_code == 401


def test_requisito_enums_invalidos():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = _norma(c)
        assert c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "R", "categoria": "xxx"}).status_code == 422
        assert c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "R", "obrigatoriedade": "xxx"}).status_code == 422


def test_requisito_visualizador_sem_escrita():
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        n = _norma(c)
        vis = _novo_usuario(c, eid, "visualizador")
        c.post("/api/auth/logout")
        login(c, vis, "senha")
        assert c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "R"}).status_code == 403
        assert c.get(f"/api/requisitos?norma_id={n['id']}").status_code == 200


def test_requisito_import_export_csv():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = _norma(c)
        csv_data = "codigo_clausula,titulo,categoria,obrigatoriedade\n4.1,Contexto,normativo,obrigatorio\n5.1,Lideranca,normativo,recomendado\n"
        imp = c.post("/api/requisitos/importar",
                     data={"norma_id": str(n["id"])},
                     files={"file": ("reqs.csv", csv_data.encode("utf-8"), "text/csv")})
        assert imp.status_code == 201 and imp.json()["importados"] == 2
        assert len(c.get(f"/api/requisitos?norma_id={n['id']}").json()) == 2
        exp = c.get(f"/api/requisitos/exportar?norma_id={n['id']}&formato=csv")
        assert exp.status_code == 200
        assert "Contexto" in exp.content.decode("utf-8-sig")


def test_revisao_com_variante():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        did = c.post("/api/pdm/documentos", json={"titulo": "Doc var", "tipo": "norma"}).json()["id"]
        c.post(f"/api/pdm/documentos/{did}/checkout")
        rev = c.post(f"/api/pdm/documentos/{did}/revisoes", json={"descricao_mudanca": "pt-BR", "variante": "pt-BR"}).json()
        assert rev["variante"] == "pt-BR"
