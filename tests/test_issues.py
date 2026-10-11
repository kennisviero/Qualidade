import io
import os
import uuid

from fastapi.testclient import TestClient

from app.db import DOCS_DIR
from app.main import app


def login(c, email, senha):
    return c.post("/api/auth/login", json={"email": email, "senha": senha})


def criar_empresa(c, nome):
    return c.post("/api/empresas", json={"razao_social": nome}).json()


def criar_editor(c, empresa_id, email=None, papel="admin"):
    email = email or f"ed_{uuid.uuid4().hex[:10]}@x.com"
    c.post(
        "/api/usuarios",
        json={"nome": "Editor", "email": email, "senha": "senha", "papel": papel, "empresa_id": empresa_id},
    )
    c.post("/api/auth/logout")
    login(c, email, "senha")
    return email


def criar_setor(c, empresa_id, nome="Produção"):
    return c.post("/api/setores", json={"nome": nome, "empresa_id": empresa_id}).json()


def criar_issue(c, **kwargs):
    me = c.get("/api/auth/me").json()
    empresa_id = me.get("empresa_id")
    setor_id = kwargs.get("setor_id")
    if setor_id is None and kwargs.get("processo_id") is None and empresa_id and me.get("papel") in ("admin", "editor"):
        setores = c.get(f"/api/setores?empresa_id={empresa_id}").json()
        if setores:
            setor_id = setores[0]["id"]
        else:
            setor_id = c.post("/api/setores", json={"nome": "Area de teste"}).json()["id"]
    body = {
        "descricao": "Defeito encontrado",
        "setor_id": setor_id,
        "detectado_em": "2026-10-10T10:00",
        "comportamento_esperado": "O processo deveria atender ao requisito documentado.",
        "comportamento_observado": "Foi observado desvio no resultado.",
        "evidencias_objetivas": "Registro de inspeção e evidência anexável.",
        "impacto": "Impacto médio no processo, sem risco imediato ao cliente.",
        "acao_emergencial": "Nenhuma ação emergencial adotada até o momento.",
        "o_que": "O resultado ficou fora do padrão.",
        "onde": "Area de teste",
        "quando": "2026-10-10T10:00",
        "quem": "Equipe responsável pelo processo.",
        "como_detectado": "Inspeção manual.",
        **kwargs,
    }
    r = c.post("/api/issues", json=body)
    return r


def test_issue_codigo_sequencial():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa RNC")["id"]
        criar_editor(c, eid)
        r1 = criar_issue(c).json()
        r2 = criar_issue(c).json()
        assert r1["codigo"] == "RNC-0001"
        assert r2["codigo"] == "RNC-0002"
        assert r1["status"] == "registrado"


def test_issue_rejeita_cadastro_vago_e_persiste_dados_iniciais():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Filtro")["id"]
        setor = criar_setor(c, eid, "Qualidade")["id"]
        criar_editor(c, eid)
        vaga = c.post("/api/issues", json={"descricao": "o sistema quebrou", "setor_id": setor})
        assert vaga.status_code == 422
        r = criar_issue(c, setor_id=setor, descricao="Falha objetiva")
        assert r.status_code == 201, r.text
        issue = r.json()
        assert issue["comportamento_observado"] == "Foi observado desvio no resultado."
        assert issue["detectado_em"] == "2026-10-10T10:00"
        assert issue["setor_id"] == setor
        assert issue["pasta"]
        assert issue["criado_por_nome"]


def test_issue_captura_permanece_apos_inicializar_banco_novamente():
    from app.db import init_db

    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Persistencia Issue")["id"]
        setor = criar_setor(c, eid, "Qualidade")["id"]
        criar_editor(c, eid)
        criada = criar_issue(c, setor_id=setor, ambiente="producao", envolvidos_afetados="cliente")
        assert criada.status_code == 201, criada.text
        issue_id = criada.json()["id"]
        init_db()
        registrada = c.get(f"/api/issues/{issue_id}").json()
        assert registrada["setor_id"] == setor
        assert registrada["comportamento_observado"] == "Foi observado desvio no resultado."
        assert registrada["ambiente"] == "producao"
        assert registrada["envolvidos_afetados"] == "cliente"


