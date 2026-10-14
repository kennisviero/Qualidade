import json
from datetime import datetime
from typing import Literal
from uuid import uuid4
from pydantic import ConfigDict, Field, ValidationError
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from app.docs import folder_for, safe_rel, save_file, guess_mime
from app.auth import get_current_user, require_papel, is_superuser
from app.db import get_connection
from app.security import SafeModel
from app.routers.issues import (now, _empresa_scope, _validar_usuario_empresa,
    issue_to_dict, RNC_CRITICIDADES, RNC_DISPOSICOES, RNC_METODOLOGIAS, AcaoIn, acao_to_dict)

router=APIRouter(prefix='/api/rncs',tags=['rncs'])
editor=require_papel('admin','editor')

class ObservacaoIn(SafeModel):
    model_config=ConfigDict(extra='forbid')
    inicio_ocorrencias: str = ''
    periodo_inicio: str = ''
    periodo_fim: str = ''
    frequencia: str = ''
    turnos_horarios: str = ''
    localizacao: str = ''
    sintomas_condicoes: str = ''
    condicoes_sem_falha: str = ''
    operadores_ids: list[int] = Field(default_factory=list)
    equipes_envolvidas: str = ''
    quantidade_afetada: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    unidade_quantidade: str = ''
    horas_perdidas: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    prejuizo_financeiro: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    moeda: str = 'BRL'
    impacto_periodo: str = ''

class TesteHipotese(SafeModel):
    model_config=ConfigDict(extra='forbid')
    procedimento: str = ''
    responsavel_id: int | None = None
    data: str = ''
    resultado: str = ''
    resultado_esperado: str = ''
    criterio_decisao: str = ''
    repeticoes: int | None = Field(default=None,ge=1,strict=True)
    configuracao: str = ''
    amostra: str = ''
    evidencias_ids: list[int] = Field(default_factory=list)
    conclusao: Literal['','confirmada','descartada','inconclusiva'] = ''

class HipoteseIn(SafeModel):
    model_config=ConfigDict(extra='forbid')
    descricao: str = ''
    evidencias_favoraveis: str = ''
    evidencias_contrarias: str = ''
    testes: list[TesteHipotese] = Field(default_factory=list)

class ComplementosInvestigacao(SafeModel):
    model_config=ConfigDict(extra='forbid')
    mudancas: str = ''
    mudancas_em: str = ''
    configuracao_anterior: str = ''
    configuracao_atual: str = ''
    abrangencia_afetados: str = ''
    abrangencia_sem_falha: str = ''
    controle_esperado: str = ''
    motivo_nao_deteccao: str = ''
    hipoteses_confirmadas: str = ''
    hipoteses_descartadas: str = ''
    hipoteses_inconclusivas: str = ''
    conclusao_tecnica: str = ''
    limitacoes_pendencias: str = ''
    revisor_id: int | None = None
    revisao_em: str = ''
    parecer: Literal['','aceita','complementar'] = ''
    observacoes_revisao: str = ''

class PorquePasso(SafeModel):
    model_config=ConfigDict(extra='forbid')
    pergunta: str = ''
    resposta: str = ''
    evidencia: str = ''

class EtapaPorques(SafeModel):
    model_config=ConfigDict(extra='forbid')
    problema: str = ''
    passos: list[PorquePasso] = Field(default_factory=list,max_length=20)
    conclusao: str = ''

class EtapaIshikawa(SafeModel):
    model_config=ConfigDict(extra='forbid')
    efeito: str = ''
    metodo: str = ''
    maquina: str = ''
    material: str = ''
    mao_obra: str = ''
    medicao: str = ''
    meio_ambiente: str = ''
    conclusao: str = ''

class RncUpdate(SafeModel):
    model_config=ConfigDict(extra='forbid')
    encerramento_aprovador_id: int | None = None
    encerramento_conclusao: str | None = None
    licoes_aprendidas: str | None = None
    resumo: str = Field(default='',max_length=25)
    impacto: str | None = None
    ambiente: str | None = None
    emitente_id: int | None = None
    responsavel_id: int | None = None
    criticidade: str | None = None
    enquadramento_normativo: str | None = None
    acao_contencao_imediata: str | None = None
    acao_contencao_definitiva: str | None = None
    contencao_responsavel_id: int | None = None
    data_limite_contencao: str | None = None
    data_conclusao_contencao: str | None = None
    contencao_validada_por_id: int | None = None
    disposicao_inicial: str | None = None
    metodologia: str | None = None
    metodologias: list[str] | None = None
    investigacao_json: dict | None = None
    observacao: ObservacaoIn | None = None
    lider_investigacao_id: int | None = None
    equipe_investigacao: list[int] | None = None
    plano_aprovador_id: int | None = None
    prazo_analise: str | None = None
    prazo_plano_acao: str | None = None
    prazo_verificacao_eficacia: str | None = None
    auditor_eficacia_id: int | None = None

