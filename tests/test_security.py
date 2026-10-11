"""Testes de segurança: sanitização de entrada (XSS)."""
from fastapi.testclient import TestClient

from app.main import app
from app.security import sanitize_text


def login(c, email="admin", senha="admin"):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def test_sanitize_text_neutraliza_xss():
    assert sanitize_text('<script>alert(1)</script>Ola') == 'alert(1)Ola'
    assert sanitize_text('<img src=x onerror=alert(1)>') == ''
    assert sanitize_text('javascript:alert(1)') == 'alert(1)'
    assert sanitize_text('<b>negrito</b> texto') == 'negrito texto'
    assert sanitize_text({'a': '<i>x</i>', 'b': ['<u>y</u>']}) == {'a': 'x', 'b': ['y']}
    assert sanitize_text(None) is None
    assert sanitize_text(123) == 123
    # conteúdo normal preservado
    assert sanitize_text('Defeito no produto — 3° lote') == 'Defeito no produto — 3° lote'


def test_campos_sanitizados_na_criacao():
    with TestClient(app) as c:
        login(c)
        r = c.post("/api/empresas", json={"razao_social": "<script>x</script>Empresa"})
        assert r.status_code == 201
        assert r.json()["razao_social"] == "xEmpresa"

        setor = c.post("/api/setores", json={"nome": "<b>Prod</b>", "empresa_id": r.json()["id"]}).json()
        assert setor["nome"] == "Prod"


def test_sintaxe_fluxograma_nao_sanitizada():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa Seg")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        sintaxe = "flowchart TD\n    A[Início] -->|x| B[Fim]"
        r = c.post("/api/processos", json={"setor_id": setor["id"], "nome": "Proc", "sintaxe": sintaxe})
        assert r.status_code == 201
        # sintaxe preservada (Mermaid precisa de -->)
        assert r.json()["sintaxe"] == sintaxe


def test_ishikawa_campos_sanitizados():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa Seg2")
        setor = c.post("/api/setores", json={"nome": "S", "empresa_id": empresa["id"]}).json()
        issue = c.post(
            "/api/issues",
            json={
                "empresa_id": empresa["id"], "setor_id": setor["id"], "investigar_causa": 1, "usar_ishikawa": 1,
                "detectado_em": "2026-10-10T10:00", "comportamento_esperado": "Padrao",
                "comportamento_observado": "Desvio", "evidencias_objetivas": "Registro",
                "impacto": "Medio", "acao_emergencial": "Nenhuma", "o_que": "Desvio",
                "onde": "Area", "quando": "Agora", "quem": "Equipe", "como_detectado": "Teste",
            },
        ).json()
        r = c.post(
            f"/api/issues/{issue['id']}/ishikawa",
            json={
                "setor_id": setor["id"],
                "nome": "Ishi",
                "efeito": "<script>alert(1)</script>Trinca",
                "causas": {"metodo": ["<img src=x onerror=alert(1)>", "causa ok"]},
                "categorias": {"metodo": "<b>Procedimento</b>"},
            },
        )
        assert r.status_code == 201
        j = r.json()
        assert j["efeito"] == "alert(1)Trinca"
        assert j["causas"]["metodo"] == ["", "causa ok"]
        assert j["categorias"]["metodo"] == "Procedimento"


def test_senha_nao_sanitizada():
    with TestClient(app) as c:
        login(c)
        empresa = criar_empresa(c, "Empresa Seg3")
        senha = "a<b>c&d"
        r = c.post(
            "/api/usuarios",
            json={"nome": "U", "email": "seg3@x.com", "senha": senha, "papel": "editor", "empresa_id": empresa["id"]},
        )
        assert r.status_code == 201
        # login com a senha original funciona (não foi alterada pela sanitização)
        c.post("/api/auth/logout")
        assert login(c, "seg3@x.com", senha).status_code == 200
