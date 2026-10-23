from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from tests.test_pareto import seed
from tests.test_issues import login
from tests.test_ferramentas_ia import access

ROOT='/api/ferramentas/matriz'

@pytest.fixture
def prepared():
    with TestClient(app) as c:
        eid,*_=seed(c)
        ids=[r['id'] for r in c.get(ROOT+'/fontes',params={'empresa_id':eid}).json()['registros']]
        result=c.get(ROOT,params={'empresa_id':eid,'contexto':'geral','rnc_ids':','.join(map(str,ids))})
        assert result.status_code==200,result.text
        yield c,eid,ids,result.json()

def body(result):
    return dict(titulo='Revisão de cobertura',**result['consulta_ia'],linhas=result['linhas'],colunas=result['colunas'],celulas=[])

def originals():
    with get_connection() as conn:
        return {table:[tuple(r) for r in conn.execute('SELECT * FROM '+table+' ORDER BY id')] for table in ['issues','rncs','acoes']}

def test_matriz_context_selection_sources_and_auth(prepared):
    c,eid,ids,result=prepared
    assert result['contexto']=='geral' and len(result['linhas'])==2 and len(result['acoes'])==2
    one=c.get(ROOT,params={'empresa_id':eid,'rnc_ids':ids[0]})
    assert one.status_code==200 and len(one.json()['linhas'])==1
    assert all(a['rnc_id']==ids[0] for a in one.json()['acoes'])
    assert c.get(ROOT+'/fontes',params={'empresa_id':eid,'categoria':'inexistente'}).json()['registros']==[]
    for params in [{'rnc_ids':''},{'rnc_ids':'a'},{'rnc_ids':','.join(map(str,ids))},{'contexto':'geral','rnc_ids':str(ids[0])},{'contexto':'geral','rnc_ids':f'{ids[0]},{ids[0]}'},{'rnc_ids':'-1'}]:
        assert c.get(ROOT,params={'empresa_id':eid,**params}).status_code==422
    assert c.get(ROOT,params={'empresa_id':eid,'rnc_ids':999999}).status_code==404
    c.post('/api/auth/logout')
    assert c.get(ROOT+'/fontes').status_code==401

def test_matriz_pending_is_not_none_and_original_plans_unchanged(prepared):
    c,eid,ids,result=prepared;before=originals();payload=body(result)
    initial=c.post(ROOT+'/preparar',json=payload).json()['resumo']
    assert initial['avaliados']==0 and initial['nao_avaliados']==4
    assert initial['linhas_com_avaliacao_pendente']==ids
    assert initial['linhas_sem_cobertura_apos_avaliacao']==[]
    payload['celulas']=[dict(linha_id=ids[0],acao_id=a,intensidade='nenhuma',justificativa='Sem contribuição para este problema') for a in result['colunas']]
    assessed=c.post(ROOT+'/preparar',json=payload)
    assert assessed.status_code==200,assessed.text
    summary=assessed.json()['resumo']
    assert summary['avaliados']==2 and summary['nao_avaliados']==2
    assert summary['linhas_com_avaliacao_pendente']==[ids[1]]
    assert summary['linhas_sem_cobertura_apos_avaliacao']==[ids[0]]
    payload['celulas'][0].update(intensidade='forte',justificativa='Contribuição a verificar')
    positive=c.post(ROOT+'/preparar',json=payload).json()['resumo']
    assert ids[0] not in positive['linhas_sem_relacao_indicada']
    saved=c.post(ROOT+'/diagramas',json=payload)
    assert saved.status_code==200,saved.text
    assert originals()==before

@pytest.mark.parametrize('variant',['reason','duplicate_cell','foreign_action','foreign_line','duplicate_line','foreign_origin','duplicate_origin','evidence','extra'])
def test_matriz_rejects_invalid_cells_lines_and_evidence(prepared,variant):
    c,eid,ids,result=prepared;payload=deepcopy(body(result))
    payload['celulas']=[dict(linha_id=ids[0],acao_id=result['colunas'][0],intensidade='nenhuma',justificativa='Avaliação justificada')]
    if variant=='reason':payload['celulas'][0]['justificativa']=' '
    if variant=='duplicate_cell':payload['celulas']*=2
    if variant=='foreign_action':payload['celulas'][0]['acao_id']=999999
    if variant=='foreign_line':payload['celulas'][0]['linha_id']=999999
    if variant=='duplicate_line':payload['linhas'].append(deepcopy(payload['linhas'][0]))
    if variant=='foreign_origin':payload['linhas'][0]['rnc_ids']=[999999]
    if variant=='duplicate_origin':payload['linhas'][0]['rnc_ids']*=2
    if variant=='evidence':payload['linhas'][0].update(situacao='fator_evidenciado',evidencia=' ')
    if variant=='extra':payload['celulas'][0]['pontuacao']=99
    response=c.post(ROOT+'/preparar',json=payload)
    assert response.status_code==422,response.text