class PendenciaIn(SafeModel):
    descricao: str
    responsavel_id: int | None = None
    prazo: str = ''

class PendenciaStatus(SafeModel):
    status: str

class EncerramentoIn(SafeModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    confirmar: Literal[True]
    encerramento_aprovador_id: int | None = None
    encerramento_conclusao: str | None = None
    licoes_aprendidas: str | None = None

class ReaberturaIn(EncerramentoIn):
    motivo: str = Field(default='',max_length=2000)

def fetch(conn,rnc_id,user):
    row=conn.execute('SELECT * FROM rncs WHERE id=?',(rnc_id,)).fetchone()
    if not row:raise HTTPException(404,'RNC não encontrada')
    if not is_superuser(user) and row['empresa_id']!=user['empresa_id']:
        raise HTTPException(404,'RNC não encontrada')
    return row

def editable(row):
    if row['status'] in ('concluida','fechada'):
        raise HTTPException(409,'RNC concluída não pode ser alterada')

def validate_date(value):
    if value:
        try:datetime.fromisoformat(value)
        except (ValueError,TypeError):raise HTTPException(422,'Data inválida') from None

def view(conn,row):
    issue=conn.execute('SELECT * FROM issues WHERE id=?',(row['issue_id'],)).fetchone()
    result=issue_to_dict(conn,issue)
    snapshot=json.loads(row['fatos_snapshot_json'])
    result.update(snapshot)
    for key in row.keys():result['rnc_'+key]=row[key]
    result['rnc_equipe_investigacao']=json.loads(row['equipe_investigacao'] or '[]')
    result['rnc_investigacao_json']=json.loads(row['investigacao_json'] or '{}')
    result['rnc_metodologias']=json.loads(row['metodologias_json'] or '[]')
    result['rnc_encerramento_historico']=json.loads(row['encerramento_historico_json'] or '[]')
    result['rnc_fatos_snapshot_json']=snapshot
    result['acoes']=[acao_to_dict(conn,a) for a in conn.execute('SELECT * FROM acoes WHERE rnc_id=? ORDER BY ordem,id',(row['id'],))]
    result['pendencias']=[dict(p) for p in conn.execute('SELECT * FROM rnc_pendencias WHERE rnc_id=? ORDER BY id',(row['id'],))]
    observation=conn.execute('SELECT * FROM rnc_observacoes WHERE rnc_id=?',(row['id'],)).fetchone()
    result['observacao']=dict(observation) if observation else ObservacaoIn().model_dump()
    if observation:result['observacao']['operadores_ids']=json.loads(observation['operadores_ids'])
    result['evidencias_investigacao']=[dict(e) for e in conn.execute('SELECT * FROM rnc_evidencias WHERE rnc_id=? ORDER BY id',(row['id'],))]
    return result

@router.get('')
def list_rncs(empresa_id: int | None=None,user: dict=Depends(get_current_user)):
    scope=_empresa_scope(user,empresa_id)
    with get_connection() as conn:
        rows=conn.execute('SELECT * FROM rncs '+('WHERE empresa_id=? ' if scope is not None else '')+'ORDER BY id DESC',
            (scope,) if scope is not None else ()).fetchall()
        return [view(conn,row) for row in rows]

@router.get('/{rnc_id}')
def get_rnc(rnc_id: int,user: dict=Depends(get_current_user)):
    with get_connection() as conn:return view(conn,fetch(conn,rnc_id,user))

@router.put('/{rnc_id}')
def update_rnc(rnc_id: int,body:RncUpdate,user:dict=Depends(editor)):
    data=body.model_dump(exclude_unset=True)
    if 'resumo' in data:data['resumo']=data['resumo'].strip()
    if 'metodologias' in data:
        methods=list(dict.fromkeys(data.pop('metodologias') or []))
        if any(method not in RNC_METODOLOGIAS for method in methods):
            raise HTTPException(422,'Metodologia inválida')
        data['metodologias_json']=json.dumps(methods)
        data['metodologia']=methods[0] if methods else ''
    elif 'metodologia' in data:
        data['metodologias_json']=json.dumps([data['metodologia']] if data['metodologia'] else [])
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        observation=data.pop('observacao',None)
        if observation is not None:
            current=conn.execute('SELECT * FROM rnc_observacoes WHERE rnc_id=?',(rnc_id,)).fetchone()
            previous={k:current[k] for k in ObservacaoIn.model_fields} if current else {}
            if current:previous['operadores_ids']=json.loads(previous['operadores_ids'])
            observation={**ObservacaoIn().model_dump(),**previous,**observation}
            for key in ('inicio_ocorrencias','periodo_inicio','periodo_fim'):validate_date(observation[key])
            if observation['periodo_inicio'] and observation['periodo_fim'] and observation['periodo_inicio']>observation['periodo_fim']:
                raise HTTPException(422,'O período final deve ser posterior ao inicial')
            for uid in observation['operadores_ids']:_validar_usuario_empresa(conn,uid,row['empresa_id'],'Operador envolvido')
            observation['operadores_ids']=json.dumps(list(dict.fromkeys(observation['operadores_ids'])))
            observation.update(rnc_id=rnc_id,atualizado_por_id=user['id'],atualizado_em=now())
            keys=','.join(observation);marks=','.join('?' for _ in observation)
            conn.execute(f'INSERT INTO rnc_observacoes ({keys}) VALUES ({marks}) ON CONFLICT(rnc_id) DO UPDATE SET '+','.join(f'{k}=excluded.{k}' for k in observation if k!='rnc_id'),tuple(observation.values()))
        for key,value in data.items():
            if key.endswith('_id'):_validar_usuario_empresa(conn,value,row['empresa_id'],key)
            elif key=='equipe_investigacao':
                for uid in value or []:_validar_usuario_empresa(conn,uid,row['empresa_id'],'Equipe')
            elif key=='investigacao_json' and value:
                if 'porques' in value or ('analise' in value and not isinstance(value['analise'],str)):
                    raise HTTPException(422,'Investigação inválida: informe apenas os dados da análise desta aba')
                for stage,model in [('etapa_porques',EtapaPorques),('etapa_ishikawa',EtapaIshikawa)]:
                    if stage in value:
                        try:value[stage]=model.model_validate(value[stage]).model_dump()
                        except (ValidationError,ValueError,TypeError):raise HTTPException(422,'Dados da etapa de investigação inválidos') from None
                if 'complementos' in value:
                    try:complement=ComplementosInvestigacao.model_validate(value['complementos'])
                    except (ValidationError,ValueError,TypeError):raise HTTPException(422,'Complementos da investigação inválidos') from None
                    validate_date(complement.mudancas_em);validate_date(complement.revisao_em)
                    _validar_usuario_empresa(conn,complement.revisor_id,row['empresa_id'],'Revisor da investigação')
                    value['complementos']=complement.model_dump()
                if 'hipoteses' in value:
                    try:
                        if not isinstance(value['hipoteses'],list):raise ValueError()
                        hypotheses=[HipoteseIn.model_validate(h) for h in value['hipoteses']]
                    except (ValidationError,ValueError,TypeError):raise HTTPException(422,'Hipóteses ou testes inválidos') from None
                    for hypothesis in hypotheses:
                        for test in hypothesis.testes:
                            _validar_usuario_empresa(conn,test.responsavel_id,row['empresa_id'],'Responsável pelo teste');validate_date(test.data)
                            for evidence_id in test.evidencias_ids:
                                if not conn.execute('SELECT 1 FROM rnc_evidencias WHERE id=? AND rnc_id=?',(evidence_id,rnc_id)).fetchone():
                                    raise HTTPException(422,'Evidência do teste não pertence à RNC')
                    value['hipoteses']=[h.model_dump() for h in hypotheses]
                    for hypothesis,saved in zip(hypotheses,value['hipoteses']):
                        for test,saved_test in zip(hypothesis.testes,saved['testes']):
                            for added in ('resultado_esperado','criterio_decisao','repeticoes','configuracao','amostra','evidencias_ids'):
                                if added not in test.model_fields_set:saved_test.pop(added,None)
            elif key.startswith(('data_','prazo_')):validate_date(value)
            elif key in ('impacto','ambiente'):
                choices={'impacto':('baixo','medio','alto','critico'),'ambiente':('producao','homologacao','campo','linha','outro')}[key]
                if value and value not in choices and value!=row[key]:raise HTTPException(422,f'{key} inválido')
            elif key in ('criticidade','disposicao_inicial','metodologia'):
                choices={'criticidade':RNC_CRITICIDADES,'disposicao_inicial':RNC_DISPOSICOES,'metodologia':RNC_METODOLOGIAS}[key]
                if value and value not in choices:raise HTTPException(422,f'{key} inválido')
            if key in ('equipe_investigacao','investigacao_json'):
                data[key]=json.dumps(value or ([] if key=='equipe_investigacao' else {}),ensure_ascii=False)
            elif not key.endswith('_id'):data[key]=value or ''
        if 'plano_aprovador_id' in data and data['plano_aprovador_id']!=row['plano_aprovador_id']:
            data.update(plano_aprovado_por_id=None,plano_aprovado_em=None)
        data['atualizado_em']=now()
        conn.execute('UPDATE rncs SET '+','.join(f'{k}=?' for k in data)+' WHERE id=?',(*data.values(),rnc_id))
        return view(conn,fetch(conn,rnc_id,user))

def invalidate_plan(conn,rnc_id):
    conn.execute('UPDATE rncs SET plano_aprovado_por_id=NULL,plano_aprovado_em=NULL,atualizado_em=? WHERE id=?',(now(),rnc_id))

@router.post('/{rnc_id}/encerrar')
def close_rnc(rnc_id:int,body:EncerramentoIn,user:dict=Depends(editor)):
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user)
        if row['status'] not in ('concluida','fechada'):
            details=body.model_dump(exclude_unset=True,exclude={'confirmar'})
            approver=details.get('encerramento_aprovador_id',row['encerramento_aprovador_id'])
            if not approver:raise HTTPException(422,'Identifique o aprovador do encerramento')
            _validar_usuario_empresa(conn,approver,row['empresa_id'],'Aprovador do encerramento')
            if approver!=user['id'] and not is_superuser(user):raise HTTPException(403,'Somente o aprovador escolhido ou o superusuário pode encerrar a RNC')
            if details:
                for key in ('encerramento_conclusao','licoes_aprendidas'):
                    if key in details:details[key]=details[key] or ''
                conn.execute('UPDATE rncs SET '+','.join(f'{key}=?' for key in details)+' WHERE id=?',(*details.values(),rnc_id))
                row=fetch(conn,rnc_id,user)
        if not row['encerramento_aprovador_id']:raise HTTPException(422,'Identifique e salve o aprovador do encerramento antes de aprovar')
        _validar_usuario_empresa(conn,row['encerramento_aprovador_id'],row['empresa_id'],'Aprovador do encerramento')
        if row['encerramento_aprovador_id']!=user['id'] and not is_superuser(user):raise HTTPException(403,'Somente o aprovador escolhido ou o superusuário pode encerrar a RNC')
        if row['status']=='concluida':
            conn.execute("UPDATE acoes SET status='finalizada',rnc_id=? WHERE rnc_id=? OR (issue_id=? AND rnc_id IS NULL)",(rnc_id,rnc_id,row['issue_id']))
            return view(conn,row)
        editable(row)
        if not conn.execute('SELECT 1 FROM acoes WHERE rnc_id=?',(rnc_id,)).fetchone():raise HTTPException(422,'Inclua e execute o plano de ação antes de encerrar')
        if conn.execute("SELECT 1 FROM rnc_pendencias WHERE rnc_id=? AND status='aberta'",(rnc_id,)).fetchone():raise HTTPException(422,'Conclua as pendências antes de encerrar')
        stamp=now()
        conn.execute("UPDATE acoes SET status='finalizada',rnc_id=? WHERE rnc_id=? OR (issue_id=? AND rnc_id IS NULL)",(rnc_id,rnc_id,row['issue_id']))
        conn.execute("UPDATE rncs SET status='concluida',encerramento_aprovado_por_id=?,encerramento_aprovado_em=?,atualizado_em=? WHERE id=?",(user['id'],stamp,stamp,rnc_id))
        return view(conn,fetch(conn,rnc_id,user))

