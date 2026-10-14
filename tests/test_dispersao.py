import json
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from app.routers.dispersao import correlation
from tests.test_pareto import seed
from tests.test_issues import login

def test_correlation_and_constant_axes():
    assert correlation([]) is None
    assert correlation([dict(x=1,y=2)]) is None
    assert correlation([dict(x=1,y=2),dict(x=1,y=3)]) is None
    assert abs(correlation([dict(x=1,y=2),dict(x=2,y=4),dict(x=3,y=6)])-1)<1e-12
    assert abs(correlation([dict(x=1,y=6),dict(x=2,y=4),dict(x=3,y=2)])+1)<1e-12

def test_rnc_same_record_pairs_units_missing_and_ai():
    with TestClient(app) as c:
        eid,a,b,d=seed(c)
        with get_connection() as conn:
            conn.execute('UPDATE rnc_observacoes SET quantidade_afetada=5,horas_perdidas=4 WHERE rnc_id=(SELECT id FROM rncs WHERE issue_id=?)',(b['id'],))
            conn.commit()
        params=dict(empresa_id=eid,base='rncs',eixo_x='quantidade',eixo_y='horas',unidade='pecas')
        response=c.get('/api/ferramentas/dispersao',params=params)
        assert response.status_code==200,response.text
        result=response.json()
        assert sorted((p['x'],p['y']) for p in result['pontos'])==[(3,2),(5,4)]
        assert abs(result['correlacao']-1)<1e-12
        assert {p['issue_id'] for p in result['pontos']}=={a['id'],b['id']}
        data=json.loads(result['consulta_ia']['snapshot'])
        assert data['ferramenta']=='dispersao' and data['resultados']['registros']==result['registros']
        assert data['parametros']['eixo_x']=='quantidade'
        with get_connection() as conn:
            conn.execute("UPDATE rnc_observacoes SET unidade_quantidade='pedidos' WHERE rnc_id=(SELECT id FROM rncs WHERE issue_id=?)",(b['id'],))
            conn.commit()
        assert c.get('/api/ferramentas/dispersao',params={**params,'unidade':''}).status_code==422
        result=c.get('/api/ferramentas/dispersao',params=params).json()
        assert result['incluidos']==1 and result['correlacao'] is None
        with get_connection() as conn:
            conn.execute('UPDATE rnc_observacoes SET horas_perdidas=NULL WHERE rnc_id=(SELECT id FROM rncs WHERE issue_id=?)',(a['id'],))
            conn.commit()
        result=c.get('/api/ferramentas/dispersao',params=params).json()
        assert result['sem_par']==1 and result['pontos']==[]

def test_issue_eligibility_filters_and_tenancy():
    with TestClient(app) as c:
        assert c.get('/api/ferramentas/dispersao').status_code==401
        eid,a,b,d=seed(c)
        result=c.get('/api/ferramentas/dispersao',params={'empresa_id':eid}).json()
        assert result['incluidos']==3
        assert all(not p['tem_rnc'] and p['status'] in ('cadastrada','em_tratamento') for p in result['pontos'])
        assert c.get('/api/ferramentas/dispersao',params={'empresa_id':eid,'eixo_x':'horas'}).status_code==422
        assert c.get('/api/ferramentas/dispersao',params={'empresa_id':eid,'eixo_y':'idade_dias'}).status_code==422
        result=c.get('/api/ferramentas/dispersao',params={'empresa_id':eid,'status':'fechada'}).json()
        assert result['selecionados']==0
        assert c.get('/api/ferramentas/dispersao',params={'inicio':'2026-10-11','fim':'2026-10-10'}).status_code==422
        login(c,'carlos','carlos')
        assert c.get('/api/ferramentas/dispersao',params={'empresa_id':eid}).status_code==403
        assert all(p['empresa_id']!=eid for p in c.get('/api/ferramentas/dispersao').json()['pontos'])
