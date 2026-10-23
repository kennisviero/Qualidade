"""Regressões de contratos e autorizações do backend."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from tests.test_issues import login,criar_empresa,criar_issue

@pytest.fixture
def qa_client():
    from app.main import app
    with TestClient(app) as c:
        login(c,'admin','admin').raise_for_status()
        eid=criar_empresa(c,'QA '+uuid4().hex)['id']
        yield c,eid

@pytest.mark.parametrize('tool',['pareto','histograma','dispersao'])
def test_rg_lac_013_usuario_sem_empresa_nao_le_base_global(qa_client,tool):
    c,eid=qa_client
    created=criar_issue(c,empresa_id=eid,o_que='Dado privado QA')
    created.raise_for_status()
    global_response=c.get('/api/ferramentas/'+tool)
    assert global_response.status_code==200
    assert any(r['id']==created.json()['id'] for r in global_response.json()['registros'])
    email='qa_orfao_'+uuid4().hex
    c.post('/api/usuarios',json={'nome':'Sem empresa','email':email,'senha':'qa','papel':'editor'}).raise_for_status()
    login(c,email,'qa').raise_for_status()
    response=c.get('/api/ferramentas/'+tool)
    assert response.status_code in (403,422), 'Conta sem empresa não pode receber dados globais: '+response.text[:250]

@pytest.mark.parametrize('field',['detectado_em','comportamento_esperado','comportamento_observado','evidencias_objetivas','impacto','acao_emergencial','o_que','onde','quando','quem','como_detectado'])
def test_rg_iss_003_cada_campo_obrigatorio_recusa_espacos(qa_client,field):
    c,eid=qa_client
    response=criar_issue(c,empresa_id=eid,**{field:'   '})
    assert response.status_code==422
    assert 'obrigatori' in response.json()['detail'].lower()

def test_rg_emi_010_fatos_preservados_apos_editar_origem(qa_client):
    c,eid=qa_client
    issue=criar_issue(c,empresa_id=eid,comportamento_observado='Fato da emissão').json()
    emitted=c.post(f"/api/issues/{issue['id']}/emitir-rnc",json={});emitted.raise_for_status()
    rid=emitted.json()['rnc_id']
    c.put(f"/api/issues/{issue['id']}",json={'comportamento_observado':'Fato posterior'}).raise_for_status()
    assert c.get(f'/api/rncs/{rid}').json()['rnc_fatos_snapshot_json']['comportamento_observado']=='Fato da emissão'

def test_rg_aut_006_logout_revoga_outra_sessao(qa_client):
    c,eid=qa_client
    from app.main import app
    with TestClient(app) as other:
        login(other,'admin','admin').raise_for_status()
        c.post('/api/auth/logout').raise_for_status()
        assert other.get('/api/auth/me').status_code==401