@router.post('/{rnc_id}/reabrir')
def reopen_rnc(rnc_id:int,body:ReaberturaIn,user:dict=Depends(editor)):
    motivo=body.motivo.strip() or 'Reativação solicitada pelo usuário.'
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user)
        if row['status'] not in ('concluida','fechada'):raise HTTPException(409,'Somente uma RNC encerrada pode ser reaberta')
        history=json.loads(row['encerramento_historico_json'] or '[]')
        stamp=now()
        history.append({'evento':'reabertura','usuario_id':user['id'],'em':stamp,'motivo':motivo,
            'encerramento_aprovado_por_id':row['encerramento_aprovado_por_id'],
            'encerramento_aprovado_em':row['encerramento_aprovado_em'],
            'conclusao':row['encerramento_conclusao'],'licoes_aprendidas':row['licoes_aprendidas']})
        conn.execute("UPDATE rncs SET status='reaberta',encerramento_aprovado_por_id=NULL,encerramento_aprovado_em=NULL,encerramento_historico_json=?,atualizado_em=? WHERE id=?",(json.dumps(history,ensure_ascii=False),stamp,rnc_id))
        conn.execute("UPDATE acoes SET status='em_andamento',data_inicio=COALESCE(data_inicio,?) WHERE rnc_id=? AND status='finalizada'",(stamp,rnc_id))
        return view(conn,fetch(conn,rnc_id,user))