def test_issue_emissao_rnc_exige_governanca_e_preserva_vinculo():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Emissao RNC")["id"]
        setor = criar_setor(c, eid, "Qualidade")["id"]
        u1 = f"lider_{uuid.uuid4().hex[:8]}@x.com"
        u2 = f"membro_{uuid.uuid4().hex[:8]}@x.com"
        c.post("/api/usuarios", json={"nome": "Lider", "email": u1, "senha": "s", "papel": "admin", "empresa_id": eid})
        c.post("/api/usuarios", json={"nome": "Membro", "email": u2, "senha": "s", "papel": "editor", "empresa_id": eid})
        c.post("/api/auth/logout")
        login(c, u1, "s")
        users = c.get("/api/usuarios").json()
        ids = {u["email"]: u["id"] for u in users}
        issue = criar_issue(c, setor_id=setor).json()
        base = {
            "criticidade": "maior",
            "enquadramento_normativo": "ISO 9001 - item 8.7",
            "origem_gatilho": "auditoria_interna",
            "acao_contencao_definitiva": "Lote segregado e acesso bloqueado.",
            "contencao_responsavel_id": ids[u1],
            "contencao_em": "2026-10-10T11:00",
            "disposicao_inicial": "retrabalho",
            "lider_investigacao_id": ids[u1],
            "auditor_eficacia_id": ids[u2],
            "equipe_investigacao": [ids[u1], ids[u2]],
            "metodologia": "ishikawa",
            "prazo_analise": "2026-10-17",
            "prazo_plano_acao": "2026-10-20",
            "prazo_verificacao_eficacia": "2026-12-10",
        }
        emitted = c.post(f"/api/issues/{issue['id']}/emitir-rnc", json=base)
        assert emitted.status_code == 200, emitted.text
        data = emitted.json()
        assert data["rnc_status"] == "emitida"
        assert data["rnc_codigo"].startswith("RNC-2026-")
        assert data["rnc_issue_codigo"] == issue["codigo"]
        assert data["rnc_criticidade"] == "maior"
        assert data["rnc_emitida_por_nome"] == "Lider"
        assert c.post(f"/api/issues/{issue['id']}/emitir-rnc", json=base).status_code == 409


def test_issue_emissao_rnc_rejeita_equipe_de_uma_pessoa():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa RNC Equipe")["id"]
        setor = criar_setor(c, eid)["id"]
        criar_editor(c, eid)
        me = c.get("/api/auth/me").json()
        issue = criar_issue(c, setor_id=setor).json()
        body = {
            "criticidade": "menor", "enquadramento_normativo": "ISO 9001 - item 10.2",
            "origem_gatilho": "inspecao_rotina", "acao_contencao_definitiva": "Item segregado",
            "contencao_responsavel_id": me["id"], "contencao_em": "2026-10-10T11:00",
            "disposicao_inicial": "refugo", "lider_investigacao_id": me["id"],
            "auditor_eficacia_id": me["id"],
            "equipe_investigacao": [me["id"]], "metodologia": "5_porques",
            "prazo_analise": "2026-10-17", "prazo_plano_acao": "2026-10-20",
            "prazo_verificacao_eficacia": "2026-12-10",
        }
        assert c.post(f"/api/issues/{issue['id']}/emitir-rnc", json=body).status_code == 422


def test_issue_superuser_cria_com_empresa():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa S")["id"]
        setor = criar_setor(c, eid)["id"]
        base = {
            "descricao": "x", "empresa_id": eid, "setor_id": setor,
            "detectado_em": "2026-10-10T10:00", "comportamento_esperado": "Padrao",
            "comportamento_observado": "Desvio", "evidencias_objetivas": "Registro",
            "impacto": "Medio", "acao_emergencial": "Nenhuma", "o_que": "Desvio",
            "onde": "Area", "quando": "Agora", "quem": "Equipe", "como_detectado": "Teste",
        }
        r = c.post("/api/issues", json=base)
        assert r.status_code == 201
        assert r.json()["empresa_id"] == eid
        assert r.json()["codigo"] == "RNC-0001"
        # superuser sem empresa e sem setor -> 400
        assert c.post("/api/issues", json={"descricao": "y"}).status_code == 400


