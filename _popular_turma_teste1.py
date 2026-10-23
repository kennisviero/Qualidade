"""Carga didática da empresa TESTE 1. Sem argumentos: ensaio em memória; --apply: grava com backup."""
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.db import DB_PATH, get_connection
from app.docs import build_issue_pasta, ensure_pasta
from app.routers.issues import IssueIn, RncEmissaoIn, _next_codigo, _validar_cadastro_inicial
from app.routers.rncs import ObservacaoIn
from app.services.rnc_emissao import emitir_rnc_transacao

EMPRESA = 'TESTE 1'
MARCADOR = 'SIM-TURMA1-20261023'
TOTAL = 50
HISTORICAS = 20
OUTPUT = Path('documentos/exemplos_turma_teste1')
CATEGORIAS = [
    dict(nome='Falha de vedação', esperado='Embalagem sem vazamento no ensaio de pressão.',
         local='Linha de envase / seladora', hipotese='Janela de temperatura ou pressão de selagem instável.',
         acao='Verificar e bloquear parâmetros de selagem por receita.'),
    dict(nome='Erro de identificação', esperado='Etiqueta compatível com código e lote liberados.',
         local='Expedição / posto de rotulagem', hipotese='Troca de rolo sem validação independente.',
         acao='Adicionar leitura do código e confirmação antes da liberação.'),
    dict(nome='Dimensão fora da tolerância', esperado='Dimensão entre 24,80 e 25,20 mm.',
         local='Usinagem / célula B', hipotese='Desgaste ou fixação irregular do dispositivo.',
         acao='Inspecionar dispositivo e validar primeira peça após ajuste.'),
    dict(nome='Atraso de entrega interna', esperado='Material entregue ao posto em até 30 minutos.',
         local='Abastecimento / supermercado', hipotese='Reposição não acionada após consumo do último contentor.',
         acao='Testar sinal de reposição e definir limite visual de acionamento.'),
    dict(nome='Mistura de componentes', esperado='Um único código de componente por contentor identificado.',
         local='Montagem / bancada 4', hipotese='Sobras de ordens anteriores retornam sem segregação.',
         acao='Separar retornos e conferir código antes do abastecimento.'),
]


def insert(conn, table, values):
    cols = ','.join(values)
    marks = ','.join('?' for _ in values)
    return conn.execute(f'INSERT INTO {table} ({cols}) VALUES ({marks})', tuple(values.values())).lastrowid


