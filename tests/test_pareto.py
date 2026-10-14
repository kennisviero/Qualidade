import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_connection
from tests.test_issues import criar_empresa, criar_issue, login

def seed(c):
    login(c,'admin','admin')
    eid=criar_empresa(c,'Pareto '+uuid4().hex)['id']
    a=criar_issue(c,empresa_id=eid,o_que='Etiqueta',impacto='Alto',ambiente='Homologação',codigo_erro='SIM-FERR-test').json()
    b=criar_issue(c,empresa_id=eid,o_que='etiquéta',impacto='alto',ambiente='homologacao').json()
    d=criar_issue(c,empresa_id=eid,o_que='Selagem',impacto='baixo').json()
    for issue in (a,b,d):assert 'id' in issue,issue
    for issue in (a,b):
        response=c.post(f"/api/issues/{issue['id']}/emitir-rnc",json={})
        assert response.status_code==200,response.text
    criar_issue(c,empresa_id=eid,o_que='Etiqueta',impacto='Alto',ambiente='Homologação',codigo_erro='SIM-FERR-aberta').raise_for_status()
    aberta=criar_issue(c,empresa_id=eid,o_que='etiquéta',impacto='alto',ambiente='homologacao').json()
    fechada=criar_issue(c,empresa_id=eid,o_que='Categoria fechada',impacto='critico').json()
    assert c.post(f"/api/issues/{fechada['id']}/fechar").status_code==200
    with get_connection() as conn:
        conn.execute("UPDATE issues SET status='em_tratamento' WHERE id=?",(aberta['id'],))
        rncs=conn.execute('SELECT id,issue_id FROM rncs WHERE empresa_id=? ORDER BY id',(eid,)).fetchall()
        for r in rncs:
            conn.execute('INSERT INTO rnc_observacoes (rnc_id,quantidade_afetada,unidade_quantidade,horas_perdidas,prejuizo_financeiro,moeda) VALUES (?,?,?,?,?,?)',
                (r['id'],3 if r['issue_id']==a['id'] else None,'peças',2,10,'BRL'))
        conn.commit()
    return eid,a,b,d

def test_pareto_filters_normalization_and_single_count():
    with TestClient(app) as c:
        eid,a,b,d=seed(c)
        result=c.get('/api/ferramentas/pareto',params={'empresa_id':eid}).json()
        assert result['dados']['total']==3
        assert [r['frequencia'] for r in result['dados']['itens']]==[2,1]
        assert result['dados']['itens'][-1]['acumulado']==100
        assert len(result['opcoes']['impacto'])==2
        assert {r['status'] for r in result['registros']}=={'cadastrada','em_tratamento'}
        assert all(not r['tem_rnc'] for r in result['registros'])
        assert {o['valor'] for o in result['opcoes']['status']}=={'cadastrada','em_tratamento'}
        assert 'categoria fechada' not in {o['valor'] for o in result['opcoes']['categoria']}
        for params,total in [({'impacto':'alto'},2),({'vinculo':'com'},0),({'vinculo':'sem'},3),({'status':'fechada'},0),({'simulados':'somente'},1),({'simulados':'excluir'},2),({'ambiente':'homologacao'},2),({'categoria':'etiqueta'},2)]:
            result=c.get('/api/ferramentas/pareto',params={'empresa_id':eid,**params}).json()
            assert result['dados']['total']==total
        result=c.get('/api/ferramentas/pareto',params={'base':'rncs','empresa_id':eid}).json()
        assert result['dados']['total']==2
        with get_connection() as conn:
            # Mesmo um status inconsistente não permite incluir Issue com RNC.
            conn.execute("UPDATE issues SET status='cadastrada',finalizado_em=NULL WHERE id=?",(a['id'],))
            conn.commit()
        result=c.get('/api/ferramentas/pareto',params={'empresa_id':eid}).json()
        assert result['dados']['total']==3
        assert a['id'] not in {r['id'] for r in result['registros']}

def test_rnc_measures_missing_units_snapshot_and_date():
    with TestClient(app) as c:
        eid,a,b,d=seed(c)
        params={'base':'rncs','empresa_id':eid,'medida':'quantidade','unidade':'pecas'}
        result=c.get('/api/ferramentas/pareto',params=params).json()
        assert result['dados']['total']==3 and result['sem_medida']==1
        result=c.get('/api/ferramentas/pareto',params={**params,'medida':'horas','unidade':''}).json()
        assert result['dados']['total']==4
        with get_connection() as conn:
            conn.execute("UPDATE issues SET o_que='Texto alterado',detectado_em='2026-10-11T02:00:00+00:00' WHERE id=?",(a['id'],))
            conn.execute("UPDATE rnc_observacoes SET quantidade_afetada=5,unidade_quantidade='pedidos' WHERE rnc_id=(SELECT id FROM rncs WHERE issue_id=?)",(b['id'],))
            conn.commit()
        result=c.get('/api/ferramentas/pareto',params={'base':'rncs','empresa_id':eid}).json()
        assert result['dados']['itens'][0]['frequencia']==2 # fatos preservados
        assert c.get('/api/ferramentas/pareto',params={**params,'unidade':''}).status_code==422
        result=c.get('/api/ferramentas/pareto',params={'empresa_id':eid,'inicio':'2026-10-10','fim':'2026-10-10'}).json()
        assert result['incluidos']==3 # inclusive e horário de São Paulo
        assert c.get('/api/ferramentas/pareto',params={'inicio':'2026-10-11','fim':'2026-10-10'}).status_code==422
        assert c.get('/api/ferramentas/pareto',params={'medida':'horas'}).status_code==422

def test_pareto_tenancy_and_auth():
    with TestClient(app) as c:
        assert c.get('/api/ferramentas/pareto').status_code==401
        eid,a,b,d=seed(c)
        login(c,'carlos','carlos')
        assert c.get('/api/ferramentas/pareto',params={'empresa_id':eid}).status_code==403
        result=c.get('/api/ferramentas/pareto').json()
        assert all(r['empresa_id']!=eid for r in result['registros'])
