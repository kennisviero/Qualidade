from typing import ClassVar
from fastapi import APIRouter,Depends,HTTPException
from pydantic import ConfigDict,Field,field_validator
from app.auth import get_current_user
from app.db import get_connection
from app.routers.llm_acessos import scope
from app.security import SafeModel
from app.services.ferramentas_ia import verify
from app.services.llm_client import consultar_ferramenta,LlmError

router=APIRouter(prefix='/api/ferramentas/ia',tags=['ferramentas-ia'])

class ConsultaIn(SafeModel):
    model_config=ConfigDict(extra='forbid')
    _sanitize_skip:ClassVar[frozenset]=frozenset({'prompt','snapshot'})
    acesso_id:int=Field(gt=0)
    prompt:str=Field(min_length=1,max_length=12000)
    snapshot:str=Field(min_length=1,max_length=1000000)
    assinatura:str=Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('prompt')
    @classmethod
    def nonempty(cls,value):
        if not value.strip():raise ValueError('Informe as instruções para a IA.')
        return value

@router.get('/acessos')
def accesses(empresa_id:int|None=None,user:dict=Depends(get_current_user)):
    company=scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,nome,provedor,modelo FROM llm_acessos WHERE empresa_id=? AND ativo=1 AND api_key<>\'\' ORDER BY nome,id',(company,))]

@router.post('/consultar')
def consult(body:ConsultaIn,user:dict=Depends(get_current_user)):
    data=verify(body.snapshot,body.assinatura)
    if not data:raise HTTPException(409,'Os dados da análise não são mais válidos. Gere o gráfico novamente e reabra a consulta.')
    company=scope(user,data['empresa_id'])
    if data['usuario_id']!=user['id']:raise HTTPException(403,'Gere a análise usando sua própria sessão.')
    with get_connection() as conn:
        row=conn.execute('SELECT * FROM llm_acessos WHERE id=? AND empresa_id=? AND ativo=1',(body.acesso_id,company)).fetchone()
        if not row or not row['api_key']:raise HTTPException(404,'Selecione um acesso LLM ativo da empresa.')
        access=dict(row)
    # Nenhuma conexão/transação de banco é mantida durante a chamada externa.
    try:
        response=consultar_ferramenta(access,body.prompt,data)
    except LlmError as error:
        raise HTTPException(502,error.message) from None
    details=response if isinstance(response,dict) else dict(resposta=response,completa=True,aviso='')
    return dict(**details,ferramenta=data['ferramenta'],modelo=access['modelo'],prompt=body.prompt)
