from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from app.routers.histograma import distribution
from tests.test_pareto import seed
from tests.test_issues import login

def test_intervals_boundaries_constant_and_empty():
    bins,stats=distribution([0,1,2,3,4],2)
    assert [b['frequencia'] for b in bins]==[2,3]
    assert stats['media']==2 and stats['mediana']==2
    assert bins[-1]['inclui_fim']
    bins,stats=distribution([0,0,0],10)
    assert len(bins)==1 and bins[0]['frequencia']==3
    assert stats['desvio_padrao']==0
    assert distribution([])[0]==[]

def test_issues_eligibility_time_filters_and_invalid_data():
    with TestClient(app) as c:
        eid,a,b,d=seed(c)
        with get_connection() as conn:
            ids=[r[0] for r in conn.execute("SELECT id FROM issues WHERE empresa_id=? AND status IN ('cadastrada','em_tratamento')",(eid,))]
            for i,issue_id in enumerate(ids):
                conn.execute('UPDATE issues SET detectado_em=?,criado_em=? WHERE id=?',
                    ('2026-10-10T10:00:00-03:00',['2026-10-10T11:00:00-03:00','2026-10-10T12:00:00-03:00','2026-10-10T09:00:00-03:00'][i],issue_id))
            conn.commit()
        params={'empresa_id':eid,'medida':'registro_horas','classes':2}
        response=c.get('/api/ferramentas/histograma',params=params)
        assert response.status_code==200,response.text
        result=response.json()
        assert result['selecionados']==3 and result['incluidos']==2 and result['invalidos']==1
        assert result['estatisticas']['media']==1.5
        assert sum(b['frequencia'] for b in result['intervalos'])==2
        assert all(not r['tem_rnc'] for r in result['registros'])
        assert c.get('/api/ferramentas/histograma',params={**params,'medida':'prejuizo'}).status_code==422
        assert c.get('/api/ferramentas/histograma',params={**params,'classes':51}).status_code==422
        assert c.get('/api/ferramentas/histograma',params={**params,'inicio':'2026-10-11','fim':'2026-10-10'}).status_code==422

def test_rnc_metrics_units_missing_containment_and_tenancy():
    with TestClient(app) as c:
        eid,a,b,d=seed(c)
        params={'empresa_id':eid,'base':'rncs','medida':'quantidade','unidade':'pecas'}
        result=c.get('/api/ferramentas/histograma',params=params).json()
        assert result['incluidos']==1 and result['sem_medida']==1
        assert result['estatisticas']['minimo']==3
        with get_connection() as conn:
            conn.execute("UPDATE rncs SET contencao_em='2026-10-10T12:00' WHERE issue_id=?",(a['id'],))
            conn.execute("UPDATE rnc_observacoes SET quantidade_afetada=5,unidade_quantidade='pedidos' WHERE rnc_id=(SELECT id FROM rncs WHERE issue_id=?)",(b['id'],))
            conn.commit()
        assert c.get('/api/ferramentas/histograma',params={**params,'unidade':''}).status_code==422
        result=c.get('/api/ferramentas/histograma',params={**params,'medida':'contencao_horas','unidade':''}).json()
        assert result['incluidos']==1 and result['sem_medida']==1
        assert result['estatisticas']['media']==2
        result=c.get('/api/ferramentas/histograma',params={**params,'medida':'horas','unidade':''}).json()
        assert result['incluidos']==2 and result['intervalos'][0]['frequencia']==2
        login(c,'carlos','carlos')
        assert c.get('/api/ferramentas/histograma',params=params).status_code==403
        assert all(r['empresa_id']!=eid for r in c.get('/api/ferramentas/histograma').json()['registros'])
        c.post('/api/auth/logout')
        assert c.get('/api/ferramentas/histograma').status_code==401
