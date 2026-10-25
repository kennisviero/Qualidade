import sqlite3, json
conn = sqlite3.connect(r'C:\Produttare\Qualidade\data\qualidade.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM rncs WHERE codigo='RNC-2026-002'")
r = cur.fetchone()
if r:
    d = dict(r)
    print('===RNC===')
    print(json.dumps(d, ensure_ascii=False, indent=2))
    if d.get('issue_id'):
        cur.execute('SELECT * FROM issues WHERE id=?', (d['issue_id'],))
        i = cur.fetchone()
        if i:
            print('\n===ISSUE===')
            print(json.dumps(dict(i), ensure_ascii=False, indent=2))
    cur.execute('SELECT * FROM acoes WHERE rnc_id=?', (d['id'],))
    for a in cur.fetchall():
        print('\n===ACAO===')
        print(json.dumps(dict(a), ensure_ascii=False, indent=2))
conn.close()
