import json
import sqlite3
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.auth import is_superuser, require_papel
from app.db import get_connection
from app.routers.llm_acessos import scope
from app.routers.issues import RncEmissaoIn
from app.services import llm_client
from app.services.issue_triagem import canonical, digest, snapshot, now, PARAMETERS, PROMPT, PROMPT_VERSION
from app.services.rnc_emissao import emitir_rnc_transacao

router = APIRouter(prefix='/api/issues/selecao',tags=['selecao-issues'])
writer = require_papel('admin','editor')


class RequestModel(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True)


class AnaliseIn(RequestModel):
    empresa_id: int | None = None
    acesso_llm_id: int = Field(gt=0)
    issue_ids: list[Annotated[int,Field(gt=0,strict=True)]] = Field(min_length=1,max_length=20)
    prompt: str | None = Field(default=None,min_length=1,max_length=20000)

    @field_validator('prompt')
    @classmethod
    def nonempty_prompt(cls,value):
        if value is not None and not value.strip(): raise ValueError('Informe o prompt')
        return value


class GeracaoItem(RequestModel):
    candidata_id: int = Field(gt=0)
    # Dados incompletos são reportados por item, sem impedir os demais.
    dados_rnc: dict


class GeracaoIn(RequestModel):
    confirmar: Literal[True]
    itens: list[GeracaoItem] = Field(min_length=1,max_length=20)

    @field_validator('confirmar',mode='before')
    @classmethod
    def explicit_confirmation(cls,value):
        if value is not True: raise ValueError('Confirmação explícita obrigatória')
        return value


def idem_key(value: str = Header(alias='Idempotency-Key')):
    try: return str(UUID(value))
    except (ValueError,TypeError): raise HTTPException(422,'Idempotency-Key deve ser um UUID') from None


def owned(conn, table, record_id, user):
    assert table in ('llm_triagens','llm_rnc_geracoes')
    row = conn.execute(f'SELECT * FROM {table} WHERE id=?',(record_id,)).fetchone()
    if not row or (not is_superuser(user) and row['empresa_id'] != user['empresa_id']):
        raise HTTPException(404,'Registro não encontrado')
    return row


def analysis_view(conn,row):
    result = {key:row[key] for key in ('id','empresa_id','status','criado_em','iniciado_em','concluido_em',
        'provedor_snapshot','modelo_snapshot','versao_prompt','erro_codigo','erro_mensagem_segura')}
    result['analise_id'] = row['id']
    parameters = json.loads(row['parametros_json'])
    result['etapa'] = parameters.get('etapa','aguardando' if row['status']=='processando' else 'enviando')
    result['prompt'] = parameters.get('prompt_text',PROMPT)
    result['url_status'] = f"/api/issues/selecao/analises/{row['id']}"
    result['total_issues'] = conn.execute('SELECT count(*) FROM llm_triagem_issues WHERE triagem_id=?',(row['id'],)).fetchone()[0]
    candidates = []
    if row['status'] == 'concluida':
        for item in conn.execute('''SELECT t.*,i.criado_em issue_criado_em FROM llm_triagem_issues t
            LEFT JOIN issues i ON i.id=t.issue_id AND i.empresa_id=t.empresa_id
            WHERE t.triagem_id=? AND t.candidata=1 ORDER BY t.id''',(row['id'],)):
            generated = conn.execute("SELECT codigo_rnc_snapshot FROM llm_rnc_geracao_itens WHERE triagem_issue_id=? AND status='gerada'",(item['id'],)).fetchone()
            candidates.append({'id':item['id'],'id_issue':item['issue_id'],'codigo_issue':item['codigo_issue_snapshot'],
                'resumo':json.loads(item['entrada_json'])['fato'],'criado_em':item['issue_criado_em'],'justificativa':json.loads(item['justificativa_json']),
                'criticidade_sugerida':item['criticidade_sugerida'],'gerada':bool(generated),
                'codigo_rnc':generated['codigo_rnc_snapshot'] if generated else None})
    result['candidatas_rnc'] = candidates
    last_generation = conn.execute('SELECT * FROM llm_rnc_geracoes WHERE triagem_id=? ORDER BY id DESC LIMIT 1',(row['id'],)).fetchone()
    result['ultima_geracao'] = generation_view(conn,last_generation) if last_generation else None
    return result