def populate(conn):
    company = conn.execute('SELECT * FROM empresas WHERE upper(trim(razao_social))=?', (EMPRESA,)).fetchone()
    if company is None:
        raise RuntimeError('Empresa TESTE 1 não encontrada.')
    editor_row = conn.execute("SELECT * FROM usuarios WHERE empresa_id=? AND papel IN ('admin','editor') AND ativo=1 ORDER BY id LIMIT 1", (company['id'],)).fetchone()
    if editor_row is None:
        raise RuntimeError('TESTE 1 precisa ter um usuário admin/editor ativo antes da carga.')
    user = dict(editor_row)
    if conn.execute('SELECT 1 FROM issues WHERE empresa_id=? AND codigo_erro LIKE ?', (company['id'], MARCADOR+'-%')).fetchone():
        raise RuntimeError('A carga já foi aplicada; nada foi alterado.')
    rows, folders = [], []
    base = datetime(2026, 4, 1, 9, tzinfo=timezone.utc)
    for n in range(TOTAL):
        # Distribuição deliberadamente desigual para permitir estratificação e Pareto.
        cat_index = (0 if n < 15 else 1 if n < 26 else 2 if n < 35 else 3 if n < 43 else 4) if n < 45 else (n % len(CATEGORIAS))
        cat = CATEGORIAS[cat_index]
        detected = base + timedelta(days=n*3 + (n % 4), hours=(n % 3)*2)
        stamp = detected.isoformat()
        inspected = 80 + (n % 6)*20
        defects = 1 + (n*7 % 13)
        response_h = [1, 2, 4, 6, 9, 12][n % 6]
        case_id = f'{MARCADOR}-{n+1:03d}'
        evidence = (f'[SIMULADO] Caso {n+1:03d}; {inspected} unidades verificadas, {defects} com desvio; '
                    f'{defects/inspected*100:.1f}% na amostra. Detecção em {detected:%d/%m/%Y %H:%M} '
                    f'no turno {1+n%3}. Contenção iniciada após {response_h} h. '
                    f'Medições e relatos foram criados para treinamento; não representam evento real.')
        issue = IssueIn(
            empresa_id=company['id'], autor_registro_id=user['id'], data=detected.date().isoformat(), detectado_em=stamp,
            comportamento_esperado='[SIMULADO] '+cat['esperado'],
            comportamento_observado=f"[SIMULADO] {cat['nome']}: {defects} ocorrência(s) no lote didático {n+1:03d}.",
            evidencias_objetivas=evidence, codigo_erro=f'{case_id}-{cat_index+1}', ambiente='Treinamento',
            envolvidos_afetados=f'Equipe {1+n%4}; turno {1+n%3}', impacto=('Alto' if n%7==0 else 'Médio' if n%3 else 'Baixo'),
            acao_emergencial='[SIMULADO] Identificar e segregar o material potencialmente afetado até a verificação.',
            o_que=cat['nome'], onde=f"{cat['local']} / ocorrência {1+n%3}", quando=stamp,
            quem=f'Operação e inspeção, turno {1+n%3}', como_detectado=['Inspeção amostral','Auditoria de processo','Alerta operacional'][n%3],
            por_que_inicial='[SIMULADO] '+cat['hipotese'], codigo_material=f'MAT-{1+n%8:03d}',
            lote=f'TR-{n+1:03d}', ordem_producao=f'OP-TR-{n+1:03d}', linha_posto=f'L{1+n%4}-P{1+n%3}',
            status_estoque='segregado', motivo_bloqueio='Avaliação didática da abrangência.', operador_id=user['id'], inspetor_id=user['id'],
            investigar_causa=1, usar_ishikawa=1, usar_porques=1)
        _validar_cadastro_inicial(issue, conn, company['id'])
        code = _next_codigo(conn, company['id'])
        folder = build_issue_pasta(company['razao_social'], code)
        values = issue.model_dump(exclude={'empresa_id'})
        values.update(codigo=code, empresa_id=company['id'], pasta=folder, status='cadastrada',
                      criado_por_id=user['id'], criado_em=stamp, atualizado_em=stamp)
        issue_id = insert(conn, 'issues', values)
        folders.append(folder)
        rnc = None
        if n < HISTORICAS:
            emitted = (detected + timedelta(hours=response_h+1)).isoformat()
            deadline = lambda days: (detected + timedelta(days=days)).date().isoformat()
            payload = RncEmissaoIn(
                criticidade='maior' if n % 4 == 0 else 'menor',
                origem_gatilho=['inspecao_rotina','auditoria_interna','reclamacao_cliente','auditoria_externa'][n%4],
                enquadramento_normativo='[SIMULADO] Critério didático CT-'+f'{cat_index+1:02d}'+': '+cat['esperado'],
                acao_contencao_definitiva='[SIMULADO] Conferir abrangência do lote e manter segregação até decisão documentada.',
                contencao_responsavel_id=user['id'], contencao_em=(detected+timedelta(hours=response_h)).isoformat(),
                disposicao_inicial=['retrabalho','refugo','devolucao_fornecedor','bloqueio_preventivo'][n%4],
                lider_investigacao_id=user['id'], equipe_investigacao=[user['id']], metodologia='ishikawa',
                prazo_analise=deadline(7), prazo_plano_acao=deadline(14), prazo_verificacao_eficacia=deadline(30),
                auditor_eficacia_id=user['id'])
            with patch('app.routers.issues.now', return_value=emitted):
                rnc = emitir_rnc_transacao(conn, issue_id, payload, user)
            investigation = {
                'analise':'[SIMULADO] Registro histórico para exercício; hipóteses não equivalem a causa confirmada.',
                'hipoteses':[{'descricao':'[SIMULADO] '+cat['hipotese'],
                    'evidencias_favoraveis':f'Repetição do tipo de desvio em {1+n%5} ocorrências simuladas.',
                    'evidencias_contrarias':'Ainda não comparadas com casos sem falha; avaliar antes de concluir.',
                    'testes':[{'procedimento':'Comparar registros de condição, turno e lote em amostras com e sem falha.',
                        'responsavel_id':user['id'],'data':deadline(5),'resultado_esperado':'Determinar se a associação se mantém em amostras comparáveis.',
                        'criterio_decisao':'Exigir evidência reproduzível e considerar explicações alternativas.',
                        'repeticoes':3,'amostra':'Três lotes conformes e três lotes com desvio, simulados.',
                        'conclusao':'inconclusiva'}]}],
                'etapa_ishikawa':{'efeito':cat['nome'],'metodo':cat['hipotese'],'maquina':'Verificar equipamento e parâmetros registrados.',
                    'material':'Verificar identificação, lote e condição de armazenamento.','mao_obra':'Verificar treinamento e passagem de turno.',
                    'medicao':'Verificar método, instrumento e amostragem.','meio_ambiente':'Verificar condição do posto e organização.',
                    'conclusao':'Hipóteses pendentes de teste.'}}
            conn.execute('UPDATE rncs SET resumo=?, responsavel_id=?, investigacao_json=?, data_limite_contencao=?, data_conclusao_contencao=? WHERE id=?',
                         (f'SIM {cat["nome"][:20]}', user['id'], json.dumps(investigation, ensure_ascii=False), deadline(1),
                          (detected+timedelta(hours=response_h)).isoformat(), rnc['id']))
            obs = ObservacaoIn(inicio_ocorrencias=stamp, periodo_inicio=stamp,
                periodo_fim=(detected+timedelta(hours=response_h)).isoformat(), frequencia=f'{defects}/{inspected} unidades na amostra',
                turnos_horarios=f'Turno {1+n%3}', localizacao=f"{cat['local']} / ocorrência {1+n%3}",
                sintomas_condicoes=evidence, condicoes_sem_falha='[SIMULADO] Comparador sem falha ainda deve ser selecionado pelo aluno.',
                operadores_ids=[user['id']], equipes_envolvidas=f'Equipe {1+n%4}', quantidade_afetada=defects,
                unidade_quantidade='unidades', horas_perdidas=float(response_h), prejuizo_financeiro=round(defects*18.75+response_h*92,2),
                moeda='BRL', impacto_periodo=detected.date().isoformat()).model_dump()
            obs['operadores_ids'] = json.dumps(obs['operadores_ids'])
            obs.update(rnc_id=rnc['id'], atualizado_por_id=user['id'], atualizado_em=emitted)
            insert(conn, 'rnc_observacoes', obs)
            conn.execute('UPDATE acoes SET descricao=?,por_que=?,onde=?,como=?,quanto=?,observacao=? WHERE rnc_id=?',
                ('[SIMULADO] '+cat['acao'],'Reduzir recorrência após validar a causa.',cat['local'],
                 'Testar a mudança em lotes definidos e registrar os resultados.',f'R$ {250+n*23:.2f} (estimativa didática)',
                 'Critério de eficácia pendente: comparar indicadores antes/depois e verificar efeitos colaterais.',rnc['id']))
            rows.append({'issue_id':issue_id,'issue_codigo':code,'categoria':cat['nome'],'amostra_id':case_id,
                         'rnc_id':rnc['id'],'rnc_codigo':rnc['codigo'],'fase':'historico_rnc','data':stamp})
        else:
            if n % 2:
                conn.execute("UPDATE issues SET status='em_tratamento', tratamento_iniciado_em=? WHERE id=?",(stamp,issue_id))
            rows.append({'issue_id':issue_id,'issue_codigo':code,'categoria':cat['nome'],'amostra_id':case_id,
                         'rnc_id':None,'rnc_codigo':None,'fase':'aberta_para_exercicio','data':stamp})
    if len(rows)!=TOTAL or sum(bool(x['rnc_id']) for x in rows)!=HISTORICAS:
        raise AssertionError('Contagens da carga não conferem.')
    if conn.execute('PRAGMA foreign_key_check').fetchall() or conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
        raise AssertionError('Falha de integridade após carga.')
    return rows, folders, company['id']