def test_issue_tenancy():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        ea = criar_empresa(c, "Empresa A")["id"]
        eb = criar_empresa(c, "Empresa B")["id"]
        ua = f"ua_{uuid.uuid4().hex[:8]}@x.com"
        ub = f"ub_{uuid.uuid4().hex[:8]}@x.com"
        c.post("/api/usuarios", json={"nome": "UA", "email": ua, "senha": "s", "papel": "admin", "empresa_id": ea})
        c.post("/api/usuarios", json={"nome": "UB", "email": ub, "senha": "s", "papel": "admin", "empresa_id": eb})
        c.post("/api/auth/logout")
        login(c, ua, "s")
        issue = criar_issue(c).json()
        c.post("/api/auth/logout")
        login(c, ub, "s")
        assert c.get("/api/issues").json() == []
        assert c.get(f"/api/issues/{issue['id']}").status_code == 403


def test_issue_resultado_esperado_do_plano():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa RE")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        r = c.put(f"/api/issues/{issue['id']}", json={"resultado_esperado": "Lote 100% liberado"})
        assert r.status_code == 200
        assert r.json()["resultado_esperado"] == "Lote 100% liberado"
        assert c.get(f"/api/issues/{issue['id']}").json()["resultado_esperado"] == "Lote 100% liberado"


def test_issue_campos_tipo_severidade_etapa():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Campos")["id"]
        criar_editor(c, eid)
        r = criar_issue(
            c, tipo="fora_especificacao", severidade="critica", etapa_captura="inspecao_final"
        )
        assert r.status_code == 201
        i = r.json()
        assert i["tipo"] == "fora_especificacao"
        assert i["severidade"] == "critica"
        assert i["etapa_captura"] == "inspecao_final"
        # padrões
        i2 = criar_issue(c).json()
        assert i2["status"] == "registrado"
        # PUT atualiza os novos campos
        put = c.put(
            f"/api/issues/{i['id']}",
            json={"resultado_esperado": "Plano definido", "tipo": "defeito", "severidade": "alta"},
        )
        assert put.status_code == 200
        j = put.json()
        assert j["resultado_esperado"] == "Plano definido"
        assert j["tipo"] == "defeito"
        assert j["severidade"] == "alta"


def test_issue_status_em_execucao():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Exec")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A1"}).json()
        # criar ação -> plano_acao
        assert c.get(f"/api/issues/{issue['id']}").json()["status"] == "plano_acao"
        # iniciar ação -> em_execucao
        c.put(f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "em_andamento"})
        assert c.get(f"/api/issues/{issue['id']}").json()["status"] == "em_execucao"
        # voltar pro backlog não regride para executando
        c.put(f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "backlog"})
        assert c.get(f"/api/issues/{issue['id']}").json()["status"] == "em_execucao"


def test_issue_investigar_causa_regra():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa X")["id"]
        criar_editor(c, eid)
        assert criar_issue(c, investigar_causa=1).status_code == 422
        assert criar_issue(c, investigar_causa=0, usar_ishikawa=1).status_code == 422
        assert criar_issue(c, investigar_causa=1, usar_ishikawa=1).status_code == 201


def test_issue_ishikawa_link_e_update():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Ishi")["id"]
        setor = criar_setor(c, eid, "Qualidade")["id"]
        criar_editor(c, eid)
        issue = criar_issue(
            c, setor_id=setor, investigar_causa=1, usar_ishikawa=1
        ).json()

        categorias = {
            "metodo": "Procedimento",
            "maquina": "Equipamento",
            "medida": "Inspeção",
            "meio": "Ambiente",
            "material": "Insumo",
            "mao": "Operador",
        }
        causas = {
            "metodo": ["Falta de treinamento"],
            "mao": ["Fadiga do operador"],
        }
        r = c.post(
            f"/api/issues/{issue['id']}/ishikawa",
            json={
                "setor_id": setor,
                "nome": "Analise Solda",
                "efeito": "Trinca",
                "ativo": "Máquina #2",
                "descricao": "Defeitos de solda",
                "causas": causas,
                "categorias": categorias,
            },
        )
        assert r.status_code == 201
        ishi = r.json()
        assert ishi["causas"]["metodo"] == ["Falta de treinamento"]
        assert ishi["categorias"]["mao"] == "Operador"
        assert ishi["pasta"] == "Empresa Ishi/Qualidade/Analise Solda"

        # edição parcial (merge) via PUT no ishikawa vinculado
        r = c.put(
            f"/api/issues/{issue['id']}/ishikawa",
            json={"efeito": "Novo defeito", "categorias": {"metodo": "Método Atualizado"}},
        )
        assert r.status_code == 200
        j = r.json()
        assert j["efeito"] == "Novo defeito"
        assert j["categorias"]["metodo"] == "Método Atualizado"
        assert j["categorias"]["mao"] == "Operador"
        assert j["causas"]["metodo"] == ["Falta de treinamento"]

        detalhe = c.get(f"/api/issues/{issue['id']}").json()
        assert detalhe["ishikawa"]["id"] == ishi["id"]


