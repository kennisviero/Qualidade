"""Carga didática aditiva; sem migração, chamada LLM ou aprovação fictícia.
Executar sem argumentos para ensaio em memória; --apply grava a base após backup.
"""
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.db import get_connection
from app.docs import build_issue_pasta, ensure_pasta
from app.routers.issues import IssueIn, RncEmissaoIn, _next_codigo, _validar_cadastro_inicial, issue_to_dict
from app.routers.rncs import HipoteseIn, ObservacaoIn, view
from app.services.rnc_emissao import emitir_rnc_transacao

TAG = 'SIM-FERR-20261014'
OUT = Path('documentos/exemplos_ferramentas')
CATEGORIES = [
    ('Etiqueta incorreta', 'Código impresso igual ao cadastro aprovado do produto', 'Arquivo de impressão antigo', 'Bloquear versões antigas e validar código por leitura'),
    ('Selagem incompleta', 'Embalagem fechada, sem abertura no ensaio de vedação', 'Temperatura insuficiente de selagem', 'Validar janela de temperatura e alarme de selagem'),
    ('Dimensão fora da faixa', 'Comprimento de 50,00 mm, tolerância de 0,20 mm', 'Desgaste do dispositivo de posicionamento', 'Revisar dispositivo e verificar primeira peça'),
    ('Atraso na liberação', 'Liberação documental do lote em até duas horas', 'Passagem de turno sem indicação de pendências', 'Padronizar passagem de turno e fila de liberação'),
    ('Material misturado', 'Um único código de material por recipiente identificado', 'Retorno de sobras sem identificação', 'Segregar sobras e conferir identificação no retorno'),
]

def insert(c, table, data):
    return c.execute(f"INSERT INTO {table} ({','.join(data)}) VALUES ({','.join('?' for _ in data)})", tuple(data.values())).lastrowid

def snapshot(c):
    names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return {t: [tuple(r) for r in c.execute(f'SELECT * FROM "{t}" ORDER BY rowid')] for t in names}

