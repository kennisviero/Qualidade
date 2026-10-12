import json

FACT_FIELDS = ('codigo', 'detectado_em', 'autor_registro_id', 'comportamento_esperado',
    'comportamento_observado', 'evidencias_objetivas', 'impacto', 'envolvidos_afetados',
    'acao_emergencial', 'o_que', 'onde', 'quando', 'quem', 'como_detectado',
    'por_que_inicial', 'ambiente', 'codigo_erro', 'codigo_material', 'lote',
    'ordem_producao', 'sn_inicio', 'sn_fim')
COLUMNS = {
    'impacto': "TEXT NOT NULL DEFAULT ''",
    'ambiente': "TEXT NOT NULL DEFAULT ''",
    'emitente_id': 'INTEGER REFERENCES usuarios(id)',
    'responsavel_id': 'INTEGER REFERENCES usuarios(id)',
    'acao_contencao_imediata': "TEXT NOT NULL DEFAULT ''",
    'data_limite_contencao': "TEXT NOT NULL DEFAULT ''",
    'data_conclusao_contencao': "TEXT NOT NULL DEFAULT ''",
    'contencao_validada_por_id': 'INTEGER REFERENCES usuarios(id)',
    'investigacao_json': "TEXT NOT NULL DEFAULT '{}'",
    'metodologias_json': "TEXT NOT NULL DEFAULT '[]'",
    'plano_aprovador_id': 'INTEGER REFERENCES usuarios(id)',
    'plano_aprovado_por_id': 'INTEGER REFERENCES usuarios(id)',
    'plano_aprovado_em': 'TEXT',
    'fatos_snapshot_json': "TEXT NOT NULL DEFAULT '{}'",
    'fatos_preservados_em': 'TEXT',
    'fatos_snapshot_origem': "TEXT NOT NULL DEFAULT ''",
    'atualizado_em': 'TEXT',
}

def facts(row):
    return {key: row[key] for key in FACT_FIELDS}

