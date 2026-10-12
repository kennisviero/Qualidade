DDL = """
CREATE TABLE IF NOT EXISTS llm_triagens (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 acesso_llm_id INTEGER REFERENCES llm_acessos(id) ON DELETE SET NULL,
 solicitado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
 idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pendente','processando','concluida','falha')),
 provedor_snapshot TEXT NOT NULL, modelo_snapshot TEXT NOT NULL,
 versao_prompt TEXT NOT NULL, parametros_json TEXT NOT NULL,
 criado_em TEXT NOT NULL, iniciado_em TEXT, concluido_em TEXT,
 erro_codigo TEXT, erro_mensagem_segura TEXT,
 UNIQUE(empresa_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS llm_triagem_issues (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 triagem_id INTEGER NOT NULL REFERENCES llm_triagens(id) ON DELETE CASCADE,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
 codigo_issue_snapshot TEXT NOT NULL, entrada_json TEXT NOT NULL, entrada_hash TEXT NOT NULL,
 candidata INTEGER NOT NULL DEFAULT 0 CHECK(candidata IN (0,1)),
 justificativa_json TEXT,
 criticidade_sugerida TEXT CHECK(criticidade_sugerida IN ('BAIXA','MÉDIA','ALTA')),
 UNIQUE(triagem_id,issue_id)
);
CREATE TABLE IF NOT EXISTS llm_rnc_geracoes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 triagem_id INTEGER NOT NULL REFERENCES llm_triagens(id) ON DELETE CASCADE,
 aprovado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
 idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
 status TEXT NOT NULL, criado_em TEXT NOT NULL, concluido_em TEXT,
 UNIQUE(empresa_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS llm_rnc_geracao_itens (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 geracao_id INTEGER NOT NULL REFERENCES llm_rnc_geracoes(id) ON DELETE CASCADE,
 empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
 triagem_issue_id INTEGER NOT NULL REFERENCES llm_triagem_issues(id),
 rnc_id INTEGER REFERENCES rncs(id) ON DELETE SET NULL,
 codigo_rnc_snapshot TEXT, dados_aprovados_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('gerada','pendente')),
 erro_codigo TEXT, erro_mensagem_segura TEXT,
 UNIQUE(geracao_id,triagem_issue_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_triagem_candidata_emitida
 ON llm_rnc_geracao_itens(triagem_issue_id) WHERE status='gerada';
CREATE INDEX IF NOT EXISTS idx_triagens_pendentes ON llm_triagens(status,id);
CREATE INDEX IF NOT EXISTS idx_triagens_empresa ON llm_triagens(empresa_id,id);
"""