@router.post('/{rnc_id}/acoes',status_code=201)
def create_task(rnc_id:int,body:AcaoIn,user:dict=Depends(editor)):
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        if not body.descricao.strip():raise HTTPException(422,'Informe a ação')
        _validar_usuario_empresa(conn,body.responsavel_id,row['empresa_id'],'Responsável')
        validate_date(body.prazo_limite)
        data=body.model_dump();data.update(issue_id=row['issue_id'],rnc_id=rnc_id,status='backlog',
            ordem=conn.execute('SELECT COALESCE(MAX(ordem),-1)+1 FROM acoes WHERE issue_id=?',(row['issue_id'],)).fetchone()[0])
        conn.execute('INSERT INTO acoes ('+','.join(data)+') VALUES ('+','.join('?' for _ in data)+')',tuple(data.values()))
        invalidate_plan(conn,rnc_id)
        return view(conn,fetch(conn,rnc_id,user))

@router.put('/{rnc_id}/acoes/{acao_id}')
def update_task(rnc_id:int,acao_id:int,body:AcaoIn,user:dict=Depends(editor)):
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        if not conn.execute('SELECT 1 FROM acoes WHERE id=? AND rnc_id=?',(acao_id,rnc_id)).fetchone():raise HTTPException(404,'Ação não encontrada')
        if not body.descricao.strip():raise HTTPException(422,'Informe a ação')
        _validar_usuario_empresa(conn,body.responsavel_id,row['empresa_id'],'Responsável');validate_date(body.prazo_limite)
        data=body.model_dump()
        conn.execute('UPDATE acoes SET '+','.join(f'{k}=?' for k in data)+' WHERE id=?',(*data.values(),acao_id))
        invalidate_plan(conn,rnc_id)
        return view(conn,fetch(conn,rnc_id,user))

