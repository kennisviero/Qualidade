from app.db import get_connection
with get_connection() as c:
    print([dict(r) for r in c.execute('SELECT id,empresa_id,nome,provedor,modelo,url_base,ativo FROM llm_acessos')])
