"""Plugin exclusivo da execução QA: falha antes de tocar caminhos operacionais."""
import os
import tempfile
from pathlib import Path
import httpx

_original=None

def pytest_sessionstart(session):
    from app.db import DB_PATH,DOCS_DIR,BASE_DIR
    for candidate,active in [(DB_PATH,BASE_DIR/'data'/'qualidade.db'),(DOCS_DIR,BASE_DIR/'Vault')]:
        resolved=candidate.resolve()
        if resolved==active.resolve() or not resolved.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise RuntimeError('QA requer banco/Vault no diretório temporário: '+str(resolved))
    global _original
    _original=httpx.HTTPTransport.handle_request
    def blocked(self,request):
        raise RuntimeError('QA bloqueou transporte HTTP real: use MockTransport/FakeClient.')
    httpx.HTTPTransport.handle_request=blocked
    evidence=os.environ.get('QA_EVIDENCE_DIR')
    if evidence:
        Path(evidence,'isolation.txt').write_text(f'Banco temporário: {DB_PATH}\nVault temporário: {DOCS_DIR}\nHTTP externo: bloqueado\n',encoding='utf-8')

def pytest_sessionfinish(session,exitstatus):
    if _original is not None:httpx.HTTPTransport.handle_request=_original