def generation_view(conn,row):
    items = conn.execute('''SELECT g.*,t.codigo_issue_snapshot FROM llm_rnc_geracao_itens g
        JOIN llm_triagem_issues t ON t.id=g.triagem_issue_id WHERE g.geracao_id=? ORDER BY g.id''',(row['id'],)).fetchall()
    return {'geracao_id':row['id'],'analise_id':row['triagem_id'],'status':row['status'],
        'itens':[{'candidata_id':item['triagem_issue_id'],'codigo_issue':item['codigo_issue_snapshot'],
            'status':item['status'],'codigo_rnc':item['codigo_rnc_snapshot'],
            'erro_codigo':item['erro_codigo'],'erro_mensagem':item['erro_mensagem_segura']} for item in items]}


@router.get('/prompt')
def default_prompt(user: dict = Depends(writer)):
    return {'prompt':PROMPT,'versao':PROMPT_VERSION}


@router.get('/elegiveis')
def eligible(empresa_id: int | None = None, status: Literal['cadastrada','em_tratamento'] | None = None,
             busca: str = Query(default='',max_length=200), page: int = Query(default=1,ge=1),
             page_size: int = Query(default=50,ge=1,le=100), user: dict = Depends(writer)):
    eid = scope(user,empresa_id)
    where = "i.empresa_id=? AND i.status IN ('cadastrada','em_tratamento') AND NOT EXISTS (SELECT 1 FROM rncs r WHERE r.issue_id=i.id)"
    params = [eid]
    if status:
        where += ' AND i.status=?'; params.append(status)
    if busca.strip():
        where += ' AND (instr(lower(i.codigo),lower(?))>0 OR instr(lower(i.comportamento_observado),lower(?))>0)'
        params.extend([busca.strip(),busca.strip()])
    with get_connection() as conn:
        total = conn.execute(f'SELECT count(*) FROM issues i WHERE {where}',params).fetchone()[0]
        rows = conn.execute(f'''SELECT i.id,i.codigo,i.comportamento_observado resumo,i.status,i.detectado_em,i.impacto,i.criado_em
            FROM issues i WHERE {where} ORDER BY i.criado_em DESC,i.id DESC LIMIT ? OFFSET ?''',params+[page_size,(page-1)*page_size]).fetchall()
    return {'itens':[dict(r) for r in rows],'total':total,'page':page,'page_size':page_size}


@router.get('/acessos-llm')
def accesses(empresa_id: int | None = None,user: dict = Depends(writer)):
    eid = scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,nome,provedor,modelo FROM llm_acessos WHERE empresa_id=? AND ativo=1 ORDER BY nome',(eid,))]


@router.get('/usuarios')
def company_users(empresa_id: int | None = None,user: dict = Depends(writer)):
    eid = scope(user,empresa_id)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute('SELECT id,nome FROM usuarios WHERE empresa_id=? AND ativo=1 ORDER BY nome,id',(eid,))]


@router.get('/analises')
def history(empresa_id: int | None = None,user: dict = Depends(writer)):
    eid = scope(user,empresa_id)
    with get_connection() as conn:
        rows = conn.execute('''SELECT t.id,t.status,t.criado_em,t.concluido_em,t.modelo_snapshot,t.provedor_snapshot,
            (SELECT count(*) FROM llm_triagem_issues i WHERE i.triagem_id=t.id) total_issues
            FROM llm_triagens t WHERE t.empresa_id=? ORDER BY t.id DESC LIMIT 50''',(eid,)).fetchall()
        return [dict(row) for row in rows]


