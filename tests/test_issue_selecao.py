import json
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.db import get_connection, init_db
from app.main import app
from app.services import issue_triagem, llm_client
from test_issues import criar_empresa, criar_issue, login

REAL_START_WORKER = issue_triagem.start_worker

PREFIX='/api/issues/selecao'


def headers(key=None):
    return {'Idempotency-Key':key or str(uuid.uuid4())}


@pytest.fixture
def setup(monkeypatch):
    # Worker determinístico: o teste aciona o mesmo processador de produção.
    monkeypatch.setattr(issue_triagem,'start_worker',lambda:(threading.Event(),SimpleNamespace(join=lambda timeout:None)))
    calls=[]
    def fake(access,prompt,items,on_progress=None):
        calls.append(items)
        return json.dumps({'candidatas_rnc':[candidate(i['id_issue']) for i in items]})
    monkeypatch.setattr(llm_client,'analisar_issues',fake)
    with TestClient(app) as client:
        login(client,'admin','admin')
        eid=criar_empresa(client,'Seleção '+uuid.uuid4().hex)['id']
        users=[]
        emails=[]
        for name,role in [('Líder','admin'),('Membro','editor')]:
            email=uuid.uuid4().hex+'@teste.com'
            response=client.post('/api/usuarios',json={'nome':name,'email':email,'senha':'teste','papel':role,'empresa_id':eid})
            assert response.status_code==201,response.text
            users.append(response.json()['id']);emails.append(email)
        access=client.post('/api/configuracao/llm',json={'empresa_id':eid,'nome':'Groq teste','provedor':'Groq',
            'modelo':'modelo-teste','url_base':'https://api.groq.com/openai/v1','api_key':'segredo-nao-expor'}).json()['id']
        login(client,emails[0],'teste')
        issues=[criar_issue(client).json(),criar_issue(client).json()]
        yield SimpleNamespace(c=client,eid=eid,users=users,emails=emails,access=access,issues=issues,calls=calls)


def candidate(issue_id):
    return {'id_issue':issue_id,'titulo':'Título da IA não altera cadastro',
        'justificativa':{'requisito_violado':'IT-04 exige o padrão.',
            'fato_e_evidencia':'Registro de inspeção demonstra desvio.','criterios_ia':'Requisito, fato e evidência explícitos.'},
        'criticidade_sugerida':'ALTA'}


def test_manual_valida_e_revalida_sem_llm(setup):
    s=setup;issue_id=s.issues[0]['id'];url=PREFIX+f'/manual/{issue_id}'
    with get_connection() as conn:
        conn.execute('UPDATE issues SET comportamento_esperado=?,comportamento_observado=?,evidencias_objetivas=? WHERE id=?',
            ('Pedido exige entrega em 10/10','Entrega ocorreu em 12/10','Protocolo 123 de 12/10',issue_id))
    validation=s.c.get(url+'/validacao')
    assert validation.status_code==200 and validation.json()['permitida']
    for field,value in [('comportamento_esperado','Pedido exige entrega em 10/10'),
                        ('comportamento_observado','Entrega ocorreu em 12/10')]:
        with get_connection() as conn:conn.execute(f'UPDATE issues SET {field}=? WHERE id=?',('',issue_id))
        assert not s.c.get(url+'/validacao').json()['permitida']
        with get_connection() as conn:conn.execute(f'UPDATE issues SET {field}=? WHERE id=?',(value,issue_id))
    body={'confirmar':True,'entrada_hash':validation.json()['entrada_hash'],'dados_rnc':{}}
    assert s.c.post(url+'/gerar',json={**body,'confirmar':False}).status_code==422
    with get_connection() as conn:
        conn.execute('UPDATE issues SET evidencias_objetivas=? WHERE id=?',('Não informado',issue_id))
    blocked=s.c.get(url+'/validacao').json()
    assert not blocked['permitida'] and blocked['pendencias']==['suporte factual ou evidência textual']
    assert s.c.post(url+'/gerar',json=body).status_code==422
    with get_connection() as conn:
        assert not conn.execute('SELECT 1 FROM rncs WHERE issue_id=?',(issue_id,)).fetchone()
        conn.execute('UPDATE issues SET evidencias_objetivas=? WHERE id=?',('Protocolo 456 de 12/10 (simulado)',issue_id))
    assert s.c.post(url+'/gerar',json=body).status_code==409
    body['entrada_hash']=s.c.get(url+'/validacao').json()['entrada_hash']
    emitted=s.c.post(url+'/gerar',json=body)
    assert emitted.status_code==200 and emitted.json()['rnc_codigo'].startswith('RNC-')
    assert s.c.post(url+'/gerar',json=body).status_code==409
    assert s.calls==[]
    login(s.c,'admin','admin')
    other=criar_empresa(s.c,'Manual outra '+uuid.uuid4().hex)['id']
    assert s.c.get(PREFIX+f'/manual/{s.issues[1]["id"]}/validacao?empresa_id={other}').status_code==404
    login(s.c,s.emails[1],'teste')
    assert s.c.get(PREFIX+f'/manual/{s.issues[1]["id"]}/validacao?empresa_id={other}').status_code==403
    with get_connection() as conn:conn.execute("UPDATE usuarios SET papel='visualizador' WHERE id=?",(s.users[1],))
    assert s.c.get(PREFIX+f'/manual/{s.issues[1]["id"]}/validacao').status_code==403