def migrate(conn):
    columns={r[1] for r in conn.execute('PRAGMA table_info(rncs)')}
    for name,ddl in COLUMNS.items():
        if name not in columns:
            conn.execute(f'ALTER TABLE rncs ADD COLUMN {name} {ddl}')
    if 'metodologias_json' not in columns:
        for row in conn.execute('SELECT id,metodologia FROM rncs').fetchall():
            conn.execute('UPDATE rncs SET metodologias_json=? WHERE id=?',
                (json.dumps([row['metodologia']] if row['metodologia'] else []),row['id']))
    if 'causa_raiz' in columns:
        conn.execute('ALTER TABLE rncs DROP COLUMN causa_raiz')
    for row in conn.execute('SELECT id,investigacao_json FROM rncs').fetchall():
        data=json.loads(row['investigacao_json'] or '{}')
        if 'porques' in data:
            del data['porques']
            conn.execute('UPDATE rncs SET investigacao_json=? WHERE id=?',(json.dumps(data,ensure_ascii=False),row['id']))
    for key in ('impacto','ambiente'):
        if key not in columns:
            for row in conn.execute('SELECT id,issue_id,fatos_snapshot_json FROM rncs').fetchall():
                snapshot=json.loads(row['fatos_snapshot_json'] or '{}')
                issue=conn.execute(f'SELECT {key} FROM issues WHERE id=?',(row['issue_id'],)).fetchone()
                conn.execute(f'UPDATE rncs SET {key}=? WHERE id=?',(snapshot.get(key,issue[0] if issue else '') or '',row['id']))
    if 'rnc_id' not in {r[1] for r in conn.execute('PRAGMA table_info(acoes)')}:
        conn.execute('ALTER TABLE acoes ADD COLUMN rnc_id INTEGER REFERENCES rncs(id) ON DELETE CASCADE')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS rnc_pendencias (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      rnc_id INTEGER NOT NULL REFERENCES rncs(id) ON DELETE CASCADE,
      descricao TEXT NOT NULL, responsavel_id INTEGER REFERENCES usuarios(id),
      prazo TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'aberta',
      criado_por_id INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL,
      concluido_por_id INTEGER REFERENCES usuarios(id), concluido_em TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_acoes_rnc ON acoes(rnc_id);
    CREATE TABLE IF NOT EXISTS rnc_observacoes (
      rnc_id INTEGER PRIMARY KEY REFERENCES rncs(id) ON DELETE CASCADE,
      inicio_ocorrencias TEXT NOT NULL DEFAULT '', periodo_inicio TEXT NOT NULL DEFAULT '', periodo_fim TEXT NOT NULL DEFAULT '',
      frequencia TEXT NOT NULL DEFAULT '', turnos_horarios TEXT NOT NULL DEFAULT '',
      localizacao TEXT NOT NULL DEFAULT '', sintomas_condicoes TEXT NOT NULL DEFAULT '', condicoes_sem_falha TEXT NOT NULL DEFAULT '',
      operadores_ids TEXT NOT NULL DEFAULT '[]', equipes_envolvidas TEXT NOT NULL DEFAULT '',
      quantidade_afetada REAL, unidade_quantidade TEXT NOT NULL DEFAULT '', horas_perdidas REAL,
      prejuizo_financeiro REAL, moeda TEXT NOT NULL DEFAULT 'BRL', impacto_periodo TEXT NOT NULL DEFAULT '',
      atualizado_por_id INTEGER REFERENCES usuarios(id), atualizado_em TEXT
    );
    CREATE TABLE IF NOT EXISTS rnc_evidencias (
      id INTEGER PRIMARY KEY AUTOINCREMENT, rnc_id INTEGER NOT NULL REFERENCES rncs(id) ON DELETE CASCADE,
      nome TEXT NOT NULL, caminho TEXT NOT NULL UNIQUE, tamanho INTEGER NOT NULL,
      mime TEXT NOT NULL, carregado_por_id INTEGER REFERENCES usuarios(id), carregado_em TEXT NOT NULL
    );
    ''')
    from datetime import datetime, timezone
    stamp=datetime.now(timezone.utc).isoformat()
    for rnc in conn.execute("SELECT * FROM rncs WHERE fatos_snapshot_json='{}'").fetchall():
        issue=conn.execute('SELECT * FROM issues WHERE id=?',(rnc['issue_id'],)).fetchone()
        snap=facts(issue)
        original=conn.execute('''SELECT t.entrada_json FROM llm_rnc_geracao_itens g
            JOIN llm_triagem_issues t ON t.id=g.triagem_issue_id
            WHERE g.rnc_id=? AND g.status='gerada' ORDER BY g.id LIMIT 1''',(rnc['id'],)).fetchone()
        source='migracao_issue_atual'
        if original:
            data=json.loads(original['entrada_json'])
            mapping={'codigo_issue':'codigo','fato':'comportamento_observado','requisito':'comportamento_esperado',
                'evidencia':'evidencias_objetivas','envolvidos':'envolvidos_afetados',
                'origem_deteccao':'como_detectado','local':'onde'}
            for key,value in data.items():
                dest=mapping.get(key,key)
                if dest in snap:snap[dest]=value
            source='migracao_triagem_complementada'
        conn.execute('''UPDATE rncs SET fatos_snapshot_json=?,fatos_preservados_em=?,fatos_snapshot_origem=?,
            acao_contencao_imediata=?,emitente_id=?,atualizado_em=? WHERE id=?''',
            (json.dumps(snap,ensure_ascii=False),stamp,source,snap.get('acao_emergencial') or '',
             rnc['emitida_por_id'] if conn.execute('SELECT 1 FROM usuarios WHERE id=? AND empresa_id=?',
                (rnc['emitida_por_id'],rnc['empresa_id'])).fetchone() else None,stamp,rnc['id']))
    conn.execute("UPDATE acoes SET rnc_id=(SELECT r.id FROM rncs r WHERE r.issue_id=acoes.issue_id AND acoes.descricao LIKE 'Tratar ' || r.codigo || ':%') WHERE rnc_id IS NULL")
