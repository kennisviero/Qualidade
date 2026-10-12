from fastapi.testclient import TestClient

from app.main import app
from app.db import get_connection
from test_issues import criar_empresa, criar_editor, login


def payload(eid):
    return dict(empresa_id=eid, nome='Modelo de teste', provedor='Provedor teste',
                modelo='modelo-teste', url_base='https://example.com/v1', api_key='chave-secreta-teste', ativo=True)


def test_llm_crud_chave_e_validacoes():
    with TestClient(app) as c:
        login(c, 'admin', 'admin')
        eid = criar_empresa(c, 'Configuração LLM')['id']
        body = payload(eid)
        response = c.post('/api/configuracao/llm', json=body)
        assert response.status_code == 201, response.text
        item = response.json()
        assert item['chave_configurada'] and 'api_key' not in item
        access_id = item['id']
        assert c.post('/api/configuracao/llm', json=body).status_code == 409
        assert c.post('/api/configuracao/llm', json={**body, 'nome':'Outra', 'api_key':''}).status_code == 422
        assert c.post('/api/configuracao/llm', json={**body, 'url_base':'javascript:alert(1)'}).status_code == 422
        assert c.post('/api/configuracao/llm', json={**body, 'nome':'   '}).status_code == 422
        updated = c.put(f'/api/configuracao/llm/{access_id}', json={**body,'modelo':'novo','api_key':'','ativo':False})
        assert updated.status_code == 200
        assert updated.json()['modelo'] == 'novo' and not updated.json()['ativo']
        with get_connection() as conn:
            assert conn.execute('SELECT api_key FROM llm_acessos WHERE id=?', (access_id,)).fetchone()[0] == body['api_key']
        assert 'chave-secreta-teste' not in c.get(f'/api/configuracao/llm?empresa_id={eid}').text
        assert c.get(f'/api/configuracao/llm/{access_id}').status_code == 200
        assert c.delete(f'/api/configuracao/llm/{access_id}').status_code == 204
        assert c.get(f'/api/configuracao/llm/{access_id}').status_code == 404


def test_llm_permissoes_e_tenancy():
    with TestClient(app) as c:
        assert c.get('/api/configuracao/llm').status_code == 401
        login(c,'admin','admin')
        eid = criar_empresa(c,'LLM A')['id']
        other = criar_empresa(c,'LLM B')['id']
        access_id = c.post('/api/configuracao/llm',json=payload(other)).json()['id']
        assert c.get('/api/configuracao/llm').status_code == 422
        criar_editor(c,eid,papel='admin')
        assert c.get(f'/api/configuracao/llm?empresa_id={other}').status_code == 403
        assert c.get(f'/api/configuracao/llm/{access_id}').status_code == 404
        assert c.put(f'/api/configuracao/llm/{access_id}',json=payload(other)).status_code == 404
        assert c.delete(f'/api/configuracao/llm/{access_id}').status_code == 404
        assert c.post('/api/configuracao/llm',json=payload(eid)).status_code == 201
        for role in ('editor','visualizador'):
            login(c,'admin','admin')
            criar_editor(c,eid,papel=role)
            assert c.get('/api/configuracao/llm').status_code == 403
            assert c.post('/api/configuracao/llm',json=payload(eid)).status_code == 403