def test_issue_porques_sem_repeticao():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Y")["id"]
        setor = criar_setor(c, eid)["id"]
        criar_editor(c, eid)
        issue = criar_issue(
            c, setor_id=setor, investigar_causa=1, usar_ishikawa=1, usar_porques=1
        ).json()
        c.post(
            f"/api/issues/{issue['id']}/ishikawa",
            json={"setor_id": setor, "nome": "Ishi RNC", "efeito": "Defeito", "causas": {"mao": ["Operador", "Treinamento"]}},
        )
        porques = [
            {"numero": 1, "item_ishikawa": "Operador", "resposta": "pq"},
            {"numero": 2, "item_ishikawa": "Operador", "resposta": "pq"},
        ]
        r = c.put(f"/api/issues/{issue['id']}/porques", json={"porques": porques, "causa_raiz": "raiz"})
        assert r.status_code == 422
        porques_ok = [
            {"numero": 1, "item_ishikawa": "Operador", "resposta": "pq"},
            {"numero": 2, "item_ishikawa": "Treinamento", "resposta": "pq"},
        ]
        assert c.put(
            f"/api/issues/{issue['id']}/porques", json={"porques": porques_ok, "causa_raiz": "raiz"}
        ).status_code == 200


def test_issue_acao_status_e_data_inicio():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Z")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "Ação 1"}).json()
        assert acao["status"] == "backlog"
        assert acao["data_inicio"] is None
        upd = c.put(
            f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "em_andamento"}
        ).json()
        assert upd["status"] == "em_andamento"
        assert upd["data_inicio"] is not None


def test_issue_finalizar():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa W")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "Ação 1"}).json()
        # finalizar com ação pendente deve falhar
        r = c.post(f"/api/issues/{issue['id']}/finalizar", json={"resultado_alcancado": "ok", "nota_atingimento": 4})
        assert r.status_code == 422
        c.put(f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "finalizada"})
        r = c.post(f"/api/issues/{issue['id']}/finalizar", json={"resultado_alcancado": "ok", "nota_atingimento": 4})
        assert r.status_code == 200
        assert r.json()["status"] == "finalizado"
        assert r.json()["nota_atingimento"] == 4
        # nota inválida
        assert c.post(
            f"/api/issues/{issue['id']}/finalizar", json={"resultado_alcancado": "x", "nota_atingimento": 9}
        ).status_code == 422


def test_issue_exclusao_transacional():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Del")["id"]
        setor = criar_setor(c, eid)["id"]
        criar_editor(c, eid)
        issue = criar_issue(c, setor_id=setor, investigar_causa=1, usar_ishikawa=1).json()
        c.post(
            f"/api/issues/{issue['id']}/ishikawa",
            json={"setor_id": setor, "nome": "Ishi Del", "efeito": "E", "causas": {"mao": ["x"]}},
        )
        c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"})
        pasta = issue["pasta"]
        ishi_pasta = None
        detail = c.get(f"/api/issues/{issue['id']}").json()
        if detail.get("ishikawa"):
            ishi_pasta = detail["ishikawa"]["pasta"]
        assert c.delete(f"/api/issues/{issue['id']}").status_code == 204
        assert c.get(f"/api/issues/{issue['id']}").status_code == 404
        assert not (DOCS_DIR / pasta).exists()
        if ishi_pasta:
            assert not (DOCS_DIR / ishi_pasta).exists()


def test_issue_visualizador_403():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa V")["id"]
        email = f"v_{uuid.uuid4().hex[:8]}@x.com"
        c.post(
            "/api/usuarios",
            json={"nome": "V", "email": email, "senha": "s", "papel": "visualizador", "empresa_id": eid},
        )
        c.post("/api/auth/logout")
        login(c, email, "s")
        assert c.get("/api/issues").status_code == 200
        assert criar_issue(c).status_code == 403


