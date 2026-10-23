from app.db import get_connection
import urllib.request,json
with get_connection() as conn:
    print('RNCs:',[dict(r) for r in conn.execute('SELECT id,issue_id,status,encerramento_aprovador_id,encerramento_aprovado_em FROM rncs')])
    print('Ações:',[dict(r) for r in conn.execute('SELECT id,issue_id,rnc_id,status FROM acoes')])
    print('Usuários:',[dict(r) for r in conn.execute('SELECT id,nome,papel,empresa_id FROM usuarios')])
    print('Usuários com sessão recente:',[dict(r) for r in conn.execute('SELECT DISTINCT u.id,u.nome,u.papel,u.empresa_id FROM sessions s JOIN usuarios u ON u.id=s.user_id ORDER BY s.criado_em DESC LIMIT 5')])
    print('Conclusão/pêndencias:',[dict(r) for r in conn.execute("SELECT id,length(encerramento_conclusao) tamanho_conclusao,(SELECT count(*) FROM rnc_pendencias p WHERE p.rnc_id=rncs.id AND p.status='aberta') pendencias_abertas FROM rncs")])
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/openapi.json',timeout=5) as response:
        spec=json.load(response);paths=spec['paths']
        print('Rota encerramento no servidor:', '/api/rncs/{rnc_id}/encerrar' in paths)
        print('Rota reabertura no servidor:', '/api/rncs/{rnc_id}/reabrir' in paths)
        print('Campos de encerramento no servidor:',list(spec['components']['schemas']['EncerramentoIn']['properties']))
    for path,needle in [('/static/js/rncs.js','closureApprover.addEventListener'),('/static/js/app.js','confirmedRnc=null')]:
        with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as response:
            print(path,'versão atual:',needle in response.read().decode())
    with urllib.request.urlopen('http://127.0.0.1:8000/',timeout=5) as response:
        print('Submenu Reativar RNC entregue pelo servidor:', 'data-rnc-view="reativar"' in response.read().decode())
except Exception as error:print(type(error).__name__)
