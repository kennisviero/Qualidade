"""Adapter Chat Completions, sem ferramentas, redirects ou retries automáticos."""
import ipaddress
import json
import os
import socket
import time
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE = 200 * 1024
SUPPORTED = {'groq', 'openai', 'openrouter', 'deepseek', 'compativel', 'compatível', 'openai-compatible'}


class LlmError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def endpoint(access, resolve=False):
    if access['provedor'].strip().lower() not in SUPPORTED:
        raise LlmError('provedor_incompativel', 'Use Groq, OpenAI, OpenRouter, DeepSeek ou Compatível com API Chat Completions.')
    try:
        url = urlsplit(access['url_base'])
        port = url.port
    except ValueError:
        raise LlmError('destino_nao_autorizado','URL LLM inválida.') from None
    allowed = {'api.groq.com', 'api.openai.com', 'openrouter.ai', 'api.deepseek.com'}
    allowed.update(h.strip().lower() for h in os.environ.get('QUALIDADE_LLM_ALLOWED_HOSTS', '').split(',') if h.strip())
    if (url.scheme != 'https' or not url.hostname or url.hostname.lower() not in allowed
            or url.username or url.password or url.query or url.fragment or port not in (None,443)):
        raise LlmError('destino_nao_autorizado', 'URL LLM não autorizada. Use HTTPS e um host de provedor permitido.')
    if resolve:
        try:
            addresses = socket.getaddrinfo(url.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise LlmError('destino_nao_autorizado', 'O provedor deve resolver para endereços públicos.')
        except OSError:
            raise LlmError('provedor_indisponivel', 'Não foi possível localizar o provedor LLM.') from None
    base = access['url_base'].rstrip('/')
    if url.hostname.lower() == 'openrouter.ai' and url.path.rstrip('/') not in ('/api/v1','/api/v1/chat/completions'):
        raise LlmError('url_invalida','No OpenRouter, use a URL base https://openrouter.ai/api/v1.')
    return base if base.endswith('/chat/completions') else base + '/chat/completions'


def analisar_issues(access, instructions, issues, on_progress=None):
    url = endpoint(access, resolve=True)
    payload = {'model': access['modelo'], 'messages': [
        {'role':'system','content':instructions},
        {'role':'user','content':json.dumps({'issues':issues}, ensure_ascii=False)}],
        'response_format':{'type':'json_object'}, 'stream':False, 'max_completion_tokens':8192}
    if access['provedor'].strip().lower() in ('openrouter', 'deepseek'):
        payload['max_tokens'] = payload.pop('max_completion_tokens')
    started = time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(60, connect=10), follow_redirects=False, trust_env=False) as client:
            if access['provedor'].strip().lower() == 'openrouter':
                catalog = client.get('https://openrouter.ai/api/v1/models',timeout=10)
                if not catalog.is_success:
                    raise LlmError('catalogo_indisponivel','Não foi possível consultar os parâmetros do modelo no OpenRouter. Tente novamente.')
                model = next((item for item in catalog.json()['data'] if item['id']==access['modelo']),None)
                if model is None:
                    raise LlmError('modelo_indisponivel','O modelo configurado não está disponível no catálogo do OpenRouter. Confira o identificador em Configuração.')
                if 'response_format' not in model.get('supported_parameters',[]):
                    payload.pop('response_format',None)
                maximum = (model.get('top_provider') or {}).get('max_completion_tokens')
                if isinstance(maximum,int) and maximum>0:
                    payload['max_tokens'] = min(payload['max_tokens'],maximum)
            if on_progress: on_progress('aguardando')
            with client.stream('POST', url, headers={'Authorization':f"Bearer {access['api_key']}"}, json=payload) as response:
                if response.status_code in (401,403):
                    raise LlmError('acesso_llm_invalido','O provedor recusou a chave de API.')
                if response.status_code == 429:
                    raise LlmError('limite_provedor','Limite de uso do provedor atingido. Tente novamente mais tarde.')
                if response.status_code == 400:
                    raise LlmError('pedido_recusado','O modelo recusou os parâmetros ou o tamanho do lote. Confira suporte a JSON e reduza a seleção.')
                if not response.is_success:
                    raise LlmError('provedor_indisponivel','O provedor não concluiu a chamada. Confira URL, modelo e compatibilidade com JSON.')
                if on_progress: on_progress('recebendo')
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_RESPONSE:
                        raise LlmError('resposta_excedida','Resposta maior que o limite permitido.')
                    if time.monotonic() - started > 60:
                        raise LlmError('timeout','O tempo limite da análise foi excedido.')
        result = json.loads(data)
        choice = result['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise LlmError('resposta_incompleta','O provedor retornou uma resposta incompleta.')
        content = choice['message']['content']
        if not isinstance(content,str):
            raise ValueError()
        return content
    except httpx.TimeoutException:
        raise LlmError('timeout','O tempo limite da análise foi excedido.') from None
    except httpx.HTTPError:
        raise LlmError('provedor_indisponivel','Não foi possível comunicar com o provedor.') from None
    except (ValueError,KeyError,IndexError,TypeError):
        raise LlmError('resposta_invalida','O provedor retornou um formato inválido.') from None
