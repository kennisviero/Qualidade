import os
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("QUALIDADE_DB", str(DATA_DIR / "qualidade.db")))
DOCS_DIR = Path(os.environ.get("QUALIDADE_DOCS", str(BASE_DIR / "Vault")))

ACOES_DDL = """
CREATE TABLE IF NOT EXISTS acoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    resultado_esperado TEXT DEFAULT '',
    responsavel_id INTEGER REFERENCES usuarios(id),
    prazo_limite TEXT DEFAULT '',
    data_inicio TEXT,
    status TEXT DEFAULT 'backlog',
    observacao TEXT DEFAULT '',
    por_que TEXT DEFAULT '',
    onde TEXT DEFAULT '',
    como TEXT DEFAULT '',
    quanto TEXT DEFAULT '',
    ordem INTEGER DEFAULT 0
);
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT NOT NULL,
    cnpj TEXT DEFAULT '',
    ativo INTEGER DEFAULT 1,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    setor_id INTEGER REFERENCES setores(id) ON DELETE SET NULL,
    posicao TEXT DEFAULT '',
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    papel TEXT NOT NULL DEFAULT 'editor',
    ativo INTEGER DEFAULT 1,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    descricao TEXT DEFAULT '',
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    dados TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS setores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    setor_id INTEGER REFERENCES setores(id) ON DELETE SET NULL,
    nome TEXT NOT NULL,
    descricao TEXT DEFAULT '',
    sintaxe TEXT DEFAULT '',
    ativo TEXT DEFAULT '',
    criado_por_id INTEGER REFERENCES usuarios(id),
    responsavel_id INTEGER REFERENCES usuarios(id),
    aprovador_id INTEGER REFERENCES usuarios(id),
    status TEXT DEFAULT 'rascunho',
    pasta TEXT DEFAULT '',
    criado_em TEXT NOT NULL,
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS revisoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processo_id INTEGER NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    sintaxe TEXT DEFAULT '',
    revisado_por_id INTEGER REFERENCES usuarios(id),
    aprovado_por_id INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL,
    revisao_em TEXT NOT NULL,
    aprovacao_em TEXT
);

CREATE TABLE IF NOT EXISTS ishikawas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setor_id INTEGER NOT NULL REFERENCES setores(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    descricao TEXT DEFAULT '',
    ativo TEXT DEFAULT '',
    efeito TEXT DEFAULT '',
    causas TEXT DEFAULT '{}',
    categorias TEXT DEFAULT '{}',
    pasta TEXT DEFAULT '',
    criado_em TEXT NOT NULL,
    atualizado_em TEXT,
    UNIQUE(setor_id, nome)
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    setor_id INTEGER REFERENCES setores(id) ON DELETE SET NULL,
    processo_id INTEGER REFERENCES processos(id) ON DELETE SET NULL,
    pasta TEXT DEFAULT '',
    descricao TEXT DEFAULT '',
    data TEXT DEFAULT '',
    origem TEXT DEFAULT '',
    produto TEXT DEFAULT '',
    norma TEXT DEFAULT '',
    reincidencia INTEGER DEFAULT 0,
    tipo TEXT DEFAULT 'nao_conformidade',
    severidade TEXT DEFAULT 'media',
    etapa_captura TEXT DEFAULT '',
    detectado_em TEXT DEFAULT '',
    comportamento_esperado TEXT DEFAULT '',
    comportamento_observado TEXT DEFAULT '',
    evidencias_objetivas TEXT DEFAULT '',
    codigo_erro TEXT DEFAULT '',
    ambiente TEXT DEFAULT '',
    envolvidos_afetados TEXT DEFAULT '',
    impacto TEXT DEFAULT '',
    acao_emergencial TEXT DEFAULT '',
    o_que TEXT DEFAULT '',
    onde TEXT DEFAULT '',
    quando TEXT DEFAULT '',
    quem TEXT DEFAULT '',
    por_que_inicial TEXT DEFAULT '',
    como_detectado TEXT DEFAULT '',
    ultimo_ok_em TEXT DEFAULT '',
    alarme_em TEXT DEFAULT '',
    margem_seguranca_min TEXT DEFAULT '',
    codigo_material TEXT DEFAULT '',
    lote TEXT DEFAULT '',
    ordem_producao TEXT DEFAULT '',
    sn_inicio TEXT DEFAULT '',
    sn_fim TEXT DEFAULT '',
    linha_posto TEXT DEFAULT '',
    status_estoque TEXT DEFAULT '',
    posicao_estoque TEXT DEFAULT '',
    operador_id INTEGER REFERENCES usuarios(id),
    inspetor_id INTEGER REFERENCES usuarios(id),
    motivo_bloqueio TEXT DEFAULT '',
    investigar_causa INTEGER DEFAULT 0,
    usar_ishikawa INTEGER DEFAULT 0,
    usar_porques INTEGER DEFAULT 0,
    rnc_status TEXT DEFAULT 'nao_emitida',
    rnc_codigo TEXT DEFAULT '',
    rnc_issue_codigo TEXT DEFAULT '',
    rnc_criticidade TEXT DEFAULT '',
    rnc_enquadramento_normativo TEXT DEFAULT '',
    rnc_origem_gatilho TEXT DEFAULT '',
    rnc_acao_contencao_definitiva TEXT DEFAULT '',
    rnc_contencao_responsavel_id INTEGER REFERENCES usuarios(id),
    rnc_contencao_em TEXT,
    rnc_disposicao_inicial TEXT DEFAULT '',
    rnc_lider_investigacao_id INTEGER REFERENCES usuarios(id),
    rnc_auditor_eficacia_id INTEGER REFERENCES usuarios(id),
    rnc_equipe_investigacao TEXT DEFAULT '[]',
    rnc_metodologia TEXT DEFAULT '',
    rnc_prazo_analise TEXT DEFAULT '',
    rnc_prazo_plano_acao TEXT DEFAULT '',
    rnc_prazo_verificacao_eficacia TEXT DEFAULT '',
    rnc_emitida_por_id INTEGER REFERENCES usuarios(id),
    rnc_emitida_em TEXT,
    autorizado_por_id INTEGER REFERENCES usuarios(id),
    autorizado_em TEXT,
    ishikawa_id INTEGER REFERENCES ishikawas(id) ON DELETE SET NULL,
    porques TEXT DEFAULT '[]',
    causa_raiz TEXT DEFAULT '',
    resultado_esperado TEXT DEFAULT '',
    resultado_alcancado TEXT DEFAULT '',
    nota_atingimento INTEGER,
    finalizado_em TEXT,
    finalizado_por_id INTEGER REFERENCES usuarios(id),
    status TEXT DEFAULT 'registrado',
    criado_por_id INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL,
    atualizado_em TEXT,
    UNIQUE(empresa_id, codigo)
);

""" + ACOES_DDL + """

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em TEXT NOT NULL,
    expira_em TEXT NOT NULL
);
"""

