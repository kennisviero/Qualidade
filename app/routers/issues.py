import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import get_current_user, is_superuser, require_papel
from app.calculations import pareto
from app.db import DOCS_DIR, get_connection
from app.docs import (
    build_ishikawa_pasta,
    build_issue_pasta,
    delete_path,
    ensure_pasta,
    folder_for,
    guess_mime,
    node,
    safe_rel,
    sanitize,
    save_file,
)
from app.security import SafeModel

router = APIRouter(prefix="/api/issues", tags=["issues"])

editor_dep = require_papel("admin", "editor")

ISSUE_STATUSES = ("registrado", "em_investigacao", "plano_acao", "em_execucao", "finalizado")
ACAO_STATUSES = ("backlog", "iniciada", "em_andamento", "em_revisao", "finalizada")
SEVERIDADES = ("baixa", "media", "alta", "critica")
RNC_CRITICIDADES = ("maior", "menor")
RNC_ORIGENS = ("auditoria_interna", "auditoria_externa", "reclamacao_cliente", "inspecao_rotina")
RNC_DISPOSICOES = ("refugo", "retrabalho", "devolucao_fornecedor", "liberacao_concessao")
RNC_METODOLOGIAS = ("5_porques", "ishikawa", "fmea")


def now():
    return datetime.now(timezone.utc).isoformat()


class IssueIn(SafeModel):
    empresa_id: int | None = None
    setor_id: int | None = None
    processo_id: int | None = None
    descricao: str = ""
    data: str = ""
    origem: str = ""
    produto: str = ""
    norma: str = ""
    reincidencia: int = 0
    tipo: str = "nao_conformidade"
    severidade: str = "media"
    etapa_captura: str = ""
    detectado_em: str = ""
    comportamento_esperado: str = ""
    comportamento_observado: str = ""
    evidencias_objetivas: str = ""
    codigo_erro: str = ""
    ambiente: str = ""
    envolvidos_afetados: str = ""
    impacto: str = ""
    acao_emergencial: str = ""
    o_que: str = ""
    onde: str = ""
    quando: str = ""
    quem: str = ""
    por_que_inicial: str = ""
    como_detectado: str = ""
    ultimo_ok_em: str = ""
    alarme_em: str = ""
    margem_seguranca_min: str = ""
    codigo_material: str = ""
    lote: str = ""
    ordem_producao: str = ""
    sn_inicio: str = ""
    sn_fim: str = ""
    linha_posto: str = ""
    status_estoque: str = ""
    posicao_estoque: str = ""
    operador_id: int | None = None
    inspetor_id: int | None = None
    motivo_bloqueio: str = ""
    investigar_causa: int = 0
    usar_ishikawa: int = 0
    usar_porques: int = 0


class IssueUpdate(SafeModel):
    setor_id: int | None = None
    processo_id: int | None = None
    descricao: str | None = None
    data: str | None = None
    origem: str | None = None
    produto: str | None = None
    norma: str | None = None
    reincidencia: int | None = None
    tipo: str | None = None
    severidade: str | None = None
    etapa_captura: str | None = None
    detectado_em: str | None = None
    comportamento_esperado: str | None = None
    comportamento_observado: str | None = None
    evidencias_objetivas: str | None = None
    codigo_erro: str | None = None
    ambiente: str | None = None
    envolvidos_afetados: str | None = None
    impacto: str | None = None
    acao_emergencial: str | None = None
    o_que: str | None = None
    onde: str | None = None
    quando: str | None = None
    quem: str | None = None
    por_que_inicial: str | None = None
    como_detectado: str | None = None
    ultimo_ok_em: str | None = None
    alarme_em: str | None = None
    margem_seguranca_min: str | None = None
    codigo_material: str | None = None
    lote: str | None = None
    ordem_producao: str | None = None
    sn_inicio: str | None = None
    sn_fim: str | None = None
    linha_posto: str | None = None
    status_estoque: str | None = None
    posicao_estoque: str | None = None
    operador_id: int | None = None
    inspetor_id: int | None = None
    motivo_bloqueio: str | None = None
    investigar_causa: int | None = None
    usar_ishikawa: int | None = None
    usar_porques: int | None = None
    resultado_esperado: str | None = None
    status: str | None = None


class RncEmissaoIn(SafeModel):
    criticidade: str
    enquadramento_normativo: str
    origem_gatilho: str
    acao_contencao_definitiva: str
    contencao_responsavel_id: int
    contencao_em: str
    disposicao_inicial: str
    lider_investigacao_id: int
    equipe_investigacao: list[int]
    metodologia: str
    prazo_analise: str
    prazo_plano_acao: str
    prazo_verificacao_eficacia: str
    auditor_eficacia_id: int


class IshikawaLinkIn(SafeModel):
    setor_id: int | None = None
    nome: str
    efeito: str = ""
    ativo: str = ""
    descricao: str = ""
    causas: dict = {}
    categorias: dict = {}


class IshikawaUpdateIn(SafeModel):
    nome: str | None = None
    efeito: str | None = None
    ativo: str | None = None
    descricao: str | None = None
    causas: dict | None = None
    categorias: dict | None = None


class PorquesIn(SafeModel):
    porques: list = []
    causa_raiz: str = ""


class AcaoIn(SafeModel):
    descricao: str
    responsavel_id: int | None = None
    prazo_limite: str = ""
    observacao: str = ""
    por_que: str = ""
    onde: str = ""
    como: str = ""
    quanto: str = ""


class AcaoUpdate(SafeModel):
    descricao: str | None = None
    responsavel_id: int | None = None
    prazo_limite: str | None = None
    observacao: str | None = None
    por_que: str | None = None
    onde: str | None = None
    como: str | None = None
    quanto: str | None = None