def populate(c):
    before = snapshot(c)
    companies = c.execute('SELECT id,razao_social FROM empresas').fetchall()
    if len(companies) != 1:
        raise RuntimeError('É necessário escolher explicitamente a empresa: base contém mais de uma empresa.')
    company = companies[0]
    userrow = c.execute("SELECT * FROM usuarios WHERE empresa_id=? AND papel IN ('admin','editor') ORDER BY id LIMIT 1", (company['id'],)).fetchone()
    if not userrow:
        raise RuntimeError('Empresa sem usuário editor/admin.')
    user = dict(userrow)
    if c.execute('SELECT 1 FROM issues WHERE codigo_erro LIKE ?', (TAG+'%',)).fetchone():
        raise RuntimeError('Carga já existe; interrompida para não duplicar exemplos.')
    rows, paths = [], []
    # Trinta lotes cronológicos comparáveis para carta p, com mudança simulada após o lote 20.
    for i in range(40):
        category = 0 if i < 12 else 1 if i < 20 else 2 if i < 25 else 3 if i < 28 else 4
        if i >= 30:
            category = (i-30) % 5
        name, expected, hypothesis, action = CATEGORIES[category]
        detected = datetime(2026, 8, 15, 11, tzinfo=timezone.utc) + timedelta(days=i*1.5)
        inspected = 180 + (i % 5)*20
        temp = round(155 + (i % 9)*2.5, 1)
        defective = max(1, round(inspected*(0.105-(temp-155)*0.003))) if i < 20 else 2+i%4
        hours = [0.5, 1, 1.5, 2, 4, 6, 8, 12][i%8]
        timestamp = detected.isoformat()
        marker = f'{TAG}-{i+1:03d}'
        evidence = (f'[SIMULADO] Folha {marker}: {inspected} unidades inspecionadas; '
                    f'{defective} unidades não conformes ({defective/inspected*100:.2f}%); '
                    f'uma categoria principal por unidade. Temperatura de selagem: {temp} °C; '
                    f'tempo até contenção: {hours} h. Medições individuais de comprimento (mm): '
                    + ', '.join(str(round(50+(j-2)*0.06+(0.24 if category==2 else 0),2)) for j in range(5))
                    + '. Dados gerados para treinamento, sem observação real.')
        issue = IssueIn(empresa_id=company['id'],autor_registro_id=user['id'],data=detected.date().isoformat(),
            detectado_em=timestamp,comportamento_esperado='[SIMULADO] '+expected,
            comportamento_observado=f'[SIMULADO] {name}: {defective} unidades no lote {i+1:03d}',
            evidencias_objetivas=evidence,codigo_erro=marker,ambiente='Homologação',
            envolvidos_afetados='Equipe interna',impacto=['Alto','Médio','Baixo'][i%3],
            acao_emergencial='[SIMULADO] Segregar lote e suspender liberação até conferência.',
            o_que=name,onde=f'Linha {1+i%3} / posto de inspeção',quando=timestamp,
            quem=f'Equipe {1+i%3} / turno {1+i%2}',como_detectado='Inspeção amostral e conferência do registro simulado',
            por_que_inicial='Hipótese para testar: '+hypothesis,codigo_material=f'PROD-{1+i%3:02d}',
            lote=f'SIM-L{i+1:03d}',ordem_producao=f'SIM-OP{i+1:03d}',operador_id=user['id'],inspetor_id=user['id'])
        _validar_cadastro_inicial(issue,c,company['id'])
        code = _next_codigo(c,company['id'])
        folder = build_issue_pasta(company['razao_social'],code)
        values = issue.model_dump(exclude={'empresa_id'})
        values.update(codigo=code,empresa_id=company['id'],pasta=folder,status='cadastrada',criado_por_id=user['id'],criado_em=timestamp,atualizado_em=timestamp)
        iid = insert(c,'issues',values)
        paths.append(folder)
        rnc = None
        if i < 30:
            emitted = (detected+timedelta(hours=hours+1)).isoformat()
            deadline = lambda days: (detected+timedelta(days=days)).date().isoformat()
            body = RncEmissaoIn(criticidade='maior' if i%3==0 else 'menor',
                enquadramento_normativo=f'[SIMULADO] Instrução interna de treinamento SIM-IT-{category+1:02d}: {expected}',
                acao_contencao_definitiva='[SIMULADO] Inspecionar o lote segregado e retrabalhar unidades não conformes.',
                contencao_responsavel_id=user['id'],contencao_em=(detected+timedelta(hours=hours)).isoformat(),
                disposicao_inicial='retrabalho',lider_investigacao_id=user['id'],equipe_investigacao=[user['id']],
                metodologia='ishikawa',prazo_analise=deadline(7),prazo_plano_acao=deadline(14),prazo_verificacao_eficacia=deadline(30),auditor_eficacia_id=user['id'])
            with patch('app.routers.issues.now',return_value=emitted):
                rnc = emitir_rnc_transacao(c,iid,body,user)
            hid = HipoteseIn(descricao='[SIMULADO] '+hypothesis,evidencias_favoraveis='Relato didático de falha recorrente no mesmo posto.',
                evidencias_contrarias='Ainda não avaliadas.',testes=[dict(procedimento='Comparar condição atual e condição corrigida em três lotes equivalentes.',
                responsavel_id=user['id'],data=deadline(5),resultado_esperado='Redução da taxa sem alteração do método de inspeção.',
                criterio_decisao='Comparar taxas, condições e rastreabilidade; associação isolada não confirma causa.',
                repeticoes=3,amostra='Três lotes de 200 unidades por condição',conclusao='inconclusiva')]).model_dump()
            investigation = dict(analise='[SIMULADO] Exercício didático. Hipóteses aguardam testes; não há aprovação humana registrada.',hipoteses=[hid],
                etapa_ishikawa=dict(efeito=name,metodo=hypothesis,maquina='Verificar ajuste e manutenção',material='Verificar lote e identificação',
                    mao_obra='Verificar clareza da instrução e passagem de turno',medicao='Verificar método e instrumento',meio_ambiente='Verificar condições do posto',conclusao='Hipóteses para testar.'))
            c.execute('UPDATE rncs SET resumo=?,responsavel_id=?,investigacao_json=?,data_limite_contencao=?,data_conclusao_contencao=? WHERE id=?',
                ('SIM '+name[:21],user['id'],json.dumps(investigation,ensure_ascii=False),deadline(1),body.contencao_em,rnc['id']))
            obs = ObservacaoIn(inicio_ocorrencias=timestamp,periodo_inicio=timestamp,periodo_fim=body.contencao_em,
                frequencia=f'{defective}/{inspected} unidades inspecionadas',turnos_horarios=f'Turno {1+i%2}',localizacao=issue.onde,
                sintomas_condicoes=evidence,condicoes_sem_falha='Lote padrão com instrução revisada; validar em teste.',
                operadores_ids=[user['id']],equipes_envolvidas=issue.quem,quantidade_afetada=defective,unidade_quantidade='unidades',
                horas_perdidas=hours,prejuizo_financeiro=round(defective*12.5+hours*85,2),impacto_periodo=detected.date().isoformat()).model_dump()
            obs['operadores_ids']=json.dumps(obs['operadores_ids'])
            obs.update(rnc_id=rnc['id'],atualizado_por_id=user['id'],atualizado_em=emitted)
            insert(c,'rnc_observacoes',obs)
            status=['backlog','iniciada','em_andamento','em_revisao','finalizada'][i%5]
            c.execute('UPDATE acoes SET descricao=?,por_que=?,onde=?,como=?,quanto=?,observacao=?,status=?,data_inicio=? WHERE rnc_id=?',
                ('[SIMULADO] '+action,'Reduzir repetição do desvio',issue.onde,'Revisar instrução, testar em três lotes e registrar resultados',
                 f'R$ {200+i*15:.2f} (estimativa simulada)','Critério de aceite: evidência comparável em três lotes; avaliação de eficácia pendente.',
                 status,None if status=='backlog' else (detected+timedelta(days=2)).isoformat(),rnc['id']))
            insert(c,'rnc_pendencias',dict(rnc_id=rnc['id'],descricao='[SIMULADO] Coletar três lotes após ação e avaliar eficácia.',responsavel_id=user['id'],prazo=deadline(30),status='aberta',criado_por_id=user['id'],criado_em=emitted))
            view(c,c.execute('SELECT * FROM rncs WHERE id=?',(rnc['id'],)).fetchone())
        elif i%2:
            c.execute("UPDATE issues SET status='em_tratamento',tratamento_iniciado_em=? WHERE id=?",(timestamp,iid))
        issue_to_dict(c,c.execute('SELECT * FROM issues WHERE id=?',(iid,)).fetchone())
        rows.append(dict(simulado=True,amostra_id=marker,issue_id=iid,issue_codigo=code,rnc_id=rnc['id'] if rnc else None,
            rnc_codigo=rnc['codigo'] if rnc else None,data=timestamp,categoria=name,lote=issue.lote,turno=1+i%2,
            inspecionadas=inspected,nao_conformes=defective,temperatura_selagem_c=temp,tempo_contencao_h=hours,
            comprimentos_mm=[round(50+(j-2)*0.06+(0.24 if category==2 else 0),2) for j in range(5)],
            fase='antes' if i<20 else 'depois',serie_controle=i<30))
    for table, original in before.items():
        after=set(tuple(r) for r in c.execute(f'SELECT * FROM "{table}"'))
        assert all(row in after for row in original), f'Registro existente alterado: {table}'
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert sum(r['rnc_id'] is not None for r in rows)==30
    return rows, paths

