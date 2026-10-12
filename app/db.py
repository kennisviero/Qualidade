import os
import json
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

RNC_FIELDS = ('codigo', 'criticidade', 'enquadramento_normativo', 'origem_gatilho', 'acao_contencao_definitiva', 'contencao_responsavel_id', 'contencao_em', 'disposicao_inicial', 'lider_investigacao_id', 'auditor_eficacia_id', 'equipe_investigacao', 'metodologia', 'prazo_analise', 'prazo_plano_acao', 'prazo_verificacao_eficacia', 'emitida_por_id', 'emitida_em')

RNCS_DDL = """
CREATE TABLE IF NOT EXISTS rncs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL UNIQUE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'emitida',
    codigo TEXT NOT NULL,
    criticidade TEXT DEFAULT '',
    enquadramento_normativo TEXT DEFAULT '',
    origem_gatilho TEXT DEFAULT '',
    acao_contencao_definitiva TEXT DEFAULT '',
    contencao_responsavel_id INTEGER REFERENCES usuarios(id),
    contencao_em TEXT,
    disposicao_inicial TEXT DEFAULT '',
    lider_investigacao_id INTEGER REFERENCES usuarios(id),
    auditor_eficacia_id INTEGER REFERENCES usuarios(id),
    equipe_investigacao TEXT DEFAULT '[]',
    metodologia TEXT DEFAULT '',
    prazo_analise TEXT DEFAULT '',
    prazo_plano_acao TEXT DEFAULT '',
    prazo_verificacao_eficacia TEXT DEFAULT '',
    emitida_por_id INTEGER REFERENCES usuarios(id),
    emitida_em TEXT,
    UNIQUE(empresa_id, codigo),
    FOREIGN KEY(issue_id, empresa_id) REFERENCES issues(id, empresa_id) ON DELETE CASCADE
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

CREATE TABLE IF NOT EXISTS llm_acessos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    provedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    url_base TEXT NOT NULL,
    api_key TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    UNIQUE(empresa_id, nome)
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
    pasta TEXT DEFAULT '',
    autor_registro_id INTEGER REFERENCES usuarios(id),
    data TEXT DEFAULT '',
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
    status TEXT DEFAULT 'cadastrada',
    tratamento_iniciado_em TEXT,
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
    from app.services.triagem_schema import DDL as TRIAGEM_DDL
    # Backup antes da primeira migração aditiva de triagem em uma base existente.
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as source:
            has_issues = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='issues'").fetchone()
            has_triagem = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='llm_triagens'").fetchone()
            has_rncs = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rncs'").fetchone()
            from app.services.rnc_schema import COLUMNS
            rnc_columns={r[1] for r in source.execute('PRAGMA table_info(rncs)')} if has_rncs else set()
            has_rnc_porques=has_rncs and 'investigacao_json' in rnc_columns and any('porques' in json.loads(r[0] or '{}') for r in source.execute('SELECT investigacao_json FROM rncs'))
            has_observacoes=source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rnc_observacoes'").fetchone()
            has_evidencias=source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rnc_evidencias'").fetchone()
            if has_rncs and (set(COLUMNS) - rnc_columns or 'causa_raiz' in rnc_columns or has_rnc_porques or not has_observacoes or not has_evidencias):
                from datetime import datetime, timezone
                folder = DB_PATH.parent / 'backups'
                folder.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                with sqlite3.connect(folder / f'qualidade_antes_rnc_abas_{stamp}.db') as target:
                    source.backup(target)
            if has_issues and not has_triagem:
                from datetime import datetime, timezone
                folder = DB_PATH.parent / 'backups'
                folder.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                with sqlite3.connect(folder / f'qualidade_antes_triagem_{stamp}.db') as target:
                    source.backup(target)
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
            ("autor_registro_id", "INTEGER REFERENCES usuarios(id)"),
            ("tratamento_iniciado_em", "TEXT"),
            ("data", "TEXT DEFAULT ''"),
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
        ]:
            if col not in ncols:
                conn.execute(f"ALTER TABLE issues ADD COLUMN {col} {ddl}")
        _remover_campos_duplicados_issue(conn)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_issues_id_empresa ON issues(id, empresa_id)")
        conn.executescript(RNCS_DDL)
        conn.executescript(TRIAGEM_DDL)
        _separar_rncs_e_corrigir_codigos(conn)
        from app.services.rnc_schema import migrate
        migrate(conn)
        _migrar_status_issues(conn)
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
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_issues_empresa_codigo ON issues(empresa_id, codigo)"
    )
    try:
        conn.execute("UPDATE sqlite_sequence SET name='issues' WHERE name='nao_conformidades'")
    except sqlite3.OperationalError:
        pass




def _separar_rncs_e_corrigir_codigos(conn):
    """Migra códigos e RNCs sem alterar IDs, ações ou caminhos dos anexos."""
    conn.execute("SAVEPOINT separar_rncs")
    try:
        rows = conn.execute("SELECT * FROM issues ORDER BY empresa_id, id").fetchall()
        used = {}
        for row in rows:
            used.setdefault(row["empresa_id"], set()).add(row["codigo"])
        for row in rows:
            match = re.fullmatch(r"RNC-(\d+)", row["codigo"] or "")
            if not match:
                continue
            codes = used[row["empresa_id"]]
            number = int(match.group(1))
            candidate = f"ISSUE-{number:04d}"
            while candidate in codes:
                number += 1
                candidate = f"ISSUE-{number:04d}"
            conn.execute("UPDATE issues SET codigo = ? WHERE id = ?", (candidate, row["id"]))
            codes.add(candidate)
        columns = {r[1] for r in conn.execute("PRAGMA table_info(issues)")}
        if "rnc_codigo" in columns:
            for row in rows:
                if not row["rnc_codigo"]:
                    continue
                values = {name: row["rnc_" + name] for name in RNC_FIELDS if "rnc_" + name in columns}
                values.update(issue_id=row["id"], empresa_id=row["empresa_id"])
                names = ", ".join(values)
                placeholders = ", ".join("?" for _ in values)
                conn.execute(f"INSERT INTO rncs ({names}) VALUES ({placeholders})", tuple(values.values()))
        conn.execute("DROP INDEX IF EXISTS idx_issues_empresa_rnc_codigo")
        for name in columns:
            if name.startswith("rnc_"):
                conn.execute(f'ALTER TABLE issues DROP COLUMN "{name}"')
        conn.execute("RELEASE SAVEPOINT separar_rncs")
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT separar_rncs")
        conn.execute("RELEASE SAVEPOINT separar_rncs")
        raise

def _migrar_status_issues(conn):
    conn.execute("UPDATE issues SET status = 'cadastrada' WHERE status = 'registrado'")
    conn.execute("UPDATE issues SET status = 'em_tratamento' WHERE status IN ('em_investigacao', 'plano_acao', 'em_execucao')")
    conn.execute("UPDATE issues SET status = 'fechada' WHERE status = 'finalizado'")
    conn.execute("UPDATE issues SET status = 'fechada', "
                 "finalizado_em = COALESCE(finalizado_em, (SELECT emitida_em FROM rncs WHERE issue_id = issues.id), atualizado_em, criado_em), "
                 "finalizado_por_id = COALESCE(finalizado_por_id, (SELECT emitida_por_id FROM rncs WHERE issue_id = issues.id)) "
                 "WHERE EXISTS (SELECT 1 FROM rncs WHERE issue_id = issues.id)")
    conn.execute("UPDATE issues SET finalizado_em = COALESCE(atualizado_em, criado_em) WHERE status = 'fechada' AND finalizado_em IS NULL")
    conn.execute("UPDATE issues SET tratamento_iniciado_em = COALESCE(atualizado_em, criado_em) "
                 "WHERE status = 'em_tratamento' AND tratamento_iniciado_em IS NULL")


def _remover_campos_duplicados_issue(conn):
    """Remove somente as colunas do bloco legado autorizado pelo usuário."""
    columns = {r[1] for r in conn.execute("PRAGMA table_info(issues)")}
    for column in ('descricao', 'etapa_captura', 'norma', 'origem', 'processo_id', 'produto', 'reincidencia', 'setor_id', 'severidade', 'tipo'):
        if column in columns:
            conn.execute(f'ALTER TABLE issues DROP COLUMN "{column}"')


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