def test_issue_kanban_global():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa K")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A1"})
        c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A2"})
        kanban = c.get("/api/issues/kanban").json()
        assert len(kanban) == 2
        assert all(a["status"] == "backlog" for a in kanban)
        assert all(a["issue_id"] == issue["id"] for a in kanban)


def test_issue_documentos_arvore():
    from app.docs import folder_for

    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Papéis")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        folder = folder_for(issue["pasta"])
        assert folder.is_dir()

        c.post(
            f"/api/issues/{issue['id']}/pastas",
            json={"nome": "Anexos", "subpasta": ""},
        )
        c.post(
            f"/api/issues/{issue['id']}/arquivos",
            data={"subpasta": "Anexos"},
            files={"file": ("laudo.pdf", b"pdf", "application/pdf")},
        )

        resp = c.get(f"/api/issues/{issue['id']}/arvore").json()["arvore"]
        assert resp["nome"] == "RNC-0001"
        assert [f["nome"] for f in resp["filhos"]] == ["Anexos"]
        assert resp["filhos"][0]["filhos"][0]["nome"] == "laudo.pdf"

        r = c.get(f"/api/issues/{issue['id']}/arquivo", params={"caminho": "Anexos/laudo.pdf"})
        assert r.status_code == 200
        assert r.content == b"pdf"

        assert c.delete(
            f"/api/issues/{issue['id']}/objetos", params={"caminho": "Anexos/laudo.pdf"}
        ).status_code == 204
        assert c.delete(
            f"/api/issues/{issue['id']}/objetos", params={"caminho": "Anexos"}
        ).status_code == 204
        resp = c.get(f"/api/issues/{issue['id']}/arvore").json()["arvore"]
        assert resp["filhos"] == []


def test_issue_stats():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Stats")["id"]
        setor = criar_setor(c, eid, "Produção")["id"]
        criar_editor(c, eid)
        criar_issue(c, setor_id=setor, tipo="nao_conformidade", severidade="alta")
        criar_issue(c, tipo="fora_especificacao", severidade="media")
        stats = c.get("/api/issues/stats").json()
        assert stats["total"] == 2
        dims = {d["chave"]: d for d in stats["dimensoes"]}
        status = dims["status"]["dados"]["itens"]
        assert {t["rotulo"]: t["frequencia"] for t in status} == {
            "registrado": 2,
        }
        setor_d = dims["setor"]["dados"]["itens"]
        assert {s["rotulo"]: s["frequencia"] for s in setor_d} == {
            "Produção": 2,
        }
        # tenancy: outro usuário da mesma empresa vê os mesmos
        email = f"ed_{uuid.uuid4().hex[:10]}@x.com"
        c.post(
            "/api/usuarios",
            json={"nome": "E", "email": email, "senha": "s", "papel": "admin", "empresa_id": eid},
        )
        c.post("/api/auth/logout")
        login(c, email, "s")
        assert c.get("/api/issues/stats").json()["total"] == 2


def test_issue_trends():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        eid = criar_empresa(c, "Empresa Trends")["id"]
        criar_editor(c, eid)
        issue = criar_issue(c).json()
        acao = c.post(f"/api/issues/{issue['id']}/acoes", json={"descricao": "A"}).json()
        c.put(f"/api/issues/{issue['id']}/acoes/{acao['id']}/status", json={"status": "finalizada"})
        c.post(f"/api/issues/{issue['id']}/finalizar", json={"resultado_alcancado": "ok", "nota_atingimento": 5})
        criar_issue(c)
        t = c.get("/api/issues/trends").json()
        assert t["criadas"] == 2
        assert t["em_aberto"] == 1
        assert t["finalizadas"] == 1
        assert sum(p["total"] for p in t["por_criacao"]) == 2
        assert sum(p["total"] for p in t["por_finalizacao"]) == 1


def test_transcricao_txt():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        r = c.post("/api/transcricao", files={"file": ("relato.txt", io.BytesIO(b"nao conforme"), "text/plain")})
        assert r.status_code == 200
        assert r.json()["texto"] == "nao conforme"


def test_transcricao_formato_invalido():
    with TestClient(app) as c:
        login(c, "admin", "admin")
        r = c.post("/api/transcricao", files={"file": ("x.png", io.BytesIO(b"123"), "image/png")})
        assert r.status_code == 400