def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        _migrar_nao_conformidades(conn)
        conn.executescript(SCHEMA)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()]
        if "empresa_id" not in cols:
            conn.execute(
                "ALTER TABLE projects ADD COLUMN empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE"
            )
        pcols = [r[1] for r in conn.execute("PRAGMA table_info(processos)").fetchall()]
        if "empresa_id" not in pcols:
            conn.execute(
                "ALTER TABLE processos ADD COLUMN empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE"
            )
        conn.execute(
            "UPDATE processos SET empresa_id = "
            "(SELECT s.empresa_id FROM setores s WHERE s.id = processos.setor_id) "
            "WHERE (empresa_id IS NULL OR empresa_id = 0) AND setor_id IS NOT NULL"
        )
        for col, ddl in [
            ("criado_por_id", "INTEGER REFERENCES usuarios(id)"),
            ("responsavel_id", "INTEGER REFERENCES usuarios(id)"),
            ("aprovador_id", "INTEGER REFERENCES usuarios(id)"),
            ("status", "TEXT DEFAULT 'rascunho'"),
            ("pasta", "TEXT DEFAULT ''"),
            ("ativo", "TEXT DEFAULT ''"),
        ]:
            if col not in pcols:
                conn.execute(f"ALTER TABLE processos ADD COLUMN {col} {ddl}")
        try:
            conn.execute("DROP INDEX IF EXISTS idx_processos_setor_nome")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_processos_empresa_nome ON processos(empresa_id, nome)"
            )
        except sqlite3.IntegrityError:
            pass
        icols = [r[1] for r in conn.execute("PRAGMA table_info(ishikawas)").fetchall()]
        for col, ddl in [
            ("descricao", "TEXT DEFAULT ''"),
            ("ativo", "TEXT DEFAULT ''"),
            ("pasta", "TEXT DEFAULT ''"),
            ("categorias", "TEXT DEFAULT '{}'"),
        ]:
            if col not in icols:
                conn.execute(f"ALTER TABLE ishikawas ADD COLUMN {col} {ddl}")
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_ishikawas_setor_nome ON ishikawas(setor_id, nome)"
            )
        except sqlite3.IntegrityError:
            pass
        ucols = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
        for col, ddl in [
            ("setor_id", "INTEGER REFERENCES setores(id) ON DELETE SET NULL"),
            ("posicao", "TEXT DEFAULT ''"),
        ]:
            if col not in ucols:
                conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {ddl}")
        ncols = [r[1] for r in conn.execute("PRAGMA table_info(issues)").fetchall()]
        for col, ddl in [
            ("setor_id", "INTEGER REFERENCES setores(id) ON DELETE SET NULL"),
            ("processo_id", "INTEGER REFERENCES processos(id) ON DELETE SET NULL"),
            ("descricao", "TEXT DEFAULT ''"),
            ("data", "TEXT DEFAULT ''"),
            ("origem", "TEXT DEFAULT ''"),
            ("produto", "TEXT DEFAULT ''"),
            ("norma", "TEXT DEFAULT ''"),
            ("reincidencia", "INTEGER DEFAULT 0"),
            ("tipo", "TEXT DEFAULT 'nao_conformidade'"),
            ("severidade", "TEXT DEFAULT 'media'"),
            ("etapa_captura", "TEXT DEFAULT ''"),
            ("detectado_em", "TEXT DEFAULT ''"),
            ("comportamento_esperado", "TEXT DEFAULT ''"),
            ("comportamento_observado", "TEXT DEFAULT ''"),
            ("evidencias_objetivas", "TEXT DEFAULT ''"),
            ("codigo_erro", "TEXT DEFAULT ''"),
            ("ambiente", "TEXT DEFAULT ''"),
            ("envolvidos_afetados", "TEXT DEFAULT ''"),
            ("impacto", "TEXT DEFAULT ''"),
            ("acao_emergencial", "TEXT DEFAULT ''"),
            ("o_que", "TEXT DEFAULT ''"),
            ("onde", "TEXT DEFAULT ''"),
            ("quando", "TEXT DEFAULT ''"),
            ("quem", "TEXT DEFAULT ''"),
            ("por_que_inicial", "TEXT DEFAULT ''"),
            ("como_detectado", "TEXT DEFAULT ''"),
            ("ultimo_ok_em", "TEXT DEFAULT ''"),
            ("alarme_em", "TEXT DEFAULT ''"),
            ("margem_seguranca_min", "TEXT DEFAULT ''"),
            ("codigo_material", "TEXT DEFAULT ''"),
            ("lote", "TEXT DEFAULT ''"),
            ("ordem_producao", "TEXT DEFAULT ''"),
            ("sn_inicio", "TEXT DEFAULT ''"),
            ("sn_fim", "TEXT DEFAULT ''"),
            ("linha_posto", "TEXT DEFAULT ''"),
            ("status_estoque", "TEXT DEFAULT ''"),
            ("posicao_estoque", "TEXT DEFAULT ''"),
            ("operador_id", "INTEGER REFERENCES usuarios(id)"),
            ("inspetor_id", "INTEGER REFERENCES usuarios(id)"),
            ("motivo_bloqueio", "TEXT DEFAULT ''"),
            ("investigar_causa", "INTEGER DEFAULT 0"),
            ("usar_ishikawa", "INTEGER DEFAULT 0"),
            ("usar_porques", "INTEGER DEFAULT 0"),
            ("rnc_status", "TEXT DEFAULT 'nao_emitida'"),
            ("rnc_codigo", "TEXT DEFAULT ''"),
            ("rnc_issue_codigo", "TEXT DEFAULT ''"),
            ("rnc_criticidade", "TEXT DEFAULT ''"),
            ("rnc_enquadramento_normativo", "TEXT DEFAULT ''"),
            ("rnc_origem_gatilho", "TEXT DEFAULT ''"),
            ("rnc_acao_contencao_definitiva", "TEXT DEFAULT ''"),
            ("rnc_contencao_responsavel_id", "INTEGER REFERENCES usuarios(id)"),
            ("rnc_contencao_em", "TEXT"),
            ("rnc_disposicao_inicial", "TEXT DEFAULT ''"),
            ("rnc_lider_investigacao_id", "INTEGER REFERENCES usuarios(id)"),
            ("rnc_auditor_eficacia_id", "INTEGER REFERENCES usuarios(id)"),
            ("rnc_equipe_investigacao", "TEXT DEFAULT '[]'"),
            ("rnc_metodologia", "TEXT DEFAULT ''"),
            ("rnc_prazo_analise", "TEXT DEFAULT ''"),
            ("rnc_prazo_plano_acao", "TEXT DEFAULT ''"),
            ("rnc_prazo_verificacao_eficacia", "TEXT DEFAULT ''"),
            ("rnc_emitida_por_id", "INTEGER REFERENCES usuarios(id)"),
            ("rnc_emitida_em", "TEXT"),
        ]:
            if col not in ncols:
                conn.execute(f"ALTER TABLE issues ADD COLUMN {col} {ddl}")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_issues_empresa_rnc_codigo "
            "ON issues(empresa_id, rnc_codigo) WHERE rnc_codigo <> ''"
        )
        seed_admin(conn)
        seed_demo(conn)
        backfill_pastas(conn)


