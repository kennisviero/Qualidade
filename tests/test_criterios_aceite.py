"""Critérios de aceite globais do PRD (Documentos/PRD.md, seção 9) e regras da issue (3.4)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import verify_password
from app.db import get_connection
from app.main import app


def login(c, email, senha):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def criar_usuario(c, empresa_id, papel="admin", senha="s"):
    email = f"u_{uuid.uuid4().hex[:10]}@x.com"
    r = c.post(
        "/api/usuarios",
        json={"nome": "U", "email": email, "senha": senha, "papel": papel, "empresa_id": empresa_id},
    )
    assert r.status_code == 201, r.text
    return email, r.json()["id"]


def entrar_como(c, email, senha="s"):
    c.post("/api/auth/logout")
    assert login(c, email, senha).status_code == 200


def preparar_empresa(c, nome):
    """Superusuário cria empresa + admin + visualizador; retorna (empresa_id, email_admin, email_visualizador)."""
    login(c, "admin", "admin")
    eid = criar_empresa(c, nome)["id"]
    admin_email, _ = criar_usuario(c, eid, "admin")
    vis_email, _ = criar_usuario(c, eid, "visualizador")
    return eid, admin_email, vis_email


def criar_issue(c, descricao="x", **extra):
    setores = c.get("/api/setores").json()
    setor_id = setores[0]["id"] if setores else c.post("/api/setores", json={"nome": "Area de teste"}).json()["id"]
    payload = {
        "descricao": descricao,
        "setor_id": setor_id,
        "detectado_em": "2026-10-10T10:00",
        "comportamento_esperado": "Padrao documentado",
        "comportamento_observado": "Desvio observado",
        "evidencias_objetivas": "Registro de teste",
        "impacto": "Impacto controlado",
        "acao_emergencial": "Nenhuma acao emergencial adotada",
        "o_que": descricao,
        "onde": "Area de teste",
        "quando": "2026-10-10T10:00",
        "quem": "Equipe de teste",
        "como_detectado": "Inspecao manual",
    }
    payload.update(extra)
    return c.post("/api/issues", json=payload)


# ---------- Senha nunca em texto puro ----------

def test_senha_gravada_como_hash():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Hash")["id"]
        email, uid = criar_usuario(c, eid, senha="segredo123")
        with get_connection() as conn:
            row = conn.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (uid,)).fetchone()
        assert row["senha_hash"] != "segredo123"
        assert "segredo123" not in row["senha_hash"]
        assert verify_password("segredo123", row["senha_hash"])
        with get_connection() as conn:
            admin = conn.execute("SELECT senha_hash FROM usuarios WHERE email = 'admin'").fetchone()
        assert admin["senha_hash"] != "admin"


# ---------- Visualizador recebe 403 em qualquer escrita ----------

ESCRITAS = [
    ("post", "/api/setores", {"nome": "S"}),
    ("put", "/api/setores/{setor}", {"nome": "S2"}),
    ("delete", "/api/setores/{setor}", None),
    ("post", "/api/processos", {"nome": "P"}),
    ("put", "/api/processos/{processo}", {"nome": "P2"}),
    ("delete", "/api/processos/{processo}", None),
    ("post", "/api/processos/{processo}/revisoes", {"sintaxe": "x"}),
    ("post", "/api/processos/{processo}/aprovar", None),
    ("post", "/api/processos/{processo}/pastas", {"nome": "X", "subpasta": ""}),
    ("delete", "/api/processos/{processo}/objetos?caminho=X", None),
    ("post", "/api/usuarios", {"nome": "N", "email": "n@x.com", "senha": "s", "papel": "editor"}),
    ("put", "/api/usuarios/{vis}", {"nome": "N"}),
    ("delete", "/api/usuarios/{vis}", None),
    ("post", "/api/issues", {"descricao": "x"}),
    ("put", "/api/issues/{issue}", {"descricao": "y"}),
    ("delete", "/api/issues/{issue}", None),
    ("post", "/api/issues/{issue}/ishikawa", {"nome": "I"}),
    ("put", "/api/issues/{issue}/ishikawa", {"efeito": "e"}),
    ("put", "/api/issues/{issue}/porques", {"porques": [], "causa_raiz": ""}),
    ("post", "/api/issues/{issue}/acoes", {"descricao": "A"}),
    ("put", "/api/issues/{issue}/acoes/{acao}", {"descricao": "B"}),
    ("put", "/api/issues/{issue}/acoes/{acao}/status", {"status": "iniciada"}),
    ("delete", "/api/issues/{issue}/acoes/{acao}", None),
    ("post", "/api/issues/{issue}/finalizar", {"resultado_alcancado": "ok", "nota_atingimento": 3}),
    ("post", "/api/issues/{issue}/pastas", {"nome": "X", "subpasta": ""}),
    ("delete", "/api/issues/{issue}/objetos?caminho=X", None),
]


def test_visualizador_403_em_toda_escrita():
    with TestClient(app) as c:
        eid, admin_email, vis_email = preparar_empresa(c, "Empresa Vis403")
        entrar_como(c, admin_email)
        ids = {
            "setor": c.post("/api/setores", json={"nome": "Setor V"}).json()["id"],
            "processo": c.post("/api/processos", json={"nome": "Proc V"}).json()["id"],
        }
        issue = criar_issue(c).json()
        ids["issue"] = issue["id"]
        ids["acao"] = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"}).json()["id"]
        ids["vis"] = next(u["id"] for u in c.get("/api/usuarios").json() if u["email"] == vis_email)

        entrar_como(c, vis_email)
        falhas = []
        for metodo, rota, body in ESCRITAS:
            url = rota.format(**ids)
            kwargs = {"json": body} if body is not None else {}
            r = getattr(c, metodo)(url, **kwargs) if metodo != "delete" else c.delete(url)
            if r.status_code != 403:
                falhas.append(f"{metodo.upper()} {url} -> {r.status_code}")
        r = c.post(
            f"/api/issues/{ids['issue']}/arquivos",
            data={"subpasta": ""},
            files={"file": ("a.txt", b"x", "text/plain")},
        )
        if r.status_code != 403:
            falhas.append(f"POST arquivos -> {r.status_code}")
        assert not falhas, falhas


# ---------- Isolamento entre empresas ----------

def test_isolamento_entre_empresas():
    with TestClient(app) as c:
        ea, admin_a, _ = preparar_empresa(c, "Empresa IsoA")
        login(c, "admin", "admin")
        eb = criar_empresa(c, "Empresa IsoB")["id"]
        admin_b, _ = criar_usuario(c, eb, "admin")

        entrar_como(c, admin_a)
        issue = criar_issue(c, descricao="da empresa A").json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"}).json()
        emails_a = {u["email"] for u in c.get("/api/usuarios").json()}

        entrar_como(c, admin_b)
        emails_b = {u["email"] for u in c.get("/api/usuarios").json()}
        assert not (emails_a & emails_b)
        assert c.get("/api/issues/kanban").json() == []
        assert c.get("/api/issues/stats").json()["total"] == 0
        assert c.get("/api/issues/trends").json()["criadas"] == 0
        assert c.get(f"/api/issues/{issue['id']}/acoes").status_code in (403, 404)
        assert c.put(
            f"/api/issues/{issue['id']}/acoes/{acao['id']}", json={"descricao": "x"}
        ).status_code in (403, 404)
        assert c.get(f"/api/issues/{issue['id']}/arvore").status_code in (403, 404)
        assert c.get(f"/api/empresas/{ea}").status_code in (403, 404)


# ---------- Ciclo fechado da issue ----------

def test_ciclo_completo_da_issue():
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, "Empresa Ciclo")
        entrar_como(c, admin_email)
        # 1. Captura
        issue = c.post("/api/issues", json={"descricao": "Peça fora de medida", "severidade": "alta"}).json()
        issue = criar_issue(c, descricao="Peca fora de medida", severidade="alta").json()
        iid = issue["id"]
        assert issue["status"] == "registrado"
        # 2. Contenção: investigar com 5 Porquês
        r = c.put(f"/api/issues/{iid}", json={"lote": "L1", "investigar_causa": 1, "usar_porques": 1})
        assert r.status_code == 200
        # 3. Investigação
        r = c.put(
            f"/api/issues/{iid}/porques",
            json={"porques": [{"numero": 1, "item_ishikawa": "", "resposta": "Ferramenta gasta"}],
                  "causa_raiz": "Ferramenta gasta"},
        )
        assert r.status_code == 200
        assert c.get(f"/api/issues/{iid}").json()["status"] == "em_investigacao"
        # 4. Ação
        acao = c.post(f"/api/issues/{iid}/acoes", json={"descricao": "Trocar ferramenta"}).json()
        assert c.get(f"/api/issues/{iid}").json()["status"] == "plano_acao"
        c.put(f"/api/issues/{iid}/acoes/{acao['id']}/status", json={"status": "em_andamento"})
        assert c.get(f"/api/issues/{iid}").json()["status"] == "em_execucao"
        c.put(f"/api/issues/{iid}/acoes/{acao['id']}/status", json={"status": "finalizada"})
        # 5. Finalização com nota
        r = c.post(f"/api/issues/{iid}/finalizar",
                   json={"resultado_alcancado": "Medida dentro da tolerância", "nota_atingimento": 5})
        assert r.status_code == 200
        final = r.json()
        assert final["status"] == "finalizado"
        assert final["nota_atingimento"] == 5
        assert final["finalizado_em"]


# ---------- Regras da issue ----------

def test_put_nao_finaliza_issue():
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, "Empresa PutFin")
        entrar_como(c, admin_email)
        issue = criar_issue(c).json()
        r = c.put(f"/api/issues/{issue['id']}", json={"status": "finalizado"})
        assert r.status_code == 422
        assert c.get(f"/api/issues/{issue['id']}").json()["status"] == "registrado"


def test_criar_acao_nao_regride_status():
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, "Empresa Regride")
        entrar_como(c, admin_email)
        issue = criar_issue(c).json()
        iid = issue["id"]
        a1 = c.post(f"/api/issues/{iid}/acoes", json={"descricao": "A1"}).json()
        c.put(f"/api/issues/{iid}/acoes/{a1['id']}/status", json={"status": "em_andamento"})
        assert c.get(f"/api/issues/{iid}").json()["status"] == "em_execucao"
        c.post(f"/api/issues/{iid}/acoes", json={"descricao": "A2"})
        assert c.get(f"/api/issues/{iid}").json()["status"] == "em_execucao"


@pytest.mark.parametrize("resultado", ["", "   "])
def test_finalizar_exige_resultado(resultado):
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, f"Empresa Res {uuid.uuid4().hex[:6]}")
        entrar_como(c, admin_email)
        issue = criar_issue(c).json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"}).json()
        c.put(f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "finalizada"})
        r = c.post(f"/api/issues/{issue['id']}/finalizar",
                   json={"resultado_alcancado": resultado, "nota_atingimento": 3})
        assert r.status_code == 422


def test_finalizar_exige_ao_menos_uma_acao():
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, "Empresa SemAcao")
        entrar_como(c, admin_email)
        issue = criar_issue(c).json()
        r = c.post(f"/api/issues/{issue['id']}/finalizar",
                   json={"resultado_alcancado": "ok", "nota_atingimento": 3})
        assert r.status_code == 422


def test_excluir_issue_remove_acoes():
    with TestClient(app) as c:
        _, admin_email, _ = preparar_empresa(c, "Empresa ExclAcoes")
        entrar_como(c, admin_email)
        issue = criar_issue(c).json()
        c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"})
        assert c.delete(f"/api/issues/{issue['id']}").status_code == 204
        with get_connection() as conn:
            n = conn.execute("SELECT COUNT(*) FROM acoes WHERE issue_id = ?", (issue["id"],)).fetchone()[0]
        assert n == 0


# ---------- Empresa desativada ----------

def test_empresa_desativada_bloqueia_acesso():
    with TestClient(app) as c:
        eid, admin_email, _ = preparar_empresa(c, "Empresa Inativa")
        entrar_como(c, admin_email)
        assert c.get("/api/auth/me").status_code == 200
        # superusuário desativa a empresa; a sessão do admin da empresa cai
        with TestClient(app) as su:
            login(su, "admin", "admin")
            assert su.put(f"/api/empresas/{eid}", json={"ativo": 0}).status_code == 200
            assert su.get("/api/auth/me").status_code == 200  # superusuário não é afetado
        assert c.get("/api/auth/me").status_code == 401
        c.cookies.clear()
        r = login(c, admin_email, "s")
        assert r.status_code == 401
        assert r.json()["detail"] == "Empresa desativada"
        # reativar libera
        login(c, "admin", "admin")
        c.put(f"/api/empresas/{eid}", json={"ativo": 1})
        c.post("/api/auth/logout")
        assert login(c, admin_email, "s").status_code == 200