def main():
    apply = sys.argv[1:] == ['--apply']
    if sys.argv[1:] and not apply:
        raise SystemExit('Use sem argumentos (ensaio) ou --apply.')
    with get_connection() as source:
        if not apply:
            c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
            source.backup(c);c.execute('PRAGMA foreign_keys=ON')
            rows,_=populate(c)
            print('ENSAIO OK: 40 Issues, 30 RNCs, 30 ações e 30 pendências; originais preservados; integridade OK.')
            return
        OUT.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=Path('data/backups')/f'qualidade_antes_ferramentas_{stamp}.db'
        backup.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(backup) as destination:source.backup(destination)
        source.execute('BEGIN IMMEDIATE')
        rows,paths=populate(source)
        for folder in paths:ensure_pasta(folder)
        (OUT/'amostras_simuladas.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        source.commit()
        print(json.dumps(dict(backup=str(backup),issues=40,rncs=30,acoes=30,pendencias=30,
            primeira_issue=rows[0]['issue_codigo'],ultima_issue=rows[-1]['issue_codigo'],
            primeira_rnc=rows[0]['rnc_codigo'],ultima_rnc=rows[29]['rnc_codigo'],verificacao='originais preservados; FK e integridade OK'),ensure_ascii=False))

if __name__=='__main__':main()
