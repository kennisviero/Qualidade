from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from tests.test_issues import criar_empresa, criar_issue, login


def test_ishikawa_objetivo_titulos_conteudo_persistem():
    with TestClient(app) as c:
        login(c,'admin','admin')
        eid=criar_empresa(c,'Ishikawa '+uuid4().hex)['id']
        issue=criar_issue(c,empresa_id=eid).json()
        assert c.post(f"/api/issues/{issue['id']}/emitir-rnc",json={}).status_code==200
        record=c.get('/api/rncs',params={'empresa_id':eid}).json()[0]
        path=f"/api/rncs/{record['rnc_id']}"
        stage={'efeito':'Reduzir erros para 1%','conclusao':'Revisar controles'}
        keys=['metodo','maquina','material','mao_obra','medicao','meio_ambiente']
        for key in keys:
            stage[key]='Conteúdo '+key
            stage[key+'_titulo']='Título livre '+key
        payload={'analise':'Notas preservadas','etapa_ishikawa':stage}
        response=c.put(path,json={'investigacao_json':payload})
        assert response.status_code==200,response.text
        assert c.get(path).json()['rnc_investigacao_json']==payload
        assert c.put(path,json={'resumo':'Outro campo'}).status_code==200
        assert c.get(path).json()['rnc_investigacao_json']==payload
        from app.db import get_connection
        import json
        with get_connection() as conn:
            stored=json.loads(conn.execute('SELECT investigacao_json FROM rncs WHERE id=?',(record['rnc_id'],)).fetchone()[0])
        assert stored==payload
        stage['metodo_titulo']=''
        assert c.put(path,json={'investigacao_json':payload}).status_code==200
        assert c.get(path).json()['rnc_investigacao_json']['etapa_ishikawa']['metodo_titulo']==''