@router.post('/analises',status_code=202)
def create_analysis(body: AnaliseIn,key: str = Depends(idem_key),user: dict = Depends(writer)):
    eid = scope(user,body.empresa_id)
    if len(set(body.issue_ids)) != len(body.issue_ids): raise HTTPException(422,'Não repita IDs no lote')
    prompt = body.prompt if body.prompt is not None else PROMPT
    hashed = digest({'empresa_id':eid,'acesso_llm_id':body.acesso_llm_id,'issue_ids':sorted(body.issue_ids),'prompt':prompt})
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT * FROM llm_triagens WHERE empresa_id=? AND idempotency_key=?',(eid,key)).fetchone()
        if existing:
            legacy_hash = digest({'empresa_id':eid,'acesso_llm_id':body.acesso_llm_id,'issue_ids':sorted(body.issue_ids)})
            legacy_retry = body.prompt is None and 'prompt_text' not in json.loads(existing['parametros_json']) and existing['request_hash'] == legacy_hash
            if existing['request_hash'] != hashed and not legacy_retry: raise HTTPException(409,'Chave já usada para outra análise')
            return analysis_view(conn,existing)
        if conn.execute("SELECT 1 FROM llm_triagens WHERE solicitado_por_id=? AND status IN ('pendente','processando')",(user['id'],)).fetchone():
            raise HTTPException(409,'Já existe uma análise em processamento para este usuário')
        access = conn.execute('SELECT * FROM llm_acessos WHERE id=? AND empresa_id=? AND ativo=1',(body.acesso_llm_id,eid)).fetchone()
        if not access or not access['api_key'].strip(): raise HTTPException(422,'Selecione um acesso LLM ativo com chave')
        try: llm_client.endpoint(dict(access))
        except llm_client.LlmError as error: raise HTTPException(422,error.message) from None
        inputs, statuses = [],{}
        for issue_id in sorted(body.issue_ids):
            issue = conn.execute('SELECT * FROM issues WHERE id=? AND empresa_id=?',(issue_id,eid)).fetchone()
            if not issue: raise HTTPException(404,'Uma das Issues não existe ou não pertence à empresa')
            if issue['status'] not in ('cadastrada','em_tratamento') or conn.execute('SELECT 1 FROM rncs WHERE issue_id=?',(issue_id,)).fetchone():
                raise HTTPException(409,'Uma das Issues está fechada ou já possui RNC')
            inputs.append(snapshot(issue)); statuses[str(issue_id)] = issue['status']
        if len((prompt+canonical(inputs)).encode('utf-8')) > PARAMETERS['max_input_bytes']:
            raise HTTPException(413,'Lote maior que 100 KB. Reduza a quantidade de Issues')
        parameters = {**PARAMETERS,'statuses':statuses,'prompt_hash':digest(prompt),'prompt_text':prompt,'url_base_snapshot':access['url_base']}
        cur = conn.execute('''INSERT INTO llm_triagens
            (empresa_id,acesso_llm_id,solicitado_por_id,idempotency_key,request_hash,status,provedor_snapshot,modelo_snapshot,versao_prompt,parametros_json,criado_em)
            VALUES (?,?,?,?,?,'pendente',?,?,?,?,?)''',
            (eid,access['id'],user['id'],key,hashed,access['provedor'],access['modelo'],PROMPT_VERSION,canonical(parameters),now()))
        for item in inputs:
            conn.execute('''INSERT INTO llm_triagem_issues
                (triagem_id,empresa_id,issue_id,codigo_issue_snapshot,entrada_json,entrada_hash) VALUES (?,?,?,?,?,?)''',
                (cur.lastrowid,eid,item['id_issue'],item['codigo_issue'],canonical(item),digest(item)))
        return analysis_view(conn,conn.execute('SELECT * FROM llm_triagens WHERE id=?',(cur.lastrowid,)).fetchone())


@router.get('/analises/{analysis_id}')
def get_analysis(analysis_id: int,user: dict = Depends(writer)):
    with get_connection() as conn: return analysis_view(conn,owned(conn,'llm_triagens',analysis_id,user))


@router.get('/geracoes/{generation_id}')
def get_generation(generation_id: int,user: dict = Depends(writer)):
    with get_connection() as conn: return generation_view(conn,owned(conn,'llm_rnc_geracoes',generation_id,user))


