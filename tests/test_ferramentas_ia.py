import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from tests.test_pareto import seed
from tests.test_issues import login
from app.services.llm_client import LlmError

def test_adapter_text_mode_preserves_triage_json_mode(monkeypatch):
    import httpx
    from app.services import llm_client
    payloads=[]
    def transport(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'Análise textual'}}]})
    real_client=httpx.Client
    monkeypatch.setattr(llm_client,'endpoint',lambda access,resolve=False:'https://api.deepseek.com/chat/completions')
    monkeypatch.setattr(llm_client.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(transport),**kwargs))
    configured=dict(provedor='deepseek',modelo='teste',api_key='chave')
    response=llm_client.consultar_ferramenta(configured,'Compare <10.',{'ferramenta':'histograma'})
    assert response['resposta']=='Análise textual' and response['completa'] is True
    assert 'response_format' not in payloads[0]
    assert payloads[0]['thinking']=={'type':'disabled'}
    message=json.loads(payloads[0]['messages'][1]['content'])['consulta_ferramenta']
    assert message['instrucoes_usuario']=='Compare <10.' and message['dados']['ferramenta']=='histograma'
    llm_client.analisar_issues(configured,'Instruções antigas',[{'id':1}])
    assert payloads[1]['response_format']=={'type':'json_object'}
    assert 'thinking' not in payloads[1]
    assert 'issues' in json.loads(payloads[1]['messages'][1]['content'])

def access(c,eid):
    response=c.post('/api/configuracao/llm',json=dict(empresa_id=eid,nome='IA ferramenta',provedor='deepseek',modelo='modelo-teste',url_base='https://api.deepseek.com',api_key='chave-secreta'))
    assert response.status_code==201,response.text
    return response.json()['id']

def test_truncated_text_is_marked_partial_and_json_remains_strict(monkeypatch):
    import httpx
    import pytest
    from app.services import llm_client
    calls=[]
    choice={'finish_reason':'length','message':{'content':'Achados parciais'}}
    def transport(request):
        calls.append(request)
        return httpx.Response(200,json={'choices':[choice]})
    real_client=httpx.Client
    monkeypatch.setattr(llm_client,'endpoint',lambda access,resolve=False:'https://api.deepseek.com/chat/completions')
    monkeypatch.setattr(llm_client.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(transport),**kwargs))
    configured=dict(provedor='deepseek',modelo='teste',api_key='chave')
    result=llm_client.consultar_ferramenta(configured,'Analise',{})
    assert result['resposta']=='Achados parciais' and result['completa'] is False
    assert result['motivo_finalizacao']=='length' and 'parcial' in result['aviso']
    assert len(calls)==1
    with pytest.raises(LlmError):llm_client.analisar_issues(configured,'Prompt',[])
    choice['message']['content']=''
    with pytest.raises(LlmError,match='sem entregar texto'):llm_client.consultar_ferramenta(configured,'Analise',{})
    choice['finish_reason']='content_filter';choice['message']['content']='Texto bloqueado'
    with pytest.raises(LlmError,match='filtro de conteúdo'):llm_client.consultar_ferramenta(configured,'Analise',{})

def test_partial_answer_metadata_reaches_interface():
    with TestClient(app) as c,patch('app.routers.ferramentas_ia.consultar_ferramenta',return_value=dict(resposta='Texto parcial',completa=False,aviso='Limite atingido.',motivo_finalizacao='length')):
        eid,a,b,d=seed(c);aid=access(c,eid)
        snapshot=c.get('/api/ferramentas/pareto',params={'empresa_id':eid}).json()['consulta_ia']
        response=c.post('/api/ferramentas/ia/consultar',json={**snapshot,'acesso_id':aid,'prompt':'Analise.'})
        assert response.status_code==200
        assert response.json()['completa'] is False and response.json()['resposta']=='Texto parcial'

def test_prompt_snapshot_and_no_automatic_provider_call():
    with TestClient(app) as c,patch('app.routers.ferramentas_ia.consultar_ferramenta',return_value='<script>texto</script>') as provider:
        eid,a,b,d=seed(c);aid=access(c,eid)
        options=c.get('/api/ferramentas/ia/acessos',params={'empresa_id':eid}).json()
        assert options[0]['id']==aid and 'chave-secreta' not in json.dumps(options)
        for tool in ('pareto','histograma'):
            analysis=c.get('/api/ferramentas/'+tool,params={'empresa_id':eid,'base':'rncs'}).json()
            snapshot=analysis['consulta_ia'];data=json.loads(snapshot['snapshot'])
            assert data['ferramenta']==tool and len(data['resultados']['registros'])==2
            assert 'chave-secreta' not in snapshot['snapshot']
            calls=provider.call_count
            # GET/options and opening a snapshot never call the provider.
            c.get('/api/ferramentas/ia/acessos',params={'empresa_id':eid})
            assert provider.call_count==calls
            prompt='Compare <10 e >2; não invente dados.\nExplique limitações.'
            result=c.post('/api/ferramentas/ia/consultar',json={**snapshot,'acesso_id':aid,'prompt':prompt})
            assert result.status_code==200,result.text
            assert result.json()['resposta']=='<script>texto</script>'
            assert provider.call_args.args[1]==prompt
            assert provider.call_args.args[2]==data
            assert result.json()['prompt']==prompt
            changed={**snapshot,'snapshot':snapshot['snapshot']+' '}
            assert c.post('/api/ferramentas/ia/consultar',json={**changed,'acesso_id':aid,'prompt':prompt}).status_code==409
        assert c.post('/api/ferramentas/ia/consultar',json={**snapshot,'acesso_id':aid,'prompt':'   '}).status_code==422

def test_tenancy_inactive_access_and_provider_failure():
    with TestClient(app) as c,patch('app.routers.ferramentas_ia.consultar_ferramenta',side_effect=LlmError('limite','Limite de uso atingido.')) as provider:
        eid,a,b,d=seed(c);aid=access(c,eid)
        snapshot=c.get('/api/ferramentas/pareto',params={'empresa_id':eid}).json()['consulta_ia']
        body={**snapshot,'acesso_id':aid,'prompt':'Analise.'}
        result=c.post('/api/ferramentas/ia/consultar',json=body)
        assert result.status_code==502 and result.json()['detail']=='Limite de uso atingido.'
        assert provider.call_count==1
        login(c,'carlos','carlos')
        assert c.get('/api/ferramentas/ia/acessos',params={'empresa_id':eid}).status_code==403
        assert c.post('/api/ferramentas/ia/consultar',json=body).status_code==403
        own=c.get('/api/ferramentas/pareto').json()['consulta_ia']
        assert c.post('/api/ferramentas/ia/consultar',json={**own,'acesso_id':aid,'prompt':'Teste'}).status_code==404
        assert provider.call_count==1