def test_investigacao_complementos_e_rastreabilidade(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    evidence=s.c.post(url+'/evidencias',files={'file':('teste.txt',b'resultado do teste','text/plain')}).json()['id']
    investigation={'analise':'Notas preservadas','complementos':{'mudancas':'Atualização',
        'mudancas_em':'2026-10-12T10:00','configuracao_anterior':'1.0','configuracao_atual':'2.0',
        'abrangencia_afetados':'Lote A','abrangencia_sem_falha':'Lote B','controle_esperado':'Inspeção',
        'motivo_nao_deteccao':'Amostra insuficiente','hipoteses_confirmadas':'Configuração',
        'hipoteses_descartadas':'Material','hipoteses_inconclusivas':'Temperatura',
        'conclusao_tecnica':'Falha reproduzida','limitacoes_pendencias':'Repetir em outro turno',
        'revisor_id':s.users[1],'revisao_em':'2026-10-12T12:00','parecer':'complementar','observacoes_revisao':'Ampliar amostra'},
        'hipoteses':[{'descricao':'Configuração','testes':[{'procedimento':'Reproduzir falha',
        'resultado_esperado':'Sem falha','criterio_decisao':'3 falhas reproduzidas','repeticoes':3,
        'configuracao':'Máquina A, versão 2.0','amostra':'3 peças','evidencias_ids':[evidence]}]}]}
    saved=s.c.put(url,json={'investigacao_json':investigation})
    assert saved.status_code==200,saved.text
    detail=s.c.get(url).json()['rnc_investigacao_json']
    assert detail['complementos']==investigation['complementos']
    assert detail['hipoteses'][0]['testes'][0]['repeticoes']==3
    with get_connection() as conn:
        stored=json.loads(conn.execute('SELECT investigacao_json FROM rncs WHERE id=?',(rid,)).fetchone()[0])
        assert stored==detail
    for invalid in [{'revisor_id':99999999},{'revisao_em':'invalida'},{'parecer':'outro'}]:
        assert s.c.put(url,json={'investigacao_json':{'complementos':invalid}}).status_code==422
    for invalid in [{'repeticoes':0},{'repeticoes':1.5},{'evidencias_ids':[99999999]}]:
        assert s.c.put(url,json={'investigacao_json':{'hipoteses':[{'testes':[invalid]}]}}).status_code==422
    assert s.c.delete(url+f'/evidencias/{evidence}').status_code==204
    detail=s.c.get(url).json()['rnc_investigacao_json']
    assert detail['hipoteses'][0]['testes'][0]['evidencias_ids']==[]
    assert detail['analise']=='Notas preservadas' and detail['complementos']==investigation['complementos']
    init_db();assert s.c.get(url).json()['rnc_investigacao_json']==detail


def test_investigacao_etapas_porques_ishikawa(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    data={'analise':'Etapa 1 preservada','hipoteses':[],
        'etapa_porques':{'problema':'Falha na entrega','passos':[{'pergunta':'Por quê?','resposta':'Configuração','evidencia':'Log 123'}],'conclusao':'Revisar parâmetro'},
        'etapa_ishikawa':{'efeito':'Atraso','metodo':'Instrução antiga','maquina':'Parâmetro','material':'Lote A',
            'mao_obra':'Treinamento','medicao':'Amostragem','meio_ambiente':'Turno','conclusao':'Testar parâmetro'}}
    saved=s.c.put(url,json={'investigacao_json':data})
    assert saved.status_code==200,saved.text
    assert s.c.get(url).json()['rnc_investigacao_json']==data


def test_encerramento_rnc_aprovador_pendencias_e_historico(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    assert s.c.put(url,json={'encerramento_aprovador_id':9999999}).status_code==422
    assert s.c.post(url+'/encerrar',json={'confirmar':True}).status_code==422
    data={'encerramento_aprovador_id':s.users[1],'encerramento_conclusao':'Plano concluído e resultados verificados','licoes_aprendidas':'Conferir configuração antes da produção'}
    assert s.c.put(url,json=data).status_code==200
    assert s.c.post(url+'/encerrar',json={'confirmar':True}).status_code==403
    login(s.c,s.emails[1],'teste')
    assert s.c.post(url+'/encerrar',json={'confirmar':False}).status_code==422
    pending=s.c.post(url+'/pendencias',json={'descricao':'Conferir documento'}).json()['pendencias'][0]['id']
    assert s.c.post(url+'/encerrar',json={'confirmar':True}).status_code==422
    assert s.c.put(url+f'/pendencias/{pending}',json={'status':'concluida'}).status_code==200
    closed=s.c.post(url+'/encerrar',json={'confirmar':True})
    assert closed.status_code==200,closed.text
    record=closed.json();assert record['rnc_status']=='concluida'
    assert record['rnc_encerramento_aprovado_por_id']==s.users[1]
    assert record['rnc_encerramento_aprovado_em'] and record['rnc_licoes_aprendidas']==data['licoes_aprendidas']
    repeated=s.c.post(url+'/encerrar',json={'confirmar':True}).json()
    assert repeated['rnc_encerramento_aprovado_em']==record['rnc_encerramento_aprovado_em']
    assert s.c.put(url,json={'licoes_aprendidas':'Alteração'}).status_code==409
    card=next(a for a in s.c.get('/api/issues/kanban').json() if a['rnc_id']==rid)
    assert card['rnc_status']=='concluida'
    assert card['status']=='finalizada'
    assert s.c.put(f"/api/issues/{s.issues[0]['id']}/acoes/{card['id']}/status",json={'status':'backlog'}).status_code==409
    init_db();assert s.c.get(url).json()['rnc_licoes_aprendidas']==data['licoes_aprendidas']
    action_url=f"/api/issues/{s.issues[0]['id']}/acoes/{card['id']}"
    assert s.c.put(action_url,json={'descricao':'Alteração indevida'}).status_code==409
    assert s.c.delete(action_url).status_code==409
    assert s.c.post(f"/api/issues/{s.issues[0]['id']}/acoes",json={'descricao':'Nova indevida'}).status_code==409
    assert s.c.delete(f"/api/issues/{s.issues[0]['id']}").status_code==409
    reopened=s.c.post(url+'/reabrir',json={'confirmar':True,'motivo':'Recorrência da falha'})
    assert reopened.status_code==200,reopened.text
    state=reopened.json();assert state['rnc_status']=='reaberta' and state['rnc_encerramento_aprovado_em'] is None
    assert state['acoes'] and all(a['status']=='em_andamento' for a in state['acoes'])
    assert next(a for a in s.c.get('/api/issues/kanban').json() if a['rnc_id']==rid)['status']=='em_andamento'
    history=state['rnc_encerramento_historico'];assert history[0]['usuario_id']==s.users[1]
    assert history[0]['encerramento_aprovado_em']==record['rnc_encerramento_aprovado_em']
    assert s.c.put(url,json={'licoes_aprendidas':'Novos testes'}).status_code==200
    assert s.c.put(action_url+'/status',json={'status':'em_andamento'}).status_code==200
    assert s.c.post(url+'/reabrir',json={'confirmar':True,'motivo':'Outra'}).status_code==409
    assert s.c.post(url+'/encerrar',json={'confirmar':True}).json()['rnc_status']=='concluida'
    assert next(a for a in s.c.get('/api/issues/kanban').json() if a['rnc_id']==rid)['status']=='finalizada'


def test_encerramento_direto_sem_salvar_e_rollback(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    body={'confirmar':True,'encerramento_aprovador_id':s.users[0],
          'encerramento_conclusao':'Concluído','licoes_aprendidas':'Revisar parâmetro'}
    pending=s.c.post(url+'/pendencias',json={'descricao':'Pendente'}).json()['pendencias'][0]['id']
    assert s.c.post(url+'/encerrar',json=body).status_code==422
    assert s.c.get(url).json()['rnc_encerramento_aprovador_id'] is None
    assert s.c.put(url+f'/pendencias/{pending}',json={'status':'concluida'}).status_code==200
    response=s.c.post(url+'/encerrar',json=body)
    assert response.status_code==200,response.text
    record=response.json();assert record['rnc_status']=='concluida'
    assert record['rnc_encerramento_aprovador_id']==s.users[0]
    assert record['acoes'] and all(action['status']=='finalizada' for action in record['acoes'])
    assert s.c.put(url,json={'resumo':'Alterar'}).status_code==409
    assert s.c.post(url+'/reabrir',json={'confirmar':True,'motivo':'Investigar novamente'}).status_code==200
    assert s.c.put(url,json={'resumo':'Reaberta'}).status_code==200


def test_kanban_rnc_encerrada_nunca_fica_backlog(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id']
    with get_connection() as conn:
        conn.execute("UPDATE rncs SET status='concluida' WHERE id=?",(rid,))
        conn.execute("UPDATE acoes SET status='backlog' WHERE rnc_id=?",(rid,))
    cards=s.c.get('/api/issues/kanban').json()
    assert next(a for a in cards if a['rnc_id']==rid)['status']=='finalizada'
    assert s.c.post(f'/api/rncs/{rid}/reabrir',json={'confirmar':True}).status_code==200
    assert next(a for a in s.c.get('/api/issues/kanban').json() if a['rnc_id']==rid)['status']=='backlog'


def test_superusuario_encerra_com_aprovador_identificado(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id']
    login(s.c,'admin','admin')
    url=f'/api/rncs/{rid}'
    assert s.c.post(url+'/encerrar',json={'confirmar':True}).status_code==422
    closed=s.c.post(url+'/encerrar',json={'confirmar':True,'encerramento_aprovador_id':s.users[1]})
    assert closed.status_code==200,closed.text
    record=closed.json();assert record['rnc_status']=='concluida'
    assert record['rnc_encerramento_aprovador_id']==s.users[1]
    assert record['rnc_encerramento_aprovado_por_id']==s.c.get('/api/auth/me').json()['id']
    assert all(a['status']=='finalizada' for a in record['acoes'])


def test_resumo_rnc_persistencia_limite_e_kanban(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    assert s.c.get(url).json()['rnc_resumo']==''
    text='Falha entrega'
    assert s.c.put(url,json={'resumo':text}).json()['rnc_resumo']==text
    assert s.c.put(url,json={'resumo':'x'*26}).status_code==422
    assert s.c.put(url,json={'resumo':'x'*25}).json()['rnc_resumo']=='x'*25
    assert s.c.put(url,json={'resumo':text}).status_code==200
    cards=s.c.get('/api/issues/kanban').json()
    assert next(c for c in cards if c['rnc_id']==rid)['rnc_resumo']==text
    init_db();assert s.c.get(url).json()['rnc_resumo']==text
    assert s.c.put(url,json={'resumo':''}).json()['rnc_resumo']==''


def test_investigacao_etapas_rejeita_dados_invalidos(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    data={'analise':'Dados preservados'}
    assert s.c.put(url,json={'investigacao_json':data}).status_code==200
    init_db();assert s.c.get(url).json()['rnc_investigacao_json']==data
    for bad in [{'etapa_porques':{'passos':[{'resposta':42}]}},{'etapa_ishikawa':{'invalido':'x'}},
                {'etapa_porques':{'passos':[{}]*21}}]:
        assert s.c.put(url,json={'investigacao_json':bad}).status_code==422
    assert s.c.get(url).json()['rnc_investigacao_json']==data


def test_prompt_editado_enviado_e_preservado(setup,monkeypatch):
    s=setup
    assert s.c.get(PREFIX+'/prompt').json()['prompt']==issue_triagem.PROMPT
    received=[]
    def fake(access,prompt,items,on_progress=None):
        received.append(prompt)
        return json.dumps({'candidatas_rnc':[]})
    monkeypatch.setattr(llm_client,'analisar_issues',fake)
    body={'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']],'prompt':'Critérios personalizados pelo usuário.'}
    key=headers()
    response=s.c.post(PREFIX+'/analises',headers=key,json=body)
    assert response.status_code==202,response.text
    assert issue_triagem.process_next()
    detail=s.c.get(PREFIX+f"/analises/{response.json()['id']}").json()
    assert detail['status']=='concluida'
    assert received==[body['prompt']] and detail['prompt']==body['prompt']
    assert s.c.post(PREFIX+'/analises',headers=key,json={**body,'prompt':'Outro prompt'}).status_code==409
    assert s.c.post(PREFIX+'/analises',headers=headers(),json={**body,'prompt':'   '}).status_code==422


def test_openrouter_endpoint():
    access={'provedor':'OpenRouter','url_base':'https://openrouter.ai/api/v1'}
    assert llm_client.endpoint(access)=='https://openrouter.ai/api/v1/chat/completions'
    with pytest.raises(llm_client.LlmError,match='URL base'):
        llm_client.endpoint({**access,'url_base':'https://openrouter.ai/workspaces/default/keys'})


def test_etapas_reais_da_analise(setup,monkeypatch):
    s=setup
    response=s.c.post(PREFIX+'/analises',headers=headers(),json={'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']]})
    url=PREFIX+f"/analises/{response.json()['id']}"
    assert response.json()['etapa']=='enviando'
    def fake(access,prompt,items,on_progress):
        assert s.c.get(url).json()['etapa']=='enviando'
        for stage in ('aguardando','recebendo'):
            on_progress(stage)
            detail=s.c.get(url).json()
            assert detail['status']=='processando' and detail['etapa']==stage
        return '{"candidatas_rnc":[]}'
    monkeypatch.setattr(llm_client,'analisar_issues',fake)
    assert issue_triagem.process_next()
    assert s.c.get(url).json()['status']=='concluida'


def analyze(s,ids=None,key=None):
    response=s.c.post(PREFIX+'/analises',headers=headers(key),json={'empresa_id':s.eid,'acesso_llm_id':s.access,
        'issue_ids':ids or [i['id'] for i in s.issues]})
    assert response.status_code==202,response.text
    analysis=response.json()
    assert issue_triagem.process_next()
    return s.c.get(PREFIX+f"/analises/{analysis['id']}").json()


def rnc_data(s):
    return {'criticidade':'menor','enquadramento_normativo':'IT-04','origem_gatilho':'inspecao_rotina',
        'acao_contencao_definitiva':'Lote segregado','contencao_responsavel_id':s.users[0],
        'contencao_em':'2026-10-11T10:00','disposicao_inicial':'retrabalho','lider_investigacao_id':s.users[0],
        'equipe_investigacao':s.users,'metodologia':'5_porques','prazo_analise':'2026-10-20',
        'prazo_plano_acao':'2026-10-25','prazo_verificacao_eficacia':'2026-11-05','auditor_eficacia_id':s.users[1]}


@pytest.mark.parametrize('com_equipe',[False,True])
def test_selecao_emite_com_complemento_opcional(setup,com_equipe):
    s=setup;analysis=analyze(s)
    data={'equipe_investigacao':[s.users[0]]} if com_equipe else {}
    result=s.c.post(PREFIX+f"/analises/{analysis['id']}/geracoes",headers=headers(),
        json={'confirmar':True,'itens':[{'candidata_id':analysis['candidatas_rnc'][0]['id'],'dados_rnc':data}]}).json()
    assert result['status']=='concluida'
    with get_connection() as conn:
        rnc=conn.execute('SELECT * FROM rncs WHERE issue_id=?',(s.issues[0]['id'],)).fetchone()
        assert rnc['contencao_responsavel_id'] is None
        assert rnc['origem_gatilho']=='' and rnc['criticidade']==''
        assert conn.execute('SELECT status FROM issues WHERE id=?',(s.issues[0]['id'],)).fetchone()[0]=='fechada'


def test_rnc_observacao_hipoteses_e_arquivos_persistem(setup):
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    observation={'inicio_ocorrencias':'2026-10-01T10:00','periodo_inicio':'2026-10-01','periodo_fim':'2026-10-11',
        'frequencia':'3 ocorrências por turno','turnos_horarios':'Turno 2','localizacao':'Linha A',
        'sintomas_condicoes':'Arquivo maior que 10 MB','condicoes_sem_falha':'Arquivo pequeno',
        'operadores_ids':s.users,'equipes_envolvidas':'Operação', 'quantidade_afetada':12,
        'unidade_quantidade':'pedidos','horas_perdidas':2.5,'prejuizo_financeiro':0,'moeda':'BRL','impacto_periodo':'Outubro'}
    hypotheses=[{'descricao':'Limite de memória','evidencias_favoraveis':'Log de uso','evidencias_contrarias':'Não encontrado',
        'testes':[{'procedimento':'Importar arquivo de 12 MB','responsavel_id':s.users[1],
        'data':'2026-10-11','resultado':'Erro reproduzido','conclusao':'confirmada'}]}]
    saved=s.c.put(url,json={'observacao':observation,'investigacao_json':{'analise':'Teste de tamanho','hipoteses':hypotheses}})
    assert saved.status_code==200,saved.text
    for key,value in observation.items():assert saved.json()['observacao'][key]==value
    assert s.c.get(url).json()['rnc_investigacao_json']['hipoteses']==hypotheses
    assert s.c.put(url,json={'observacao':{'quantidade_afetada':-1}}).status_code==422
    assert s.c.put(url,json={'observacao':{'operadores_ids':[9999999]}}).status_code==422
    assert s.c.put(url,json={'observacao':{'periodo_inicio':'2026-10-20','periodo_fim':'2026-10-10'}}).status_code==422
    assert s.c.get(url).json()['observacao']['localizacao']=='Linha A'
    assert s.c.post(url+'/evidencias',files={'file':('vazio.txt',b'','text/plain')}).status_code==422
    uploaded=[]
    for content in (b'evidencia original',b'outra evidencia'):
        response=s.c.post(url+'/evidencias',files={'file':('medicao.txt',content,'text/plain')})
        assert response.status_code==201,response.text
        evidence=response.json();uploaded.append(evidence)
        assert evidence['carregado_por_id']==s.users[0]
        assert s.c.get(url+f"/evidencias/{evidence['id']}").content==content
    assert uploaded[0]['caminho']!=uploaded[1]['caminho']
    assert len(s.c.get(url).json()['evidencias_investigacao'])==2
    init_db();assert s.c.get(url).json()['observacao']['horas_perdidas']==2.5
    assert len(s.c.get(url).json()['evidencias_investigacao'])==2
    with get_connection() as conn:
        assert conn.execute('SELECT count(*) FROM rnc_observacoes WHERE rnc_id=?',(rid,)).fetchone()[0]==1
        conn.execute("UPDATE usuarios SET papel='visualizador' WHERE id=?",(s.users[1],))
    login(s.c,s.emails[1],'teste')
    assert s.c.get(url+f"/evidencias/{uploaded[0]['id']}").status_code==200
    assert s.c.post(url+'/evidencias',files={'file':('nao.txt',b'nao','text/plain')}).status_code==403
    assert s.c.delete(url+f"/evidencias/{uploaded[0]['id']}").status_code==403
    login(s.c,'admin','admin');eid=criar_empresa(s.c,'Evidências '+uuid.uuid4().hex)['id']
    email=uuid.uuid4().hex+'@teste.com'
    s.c.post('/api/usuarios',json={'nome':'Outro','email':email,'senha':'teste','papel':'editor','empresa_id':eid})
    login(s.c,email,'teste')
    assert s.c.get(url+f"/evidencias/{uploaded[0]['id']}").status_code==404
    assert s.c.post(url+'/evidencias',files={'file':('outro.txt',b'nao','text/plain')}).status_code==404
    assert s.c.delete(url+f"/evidencias/{uploaded[0]['id']}").status_code==404
    login(s.c,s.emails[0],'teste')
    from app.docs import folder_for
    with get_connection() as conn:folder=folder_for(conn.execute('SELECT pasta FROM issues WHERE id=?',(s.issues[0]['id'],)).fetchone()[0])
    target=folder/uploaded[0]['caminho'];assert target.is_file()
    assert s.c.delete(url+f"/evidencias/{uploaded[0]['id']}").status_code==204
    assert not target.exists()
    assert s.c.get(url+f"/evidencias/{uploaded[0]['id']}").status_code==404
    assert (folder/uploaded[1]['caminho']).is_file()
    assert len(s.c.get(url).json()['evidencias_investigacao'])==1
    with get_connection() as conn:conn.execute("UPDATE rncs SET status='concluida' WHERE id=?",(rid,))
    assert s.c.delete(url+f"/evidencias/{uploaded[1]['id']}").status_code==409


def test_rnc_exclusao_arquivo_falha_preserva_metadados(setup,monkeypatch):
    from pathlib import Path
    from app.docs import folder_for
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id'];url=f'/api/rncs/{rid}'
    evidence=s.c.post(url+'/evidencias',files={'file':('preservar.txt',b'evidencia','text/plain')}).json()
    with get_connection() as conn:target=folder_for(conn.execute('SELECT pasta FROM issues WHERE id=?',(s.issues[0]['id'],)).fetchone()[0])/evidence['caminho']
    original=Path.unlink
    def fail(path,*args,**kwargs):
        if path==target:raise OSError('falha simulada')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',fail)
    with pytest.raises(OSError):s.c.delete(url+f"/evidencias/{evidence['id']}")
    assert target.read_bytes()==b'evidencia'
    assert len(s.c.get(url).json()['evidencias_investigacao'])==1


def test_rnc_upload_rollback_nao_deixa_arquivo(setup):
    from app.docs import folder_for
    s=setup;rid=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()['rnc_id']
    with get_connection() as conn:
        conn.execute("CREATE TRIGGER falha_evidencia BEFORE INSERT ON rnc_evidencias BEGIN SELECT RAISE(ABORT,'teste'); END")
        folder=folder_for(conn.execute('SELECT pasta FROM issues WHERE id=?',(s.issues[0]['id'],)).fetchone()[0])
    files_before=set(p for p in folder.rglob('*') if p.is_file())
    try:
        with pytest.raises(Exception):s.c.post(f'/api/rncs/{rid}/evidencias',files={'file':('falha.txt',b'teste','text/plain')})
        assert set(p for p in folder.rglob('*') if p.is_file())==files_before
        with get_connection() as conn:assert conn.execute('SELECT count(*) FROM rnc_evidencias WHERE rnc_id=?',(rid,)).fetchone()[0]==0
    finally:
        with get_connection() as conn:conn.execute('DROP TRIGGER falha_evidencia')


def test_rnc_migracao_remove_porques_causa_sem_alterar_issue(setup):
    s=setup
    emitted=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()
    with get_connection() as conn:
        conn.execute("ALTER TABLE rncs ADD COLUMN causa_raiz TEXT DEFAULT ''")
        conn.execute('UPDATE rncs SET causa_raiz=?,investigacao_json=? WHERE id=?',
            ('Causa antiga',json.dumps({'porques':['Teste'],'analise':'Notas preservadas'}),emitted['rnc_id']))
        conn.execute('UPDATE issues SET causa_raiz=?,porques=? WHERE id=?',('Causa da Issue','[]',s.issues[0]['id']))
        snapshot=conn.execute('SELECT fatos_snapshot_json FROM rncs WHERE id=?',(emitted['rnc_id'],)).fetchone()[0]
    init_db();init_db()
    with get_connection() as conn:
        assert 'causa_raiz' not in {row[1] for row in conn.execute('PRAGMA table_info(rncs)')}
        row=conn.execute('SELECT investigacao_json,fatos_snapshot_json FROM rncs WHERE id=?',(emitted['rnc_id'],)).fetchone()
        assert json.loads(row[0])=={'analise':'Notas preservadas'}
        assert row[1]==snapshot
        assert conn.execute('SELECT causa_raiz FROM issues WHERE id=?',(s.issues[0]['id'],)).fetchone()[0]=='Causa da Issue'


def test_rnc_abas_snapshot_plano_pendencias_e_permissoes(setup):
    s=setup
    emitted=s.c.post(f"/api/issues/{s.issues[0]['id']}/emitir-rnc",json={}).json()
    rid=emitted['rnc_id'];url=f'/api/rncs/{rid}'
    initial=s.c.get(url).json()
    assert initial['rnc_impacto']==s.issues[0]['impacto']
    assert s.c.put(url,json={'impacto':'critico','ambiente':'campo'}).status_code==200
    classified=s.c.get(url).json()
    assert classified['rnc_impacto']=='critico' and classified['rnc_ambiente']=='campo'
    assert classified['rnc_fatos_snapshot_json']==initial['rnc_fatos_snapshot_json']
    assert s.c.put(url,json={'impacto':'inexistente'}).status_code==422
    assert initial['rnc_fatos_snapshot_origem']=='emissao'
    old=initial['comportamento_observado']
    s.c.put(f"/api/issues/{s.issues[0]['id']}",json={'comportamento_observado':'Alterado depois da emissão'})
    assert s.c.get(url).json()['comportamento_observado']==old
    assert s.c.put(url,json={'fatos_snapshot_json':{}}).status_code==422
    body={'emitente_id':s.users[0],'responsavel_id':s.users[1],
        'acao_contencao_imediata':'Segregar','data_limite_contencao':'2026-10-20T10:00',
        'data_conclusao_contencao':'2026-10-19T10:00','contencao_validada_por_id':s.users[1],
        'metodologia':'5_porques',
        'investigacao_json':{'analise':'Por falta de verificação'},'plano_aprovador_id':s.users[1]}
    result=s.c.put(url,json=body)
    assert result.status_code==200,result.text
    assert result.json()['rnc_investigacao_json']['analise']=='Por falta de verificação'
    assert result.json()['rnc_metodologias']==['5_porques']
    multi=s.c.put(url,json={'metodologias':['5_porques','ishikawa','5_porques']})
    assert multi.status_code==200,multi.text
    assert multi.json()['rnc_metodologias']==['5_porques','ishikawa']
    assert s.c.put(url,json={'metodologias':['invalida']}).status_code==422
    assert s.c.get(url).json()['rnc_metodologias']==['5_porques','ishikawa']
    assert s.c.put(url,json={'metodologias':[]}).json()['rnc_metodologias']==[]
    assert s.c.put(url,json={'causa_raiz':'Removida'}).status_code==422
    assert s.c.put(url,json={'investigacao_json':{'porques':[]}}).status_code==422
    assert s.c.put(url,json={'responsavel_id':9999999}).status_code==422
    assert s.c.put(url,json={'data_limite_contencao':'ontem'}).status_code==422
    assert s.c.post(url+'/aprovar-plano').status_code==403
    login(s.c,s.emails[1],'teste')
    assert s.c.post(url+'/aprovar-plano').json()['rnc_plano_aprovado_por_id']==s.users[1]
    task=s.c.post(url+'/acoes',json={'descricao':'Atualizar procedimento','responsavel_id':s.users[0],
        'prazo_limite':'2026-10-25','por_que':'Eliminar causa','onde':'Linha','como':'Revisar','quanto':'100'})
    assert task.status_code==201,task.text
    assert task.json()['rnc_plano_aprovado_em'] is None
    assert len(task.json()['acoes'])==2
    action=task.json()['acoes'][-1]
    fetched=s.c.get(url).json()['acoes'][-1]
    for key,value in {'descricao':'Atualizar procedimento','por_que':'Eliminar causa','onde':'Linha','responsavel_id':s.users[0],'prazo_limite':'2026-10-25','como':'Revisar','quanto':'100'}.items():
        assert fetched[key]==value
    assert action['rnc_id']==rid
    assert s.c.put(url+f"/acoes/{action['id']}",json={'descricao':'Revisar e treinar'}).status_code==200
    pending=s.c.post(url+'/pendencias',json={'descricao':'Confirmar medição','responsavel_id':s.users[0],'prazo':'2026-10-21'})
    assert pending.status_code==201,pending.text
    pid=pending.json()['pendencias'][0]['id']
    assert s.c.put(url+f'/pendencias/{pid}',json={'status':'concluida'}).json()['pendencias'][0]['concluido_por_id']==s.users[1]
    init_db();assert s.c.get(url).json()['comportamento_observado']==old
    with get_connection() as conn:
        assert conn.execute('SELECT count(*) FROM rnc_pendencias WHERE rnc_id=?',(rid,)).fetchone()[0]==1
        conn.execute("UPDATE usuarios SET papel='visualizador' WHERE id=?",(s.users[1],))
    login(s.c,s.emails[1],'teste')
    assert s.c.get(url).status_code==200
    assert s.c.put(url,json={'metodologia':'ishikawa'}).status_code==403
    login(s.c,'admin','admin')
    eid=criar_empresa(s.c,'Outra '+uuid.uuid4().hex)['id']
    foreign_email=uuid.uuid4().hex+'@teste.com'
    foreign=s.c.post('/api/usuarios',json={'nome':'Outro','email':foreign_email,'senha':'teste','papel':'editor','empresa_id':eid}).json()
    login(s.c,s.emails[0],'teste')
    assert s.c.put(url,json={'emitente_id':foreign['id']}).status_code==422
    login(s.c,foreign_email,'teste')
    assert s.c.get(url).status_code==404
    assert s.c.get('/api/rncs',params={'empresa_id':s.eid}).status_code==403


def test_selecao_fluxo_completo_aprovacao_parcial_idempotencia(setup):
    s=setup
    assert 'issue-view-selecao' in s.c.get('/').text
    assert s.c.get('/static/js/issue_selecao.js').status_code==200
    assert s.c.get(PREFIX+'/elegiveis').json()['total']==2
    access=s.c.get(PREFIX+'/acessos-llm').text
    assert 'api_key' not in access and 'segredo' not in access
    key=str(uuid.uuid4());analysis=analyze(s,key=key)
    assert analysis['status']=='concluida' and len(analysis['candidatas_rnc'])==2
    assert len(s.calls)==1 and len(s.calls[0])==2
    repeated=s.c.post(PREFIX+'/analises',headers=headers(key),json={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[i['id'] for i in s.issues]})
    assert repeated.json()['id']==analysis['id'] and len(s.calls)==1
    conflict=s.c.post(PREFIX+'/analises',headers=headers(key),json={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']]})
    assert conflict.status_code==409
    candidate_id=analysis['candidatas_rnc'][0]['id']
    body={'confirmar':True,'itens':[{'candidata_id':candidate_id,'dados_rnc':rnc_data(s)}]}
    generation_key=str(uuid.uuid4());url=PREFIX+f"/analises/{analysis['id']}/geracoes"
    for confirmation in (False,1,'true'):
        assert s.c.post(url,headers=headers(),json={**body,'confirmar':confirmation}).status_code==422
    result=s.c.post(url,headers=headers(generation_key),json=body)
    assert result.status_code==200,result.text
    result=result.json();assert result['status']=='concluida'
    assert s.c.post(url,headers=headers(generation_key),json=body).json()==result
    assert s.c.get(PREFIX+f"/geracoes/{result['geracao_id']}").json()==result
    assert s.c.get(f"/api/issues/{s.issues[0]['id']}").json()['status']=='fechada'
    assert s.c.get(f"/api/issues/{s.issues[1]['id']}").json()['status']=='cadastrada'
    with get_connection() as conn:
        assert conn.execute('SELECT count(*) FROM rncs WHERE empresa_id=?',(s.eid,)).fetchone()[0]==1
        assert conn.execute('SELECT criticidade FROM rncs WHERE issue_id=?',(s.issues[0]['id'],)).fetchone()[0]=='menor'
        assert conn.execute('SELECT count(*) FROM acoes WHERE issue_id=?',(s.issues[0]['id'],)).fetchone()[0]==1
        assert 'Requisito, fato' in conn.execute('SELECT justificativa_json FROM llm_triagem_issues WHERE id=?',(candidate_id,)).fetchone()[0]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert len(s.c.get(PREFIX+'/analises').json())==1
    cards=s.c.get(PREFIX.replace('/selecao','')+'/kanban',params={'empresa_id':s.eid}).json()
    card=next(item for item in cards if item['issue_id']==s.issues[0]['id'])
    assert card['status']=='backlog' and card['data_inicio'] is None
    assert card['rnc_codigo']==result['itens'][0]['codigo_rnc']
    assert card['responsavel_id']==s.users[0]
    moved=s.c.put(f"/api/issues/{card['issue_id']}/acoes/{card['id']}/status",json={'status':'iniciada'})
    assert moved.status_code==200
    assert s.c.get(f"/api/issues/{card['issue_id']}").json()['status']=='fechada'


def test_selecao_vazia_e_status_nao_alterado(setup,monkeypatch):
    s=setup
    monkeypatch.setattr(llm_client,'analisar_issues',lambda *args:'{"candidatas_rnc":[]}')
    result=analyze(s,ids=[s.issues[0]['id']])
    assert result['status']=='concluida' and result['candidatas_rnc']==[]
    assert s.c.get(f"/api/issues/{s.issues[0]['id']}").json()['status']=='cadastrada'


@pytest.mark.parametrize('kind',['markdown','unknown','duplicate','blank','enum','extra','float','duplicate_key'])
def test_selecao_rejeita_resposta_invalida(setup,monkeypatch,kind):
    s=setup;item=candidate(s.issues[0]['id']);result={'candidatas_rnc':[item]}
    if kind=='unknown':item['id_issue']=99999999
    if kind=='duplicate':result['candidatas_rnc'].append(item)
    if kind=='blank':item['justificativa']['criterios_ia']=' '
    if kind=='enum':item['criticidade_sugerida']='CRÍTICA'
    if kind=='extra':item['comando']='emitir'
    if kind=='float':item['id_issue']=float(item['id_issue'])
    text=json.dumps(result)
    if kind=='markdown':text='```json\n'+text+'\n```'
    if kind=='duplicate_key':text='{"candidatas_rnc":[],"candidatas_rnc":[]}'
    monkeypatch.setattr(llm_client,'analisar_issues',lambda *args:text)
    analysis=analyze(s)
    assert analysis['status']=='falha' and analysis['erro_codigo']=='resposta_invalida'
    assert analysis['candidatas_rnc']==[]
    with get_connection() as conn:
        assert conn.execute('SELECT count(*) FROM rncs WHERE empresa_id=?',(s.eid,)).fetchone()[0]==0


def test_selecao_snapshot_pendencias_e_retomada(setup):
    s=setup;analysis=analyze(s);first,second=analysis['candidatas_rnc']
    s.c.put(f"/api/issues/{s.issues[1]['id']}",json={'comportamento_observado':'Desvio alterado após análise'})
    body={'confirmar':True,'itens':[{'candidata_id':first['id'],'dados_rnc':rnc_data(s)},
        {'candidata_id':second['id'],'dados_rnc':rnc_data(s)}]}
    result=s.c.post(PREFIX+f"/analises/{analysis['id']}/geracoes",headers=headers(),json=body).json()
    assert result['status']=='parcial'
    assert result['itens'][1]['erro_codigo']=='issue_alterada'
    next_analysis=analyze(s,ids=[s.issues[1]['id']])
    candidate_id=next_analysis['candidatas_rnc'][0]['id']
    invalid={'confirmar':True,'itens':[{'candidata_id':candidate_id,'dados_rnc':{'criticidade':'invalida'}}]}
    url=PREFIX+f"/analises/{next_analysis['id']}/geracoes"
    failed=s.c.post(url,headers=headers(),json=invalid).json()
    assert failed['status']=='falha' and failed['itens'][0]['erro_codigo']=='dados_rnc_invalidos'
    invalid['itens'][0]['dados_rnc']=rnc_data(s)
    assert s.c.post(url,headers=headers(),json=invalid).json()['status']=='concluida'


def test_selecao_rollback_gravacao_e_retentativa(setup,monkeypatch):
    from app.routers import issue_selecao
    s=setup;analysis=analyze(s);candidate_id=analysis['candidatas_rnc'][0]['id']
    original=issue_selecao.emitir_rnc_transacao
    def broken(*args):
        original(*args)
        raise RuntimeError('Falha depois da emissão')
    monkeypatch.setattr(issue_selecao,'emitir_rnc_transacao',broken)
    body={'confirmar':True,'itens':[{'candidata_id':candidate_id,'dados_rnc':rnc_data(s)}]}
    url=PREFIX+f"/analises/{analysis['id']}/geracoes"
    result=s.c.post(url,headers=headers(),json=body).json()
    assert result['status']=='falha'
    assert s.c.get(f"/api/issues/{s.issues[0]['id']}").json()['status']=='cadastrada'
    with get_connection() as conn:
        assert not conn.execute('SELECT 1 FROM rncs WHERE issue_id=?',(s.issues[0]['id'],)).fetchone()
    monkeypatch.setattr(issue_selecao,'emitir_rnc_transacao',original)
    assert s.c.post(url,headers=headers(),json=body).json()['status']=='concluida'


def test_selecao_limites_e_elegibilidade(setup):
    s=setup;body={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[]}
    assert s.c.post(PREFIX+'/analises',headers=headers(),json=body).status_code==422
    body['issue_ids']=[s.issues[0]['id']]*2
    assert s.c.post(PREFIX+'/analises',headers=headers(),json=body).status_code==422
    body['issue_ids']=[s.issues[0]['id']]*21
    assert s.c.post(PREFIX+'/analises',headers=headers(),json=body).status_code==422
    s.c.post(f"/api/issues/{s.issues[0]['id']}/fechar")
    body['issue_ids']=[s.issues[0]['id']]
    assert s.c.post(PREFIX+'/analises',headers=headers(),json=body).status_code==409
    assert s.c.get(PREFIX+'/elegiveis').json()['total']==1
    with get_connection() as conn:
        conn.execute('UPDATE issues SET evidencias_objetivas=? WHERE id=?',('x'*110000,s.issues[1]['id']))
    body['issue_ids']=[s.issues[1]['id']]
    assert s.c.post(PREFIX+'/analises',headers=headers(),json=body).status_code==413


def test_selecao_empresa_permissoes_e_modelos(setup):
    s=setup;analysis=analyze(s)
    login(s.c,'admin','admin');other=criar_empresa(s.c,'Outra '+uuid.uuid4().hex)['id']
    assert s.c.get(PREFIX+'/elegiveis').status_code==422
    login(s.c,s.emails[1],'teste')
    assert s.c.get(PREFIX+f'/acessos-llm?empresa_id={s.eid}').status_code==200
    assert s.c.get(PREFIX+f'/elegiveis?empresa_id={other}').status_code==403
    with get_connection() as conn:
        conn.execute('UPDATE usuarios SET papel=? WHERE id=?',('visualizador',s.users[1]))
    assert s.c.get(PREFIX+'/elegiveis').status_code==403
    assert s.c.get(PREFIX+f"/analises/{analysis['id']}").status_code==403
    s.c.post('/api/auth/logout')
    assert s.c.get(PREFIX+'/elegiveis').status_code==401


def test_selecao_limpeza_preserva_snapshot(setup):
    s=setup;analysis=analyze(s)
    preview=s.c.get('/api/issues/limpeza?escopo=todas').json()
    response=s.c.post('/api/issues/limpeza',json={**preview,'confirmar':True})
    assert response.status_code==200,response.text
    history=s.c.get(PREFIX+f"/analises/{analysis['id']}").json()
    assert len(history['candidatas_rnc'])==2
    assert history['candidatas_rnc'][0]['id_issue'] is None
    assert history['candidatas_rnc'][0]['codigo_issue']==s.issues[0]['codigo']
    init_db()
    assert s.c.get(PREFIX+f"/analises/{analysis['id']}").json()['status']=='concluida'


def test_selecao_timeout_configuracao_e_recuperacao(setup,monkeypatch):
    s=setup
    def fail(*args):raise llm_client.LlmError('timeout','Tempo excedido')
    monkeypatch.setattr(llm_client,'analisar_issues',fail)
    result=analyze(s)
    assert result['status']=='falha' and result['erro_codigo']=='timeout'
    response=s.c.post(PREFIX+'/analises',headers=headers(),json={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']]}).json()
    with get_connection() as conn:
        conn.execute("UPDATE llm_triagens SET status='processando',iniciado_em='2020-01-01T00:00:00+00:00' WHERE id=?",(response['id'],))
    issue_triagem.process_next()
    assert s.c.get(PREFIX+f"/analises/{response['id']}").json()['erro_codigo']=='analise_interrompida'
    with get_connection() as conn:conn.execute('UPDATE llm_acessos SET url_base=? WHERE id=?',('https://localhost/v1',s.access))
    rejected=s.c.post(PREFIX+'/analises',headers=headers(),json={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']]})
    assert rejected.status_code==422


def test_adapter_bloqueia_destinos_e_provedores():
    with pytest.raises(llm_client.LlmError):llm_client.endpoint({'provedor':'não suportado','url_base':'https://api.groq.com/openai/v1'})
    for url in ['http://api.groq.com/v1','https://127.0.0.1/v1','https://localhost/v1','https://api.groq.com:8080/v1','https://api.groq.com:abc/v1','https://api.groq.com/v1?api_key=segredo']:
        with pytest.raises(llm_client.LlmError):llm_client.endpoint({'provedor':'Groq','url_base':url})


@pytest.mark.parametrize('base',['https://api.deepseek.com','https://api.deepseek.com/v1'])
def test_deepseek_endpoint(base):
    assert llm_client.endpoint({'provedor':'DeepSeek','url_base':base}) == base+'/chat/completions'
    with pytest.raises(llm_client.LlmError):
        llm_client.endpoint({'provedor':'DeepSeek','url_base':'https://platform.deepseek.com/api_keys'})


def test_selecao_concorrencia_nao_duplica_rnc(setup):
    s=setup;analysis=analyze(s);candidate_id=analysis['candidatas_rnc'][0]['id']
    body={'confirmar':True,'itens':[{'candidata_id':candidate_id,'dados_rnc':rnc_data(s)}]}
    url=PREFIX+f"/analises/{analysis['id']}/geracoes"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:s.c.post(url,headers=headers(),json=body).json(),range(2)))
    assert sorted(r['status'] for r in results)==['concluida','falha']
    with get_connection() as conn:
        assert conn.execute('SELECT count(*) FROM rncs WHERE issue_id=?',(s.issues[0]['id'],)).fetchone()[0]==1


def test_selecao_worker_processa_lote_persistido(setup,monkeypatch):
    s=setup;called=threading.Event()
    def fake(access,prompt,items,on_progress=None):
        called.set()
        return '{"candidatas_rnc":[]}'
    monkeypatch.setattr(llm_client,'analisar_issues',fake)
    result=s.c.post(PREFIX+'/analises',headers=headers(),json={'empresa_id':s.eid,'acesso_llm_id':s.access,'issue_ids':[s.issues[0]['id']]}).json()
    stop,thread=REAL_START_WORKER()
    try:assert called.wait(timeout=3)
    finally:stop.set();thread.join(timeout=3)
    assert not thread.is_alive()
    assert s.c.get(PREFIX+f"/analises/{result['id']}").json()['status']=='concluida'


def test_worker_ocioso_nao_adquire_lock_de_escrita(setup,monkeypatch):
    statements=[]
    original=issue_triagem.get_connection
    def traced():
        conn=original();conn.set_trace_callback(statements.append);return conn
    monkeypatch.setattr(issue_triagem,'get_connection',traced)
    assert not issue_triagem.process_next()
    assert not any(sql.lstrip().upper().startswith(('BEGIN','UPDATE','INSERT','DELETE')) for sql in statements)


@pytest.mark.parametrize('status,expected',[(401,'acesso_llm_invalido'),(429,'limite_provedor'),(500,'provedor_indisponivel'),(302,'provedor_indisponivel'),(200,None)])
@pytest.mark.parametrize('provider',['Groq','OpenRouter','DeepSeek'])
def test_adapter_http_payload_e_erros(monkeypatch,status,expected,provider):
    import httpx
    original=httpx.Client
    captured=[]
    stages=[]
    def handler(request):
        if request.method=='GET':
            return httpx.Response(200,json={'data':[{'id':'modelo-teste','supported_parameters':['response_format']}]})
        captured.append(json.loads(request.content))
        assert request.headers['Authorization']=='Bearer chave-ficticia'
        return httpx.Response(status,json={'choices':[{'finish_reason':'stop','message':{'content':'{"candidatas_rnc":[]}'}}]})
    monkeypatch.setattr(llm_client,'endpoint',lambda *args,**kwargs:'https://api.groq.com/openai/v1/chat/completions')
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    access={'provedor':provider,'modelo':'modelo-teste','api_key':'chave-ficticia'}
    if expected:
        with pytest.raises(llm_client.LlmError) as error:llm_client.analisar_issues(access,'prompt',[],stages.append)
        assert error.value.code==expected
    else:assert llm_client.analisar_issues(access,'prompt',[],stages.append)=='{"candidatas_rnc":[]}'
    assert stages==(['aguardando'] if expected else ['aguardando','recebendo'])
    assert captured[0]['response_format']=={'type':'json_object'}
    assert captured[0]['messages'][0]['role']=='system'
    assert captured[0]['max_tokens' if provider in ('OpenRouter','DeepSeek') else 'max_completion_tokens']==8192
    assert 'tools' not in captured[0]


def test_openrouter_sem_json_mode_preserva_validacao(monkeypatch):
    import httpx
    original=httpx.Client
    captured=[]
    def handler(request):
        if request.method=='GET':
            return httpx.Response(200,json={'data':[{'id':'ling-teste','supported_parameters':['max_tokens'],
                'top_provider':{'max_completion_tokens':4096}}]})
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"candidatas_rnc":[]}'}}]})
    monkeypatch.setattr(llm_client,'endpoint',lambda *args,**kwargs:'https://openrouter.ai/api/v1/chat/completions')
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result=llm_client.analisar_issues({'provedor':'OpenRouter','modelo':'ling-teste','api_key':'ficticia'},'Retorne JSON',[])
    assert 'response_format' not in captured[0]
    assert captured[0]['max_tokens']==4096
    assert issue_triagem.validate_result(result,set())==[]
    with pytest.raises(llm_client.LlmError):issue_triagem.validate_result('Texto inválido',set())
