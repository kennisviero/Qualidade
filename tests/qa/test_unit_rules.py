"""Unidades críticas com rastreabilidade explícita às regras RG."""
from datetime import date
import pytest
from app.routers.pareto import norm,local_date
from app.routers.histograma import distribution,elapsed
from app.routers.dispersao import correlation
from app.services.ferramentas_ia import context,verify
from app.services.issue_triagem import validate_result,canonical
from app.services.llm_client import LlmError
from app.docs import safe_rel

@pytest.mark.parametrize('value,expected',[('  SELÁGEM  DUPLA ','selagem dupla'),(None,''),('A\t B','a b')])
def test_rg_fil_007_normalizacao(value,expected):
    assert norm(value)==expected

def test_rg_fil_006_limite_dia_local():
    assert local_date('2026-10-16T01:30:00+00:00')==date(2026,10,15)
    assert local_date('inválido') is None

def test_rg_his_003_limites_internos_e_maximo():
    bins,stats=distribution([0,1,2,3,4],2)
    assert [b['frequencia'] for b in bins]==[2,3]
    assert [b['inclui_fim'] for b in bins]==[False,True]
    assert sum(b['percentual'] for b in bins)==pytest.approx(100)
    assert stats['media']==2 and stats['mediana']==2

def test_rg_his_004_amostra_unica_e_vazia():
    bins,stats=distribution([8],50)
    assert len(bins)==1 and bins[0]['frequencia']==1
    assert stats['desvio_padrao'] is None
    assert distribution([])[1]['n']==0

def test_rg_his_005_tempo_nao_imputa_data():
    assert elapsed('2026-10-15T10:00','2026-10-15T11:30',3600)==1.5
    assert elapsed('2026-10-15','2026-10-16',3600) is None

def test_rg_dis_005_pearson_negativo_e_constante():
    assert correlation([{'x':1,'y':8},{'x':2,'y':4},{'x':3,'y':0}])==pytest.approx(-1)
    assert correlation([{'x':1,'y':1},{'x':1,'y':4}]) is None

def test_rg_llm_013_assinatura_rejeita_adulteracao():
    signed=context('relacoes',9,{'id':17},{'base':'issues'},{'registros':[]})
    assert verify(signed['snapshot'],signed['assinatura'])['usuario_id']==17
    assert verify(signed['snapshot'].replace('"empresa_id":9','"empresa_id":8'),signed['assinatura']) is None

@pytest.mark.parametrize('content',['{"candidatas_rnc":[],"candidatas_rnc":[]}','```json\n{"candidatas_rnc":[]}\n```','{"candidatas_rnc":[],"extra":true}'])
def test_rg_tri_009_json_estrito(content):
    with pytest.raises(LlmError):validate_result(content,{1})
    assert validate_result(canonical({'candidatas_rnc':[]}),{1})==[]

def test_rg_doc_005_traversal_e_caminho_valido(tmp_path):
    assert safe_rel(tmp_path,'sub/pasta')==tmp_path/'sub'/'pasta'
    with pytest.raises(ValueError):safe_rel(tmp_path,'../fora')