@router.post('/{rnc_id}/aprovar-plano')
def approve(rnc_id:int,user:dict=Depends(editor)):
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        if row['plano_aprovador_id']!=user['id']:raise HTTPException(403,'Somente o aprovador escolhido pode aprovar o plano')
        if not conn.execute('SELECT 1 FROM acoes WHERE rnc_id=?',(rnc_id,)).fetchone():raise HTTPException(422,'Inclua ações no plano')
        conn.execute('UPDATE rncs SET plano_aprovado_por_id=?,plano_aprovado_em=?,atualizado_em=? WHERE id=?',(user['id'],now(),now(),rnc_id))
        return view(conn,fetch(conn,rnc_id,user))

@router.post('/{rnc_id}/pendencias',status_code=201)
def create_pending(rnc_id:int,body:PendenciaIn,user:dict=Depends(editor)):
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        if not body.descricao.strip():raise HTTPException(422,'Descreva a pendência')
        _validar_usuario_empresa(conn,body.responsavel_id,row['empresa_id'],'Responsável');validate_date(body.prazo)
        conn.execute('INSERT INTO rnc_pendencias (rnc_id,descricao,responsavel_id,prazo,criado_por_id,criado_em) VALUES (?,?,?,?,?,?)',
            (rnc_id,body.descricao.strip(),body.responsavel_id,body.prazo,user['id'],now()))
        return view(conn,fetch(conn,rnc_id,user))