@router.post('/analises/{analysis_id}/geracoes')
def generate(analysis_id: int,body: GeracaoIn,key: str = Depends(idem_key),user: dict = Depends(writer)):
    ids = [item.candidata_id for item in body.itens]
    if len(set(ids)) != len(ids): raise HTTPException(422,'Não repita candidatas')
    hashed = digest({'analise_id':analysis_id,'itens':sorted([item.model_dump() for item in body.itens],key=lambda x:x['candidata_id'])})
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        analysis = owned(conn,'llm_triagens',analysis_id,user)
        existing = conn.execute('SELECT * FROM llm_rnc_geracoes WHERE empresa_id=? AND idempotency_key=?',(analysis['empresa_id'],key)).fetchone()
        if existing:
            if existing['request_hash'] != hashed: raise HTTPException(409,'Chave já usada para outra geração')
            return generation_view(conn,existing)
        if analysis['status'] != 'concluida': raise HTTPException(409,'A análise ainda não foi concluída')
        candidates = {}
        for item in body.itens:
            candidate = conn.execute('SELECT * FROM llm_triagem_issues WHERE id=? AND triagem_id=? AND candidata=1 AND empresa_id=?',
                (item.candidata_id,analysis_id,analysis['empresa_id'])).fetchone()
            if not candidate: raise HTTPException(422,'Candidata inválida para esta análise')
            candidates[item.candidata_id] = candidate
        cur = conn.execute('''INSERT INTO llm_rnc_geracoes
            (empresa_id,triagem_id,aprovado_por_id,idempotency_key,request_hash,status,criado_em)
            VALUES (?,?,?,?,?,'processando',?)''',(analysis['empresa_id'],analysis_id,user['id'],key,hashed,now()))
        generation_id = cur.lastrowid
        successes = 0
        for item in body.itens:
            candidate = candidates[item.candidata_id]
            code,message,status,rnc = None,None,'pendente',None
            conn.execute('SAVEPOINT emitir_item')
            try:
                issue = conn.execute('SELECT * FROM issues WHERE id=? AND empresa_id=?',(candidate['issue_id'],analysis['empresa_id'])).fetchone()
                if not issue: raise HTTPException(409,'Issue removida')
                if issue['status'] not in ('cadastrada','em_tratamento'): raise HTTPException(409,'Issue fechada')
                if digest(snapshot(issue)) != candidate['entrada_hash']:
                    code = 'issue_alterada'
                    raise HTTPException(409,'Os dados da Issue mudaram. Solicite nova análise')
                if conn.execute('SELECT 1 FROM rncs WHERE issue_id=?',(issue['id'],)).fetchone():
                    raise HTTPException(409,'Issue já possui RNC')
                extra = set(item.dados_rnc)-set(RncEmissaoIn.model_fields)
                if extra: raise HTTPException(422,'Dados da RNC contêm campos desconhecidos')
                data = RncEmissaoIn.model_validate(item.dados_rnc)
                rnc = emitir_rnc_transacao(conn,issue['id'],data,user)
                conn.execute('''INSERT INTO llm_rnc_geracao_itens
                    (geracao_id,empresa_id,triagem_issue_id,rnc_id,codigo_rnc_snapshot,dados_aprovados_json,status)
                    VALUES (?,?,?,?,?,?,'gerada')''',
                    (generation_id,analysis['empresa_id'],candidate['id'],rnc['id'],rnc['codigo'],canonical(data.model_dump())))
                status = 'gerada'; successes += 1
            except (HTTPException,ValidationError,sqlite3.IntegrityError) as error:
                conn.execute('ROLLBACK TO emitir_item')
                code = code or ('dados_rnc_invalidos' if isinstance(error,ValidationError) or getattr(error,'status_code',None)==422 else 'issue_indisponivel')
                message = error.detail if isinstance(error,HTTPException) else 'Confira os campos obrigatórios e os vínculos da RNC'
            except Exception:
                conn.execute('ROLLBACK TO emitir_item')
                code,message = 'falha_gravacao','Não foi possível gravar esta RNC. Nenhum dado deste item foi confirmado'
            finally: conn.execute('RELEASE emitir_item')
            if status == 'pendente':
                conn.execute('''INSERT INTO llm_rnc_geracao_itens
                    (geracao_id,empresa_id,triagem_issue_id,dados_aprovados_json,status,erro_codigo,erro_mensagem_segura)
                    VALUES (?,?,?,?,'pendente',?,?)''',
                    (generation_id,analysis['empresa_id'],candidate['id'],canonical(item.dados_rnc),code,message))
        status = 'concluida' if successes==len(body.itens) else 'parcial' if successes else 'falha'
        conn.execute('UPDATE llm_rnc_geracoes SET status=?,concluido_em=? WHERE id=?',(status,now(),generation_id))
        return generation_view(conn,conn.execute('SELECT * FROM llm_rnc_geracoes WHERE id=?',(generation_id,)).fetchone())
