"""Aplica a coluna opcional resumo da RNC com backup antes da migração."""
from app.db import get_connection, init_db, DB_PATH

def counts():
    with get_connection() as conn:
        return {table:conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                for table in ('issues','rncs','acoes','usuarios')}

before=counts()
init_db()
after=counts()
assert before==after,(before,after)
with get_connection() as conn:
    assert 'resumo' in {row[1] for row in conn.execute('PRAGMA table_info(rncs)')}
print('Coluna resumo disponível. Registros preservados:',after)
print('Banco:',DB_PATH)