@router.put('/{rnc_id}/pendencias/{pendencia_id}')
def close_pending(rnc_id:int,pendencia_id:int,body:PendenciaStatus,user:dict=Depends(editor)):
    if body.status not in ('aberta','concluida'):raise HTTPException(422,'Status inválido')
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=fetch(conn,rnc_id,user);editable(row)
        pending=conn.execute('SELECT * FROM rnc_pendencias WHERE id=? AND rnc_id=?',(pendencia_id,rnc_id)).fetchone()
        if not pending:raise HTTPException(404,'Pendência não encontrada')
        if pending['status']!=body.status:
            conn.execute('UPDATE rnc_pendencias SET status=?,concluido_por_id=?,concluido_em=? WHERE id=?',
                (body.status,user['id'] if body.status=='concluida' else None,now() if body.status=='concluida' else None,pendencia_id))
        return view(conn,fetch(conn,rnc_id,user))

@router.post('/{rnc_id}/evidencias',status_code=201)
def upload_evidence(rnc_id:int,file:UploadFile=File(...),user:dict=Depends(editor)):
    written=None
    try:
        with get_connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=fetch(conn,rnc_id,user);editable(row)
            issue=conn.execute('SELECT pasta FROM issues WHERE id=?',(row['issue_id'],)).fetchone()
            if not issue['pasta']:raise HTTPException(422,'Pasta da Issue não configurada')
            data=file.file.read(20*1024*1024+1)
            if not data:raise HTTPException(422,'Arquivo vazio')
            if len(data)>20*1024*1024:raise HTTPException(413,'Limite de 20 MB por arquivo')
            relative=f"investigacao/{row['codigo']}/{uuid4().hex}"
            folder=safe_rel(folder_for(issue['pasta']),relative)
            name=save_file(folder,file.filename or 'evidencia',data)
            written=folder/name
            cursor=conn.execute('INSERT INTO rnc_evidencias (rnc_id,nome,caminho,tamanho,mime,carregado_por_id,carregado_em) VALUES (?,?,?,?,?,?,?)',
                (rnc_id,name,f'{relative}/{name}',len(data),guess_mime(name),user['id'],now()))
            result=dict(conn.execute('SELECT * FROM rnc_evidencias WHERE id=?',(cursor.lastrowid,)).fetchone())
        return result
    except Exception:
        if written and written.exists():written.unlink()
        raise

@router.get('/{rnc_id}/evidencias/{evidencia_id}')
def download_evidence(rnc_id:int,evidencia_id:int,user:dict=Depends(get_current_user)):
    with get_connection() as conn:
        row=fetch(conn,rnc_id,user)
        evidence=conn.execute('SELECT * FROM rnc_evidencias WHERE id=? AND rnc_id=?',(evidencia_id,rnc_id)).fetchone()
        if not evidence:raise HTTPException(404,'Evidência não encontrada')
        issue=conn.execute('SELECT pasta FROM issues WHERE id=?',(row['issue_id'],)).fetchone()
        try:path=safe_rel(folder_for(issue['pasta']),evidence['caminho'])
        except ValueError:raise HTTPException(400,'Caminho de evidência inválido') from None
        if not path.is_file():raise HTTPException(404,'Arquivo de evidência não encontrado')
        return FileResponse(path,media_type=evidence['mime'],filename=evidence['nome'],content_disposition_type='attachment')

@router.delete('/{rnc_id}/evidencias/{evidencia_id}',status_code=204)
def delete_evidence(rnc_id:int,evidencia_id:int,user:dict=Depends(editor)):
    removed=False;path=None;original=None
    try:
        with get_connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=fetch(conn,rnc_id,user);editable(row)
            evidence=conn.execute('SELECT * FROM rnc_evidencias WHERE id=? AND rnc_id=?',(evidencia_id,rnc_id)).fetchone()
            if not evidence:raise HTTPException(404,'Evidência não encontrada')
            issue=conn.execute('SELECT pasta FROM issues WHERE id=?',(row['issue_id'],)).fetchone()
            try:path=safe_rel(folder_for(issue['pasta']),evidence['caminho'])
            except ValueError:raise HTTPException(400,'Caminho de evidência inválido') from None
            if path.is_file():original=path.read_bytes()
            conn.execute('DELETE FROM rnc_evidencias WHERE id=?',(evidencia_id,))
            investigation=json.loads(row['investigacao_json'] or '{}')
            for hypothesis in investigation.get('hipoteses',[]):
                for test in hypothesis.get('testes',[]):
                    if 'evidencias_ids' in test:test['evidencias_ids']=[eid for eid in test['evidencias_ids'] if eid!=evidencia_id]
            conn.execute('UPDATE rncs SET investigacao_json=? WHERE id=?',(json.dumps(investigation,ensure_ascii=False),rnc_id))
            if original is not None:path.unlink();removed=True
    except Exception:
        if removed and original is not None:path.write_bytes(original)
        raise
