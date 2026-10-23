"""Servidor exclusivo do E2E; nunca reutiliza a base ou o Vault operacionais."""
import os
import tempfile
from pathlib import Path
import httpx

for key in ['QUALIDADE_DB','QUALIDADE_DOCS']:
    value=Path(os.environ[key]).resolve()
    if not value.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not value.name.startswith('qualidade_qa_'):
        raise RuntimeError('Servidor QA exige diretório temporário próprio.')

def blocked(self,request):
    raise RuntimeError('E2E não autoriza chamadas reais a provedores externos.')
httpx.HTTPTransport.handle_request=blocked

if __name__=='__main__':
    import uvicorn
    from app.main import app
    config=uvicorn.Config(app,host='127.0.0.1',port=18765,log_level='info')
    server=uvicorn.Server(config)
    @app.post('/__qa__/shutdown',include_in_schema=False)
    def shutdown():
        server.should_exit=True
        return {'shutdown':True}
    server.run()
