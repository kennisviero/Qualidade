import json

from fastapi.testclient import TestClient

from app.main import app
from tests.test_pdm import _empresa_com_editor


def _acesso_llm(c, empresa_id):
    r = c.post("/api/configuracao/llm", json={
        "empresa_id": empresa_id, "nome": "OR", "provedor": "openrouter",
        "modelo": "modelo-visao", "url_base": "https://openrouter.ai/api/v1",
        "api_key": "chave", "ativo": True})
    return r.json()["id"]


def _norma_com_texto(c):
    """Cria norma com documento, faz check-out, sobe TXT e roda a leitura (digital)."""
    n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "ISO X"}).json()
    did = n["documento"]["id"]
    c.post(f"/api/pdm/documentos/{did}/checkout")
    c.post(f"/api/pdm/documentos/{did}/revisoes/1/arquivo",
           files={"file": ("norma.txt", "4.1 Contexto da organizacao".encode("utf-8"), "text/plain")})
    c.post(f"/api/pdm/documentos/{did}/revisoes/1/ler", data={})
    return n


def test_sugerir_requisitos_por_ia(monkeypatch):
    fake = '{"requisitos":[{"codigo_clausula":"4.1","titulo":"Contexto","categoria":"normativo","obrigatoriedade":"obrigatorio"}]}'
    monkeypatch.setattr("app.services.requisitos_ia.analisar_issues", lambda *a, **k: fake)
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        acesso_id = _acesso_llm(c, eid)
        n = _norma_com_texto(c)
        r = c.post("/api/requisitos/sugerir", json={"norma_id": n["id"], "acesso_id": acesso_id})
        assert r.status_code == 200
        sug = r.json()["sugestoes"]
        assert len(sug) == 1 and sug[0]["titulo"] == "Contexto"
        # aprovação humana cria o requisito
        c.post("/api/requisitos", json={"norma_id": n["id"], **sug[0]})
        assert len(c.get(f"/api/requisitos?norma_id={n['id']}").json()) == 1


def test_sugerir_sem_texto_lido(monkeypatch):
    monkeypatch.setattr("app.services.requisitos_ia.analisar_issues", lambda *a, **k: '{"requisitos":[]}')
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        acesso_id = _acesso_llm(c, eid)
        # norma sem documento/sem leitura
        n = c.post("/api/normas", json={"tipo_fonte": "outro", "titulo": "N", "criar_documento": False}).json()
        r = c.post("/api/requisitos/sugerir", json={"norma_id": n["id"], "acesso_id": acesso_id})
        assert r.status_code == 400


def test_sugerir_json_invalido_da_ia(monkeypatch):
    monkeypatch.setattr("app.services.requisitos_ia.analisar_issues", lambda *a, **k: "isto nao e json")
    with TestClient(app) as c:
        eid, _ = _empresa_com_editor(c)
        acesso_id = _acesso_llm(c, eid)
        n = _norma_com_texto(c)
        r = c.post("/api/requisitos/sugerir", json={"norma_id": n["id"], "acesso_id": acesso_id})
        assert r.status_code == 502


def test_matriz_preparar_snapshot_assinado():
    with TestClient(app) as c:
        _empresa_com_editor(c)
        n = c.post("/api/normas", json={"tipo_fonte": "norma_tecnica", "titulo": "N", "criar_documento": False}).json()
        c.post("/api/requisitos", json={"norma_id": n["id"], "titulo": "Req"})
        r = c.post("/api/conformidade/matriz/preparar", json={"norma_id": n["id"]})
        assert r.status_code == 200
        cia = r.json()["consulta_ia"]
        assert "snapshot" in cia and len(cia["assinatura"]) == 64
        snap = json.loads(cia["snapshot"])
        assert snap["ferramenta"] == "conformidade"