def _migrar_nao_conformidades(conn):
    """Banco antigo: nao_conformidades -> issues (mantém dados e FKs)."""
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "nao_conformidades" not in tabs:
        return
    conn.execute("ALTER TABLE nao_conformidades RENAME TO issues")
    if "acoes" in tabs:
        conn.execute("ALTER TABLE acoes RENAME TO acoes_old")
        conn.executescript(ACOES_DDL)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(acoes_old)").fetchall()]
        if "nao_conformidade_id" in cols and "issue_id" not in cols:
            names = ", ".join(
                "issue_id" if col == "nao_conformidade_id" else col for col in cols
            )
            selects = ", ".join(
                "nao_conformidade_id AS issue_id" if col == "nao_conformidade_id" else col
                for col in cols
            )
            conn.execute(f"INSERT INTO acoes ({names}) SELECT {selects} FROM acoes_old")
        conn.execute("DROP TABLE acoes_old")
    ncols = [r[1] for r in conn.execute("PRAGMA table_info(issues)").fetchall()]
    for col, ddl in [
        ("tipo", "TEXT DEFAULT 'nao_conformidade'"),
        ("severidade", "TEXT DEFAULT 'media'"),
        ("etapa_captura", "TEXT DEFAULT ''"),
    ]:
        if col not in ncols:
            conn.execute(f"ALTER TABLE issues ADD COLUMN {col} {ddl}")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_issues_empresa_codigo ON issues(empresa_id, codigo)"
    )
    try:
        conn.execute("UPDATE sqlite_sequence SET name='issues' WHERE name='nao_conformidades'")
    except sqlite3.OperationalError:
        pass