def test_matriz_persistence_revision_and_snapshot(prepared):
    c,eid,ids,result=prepared;payload=body(result)
    saved=c.post(ROOT+'/diagramas',json=payload).json();did=saved['id']
    assert c.get(ROOT+'/diagramas',params={'empresa_id':eid,'contexto':'geral'}).json()[0]['id']==did
    assert c.get(ROOT+'/diagramas',params={'empresa_id':eid,'contexto':'rnc'}).json()==[]
    action=result['acoes'][0]
    with get_connection() as conn:
        conn.execute("UPDATE acoes SET descricao='Plano posterior' WHERE id=?",(action['id'],));conn.commit()
    reopened=c.get(f'{ROOT}/diagramas/{did}').json()
    assert next(a for a in reopened['acoes'] if a['id']==action['id'])==action
    update=c.put(f'{ROOT}/diagramas/{did}',json={**payload,'revisao':1,'titulo':'Revista'})
    assert update.status_code==200 and update.json()['revisao']==2
    assert c.put(f'{ROOT}/diagramas/{did}',json={**payload,'revisao':1}).status_code==409
    one=c.get(ROOT,params={'empresa_id':eid,'rnc_ids':ids[0]}).json()
    assert c.put(f'{ROOT}/diagramas/{did}',json={**body(one),'revisao':2}).status_code==422

def test_matriz_tenancy_viewer_and_snapshot_identity(prepared):
    c,eid,ids,result=prepared;payload=body(result)
    did=c.post(ROOT+'/diagramas',json=payload).json()['id']
    assert c.post(ROOT+'/preparar',json={**payload,'assinatura':'0'*64}).status_code==409
    login(c,'carlos','carlos')
    assert c.get(ROOT+'/fontes',params={'empresa_id':eid}).status_code==403
    assert c.get(ROOT,params={'rnc_ids':ids[0]}).status_code==404
    assert c.get(f'{ROOT}/diagramas/{did}').status_code==403
    login(c,'admin','admin')
    with get_connection() as conn:
        uid=conn.execute("SELECT id FROM usuarios WHERE email='admin'").fetchone()[0]
        conn.execute("UPDATE usuarios SET papel='visualizador',empresa_id=? WHERE id=?",(eid,uid));conn.commit()
    try:
        assert c.get(f'{ROOT}/diagramas/{did}').status_code==200
        assert c.post(ROOT+'/preparar',json=payload).status_code==200
        assert c.post(ROOT+'/diagramas',json=payload).status_code==403
        assert c.put(f'{ROOT}/diagramas/{did}',json=payload).status_code==403
    finally:
        with get_connection() as conn:
            conn.execute("UPDATE usuarios SET papel='admin',empresa_id=NULL WHERE id=?",(uid,));conn.commit()

def test_matriz_ai_explicit_signed_snapshot_and_mock_provider(prepared):
    c,eid,ids,result=prepared;payload=body(result);aid=access(c,eid);before=originals()
    with patch('app.routers.ferramentas_ia.consultar_ferramenta',return_value='Revisão simulada') as provider:
        preview=c.post(ROOT+'/preparar',json=payload)
        assert preview.status_code==200,preview.text
        assert provider.call_count==0
        signed=preview.json()['consulta_ia'];decoded=json.loads(signed['snapshot'])
        assert decoded['ferramenta']=='matriz' and decoded['resultados']['contexto']=='geral'
        response=c.post('/api/ferramentas/ia/consultar',json={**signed,'acesso_id':aid,'prompt':'Revise as relações sem inventar eficácia.'})
        assert response.status_code==200,response.text
        assert provider.call_count==1 and provider.call_args.args[2]==decoded
        assert response.json()['resposta']=='Revisão simulada'
        assert c.post('/api/ferramentas/ia/consultar',json={**signed,'snapshot':signed['snapshot']+' ','acesso_id':aid,'prompt':'Revise'}).status_code==409
        assert provider.call_count==1
    assert originals()==before

def test_matriz_limits_long_report_and_same_company_other_user(prepared):
    c,eid,ids,result=prepared;payload=body(result)
    for field,items in [('linhas',[dict(id=n+1,nome='Fator',rnc_ids=[ids[0]]) for n in range(41)]),('colunas',list(range(1,62)))]:
        assert c.post(ROOT+'/preparar',json={**payload,field:items}).status_code==422
    assert c.get(ROOT,params={'empresa_id':eid,'contexto':'geral','rnc_ids':','.join(map(str,range(1,22)))}).status_code==422
    long='Relato factual detalhado. '*120
    with get_connection() as conn:
        row=conn.execute('SELECT fatos_snapshot_json FROM rncs WHERE id=?',(ids[0],)).fetchone()
        facts=json.loads(row[0]);facts['comportamento_observado']=long
        conn.execute('UPDATE rncs SET fatos_snapshot_json=? WHERE id=?',(json.dumps(facts),ids[0]));conn.commit()
    fresh=c.get(ROOT,params={'empresa_id':eid,'rnc_ids':ids[0]}).json()
    assert len(fresh['linhas'][0]['nome'])<=2000 and 'relato completo' in fresh['linhas'][0]['nome']
    assert fresh['registros'][0]['fatos']['comportamento_observado']==long
    assert c.post(ROOT+'/preparar',json=body(fresh)).status_code==200
    with get_connection() as conn:
        issue_id=conn.execute('SELECT issue_id FROM rncs WHERE id=?',(ids[0],)).fetchone()[0]
        conn.executemany('INSERT INTO acoes (issue_id,rnc_id,descricao) VALUES (?,?,?)',[(issue_id,ids[0],'Ação sintética de limite') for _ in range(60)])
        conn.commit()
    assert c.get(ROOT,params={'empresa_id':eid,'rnc_ids':ids[0]}).status_code==422
    email='matriz-other-'+str(eid)
    assert c.post('/api/usuarios',json={'nome':'Outro analista','email':email,'senha':'qa','papel':'editor','empresa_id':eid}).status_code==201
    login(c,email,'qa')
    assert c.post(ROOT+'/preparar',json=payload).status_code==403
