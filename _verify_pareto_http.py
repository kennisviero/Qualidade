import json
import urllib.request
from app.db import get_connection
from app.routers.pareto import analysis

with get_connection() as conn:
    user=dict(conn.execute("SELECT * FROM usuarios WHERE empresa_id=4 AND papel='admin' ORDER BY id LIMIT 1").fetchone())
result=analysis(base='rncs',empresa_id=4,simulados='somente',user=user)
from collections import Counter
batch=[r for r in result['registros'] if 'RNC-2026-002'<=r['codigo']<='RNC-2026-031']
assert len(batch)==30
assert sorted(Counter(r['categoria'] for r in batch).values())==[2,3,5,8,12]
print('Base ativa: lote de 30 RNCs preservado, categorias 12/8/5/3/2; total de simuladas identificadas:',result['dados']['total'])
from app.routers.histograma import histogram
for base,metrics in [('issues',['idade_dias','registro_horas']),('rncs',['idade_dias','emissao_horas','contencao_horas','horas','quantidade','prejuizo'])]:
    for metric in metrics:
        data=histogram(base=base,empresa_id=4,medida=metric,classes=None,user=user)
        assert sum(b['frequencia'] for b in data['intervalos'])==data['incluidos']
        if base=='issues':assert all(not r['tem_rnc'] and r['status'] in ('cadastrada','em_tratamento') for r in data['registros'])
        print('Histograma:',base,metric,'incluídos',data['incluidos'],'sem medida',data['sem_medida'],'inválidos',data['invalidos'])
try:
    from app.routers.dispersao import scatter
    for x,y in [('quantidade','horas'),('quantidade','prejuizo'),('contencao_horas','quantidade')]:
        data=scatter(base='rncs',empresa_id=4,eixo_x=x,eixo_y=y,unidade='unidades',moeda='BRL',user=user)
        assert data['incluidos']==len(data['pontos'])
        print('Dispersão:',x,y,'pares',data['incluidos'],'r',data['correlacao'])
    with urllib.request.urlopen('http://127.0.0.1:8000/openapi.json',timeout=5) as response:
        paths=json.load(response)['paths']
    print('Servidor ativo com rota Pareto:', '/api/ferramentas/pareto' in paths)
    with urllib.request.urlopen('http://127.0.0.1:8000/',timeout=5) as response:
        print('Menu entregue pelo servidor:', 'section-pareto' in response.read().decode())
except Exception as error:
    print('Servidor não verificado:',type(error).__name__)