def _sanitize(name):
    name = (name or "").strip().strip(".")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    return (name or "_")[:80]


def backfill_pastas(conn):
    rows = conn.execute(
        "SELECT p.id, p.nome, s.nome AS setor_nome, e.razao_social "
        "FROM processos p LEFT JOIN setores s ON s.id = p.setor_id "
        "JOIN empresas e ON e.id = p.empresa_id "
        "WHERE p.pasta = '' OR p.pasta IS NULL"
    ).fetchall()
    for r in rows:
        if r["setor_nome"]:
            pasta = "/".join(
                [_sanitize(r["razao_social"]), _sanitize(r["setor_nome"]), _sanitize(r["nome"])]
            )
        else:
            pasta = "/".join([_sanitize(r["razao_social"]), _sanitize(r["nome"])])
        conn.execute("UPDATE processos SET pasta = ? WHERE id = ?", (pasta, r["id"]))
    if rows:
        conn.commit()


def seed_admin(conn):
    from datetime import datetime, timezone

    row = conn.execute("SELECT id FROM usuarios WHERE email = 'admin'").fetchone()
    if row is None:
        from app.auth import hash_password

        criado_em = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO usuarios (empresa_id, nome, email, senha_hash, papel, ativo, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (None, "Superusuário", "admin", hash_password("admin"), "admin", 1, criado_em),
        )
        conn.commit()


def seed_demo(conn):
    from datetime import datetime, timezone

    empresa = conn.execute(
        "SELECT id FROM empresas WHERE razao_social = 'Empresa teste'"
    ).fetchone()
    if empresa is None:
        criado_em = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO empresas (razao_social, cnpj, ativo, criado_em) VALUES (?, '', 1, ?)",
            ("Empresa teste", criado_em),
        )
        empresa_id = cur.lastrowid
        conn.commit()
    else:
        empresa_id = empresa["id"]

    row = conn.execute("SELECT id FROM usuarios WHERE email = 'carlos'").fetchone()
    if row is None:
        from app.auth import hash_password

        criado_em = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO usuarios (empresa_id, nome, email, senha_hash, papel, ativo, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (empresa_id, "Carlos", "carlos", hash_password("carlos"), "admin", 1, criado_em),
        )
        conn.commit()
