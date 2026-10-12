const selecaoState = {epoch:0, page:1, total:0, items:[], selected:new Set(), users:[], analysis:null,
  candidates:[], timer:null, busy:false, generationKey:null, analysisKey:null, lastRequest:null, pageRequest:0};
const selEl = (id) => document.getElementById(id);
const selUrl = (path) => issueApiUrl('/api/issues/selecao' + path);
let selecaoDefaultPrompt = '';
function selecaoProgress(stage,status) {
  const stages=['enviando','aguardando','recebendo'];
  const labels=['Enviando para a IA','Aguardando a IA processar','Recebendo dados da IA'];
  const current=status==='concluida' ? 3 : stages.indexOf(stage);
  selEl('selecaoProgresso').replaceChildren();
  labels.forEach((label,index)=>{
    const step=document.createElement('span');
    step.textContent=`${index<current ? '✓' : index===current && status!=='falha' ? '●' : '○'} ${label}${index<2 ? ' → ' : ''}`;
    step.style.color=index===current && status!=='falha' ? '#1e3a8a' : index<current ? '#15803d' : '#64748b';
    step.style.fontWeight=index===current ? '700' : '400';
    selEl('selecaoProgresso').appendChild(step);
  });
  return status==='concluida' ? 'Dados da IA recebidos. Análise concluída.' : status==='falha' ? 'Falha na análise.' : labels[Math.max(0,current)]+'…';
}
function selecaoUUID() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
function issueRegisteredTime(value) {
  const created = value ? new Date(value).getTime() : NaN;
  if (!Number.isFinite(created)) return 'Data de cadastro não informada';
  const days = Math.max(0, Math.floor((Date.now() - created) / 86400000));
  return days === 0 ? 'Cadastrada hoje' : `Cadastrada há ${days} ${days === 1 ? 'dia' : 'dias'}`;
}
function issueCodeLink(code,id) {
  const link=document.createElement(id ? 'a' : 'span');
  link.className='selecao-codigo';link.textContent=code;
  if(id) {
    link.href='#';link.title='Duplo clique para consultar a Issue';
    link.onclick=(event)=>event.preventDefault();
    const open=async(event)=>{
      event.preventDefault();
      try {await showIssueView('capturar');await selectIssue(id);}
      catch(error){selEl('selecaoMensagem').textContent=error.message;}
    };
    link.ondblclick=open;
    link.onkeydown=(event)=>{if(event.key==='Enter')open(event);};
  }
  return link;
}
function stopIssueSelecaoPolling() { clearTimeout(selecaoState.timer); selecaoState.timer = null; }
function resetIssueSelecao() {
  stopIssueSelecaoPolling(); selecaoState.epoch++;
  Object.assign(selecaoState,{page:1,total:0,items:[],selected:new Set(),users:[],analysis:null,candidates:[],busy:false,
    generationKey:null,analysisKey:null,lastRequest:null});
  ['selecaoLista','selecaoCandidatas','selecaoResultado','selecaoMensagem'].forEach((id)=>selEl(id).textContent='');
  ['selecaoAcesso','selecaoHistorico'].forEach((id)=>selEl(id).replaceChildren());
  selEl('selecaoCandidatasBloco').classList.add('hidden'); selEl('selecaoResultadoBloco').classList.add('hidden');
  selEl('selecaoTodos').checked=false; selEl('selecaoAnalisar').disabled=true; selEl('selecaoGerar').disabled=true;
  selEl('selecaoStatusFiltro').value=''; selEl('selecaoBusca').value='';
  selEl('selecaoPrompt').value=''; selEl('selecaoPromptUsado').textContent='';
  selEl('selecaoProgresso').replaceChildren();
  selecaoCount();
}
function selecaoCount() {
  selEl('selecaoContador').textContent=`${selecaoState.selected.size} selecionadas (máximo 20 por análise). ${selecaoState.total} elegíveis.`;
  selEl('selecaoAnalisar').disabled=selecaoState.busy;
  selEl('selecaoAnalisar').textContent=selecaoState.busy ? 'Análise em andamento…' : 'Enviar para a IA';
  selEl('selecaoEnvioHint').textContent=selecaoState.selected.size>20 ? 'Selecione no máximo 20 Issues para enviar.' : !selEl('selecaoAcesso').value ? 'Selecione o acesso LLM.' : !selecaoState.selected.size ? 'Marque pelo menos uma Issue.' : '';
  selEl('selecaoTodos').checked=selecaoState.items.length>0 && selecaoState.items.every(i=>selecaoState.selected.has(i.id));
}
async function loadIssueSelecao() {
  if (!isEditor() || !state.empresaId) {selEl('selecaoMensagem').textContent='Selecione uma empresa.'; return;}
  const epoch=selecaoState.epoch;
  const [accesses,users,prompt]=await Promise.all([api(selUrl('/acessos-llm')),api(selUrl('/usuarios')),api(selUrl('/prompt'))]);
  if (epoch!==selecaoState.epoch) return;
  selecaoDefaultPrompt=prompt.prompt;
  if(!selEl('selecaoPrompt').value)selEl('selecaoPrompt').value=prompt.prompt;
  const old=selEl('selecaoAcesso').value;
  selEl('selecaoAcesso').replaceChildren(new Option('Selecione o acesso LLM',''));
  accesses.forEach(a=>selEl('selecaoAcesso').appendChild(new Option(`${a.nome} · ${a.provedor} · ${a.modelo}`,a.id)));
  if (accesses.some(a=>String(a.id)===old)) selEl('selecaoAcesso').value=old;
  else if(accesses.length===1)selEl('selecaoAcesso').value=String(accesses[0].id);
  selecaoState.users=users;
  if (!accesses.length) selEl('selecaoMensagem').textContent='Nenhum acesso LLM ativo. Solicite o cadastro em Configuração.';
  await Promise.all([loadSelecaoPage(),loadSelecaoHistory()]);
  if (epoch!==selecaoState.epoch) return;
  if (selecaoState.analysis) await pollSelecaoAnalysis(selecaoState.analysis.id,epoch);
}
async function loadSelecaoPage() {
  const epoch=selecaoState.epoch; const request=++selecaoState.pageRequest;
  const query=new URLSearchParams({page:selecaoState.page,page_size:50,busca:selEl('selecaoBusca').value});
  if (selEl('selecaoStatusFiltro').value) query.set('status',selEl('selecaoStatusFiltro').value);
  const result=await api(selUrl('/elegiveis?'+query));
  if (epoch!==selecaoState.epoch || request!==selecaoState.pageRequest) return;
  selecaoState.items=result.itens; selecaoState.total=result.total;
  selEl('selecaoLista').replaceChildren();
  if (!result.itens.length) selEl('selecaoLista').textContent='Nenhuma Issue elegível para estes filtros.';
  result.itens.forEach(item=>{
    const row=document.createElement('div'); row.className='selecao-linha';
    const check=document.createElement('input'); check.type='checkbox'; check.checked=selecaoState.selected.has(item.id);
    check.setAttribute('aria-label',`Selecionar ${item.codigo}`);
    check.onchange=()=>{if(check.checked)selecaoState.selected.add(item.id);else selecaoState.selected.delete(item.id);selecaoCount();};
    const meta=document.createElement('div');meta.className='meta';
    const code=issueCodeLink(item.codigo,item.id);
    const title=document.createElement('strong');title.textContent=item.resumo;
    const details=document.createElement('span');details.textContent=`${ISSUE_STATUS_LABELS[item.status]} · Impacto: ${item.impacto || 'Não informado'} · ${item.detectado_em || ''}`;
    const age=document.createElement('span');age.textContent=issueRegisteredTime(item.criado_em);
    meta.append(code,title,details,age);row.append(check,meta);selEl('selecaoLista').appendChild(row);
  });
  selEl('selecaoPagina').textContent=`Página ${selecaoState.page} de ${Math.max(1,Math.ceil(result.total/50))}`;
  selEl('selecaoAnterior').disabled=selecaoState.page<=1;selEl('selecaoProxima').disabled=selecaoState.page*50>=result.total;
  selecaoCount();
}
async function loadSelecaoHistory() {
  const epoch=selecaoState.epoch;
  const items=await api(selUrl('/analises'));
  if(epoch!==selecaoState.epoch)return;
  selEl('selecaoHistorico').replaceChildren(new Option('Selecione uma análise',''));
  items.forEach(a=>selEl('selecaoHistorico').appendChild(new Option(`#${a.id} · ${a.status} · ${a.total_issues} Issues · ${a.modelo_snapshot}`,a.id)));
  if(selecaoState.analysis)selEl('selecaoHistorico').value=selecaoState.analysis.id;
}
async function pollSelecaoAnalysis(id,epoch=selecaoState.epoch) {
  stopIssueSelecaoPolling();
  try {
    const result=await api('/api/issues/selecao/analises/'+id);
    if(epoch!==selecaoState.epoch || state.issueView!=='selecao' || !selEl('section-issues').classList.contains('active'))return;
    if(selecaoState.analysis && selecaoState.analysis.id!==id)return;
    selecaoState.analysis=result;
    selEl('selecaoPromptUsado').textContent=result.prompt || '';
    selecaoState.busy=['pendente','processando'].includes(result.status);
    const message=selecaoProgress(result.etapa || (result.status==='processando' ? 'aguardando' : 'enviando'),result.status);
    selEl('selecaoMensagem').textContent=`Análise #${id}: ${message} ${result.erro_mensagem_segura || ''}`;
    selecaoCount();
    if(selecaoState.busy)selecaoState.timer=setTimeout(()=>pollSelecaoAnalysis(id,epoch),2000);
    else {
      if(result.status==='concluida') {
        renderSelecaoCandidates(result.candidatas_rnc);
        if(result.ultima_geracao)renderSelecaoGeneration(result.ultima_geracao);
      }
      else selEl('selecaoCandidatasBloco').classList.add('hidden');
      await loadSelecaoHistory();
    }
  }catch(e){if(epoch===selecaoState.epoch){selecaoState.busy=false;selecaoCount();selEl('selecaoMensagem').textContent=e.message;}}
}
function rncControl(name,label,type,options,value) {
  const wrap=document.createElement('div');const text=document.createElement('label');text.textContent=label;
  let input;
  if(type==='select' || type==='multiple') {
    input=document.createElement('select');input.multiple=type==='multiple';
    if(!input.multiple)input.appendChild(new Option('Selecione',''));
    options.forEach(([key,title])=>input.appendChild(new Option(title,key)));
  } else if(type==='textarea'){input=document.createElement('textarea');input.rows=2;}
  else {input=document.createElement('input');input.type=type;}
  input.dataset.rncField=name;input.required=false;input.disabled=true;
  if(value)input.value=value;
  text.appendChild(input);wrap.appendChild(text);return wrap;
}
function renderSelecaoCandidates(items) {
  selecaoState.candidates=items;
  selEl('selecaoCandidatasBloco').classList.remove('hidden');selEl('selecaoCandidatas').replaceChildren();
  selEl('selecaoGerar').disabled=true;
  if(!items.length){selEl('selecaoCandidatas').textContent='Nenhuma Issue atende aos critérios com os dados fornecidos.';return;}
  const users=selecaoState.users.map(u=>[u.id,u.nome]);
  items.forEach(item=>{
    const card=document.createElement('div');card.className='selecao-candidata';card.dataset.candidateId=item.id;
    const check=document.createElement('input');check.type='checkbox';check.dataset.candidateCheck=item.id;check.disabled=item.gerada || !item.id_issue;
    check.setAttribute('aria-label',`Selecionar candidata ${item.codigo_issue}`);
    const title=document.createElement('strong');title.textContent=item.resumo;
    card.append(check,issueCodeLink(item.codigo_issue,item.id_issue),title);
    const age=document.createElement('p');age.textContent=issueRegisteredTime(item.criado_em);card.appendChild(age);
    for(const [caption,text] of [['Criticidade sugerida',item.criticidade_sugerida],['Requisito violado',item.justificativa.requisito_violado],
      ['Fato e evidência',item.justificativa.fato_e_evidencia],['Critérios da IA',item.justificativa.criterios_ia]]) {
      const p=document.createElement('p');const title=document.createElement('strong');title.textContent=caption+': ';
      p.append(title,document.createTextNode(text));card.appendChild(p);
    }
    if(item.gerada){const p=document.createElement('p');p.textContent=`RNC já gerada: ${item.codigo_rnc}`;card.appendChild(p);}
    else if(!item.id_issue){const p=document.createElement('p');p.textContent='Issue removida; histórico preservado.';card.appendChild(p);}
    else {
      const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Complemento da RNC (opcional)';details.appendChild(summary);
      const grid=document.createElement('div');grid.className='grid-3';
      [
        ['criticidade','Classificação (não conformidade)','select',[['maior','Maior'],['menor','Menor']]],
        ['enquadramento_normativo','Enquadramento normativo / contratual','textarea',null,item.justificativa.requisito_violado],
        ['acao_contencao_definitiva','Contenção definitiva','textarea'],
        ['contencao_responsavel_id','Responsável pela contenção','select',users],
        ['contencao_em','Data/hora da contenção','datetime-local'],
        ['disposicao_inicial','Disposição inicial','select',[['refugo','Refugo'],['retrabalho','Retrabalho'],['devolucao_fornecedor','Devolução ao fornecedor'],['liberacao_concessao','Liberação por concessão']]],
        ['lider_investigacao_id','Líder da investigação','select',users],
        ['equipe_investigacao','Equipe de investigação','multiple',users],
        ['metodologia','Metodologia','select',[['5_porques','5 Porquês'],['ishikawa','Ishikawa'],['fmea','FMEA']]],
        ['prazo_analise','Prazo de análise','date'],['prazo_plano_acao','Prazo do plano de ação','date'],
        ['prazo_verificacao_eficacia','Prazo de verificação da eficácia','date'],['auditor_eficacia_id','Auditor da eficácia','select',users],
      ].forEach(args=>grid.appendChild(rncControl(...args)));
      details.appendChild(grid);card.appendChild(details);
      check.onchange=()=>{
        card.querySelectorAll('[data-rnc-field]').forEach(el=>el.disabled=!check.checked);
        details.open=check.checked;
        selEl('selecaoGerar').disabled=selecaoState.busy || !selEl('selecaoCandidatas').querySelector('[data-candidate-check]:checked');
      };
    }
    selEl('selecaoCandidatas').appendChild(card);
  });
}
async function selecaoAnalyze(event) {
  event.preventDefault();if(selecaoState.busy)return;
  const epoch=selecaoState.epoch;
  try {
    const body={empresa_id:state.empresaId,acesso_llm_id:Number(selEl('selecaoAcesso').value),issue_ids:Array.from(selecaoState.selected).sort((a,b)=>a-b),prompt:selEl('selecaoPrompt').value};
    if(!body.issue_ids.length || body.issue_ids.length>20)throw new Error('Selecione de 1 a 20 Issues.');
    if(!body.acesso_llm_id)throw new Error('Selecione o acesso LLM.');
    if(!body.prompt.trim())throw new Error('Informe o prompt antes de enviar.');
    if(body.prompt.length>20000)throw new Error('O prompt deve ter no máximo 20.000 caracteres.');
    const request=JSON.stringify(body);
    if(request!==selecaoState.lastRequest){selecaoState.analysisKey=selecaoUUID();selecaoState.lastRequest=request;}
    selecaoState.busy=true;selecaoCount();
    selEl('selecaoMensagem').textContent=selecaoProgress('enviando','pendente');
    selEl('selecaoCandidatasBloco').classList.add('hidden');selEl('selecaoResultadoBloco').classList.add('hidden');
    const result=await api('/api/issues/selecao/analises',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':selecaoState.analysisKey},body});
    if(epoch!==selecaoState.epoch)return;
    selecaoState.analysis=result;selecaoState.lastRequest=null;
    await pollSelecaoAnalysis(result.id,epoch);
  }catch(e){if(epoch===selecaoState.epoch){selecaoState.busy=false;selecaoCount();selEl('selecaoMensagem').textContent=e.message;}}
}
async function selecaoGenerate(event) {
  event.preventDefault();if(selecaoState.busy || !selecaoState.analysis)return;
  const items=[];
  for(const check of selEl('selecaoCandidatas').querySelectorAll('[data-candidate-check]:checked')) {
    const card=check.closest('[data-candidate-id]');const data={};
    card.querySelectorAll('[data-rnc-field]').forEach(input=>{
      const field=input.dataset.rncField;
      data[field]=input.multiple ? Array.from(input.selectedOptions).map(o=>Number(o.value)) : field.endsWith('_id') ? (input.value ? Number(input.value) : null) : input.value;
    });
    items.push({candidata_id:Number(check.dataset.candidateCheck),dados_rnc:data});
  }
  if(!items.length || !confirm(`Gerar ${items.length} RNC(s) e fechar as Issues de origem?`))return;
  const epoch=selecaoState.epoch;const analysisId=selecaoState.analysis.id;
  const body={confirmar:true,itens:items};const fingerprint=JSON.stringify(body);
  try {
    if(!selecaoState.generationKey || selecaoState.generationKey.fingerprint!==fingerprint)
      selecaoState.generationKey={fingerprint,key:selecaoUUID()};
    selecaoState.busy=true;selEl('selecaoGerar').disabled=true;selecaoCount();
    const result=await api(`/api/issues/selecao/analises/${analysisId}/geracoes`,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':selecaoState.generationKey.key},body});
    if(epoch!==selecaoState.epoch)return;
    selecaoState.generationKey=null;
    if(selecaoState.analysis?.id!==analysisId)return;
    renderSelecaoGeneration(result);
    selecaoState.candidates.forEach(item=>{
      const success=result.itens.find(i=>i.candidata_id===item.id && i.status==='gerada');
      if(success){item.gerada=true;item.codigo_rnc=success.codigo_rnc;selecaoState.selected.delete(item.id_issue);
        const card=selEl('selecaoCandidatas').querySelector(`[data-candidate-id="${item.id}"]`);
        card.querySelectorAll('input,select,textarea').forEach(el=>el.disabled=true);
        card.querySelector('[data-candidate-check]').checked=false;
        const info=document.createElement('p');info.textContent=`RNC gerada: ${success.codigo_rnc}`;card.appendChild(info);}
    });
    selEl('selecaoMensagem').textContent=`Geração #${result.geracao_id}: ${result.status}. ${result.status!=='concluida' ? 'Corrija as pendências antes de tentar novamente.' : ''}`;
    await Promise.all([loadSelecaoPage(),loadSelecaoHistory(),loadIssueList(),loadIssueKanban()]);
  }catch(e){if(epoch===selecaoState.epoch)selEl('selecaoMensagem').textContent=e.message;}
  finally{if(epoch===selecaoState.epoch){selecaoState.busy=false;selecaoCount();selEl('selecaoGerar').disabled=!selEl('selecaoCandidatas').querySelector('[data-candidate-check]:checked');}}
}
function renderSelecaoGeneration(result) {
  selEl('selecaoResultadoBloco').classList.remove('hidden');selEl('selecaoResultado').replaceChildren();
  result.itens.forEach(item=>{const row=document.createElement('div');row.className='selecao-resultado-item';
    row.textContent=`${item.codigo_issue} · ${item.codigo_rnc || 'Pendente'} · ${item.erro_mensagem || 'RNC gerada com sucesso'}`;
    selEl('selecaoResultado').appendChild(row);});
}
selEl('selecaoAnaliseForm').addEventListener('submit',selecaoAnalyze);
selEl('selecaoGerarForm').addEventListener('submit',selecaoGenerate);
selEl('selecaoAcesso').addEventListener('change',selecaoCount);
selEl('selecaoRestaurarPrompt').onclick=()=>{selEl('selecaoPrompt').value=selecaoDefaultPrompt;};
selEl('selecaoTodos').addEventListener('change',()=>{
  const checked=selEl('selecaoTodos').checked;
  selecaoState.items.forEach(i=>{if(checked)selecaoState.selected.add(i.id);else selecaoState.selected.delete(i.id);});
  loadSelecaoPage().catch(e=>selEl('selecaoMensagem').textContent=e.message);
});
selEl('selecaoFiltrar').onclick=()=>{selecaoState.page=1;loadSelecaoPage().catch(e=>selEl('selecaoMensagem').textContent=e.message);};
selEl('selecaoAnterior').onclick=()=>{selecaoState.page--;loadSelecaoPage().catch(e=>selEl('selecaoMensagem').textContent=e.message);};
selEl('selecaoProxima').onclick=()=>{selecaoState.page++;loadSelecaoPage().catch(e=>selEl('selecaoMensagem').textContent=e.message);};
selEl('selecaoHistorico').onchange=()=>{
  stopIssueSelecaoPolling();const id=Number(selEl('selecaoHistorico').value);
  selecaoState.analysis=id ? {id} : null;selecaoState.busy=false;
  selEl('selecaoCandidatasBloco').classList.add('hidden');selEl('selecaoResultadoBloco').classList.add('hidden');
  if(id)pollSelecaoAnalysis(id);else selecaoCount();
};
