from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from tests.test_issues import criar_empresa, criar_issue, login


def test_arvore_persistencia_hierarquia_e_isolamento():
    with TestClient(app) as c:
        login(c,'admin','admin')
        eid=criar_empresa(c,'Arvore '+uuid4().hex)['id']
        issue=criar_issue(c,empresa_id=eid).json()
        assert c.post(f"/api/issues/{issue['id']}/emitir-rnc",json={}).status_code==200
        record=c.get('/api/rncs',params={'empresa_id':eid}).json()[0]
        path=f"/api/rncs/{record['rnc_id']}"
        previous=record['acoes']
        nodes=[{'id':1,'descricao':'Controlar arquivos'},
               {'id':2,'pai_id':1,'descricao':'Retirar versões antigas','prazo':'2026-11-01','criterio_aceite':'Somente revisão aprovada disponível'}]
        assert c.put(path,json={'arvore':nodes}).status_code==422
        response=c.put(path,json={'objetivo':'Reduzir erros de etiqueta para 1%','arvore':nodes})
        assert response.status_code==200,response.text
        saved=c.get(path).json()
        assert saved['rnc_arvore'][1]['pai_id']==1
        assert saved['acoes']==previous
        assert c.put(path,json={'resumo':'Etiquetas'}).status_code==200
        assert c.get(path).json()['rnc_arvore']==saved['rnc_arvore']
        for bad in ([{'id':1,'pai_id':1,'descricao':'Ciclo'}],
                    [{'id':1,'pai_id':9,'descricao':'Órfão'}],
                    [{'id':1,'descricao':'A'},{'id':1,'descricao':'B'}],
                    [{'id':1,'descricao':' '}],
                    [{'id':1,'descricao':'A','prazo':'inválida'}],
                    [{'id':1,'descricao':'A','responsavel_id':999999}]):
            assert c.put(path,json={'arvore':bad}).status_code==422
            assert c.get(path).json()['rnc_arvore']==saved['rnc_arvore']
        assert c.put(path,json={'objetivo':''}).status_code==422
        login(c,'carlos','carlos')
        assert c.get(path).status_code==404
        assert c.put(path,json={'objetivo':'Outro'}).status_code==404
        login(c,'admin','admin')
        from app.db import get_connection
        with get_connection() as conn:
            conn.execute("UPDATE rncs SET status='concluida' WHERE id=?",(record['rnc_id'],))
        assert c.put(path,json={'arvore':[]}).status_code==409