class AcaoStatusIn(SafeModel):
    status: str


class FinalizarIn(SafeModel):
    resultado_alcancado: str
    nota_atingimento: int


class PastaIn(SafeModel):
    nome: str
    subpasta: str = ""


class ArquivoIn(SafeModel):
    nome: str
    subpasta: str = ""


def _valida_investigacao(investigar_causa, usar_ishikawa, usar_porques):
    if investigar_causa and not (usar_ishikawa or usar_porques):
        raise HTTPException(
            status_code=422,
            detail="Ao investigar a causa, marque ao menos uma ferramenta (Ishikawa ou 5 Porquês)",
        )
    if not investigar_causa and (usar_ishikawa or usar_porques):
        raise HTTPException(status_code=422, detail="Ferramentas de causa exigem investigacao habilitada")


INITIAL_REQUIRED_FIELDS = (
    ("detectado_em", "Data e hora da detecção"),
    ("comportamento_esperado", "Comportamento esperado"),
    ("comportamento_observado", "Comportamento observado"),
    ("evidencias_objetivas", "Evidências objetivas"),
    ("impacto", "Impacto"),
    ("acao_emergencial", "Ação de emergência adotada"),
    ("o_que", "O que aconteceu"),
    ("onde", "Onde ocorreu"),
    ("quando", "Quando ocorreu"),
    ("quem", "Quem foi afetado/envolvido"),
    ("como_detectado", "Como foi detectado"),
)