def main():
    apply = sys.argv[1:] == ['--apply']
    if sys.argv[1:] and not apply:
        raise SystemExit('Use sem argumentos para ensaio ou --apply para gravar.')
    with get_connection() as source:
        if not apply:
            memory = sqlite3.connect(':memory:')
            memory.row_factory = sqlite3.Row
            source.backup(memory)
            memory.execute('PRAGMA foreign_keys=ON')
            rows, _, _ = populate(memory)
            print(f'ENSAIO OK: {len(rows)} Issues, {sum(bool(r["rnc_id"]) for r in rows)} RNCs históricas, '
                  f'{sum(not r["rnc_id"] for r in rows)} Issues abertas; integridade OK.')
            memory.close()
            return
        source.execute('PRAGMA foreign_keys=ON')
        backup = Path('data/backups') / f'qualidade_antes_turma_teste1_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.db'
        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup) as target:
            source.backup(target)
        source.execute('BEGIN IMMEDIATE')
        rows, folders, company_id = populate(source)
        source.commit()
        for folder in folders:
            ensure_pasta(folder)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT/'manifesto.json').write_text(json.dumps({'simulado':True,'empresa_id':company_id,'issues':rows,
            'total_issues':len(rows),'rncs_historicas':sum(bool(r['rnc_id']) for r in rows),
            'issues_para_exercicio':sum(not r['rnc_id'] for r in rows)},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'backup':str(backup),'empresa':'TESTE 1','issues':len(rows),
            'rncs_historicas':sum(bool(r['rnc_id']) for r in rows),
            'issues_para_exercicio':sum(not r['rnc_id'] for r in rows),
            'primeira_issue':rows[0]['issue_codigo'],'ultima_issue':rows[-1]['issue_codigo'],
            'integridade':'ok'},ensure_ascii=False))


if __name__=='__main__':
    main()
