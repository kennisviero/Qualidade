"""Snapshot assinado da análise exibida: consulta externa somente após envio explícito."""
import hashlib
import hmac
import json
import secrets

_KEY=secrets.token_bytes(32)

def context(tool,company,user,parameters,result):
    snapshot=json.dumps(dict(ferramenta=tool,empresa_id=company,usuario_id=user['id'],parametros=parameters,resultados=result),ensure_ascii=False,default=str,separators=(',',':'))
    signature=hmac.new(_KEY,snapshot.encode('utf-8'),hashlib.sha256).hexdigest()
    return dict(snapshot=snapshot,assinatura=signature)

def verify(snapshot,signature):
    expected=hmac.new(_KEY,snapshot.encode('utf-8'),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):return None
    return json.loads(snapshot)