def _validar_cadastro_inicial_legacy(issue, conn, empresa_id, user, existing=None):
    """Garante o conjunto factual mínimo antes de criar ou editar uma Issue."""
    values = {}
    for field, _label in INITIAL_REQUIRED_FIELDS:
        value = getattr(issue, field, None)
        if value is None and existing is not None:
            value = existing[field]
        values[field] = (value or "").strip()
    missing = [label for field, label in INITIAL_REQUIRED_FIELDS if not values[field]]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Preencha os dados iniciais obrigatórios: " + ", ".join(missing),
        )
    if issue.setor_id is None and issue.processo_id is None and existing is None:
        raise HTTPException(status_code=422, detail="Informe a área/setor ou o processo afetado")
    setor_id = getattr(issue, "setor_id", None)
    processo_id = getattr(issue, "processo_id", None)
    operador_id = getattr(issue, "operador_id", None)
    inspetor_id = getattr(issue, "inspetor_id", None)
    if existing is not None:
        setor_id = setor_id if setor_id is not None else existing["setor_id"]
        processo_id = processo_id if processo_id is not None else existing["processo_id"]
        operador_id = operador_id if operador_id is not None else existing["operador_id"]
        inspetor_id = inspetor_id if inspetor_id is not None else existing["inspetor_id"]
        if setor_id is None and processo_id is None:
            raise HTTPException(status_code=422, detail="Informe a área/setor ou o processo afetado")
    if setor_id is not None:
        setor = conn.execute("SELECT empresa_id FROM setores WHERE id = ?", (setor_id,)).fetchone()
        if setor is None or setor["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail="Setor/u00e1rea inválido para a empresa da Issue")
    if processo_id is not None:
        processo = conn.execute("SELECT empresa_id FROM processos WHERE id = ?", (processo_id,)).fetchone()
        if processo is None or processo["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail="Processo inválido para a empresa da Issue")
    for field, user_id in (("operador_id", operador_id), ("inspetor_id", inspetor_id)):
        if user_id is None:
            continue
        target = conn.execute("SELECT empresa_id FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        if target is None or target["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail=f"{field} inválido para a empresa da Issue")
    if not investigar_causa and (usar_ishikawa or usar_porques):
        raise HTTPException(
            status_code=422,
            detail="Não é possível usar Ishikawa/5 Porquês sem investigar a causa",
        )


def _next_codigo(conn, empresa_id):
    rows = conn.execute(
        "SELECT codigo FROM issues WHERE empresa_id = ?", (empresa_id,)
    ).fetchall()
    maxn = 0
    for r in rows:
        m = re.match(r"RNC-(\d+)", r["codigo"] or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"RNC-{maxn + 1:04d}"


def _next_rnc_codigo(conn, empresa_id):
    ano = datetime.now(timezone.utc).year
    rows = conn.execute(
        "SELECT rnc_codigo FROM issues WHERE empresa_id = ? AND rnc_codigo LIKE ?",
        (empresa_id, f"RNC-{ano}-%"),
    ).fetchall()
    maxn = 0
    for r in rows:
        m = re.match(rf"RNC-{ano}-(\d+)$", r["rnc_codigo"] or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"RNC-{ano}-{maxn + 1:03d}"


def _validar_cadastro_inicial(issue, conn, empresa_id, existing=None):
    """Valida o conjunto factual minimo antes de criar ou editar uma Issue."""
    values = {}
    for field, _label in INITIAL_REQUIRED_FIELDS:
        value = getattr(issue, field, None)
        if value is None and existing is not None:
            value = existing[field]
        values[field] = (value or "").strip()
    missing = [label for field, label in INITIAL_REQUIRED_FIELDS if not values[field]]
    if missing:
        raise HTTPException(status_code=422, detail="Preencha os dados iniciais obrigatorios: " + ", ".join(missing))

    setor_id = getattr(issue, "setor_id", None)
    processo_id = getattr(issue, "processo_id", None)
    operador_id = getattr(issue, "operador_id", None)
    inspetor_id = getattr(issue, "inspetor_id", None)
    if existing is not None:
        setor_id = setor_id if setor_id is not None else existing["setor_id"]
        processo_id = processo_id if processo_id is not None else existing["processo_id"]
        operador_id = operador_id if operador_id is not None else existing["operador_id"]
        inspetor_id = inspetor_id if inspetor_id is not None else existing["inspetor_id"]
    if setor_id is None and processo_id is None:
        raise HTTPException(status_code=422, detail="Informe a area/setor ou o processo afetado")
    if setor_id is not None:
        setor = conn.execute("SELECT empresa_id FROM setores WHERE id = ?", (setor_id,)).fetchone()
        if setor is None or setor["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail="Setor/area invalido para a empresa da Issue")
    if processo_id is not None:
        processo = conn.execute("SELECT empresa_id FROM processos WHERE id = ?", (processo_id,)).fetchone()
        if processo is None or processo["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail="Processo invalido para a empresa da Issue")
    for field, user_id in (("operador_id", operador_id), ("inspetor_id", inspetor_id)):
        if user_id is None:
            continue
        target = conn.execute("SELECT empresa_id FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        if target is None or target["empresa_id"] != empresa_id:
            raise HTTPException(status_code=422, detail=f"{field} invalido para a empresa da Issue")


def _validar_usuario_empresa(conn, user_id, empresa_id, campo):
    if user_id is None:
        return
    target = conn.execute("SELECT empresa_id FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    if target is None or target["empresa_id"] != empresa_id:
        raise HTTPException(status_code=422, detail=f"{campo} invalido para a empresa da Issue")


def fetch_issue(conn, issue_id, user):
    row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Issue não encontrada")
    if not (is_superuser(user) or user["empresa_id"] == row["empresa_id"]):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return row


def user_nome(conn, user_id):
    if user_id is None:
        return None
    row = conn.execute("SELECT nome FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    return row["nome"] if row else None


def user_cargo(conn, user_id):
    if user_id is None:
        return None
    row = conn.execute("SELECT posicao FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    return row["posicao"] if row else None


def acao_to_dict(conn, row):
    d = dict(row)
    d["responsavel_nome"] = user_nome(conn, d.get("responsavel_id"))
    return d


def issue_to_dict(conn, row, include_acoes=False):
    d = dict(row)
    d["porques"] = json.loads(d.get("porques") or "[]")
    d["operador_nome"] = user_nome(conn, d.get("operador_id"))
    d["inspetor_nome"] = user_nome(conn, d.get("inspetor_id"))
    d["criado_por_nome"] = user_nome(conn, d.get("criado_por_id"))
    d["criado_por_cargo"] = user_cargo(conn, d.get("criado_por_id"))
    d["finalizado_por_nome"] = user_nome(conn, d.get("finalizado_por_id"))
    d["autorizado_por_nome"] = user_nome(conn, d.get("autorizado_por_id"))
    try:
        d["rnc_equipe_investigacao"] = json.loads(d.get("rnc_equipe_investigacao") or "[]")
    except (TypeError, json.JSONDecodeError):
        d["rnc_equipe_investigacao"] = []
    d["rnc_lider_investigacao_nome"] = user_nome(conn, d.get("rnc_lider_investigacao_id"))
    d["rnc_auditor_eficacia_nome"] = user_nome(conn, d.get("rnc_auditor_eficacia_id"))
    d["rnc_contencao_responsavel_nome"] = user_nome(conn, d.get("rnc_contencao_responsavel_id"))
    d["rnc_emitida_por_nome"] = user_nome(conn, d.get("rnc_emitida_por_id"))
    d["rnc_equipe_investigacao_nomes"] = [
        nome for nome in (user_nome(conn, user_id) for user_id in d["rnc_equipe_investigacao"]) if nome
    ]
    d["ishikawa"] = None
    if d.get("ishikawa_id"):
        irow = conn.execute(
            "SELECT * FROM ishikawas WHERE id = ?", (d["ishikawa_id"],)
        ).fetchone()
        if irow:
            ishi = dict(irow)
            ishi["causas"] = json.loads(ishi.get("causas") or "{}")
            ishi["categorias"] = json.loads(ishi.get("categorias") or "{}")
            d["ishikawa"] = ishi
    if include_acoes:
        acoes = conn.execute(
            "SELECT * FROM acoes WHERE issue_id = ? ORDER BY ordem, id",
            (d["id"],),
        ).fetchall()
        d["acoes"] = [acao_to_dict(conn, a) for a in acoes]
    return d


def _scope_issues_query(user):
    if is_superuser(user):
        return "SELECT * FROM issues ORDER BY id DESC", ()
    return "SELECT * FROM issues WHERE empresa_id = ? ORDER BY id DESC", (user["empresa_id"],)


@router.get("")
def list_issues(user: dict = Depends(get_current_user)):
    query, params = _scope_issues_query(user)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        result = [issue_to_dict(conn, r) for r in rows]
    return result


@router.post("", status_code=201)
def create_issue(issue: IssueIn, user: dict = Depends(editor_dep)):
    criado_em = now()
    _valida_investigacao(issue.investigar_causa, issue.usar_ishikawa, issue.usar_porques)
    if issue.severidade not in SEVERIDADES:
        raise HTTPException(status_code=422, detail="Severidade invalida")
    with get_connection() as conn:
        if not is_superuser(user):
            empresa_id = user["empresa_id"]
        else:
            empresa_id = None
            if issue.setor_id is not None:
                setor = conn.execute(
                    "SELECT empresa_id FROM setores WHERE id = ?", (issue.setor_id,)
                ).fetchone()
                if setor is None:
                    raise HTTPException(status_code=404, detail="Setor não encontrado")
                empresa_id = setor["empresa_id"]
            if empresa_id is None:
                empresa_id = issue.empresa_id
        if empresa_id is None:
            raise HTTPException(
                status_code=400,
                detail="Informe a empresa (ou o setor) da issue",
            )
        empresa = conn.execute(
            "SELECT razao_social FROM empresas WHERE id = ?", (empresa_id,)
        ).fetchone()
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        if issue.setor_id is not None:
            srow = conn.execute(
                "SELECT empresa_id FROM setores WHERE id = ?", (issue.setor_id,)
            ).fetchone()
            if srow is None or (not is_superuser(user) and srow["empresa_id"] != empresa_id):
                raise HTTPException(status_code=404, detail="Setor não encontrado")
        _validar_cadastro_inicial(issue, conn, empresa_id)
        codigo = _next_codigo(conn, empresa_id)
        pasta = build_issue_pasta(empresa["razao_social"], codigo)
        ensure_pasta(pasta)
        cur = conn.execute(
            "INSERT INTO issues (codigo, empresa_id, setor_id, processo_id, pasta, "
            "descricao, data, origem, produto, norma, reincidencia, "
            "tipo, severidade, etapa_captura, detectado_em, comportamento_esperado, comportamento_observado, "
            "evidencias_objetivas, codigo_erro, ambiente, envolvidos_afetados, impacto, acao_emergencial, "
            "o_que, onde, quando, quem, por_que_inicial, como_detectado, "
            "ultimo_ok_em, alarme_em, margem_seguranca_min, codigo_material, lote, ordem_producao, sn_inicio, sn_fim, "
            "linha_posto, status_estoque, posicao_estoque, operador_id, inspetor_id, motivo_bloqueio, "
            "investigar_causa, usar_ishikawa, usar_porques, status, criado_por_id, criado_em, atualizado_em) "
            "VALUES (" + ", ".join(["?"] * 46) + ", 'registrado', ?, ?, ?)",
            (
                codigo,
                empresa_id,
                issue.setor_id,
                issue.processo_id,
                pasta,
                issue.descricao.strip() or issue.comportamento_observado.strip(),
                issue.data,
                issue.origem,
                issue.produto,
                issue.norma,
                issue.reincidencia,
                issue.tipo,
                issue.severidade,
                issue.etapa_captura,
                issue.detectado_em,
                issue.comportamento_esperado,
                issue.comportamento_observado,
                issue.evidencias_objetivas,
                issue.codigo_erro,
                issue.ambiente,
                issue.envolvidos_afetados,
                issue.impacto,
                issue.acao_emergencial,
                issue.o_que,
                issue.onde,
                issue.quando,
                issue.quem,
                issue.por_que_inicial,
                issue.como_detectado,
                issue.ultimo_ok_em,
                issue.alarme_em,
                issue.margem_seguranca_min,
                issue.codigo_material,
                issue.lote,
                issue.ordem_producao,
                issue.sn_inicio,
                issue.sn_fim,
                issue.linha_posto,
                issue.status_estoque,
                issue.posicao_estoque,
                issue.operador_id,
                issue.inspetor_id,
                issue.motivo_bloqueio,
                issue.investigar_causa,
                issue.usar_ishikawa,
                issue.usar_porques,
                user["id"],
                criado_em,
                criado_em,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = issue_to_dict(conn, row, include_acoes=True)
    return result


@router.get("/kanban")
def list_kanban(user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        if is_superuser(user):
            rows = conn.execute(
                "SELECT a.*, n.codigo, n.empresa_id, n.status AS issue_status, n.descricao AS issue_descricao "
                "FROM acoes a JOIN issues n ON n.id = a.issue_id "
                "ORDER BY a.status, a.ordem, a.id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.*, n.codigo, n.empresa_id, n.status AS issue_status, n.descricao AS issue_descricao "
                "FROM acoes a JOIN issues n ON n.id = a.issue_id "
                "WHERE n.empresa_id = ? ORDER BY a.status, a.ordem, a.id",
                (user["empresa_id"],),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["responsavel_nome"] = user_nome(conn, d.get("responsavel_id"))
            result.append(d)
    return result


@router.get("/stats")
def issue_stats(user: dict = Depends(get_current_user)):
    if is_superuser(user):
        query = "SELECT tipo, origem, produto, severidade, status, setor_id, criado_em, finalizado_em FROM issues"
        params: tuple = ()
    else:
        query = (
            "SELECT tipo, origem, produto, severidade, status, setor_id, criado_em, finalizado_em "
            "FROM issues WHERE empresa_id = ?"
        )
        params = (user["empresa_id"],)
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        setores = {
            r["id"]: r["nome"]
            for r in conn.execute(
                "SELECT id, nome FROM setores WHERE empresa_id = ?",
                (user["empresa_id"],) if not is_superuser(user) else (None,),
            ).fetchall()
        }

    def contar(campo, vazio):
        c = Counter()
        for r in rows:
            val = (r.get(campo) or "").strip() or vazio
            c[val] += 1
        return c

    def dimensao(campo, rotulo, vazio):
        return {
            "chave": campo,
            "rotulo": rotulo,
            "dados": pareto(
                [{"rotulo": k, "frequencia": v} for k, v in contar(campo, vazio).items()]
            ),
        }

    setor_counter = Counter()
    for r in rows:
        sid = r.get("setor_id")
        setor_counter[setores.get(sid, "Sem setor")] += 1

    return {
        "total": len(rows),
        "dimensoes": [
            dimensao("status", "Status", "Não informado"),
            dimensao("tipo", "Tipo", "Não informado"),
            dimensao("severidade", "Severidade", "Não informado"),
            dimensao("origem", "Origem", "Não informado"),
            dimensao("produto", "Produto", "Não informado"),
            {
                "chave": "setor",
                "rotulo": "Setor",
                "dados": pareto(
                    [{"rotulo": k, "frequencia": v} for k, v in setor_counter.items()]
                ),
            },
        ],
    }


@router.get("/trends")
def issue_trends(user: dict = Depends(get_current_user)):
    if is_superuser(user):
        query = "SELECT criado_em, finalizado_em, status FROM issues"
        params: tuple = ()
    else:
        query = "SELECT criado_em, finalizado_em, status FROM issues WHERE empresa_id = ?"
        params = (user["empresa_id"],)
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]

    criadas = defaultdict(int)
    finalizadas = defaultdict(int)
    em_aberto = 0
    for r in rows:
        criadas[(r["criado_em"] or "")[:7]] += 1
        if r.get("finalizado_em"):
            finalizadas[(r["finalizado_em"] or "")[:7]] += 1
        if r["status"] != "finalizado":
            em_aberto += 1
    periodos = sorted(set(criadas) | set(finalizadas))
    return {
        "criadas": len(rows),
        "finalizadas": len(rows) - em_aberto,
        "em_aberto": em_aberto,
        "por_criacao": [{"periodo": p, "total": criadas[p]} for p in periodos],
        "por_finalizacao": [{"periodo": p, "total": finalizadas[p]} for p in periodos],
    }


@router.get("/{issue_id}")
def get_issue(issue_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        result = issue_to_dict(conn, row, include_acoes=True)
    return result


@router.post("/{issue_id}/emitir-rnc")
def emitir_rnc(issue_id: int, body: RncEmissaoIn, user: dict = Depends(editor_dep)):
    """Promove a Issue a uma RNC formal, preservando o vínculo e a auditoria."""
    required = {
        "criticidade": body.criticidade,
        "enquadramento_normativo": body.enquadramento_normativo,
        "origem_gatilho": body.origem_gatilho,
        "acao_contencao_definitiva": body.acao_contencao_definitiva,
        "contencao_em": body.contencao_em,
        "disposicao_inicial": body.disposicao_inicial,
        "metodologia": body.metodologia,
        "prazo_analise": body.prazo_analise,
        "prazo_plano_acao": body.prazo_plano_acao,
        "prazo_verificacao_eficacia": body.prazo_verificacao_eficacia,
    }
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise HTTPException(status_code=422, detail="Preencha todos os campos obrigatorios da RNC")
    if body.criticidade not in RNC_CRITICIDADES:
        raise HTTPException(status_code=422, detail="Classificacao da RNC invalida")
    if body.origem_gatilho not in RNC_ORIGENS:
        raise HTTPException(status_code=422, detail="Origem do gatilho da RNC invalida")
    if body.disposicao_inicial not in RNC_DISPOSICOES:
        raise HTTPException(status_code=422, detail="Disposicao inicial invalida")
    if body.metodologia not in RNC_METODOLOGIAS:
        raise HTTPException(status_code=422, detail="Metodologia de analise invalida")
    equipe = list(dict.fromkeys(body.equipe_investigacao or []))
    if len(equipe) < 2:
        raise HTTPException(status_code=422, detail="Informe ao menos duas pessoas na equipe de investigacao")
    if body.lider_investigacao_id not in equipe:
        raise HTTPException(status_code=422, detail="O lider da investigacao deve participar da equipe")
    emitida_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        if row["rnc_status"] == "emitida" or row["rnc_codigo"]:
            raise HTTPException(status_code=409, detail="A RNC desta Issue ja foi emitida")
        _validar_cadastro_inicial(IssueUpdate(), conn, row["empresa_id"], row)
        for campo, user_id in (
            ("Lider da investigacao", body.lider_investigacao_id),
            ("Responsavel pela contencao", body.contencao_responsavel_id),
            ("Auditor da eficacia", body.auditor_eficacia_id),
        ):
            _validar_usuario_empresa(conn, user_id, row["empresa_id"], campo)
        for user_id in equipe:
            _validar_usuario_empresa(conn, user_id, row["empresa_id"], "Membro da equipe de investigacao")
        rnc_codigo = _next_rnc_codigo(conn, row["empresa_id"])
        conn.execute(
            "UPDATE issues SET rnc_status = 'emitida', rnc_codigo = ?, rnc_issue_codigo = ?, "
            "rnc_criticidade = ?, rnc_enquadramento_normativo = ?, rnc_origem_gatilho = ?, "
            "rnc_acao_contencao_definitiva = ?, rnc_contencao_responsavel_id = ?, rnc_contencao_em = ?, "
            "rnc_disposicao_inicial = ?, rnc_lider_investigacao_id = ?, rnc_auditor_eficacia_id = ?, rnc_equipe_investigacao = ?, "
            "rnc_metodologia = ?, rnc_prazo_analise = ?, rnc_prazo_plano_acao = ?, "
            "rnc_prazo_verificacao_eficacia = ?, rnc_emitida_por_id = ?, rnc_emitida_em = ?, atualizado_em = ? "
            "WHERE id = ?",
            (
                rnc_codigo,
                row["codigo"],
                body.criticidade,
                body.enquadramento_normativo.strip(),
                body.origem_gatilho,
                body.acao_contencao_definitiva.strip(),
                body.contencao_responsavel_id,
                body.contencao_em.strip(),
                body.disposicao_inicial,
                body.lider_investigacao_id,
                body.auditor_eficacia_id,
                json.dumps(equipe),
                body.metodologia,
                body.prazo_analise.strip(),
                body.prazo_plano_acao.strip(),
                body.prazo_verificacao_eficacia.strip(),
                user["id"],
                emitida_em,
                emitida_em,
                issue_id,
            ),
        )
        conn.commit()
        result = issue_to_dict(
            conn,
            conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone(),
            include_acoes=True,
        )
    return result


@router.put("/{issue_id}")
def update_issue(issue_id: int, issue: IssueUpdate, user: dict = Depends(editor_dep)):
    atualizado_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        _validar_cadastro_inicial(issue, conn, row["empresa_id"], row)
        fields = [
            "setor_id", "processo_id", "descricao", "data", "origem", "produto", "norma",
            "reincidencia", "tipo", "severidade", "etapa_captura",
            "detectado_em", "comportamento_esperado", "comportamento_observado",
            "evidencias_objetivas", "codigo_erro", "ambiente", "envolvidos_afetados",
            "impacto", "acao_emergencial", "o_que", "onde", "quando", "quem",
            "por_que_inicial", "como_detectado",
            "ultimo_ok_em", "alarme_em", "margem_seguranca_min",
            "codigo_material", "lote", "ordem_producao", "sn_inicio", "sn_fim",
            "linha_posto", "status_estoque", "posicao_estoque", "operador_id",
            "inspetor_id", "motivo_bloqueio", "investigar_causa", "usar_ishikawa",
            "usar_porques", "resultado_esperado", "status",
        ]
        data = dict(issue.model_dump(exclude_unset=True))
        investigar = data.get("investigar_causa", row["investigar_causa"])
        usar_ishikawa = data.get("usar_ishikawa", row["usar_ishikawa"])
        usar_porques = data.get("usar_porques", row["usar_porques"])
        _valida_investigacao(investigar, usar_ishikawa, usar_porques)
        if "status" in data and data["status"] not in ISSUE_STATUSES:
            raise HTTPException(status_code=422, detail="Status inválido")
        if "severidade" in data and data["severidade"] not in SEVERIDADES:
            raise HTTPException(status_code=422, detail="Severidade invalida")
        if data.get("status") == "finalizado":
            raise HTTPException(status_code=422, detail="Use a finalização da issue para finalizar")
        sets = []
        vals = []
        for f in fields:
            if f in data:
                sets.append(f"{f} = ?")
                vals.append(data[f])
        if sets:
            sets.append("atualizado_em = ?")
            vals.append(atualizado_em)
            vals.append(issue_id)
            conn.execute(f"UPDATE issues SET {', '.join(sets)} WHERE id = ?", vals)
            conn.commit()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        result = issue_to_dict(conn, row, include_acoes=True)
    return result


@router.delete("/{issue_id}", status_code=204)
def delete_issue(issue_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        pasta = row["pasta"] or ""
        ishikawa_id = row["ishikawa_id"]
        ishikawa_pasta = None
        if ishikawa_id:
            irow = conn.execute(
                "SELECT pasta FROM ishikawas WHERE id = ?", (ishikawa_id,)
            ).fetchone()
            ishikawa_pasta = irow["pasta"] if irow else None
        try:
            conn.execute("DELETE FROM acoes WHERE issue_id = ?", (issue_id,))
            if ishikawa_id:
                conn.execute("DELETE FROM ishikawas WHERE id = ?", (ishikawa_id,))
            conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    if pasta:
        try:
            delete_path(DOCS_DIR, pasta)
        except (ValueError, FileNotFoundError):
            pass
    if ishikawa_pasta:
        try:
            delete_path(DOCS_DIR, ishikawa_pasta)
        except (ValueError, FileNotFoundError):
            pass


@router.post("/{issue_id}/ishikawa", status_code=201)
def link_ishikawa(issue_id: int, body: IshikawaLinkIn, user: dict = Depends(editor_dep)):
    criado_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        if not row["investigar_causa"] or not row["usar_ishikawa"]:
            raise HTTPException(
                status_code=403,
                detail="A issue não está configurada para usar Ishikawa",
            )
        setor_id = body.setor_id
        if setor_id is None:
            default_setor = conn.execute(
                "SELECT id FROM setores WHERE empresa_id = ? ORDER BY id LIMIT 1",
                (row["empresa_id"],),
            ).fetchone()
            setor_id = default_setor["id"] if default_setor else None
        if setor_id is None:
            raise HTTPException(status_code=400, detail="Informe o setor do Ishikawa")
        setor = conn.execute("SELECT * FROM setores WHERE id = ?", (setor_id,)).fetchone()
        if setor is None or (not is_superuser(user) and setor["empresa_id"] != row["empresa_id"]):
            raise HTTPException(status_code=404, detail="Setor não encontrado")
        empresa = conn.execute(
            "SELECT razao_social FROM empresas WHERE id = ?", (setor["empresa_id"],)
        ).fetchone()
        existing = conn.execute(
            "SELECT id FROM ishikawas WHERE setor_id = ? AND nome = ?",
            (setor_id, body.nome),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Já existe um Ishikawa com este nome neste setor")
        pasta = build_ishikawa_pasta(empresa["razao_social"], setor["nome"], body.nome)
        ensure_pasta(pasta)
        cur = conn.execute(
            "INSERT INTO ishikawas (setor_id, nome, descricao, ativo, efeito, causas, categorias, pasta, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                setor_id,
                body.nome,
                body.descricao,
                body.ativo,
                body.efeito,
                json.dumps(body.causas),
                json.dumps(body.categorias),
                pasta,
                criado_em,
                criado_em,
            ),
        )
        conn.execute(
            "UPDATE issues SET ishikawa_id = ?, atualizado_em = ? WHERE id = ?",
            (cur.lastrowid, criado_em, issue_id),
        )
        conn.commit()
        irow = conn.execute("SELECT * FROM ishikawas WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = dict(irow)
        result["causas"] = json.loads(result.get("causas") or "{}")
        result["categorias"] = json.loads(result.get("categorias") or "{}")
    return result


@router.put("/{issue_id}/ishikawa")
def update_ishikawa(issue_id: int, body: IshikawaUpdateIn, user: dict = Depends(editor_dep)):
    atualizado_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        if not row["investigar_causa"] or not row["usar_ishikawa"]:
            raise HTTPException(
                status_code=403,
                detail="A issue não está configurada para usar Ishikawa",
            )
        if not row["ishikawa_id"]:
            raise HTTPException(status_code=404, detail="Ishikawa não vinculado à issue")
        irow = conn.execute(
            "SELECT * FROM ishikawas WHERE id = ?", (row["ishikawa_id"],)
        ).fetchone()
        if irow is None:
            raise HTTPException(status_code=404, detail="Ishikawa não encontrado")
        nome = body.nome if body.nome is not None else irow["nome"]
        descricao = body.descricao if body.descricao is not None else irow["descricao"]
        ativo = body.ativo if body.ativo is not None else irow["ativo"]
        efeito = body.efeito if body.efeito is not None else irow["efeito"]
        causas = (
            body.causas
            if body.causas is not None
            else json.loads(irow["causas"] or "{}")
        )
        categorias = json.loads(irow["categorias"] or "{}")
        if body.categorias is not None:
            categorias.update(body.categorias)
        conn.execute(
            "UPDATE ishikawas SET nome = ?, descricao = ?, ativo = ?, efeito = ?, causas = ?, categorias = ?, atualizado_em = ? WHERE id = ?",
            (
                nome,
                descricao,
                ativo,
                efeito,
                json.dumps(causas),
                json.dumps(categorias),
                atualizado_em,
                row["ishikawa_id"],
            ),
        )
        conn.execute(
            "UPDATE issues SET atualizado_em = ? WHERE id = ?",
            (atualizado_em, issue_id),
        )
        conn.commit()
        irow = conn.execute(
            "SELECT * FROM ishikawas WHERE id = ?", (row["ishikawa_id"],)
        ).fetchone()
        result = dict(irow)
        result["causas"] = json.loads(result.get("causas") or "{}")
        result["categorias"] = json.loads(result.get("categorias") or "{}")
    return result


@router.put("/{issue_id}/porques")
def save_porques(issue_id: int, body: PorquesIn, user: dict = Depends(editor_dep)):
    atualizado_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        if not row["investigar_causa"] or not row["usar_porques"]:
            raise HTTPException(
                status_code=403, detail="A issue não está configurada para usar 5 Porquês"
            )
        if row["usar_ishikawa"]:
            itens = [p.get("item_ishikawa") for p in body.porques if p.get("item_ishikawa")]
            if len(itens) != len(set(itens)):
                raise HTTPException(
                    status_code=422, detail="Cada porquê deve usar um item distinto do Ishikawa"
                )
        conn.execute(
            "UPDATE issues SET porques = ?, causa_raiz = ?, status = 'em_investigacao', atualizado_em = ? WHERE id = ?",
            (json.dumps(body.porques), body.causa_raiz, atualizado_em, issue_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        result = issue_to_dict(conn, row, include_acoes=True)
    return result


@router.get("/{issue_id}/acoes")
def list_acoes(issue_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        fetch_issue(conn, issue_id, user)
        rows = conn.execute(
            "SELECT * FROM acoes WHERE issue_id = ? ORDER BY ordem, id", (issue_id,)
        ).fetchall()
        result = [acao_to_dict(conn, r) for r in rows]
    return result


@router.post("/{issue_id}/acoes", status_code=201)
def create_acao(issue_id: int, acao: AcaoIn, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        _validar_usuario_empresa(conn, acao.responsavel_id, row["empresa_id"], "Responsavel")
        maxordem = conn.execute(
            "SELECT COALESCE(MAX(ordem), 0) FROM acoes WHERE issue_id = ?", (issue_id,)
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO acoes (issue_id, descricao, responsavel_id, "
            "prazo_limite, status, observacao, por_que, onde, como, quanto, ordem) "
            "VALUES (?, ?, ?, ?, 'backlog', ?, ?, ?, ?, ?, ?)",
            (
                issue_id,
                acao.descricao,
                acao.responsavel_id,
                acao.prazo_limite,
                acao.observacao,
                acao.por_que,
                acao.onde,
                acao.como,
                acao.quanto,
                maxordem + 1,
            ),
        )
        if row["status"] in ("registrado", "em_investigacao"):
            conn.execute(
                "UPDATE issues SET status = 'plano_acao', atualizado_em = ? WHERE id = ?",
                (now(), issue_id),
            )
        conn.commit()
        arow = conn.execute("SELECT * FROM acoes WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = acao_to_dict(conn, arow)
    return result


@router.put("/{issue_id}/acoes/{acao_id}")
def update_acao(issue_id: int, acao_id: int, acao: AcaoUpdate, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        arow = conn.execute(
            "SELECT * FROM acoes WHERE id = ? AND issue_id = ?", (acao_id, issue_id)
        ).fetchone()
        if arow is None:
            raise HTTPException(status_code=404, detail="Ação não encontrada")
        fields = [
            "descricao", "responsavel_id", "prazo_limite",
            "observacao", "por_que", "onde", "como", "quanto",
        ]
        data = dict(acao.model_dump(exclude_unset=True))
        if "responsavel_id" in data:
            _validar_usuario_empresa(conn, data["responsavel_id"], row["empresa_id"], "Responsavel")
        sets = []
        vals = []
        for f in fields:
            if f in data:
                sets.append(f"{f} = ?")
                vals.append(data[f])
        if sets:
            vals.append(acao_id)
            conn.execute(f"UPDATE acoes SET {', '.join(sets)} WHERE id = ?", vals)
            conn.commit()
        arow = conn.execute("SELECT * FROM acoes WHERE id = ?", (acao_id,)).fetchone()
        result = acao_to_dict(conn, arow)
    return result


@router.delete("/{issue_id}/acoes/{acao_id}", status_code=204)
def delete_acao(issue_id: int, acao_id: int, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        fetch_issue(conn, issue_id, user)
        arow = conn.execute(
            "SELECT * FROM acoes WHERE id = ? AND issue_id = ?", (acao_id, issue_id)
        ).fetchone()
        if arow is None:
            raise HTTPException(status_code=404, detail="Ação não encontrada")
        conn.execute("DELETE FROM acoes WHERE id = ?", (acao_id,))
        conn.commit()


@router.put("/{issue_id}/acoes/{acao_id}/status")
def update_acao_status(issue_id: int, acao_id: int, body: AcaoStatusIn, user: dict = Depends(editor_dep)):
    if body.status not in ACAO_STATUSES:
        raise HTTPException(status_code=422, detail="Status inválido")
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        arow = conn.execute(
            "SELECT * FROM acoes WHERE id = ? AND issue_id = ?", (acao_id, issue_id)
        ).fetchone()
        if arow is None:
            raise HTTPException(status_code=404, detail="Ação não encontrada")
        data_inicio = arow["data_inicio"]
        if body.status != "backlog" and data_inicio is None:
            data_inicio = now()
        conn.execute(
            "UPDATE acoes SET status = ?, data_inicio = ? WHERE id = ?",
            (body.status, data_inicio, acao_id),
        )
        if body.status != "backlog" and row["status"] == "plano_acao":
            conn.execute(
                "UPDATE issues SET status = 'em_execucao', atualizado_em = ? WHERE id = ?",
                (now(), issue_id),
            )
        conn.commit()
        arow = conn.execute("SELECT * FROM acoes WHERE id = ?", (acao_id,)).fetchone()
        result = acao_to_dict(conn, arow)
    return result


@router.post("/{issue_id}/finalizar")
def finalizar_issue(issue_id: int, body: FinalizarIn, user: dict = Depends(editor_dep)):
    if not (1 <= body.nota_atingimento <= 5):
        raise HTTPException(status_code=422, detail="Nota de atingimento deve ser de 1 a 5")
    if not body.resultado_alcancado.strip():
        raise HTTPException(status_code=422, detail="Informe o resultado alcançado")
    finalizado_em = now()
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        total = conn.execute(
            "SELECT COUNT(*) FROM acoes WHERE issue_id = ?", (issue_id,)
        ).fetchone()[0]
        if total == 0:
            raise HTTPException(
                status_code=422,
                detail="A issue precisa de ao menos uma ação para ser finalizada",
            )
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM acoes WHERE issue_id = ? AND status != 'finalizada'",
            (issue_id,),
        ).fetchone()[0]
        if pendentes > 0:
            raise HTTPException(
                status_code=422,
                detail="Todas as ações devem estar finalizadas antes de finalizar a issue",
            )
        conn.execute(
            "UPDATE issues SET resultado_alcancado = ?, nota_atingimento = ?, "
            "status = 'finalizado', finalizado_em = ?, finalizado_por_id = ?, atualizado_em = ? WHERE id = ?",
            (
                body.resultado_alcancado,
                body.nota_atingimento,
                finalizado_em,
                user["id"],
                finalizado_em,
                issue_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        result = issue_to_dict(conn, row, include_acoes=True)
    return result


@router.get("/{issue_id}/arvore")
def issue_arvore(issue_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    if folder.exists():
        arvore = node(folder)
    else:
        arvore = {"nome": folder.name, "tipo": "dir", "filhos": []}
    return {"issue_id": issue_id, "arvore": arvore}


@router.post("/{issue_id}/arquivos", status_code=201)
def issue_upload(
    issue_id: int,
    subpasta: str = Form(""),
    file: UploadFile = File(...),
    user: dict = Depends(editor_dep),
):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    try:
        target_dir = safe_rel(folder, subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if target_dir.exists() and not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target_dir.mkdir(parents=True, exist_ok=True)
    nome = save_file(target_dir, file.filename or "arquivo", data)
    return {"nome": nome}


@router.post("/{issue_id}/arquivos/criar", status_code=201)
def issue_criar_arquivo(issue_id: int, body: ArquivoIn, user: dict = Depends(editor_dep)):
    nome = sanitize(body.nome)
    if nome == "_":
        raise HTTPException(status_code=400, detail="Nome inválido")
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    try:
        target_dir = safe_rel(folder, body.subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if target_dir.exists() and not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target_dir.mkdir(parents=True, exist_ok=True)
    nome_disco = save_file(target_dir, nome, b"")
    return {"nome": nome_disco}


@router.post("/{issue_id}/pastas", status_code=201)
def issue_criar_pasta(issue_id: int, body: PastaIn, user: dict = Depends(editor_dep)):
    nome = sanitize(body.nome)
    if nome == "_":
        raise HTTPException(status_code=400, detail="Nome inválido")
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    try:
        base = safe_rel(folder, body.subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target = base / nome
    target.mkdir(parents=True, exist_ok=True)
    return {"nome": target.name}


@router.delete("/{issue_id}/objetos", status_code=204)
def issue_delete_objeto(issue_id: int, caminho: str, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    try:
        delete_path(folder, caminho)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Objeto não encontrado")


@router.get("/{issue_id}/arquivo")
def issue_abrir_arquivo(issue_id: int, caminho: str, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        row = fetch_issue(conn, issue_id, user)
        folder = folder_for(row["pasta"] or "")
    try:
        target = safe_rel(folder, caminho)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    mime = guess_mime(target.name)
    inline = (
        mime.startswith("image/")
        or mime == "application/pdf"
        or mime.startswith("text/")
    )
    return FileResponse(
        target,
        media_type=mime,
        filename=target.name,
        content_disposition_type="inline" if inline else "attachment",
    )
