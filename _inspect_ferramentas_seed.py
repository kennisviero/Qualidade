from app.db import get_connection
with get_connection() as c:
    for sql in ['SELECT id,razao_social FROM empresas','SELECT id,nome,papel,empresa_id FROM usuarios','SELECT empresa_id,count(*) total FROM issues GROUP BY empresa_id','SELECT empresa_id,count(*) total FROM rncs GROUP BY empresa_id','PRAGMA table_info(issues)','PRAGMA table_info(rncs)']:
        print(sql, [dict(r) for r in c.execute(sql)])
