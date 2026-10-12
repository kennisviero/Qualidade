import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.db import DB_PATH, DOCS_DIR, get_connection
from app.main import app
from test_issues import criar_empresa, criar_editor, criar_issue, login


def test_limpeza_preview_backup_preserva_rnc_e_arquivos():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Limpeza")["id"]
        criar_editor(c, eid)
        closed = criar_issue(c).json()
        action = c.post(f"/api/issues/{closed['id']}/acoes", json={"descricao": "Remover ação"}).json()
        c.post(f"/api/issues/{closed['id']}/fechar")
        opened = criar_issue(c).json()
        protected = criar_issue(c).json()
        c.post(f"/api/issues/{protected['id']}/fechar")
        with get_connection() as conn:
            conn.execute("INSERT INTO rncs (issue_id, empresa_id, codigo) VALUES (?, ?, 'RNC-2026-099')", (protected["id"], eid))
        evidence = DOCS_DIR / closed["pasta"] / "preservada.txt"
        evidence.write_text("Preservar evidência", encoding="utf-8")
        preview = c.get("/api/issues/limpeza").json()
        assert preview["issues"] == 1
        assert preview["acoes"] == 1
        assert preview["vinculadas_rnc_preservadas"] == 1
        assert c.post("/api/issues/limpeza", json={**preview, "confirmar": False}).status_code == 422
        assert c.get(f"/api/issues/{closed['id']}").status_code == 200
        response = c.post("/api/issues/limpeza", json={**preview, "confirmar": True})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["removidas"] == 1
        backup = DB_PATH.parent / "backups" / result["backup"]
        with sqlite3.connect(backup) as conn:
            assert conn.execute("SELECT id FROM issues WHERE id = ?", (closed["id"],)).fetchone()
        assert evidence.read_text(encoding="utf-8") == "Preservar evidência"
        assert c.get(f"/api/issues/{closed['id']}").status_code == 404
        assert c.get(f"/api/issues/{opened['id']}").status_code == 200
        assert c.get(f"/api/issues/{protected['id']}").json()["rnc_codigo"] == "RNC-2026-099"
        with get_connection() as conn:
            assert not conn.execute("SELECT id FROM acoes WHERE id = ?", (action["id"],)).fetchone()
        preview = c.get("/api/issues/limpeza?escopo=todas").json()
        assert preview["issues"] == 1
        assert c.post("/api/issues/limpeza", json={**preview, "confirmar": True}).json()["removidas"] == 1
        assert c.get(f"/api/issues/{protected['id']}").status_code == 200


def test_limpeza_permissoes_e_empresa_obrigatoria():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        assert c.get("/api/issues/limpeza").status_code == 422
        eid = criar_empresa(c, "Empresa Limpeza Permissões")["id"]
        other = criar_empresa(c, "Outra Limpeza Permissões")["id"]
        criar_editor(c, eid)
        assert c.get(f"/api/issues/limpeza?empresa_id={other}").status_code == 403
        assert c.post("/api/issues/limpeza", json={"empresa_id": other, "confirmar": True, "revisao": "x"}).status_code == 403
        for papel in ("editor", "visualizador"):
            login(c, "admin", "admin")
            criar_editor(c, eid, papel=papel)
            assert c.get("/api/issues/limpeza").status_code == 403
            assert c.post("/api/issues/limpeza", json={"confirmar": True, "revisao": "x"}).status_code == 403


def test_limpeza_rejeita_preview_desatualizado():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Limpeza Revisão")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        c.post(f"/api/issues/{issue['id']}/fechar")
        preview = c.get("/api/issues/limpeza").json()
        c.put(f"/api/issues/{issue['id']}", json={"ambiente": "campo"})
        assert c.post("/api/issues/limpeza", json={**preview, "confirmar": True}).status_code == 409
        assert c.get(f"/api/issues/{issue['id']}").status_code == 200


def test_limpeza_rollback_em_falha():
    with TestClient(app, raise_server_exceptions=False) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Limpeza Rollback")["id"]
        criar_editor(c, eid)
        ids = [criar_issue(c).json()["id"] for _ in range(2)]
        for issue_id in ids:
            c.post(f"/api/issues/{issue_id}/acoes", json={"descricao": "Preservar em falha"})
            c.post(f"/api/issues/{issue_id}/fechar")
        with get_connection() as conn:
            conn.execute(f"CREATE TRIGGER bloquear_limpeza_teste BEFORE DELETE ON issues WHEN OLD.id = {ids[-1]} "
                         "BEGIN SELECT RAISE(ABORT, 'Falha simulada'); END")
        try:
            preview = c.get("/api/issues/limpeza").json()
            assert c.post("/api/issues/limpeza", json={**preview, "confirmar": True}).status_code == 500
            for issue_id in ids:
                assert c.get(f"/api/issues/{issue_id}").status_code == 200
                assert len(c.get(f"/api/issues/{issue_id}/acoes").json()) == 1
        finally:
            with get_connection() as conn:
                conn.execute("DROP TRIGGER bloquear_limpeza_teste")


def test_dashboard_filtro_empresa_e_tenancy():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Dashboard")["id"]
        other = criar_empresa(c, "Outra Dashboard")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        for endpoint in ("", "/kpis", "/stats", "/trends", "/kanban"):
            assert c.get(f"/api/issues{endpoint}?empresa_id={other}").status_code == 403
        login(c, "admin", "admin")
        items = c.get(f"/api/issues?empresa_id={eid}").json()
        assert [i["id"] for i in items] == [issue["id"]]
        assert c.get(f"/api/issues/stats?empresa_id={eid}").json()["total"] == 1
        assert c.get(f"/api/issues/kpis?empresa_id={eid}").json()["cadastradas"] == 1


def test_dashboard_usuario_sem_empresa_nao_acessa_base_global():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        email = f"sem_empresa_{uuid.uuid4().hex}@x.com"
        response = c.post("/api/usuarios", json={"nome": "Sem empresa", "email": email, "senha": "s", "papel": "editor"})
        assert response.status_code == 201
        login(c, email, "s")
        assert c.get("/api/issues").json() == []
        assert c.get("/api/issues/kanban").json() == []
        assert c.get("/api/issues/stats").json()["total"] == 0
        assert c.get("/api/issues/trends").json()["criadas"] == 0
        assert c.get("/api/issues/kpis").json()["cadastradas"] == 0
