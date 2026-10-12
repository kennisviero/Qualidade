function rncKanbanLabel(actions) {
  const counts=new Map();
  for(const action of actions || [])counts.set(action.status,(counts.get(action.status)||0)+1);
  const order=['backlog','iniciada','em_andamento','em_revisao','finalizada'];
  const statuses=order.filter(status=>counts.has(status));
  if(!statuses.length)return 'Sem cartão';
  return statuses.map(status=>`${KANBAN_LABELS[status] || status}${statuses.length>1?` (${counts.get(status)})`:''}`).join(' · ');
}

function updateRncKanbanStatus(actions) {
  const status=document.querySelector('[data-rnc-kanban-status]');
  if(!status)return;
  const own=actions.filter(action=>String(action.rnc_id)===status.dataset.rncKanbanStatus);
  status.textContent='Status no Kanban: '+rncKanbanLabel(own);
  document.querySelectorAll('[data-rnc-task-status]').forEach(cell=>{
    const action=own.find(row=>String(row.id)===cell.dataset.rncTaskStatus);
    if(action)cell.textContent=KANBAN_LABELS[action.status]||action.status;
  });
  rncRecords=rncRecords.map(record=>({...record,acoes:(record.acoes||[]).map(action=>{
    const current=actions.find(row=>row.id===action.id);return current?{...action,status:current.status}:action;
  })}));
}

async function renderRncTabs(target, item, activeTab='registro') {
  const company=state.empresaId;
  target.replaceChildren();
  const header=document.createElement('div');header.className='rnc-header';
  const title=document.createElement('h3');title.textContent=item.rnc_codigo;
  const badge=document.createElement('span');badge.className='meta-chip';badge.textContent=item.rnc_status==='emitida'?'Emitida':item.rnc_status;
  const spacer=document.createElement('span');spacer.className='spacer';
  const origin=document.createElement('button');origin.type='button';origin.className='btn';origin.textContent='Consultar Issue de origem';
  origin.onclick=async()=>{navigate('issues');await showIssueView('capturar');await selectIssue(item.id);};
  const actions=document.createElement('div');actions.className='rnc-header-actions';
  const kanbanStatus=document.createElement('span');kanbanStatus.className='rnc-kanban-status';kanbanStatus.dataset.rncKanbanStatus=String(item.rnc_id);kanbanStatus.setAttribute('aria-live','polite');
  kanbanStatus.textContent='Status no Kanban: '+rncKanbanLabel(item.acoes);
  actions.append(origin,kanbanStatus);
  header.append(title,badge,spacer,actions);target.appendChild(header);
  const message=document.createElement('p');message.className='hint';message.setAttribute('role','status');target.appendChild(message);
  let users;
  try { users=(await api('/api/usuarios')).filter(u=>u.empresa_id===item.rnc_empresa_id); }
  catch(error){message.textContent=error.message;return;}
  if(company!==state.empresaId || String(item.id)!==document.getElementById('rncSelect').value)return;
  const userOptions=users.map(u=>[u.id,u.nome]);
  const writable=isEditor() && !['concluida','fechada'].includes(item.rnc_status);
  const tabs=document.createElement('div');tabs.className='rnc-tabs';target.appendChild(tabs);
  const panes={};const tabButtons={};
  for(const [key,label] of [['registro','1. Registro'],['contencao','2. Contenção'],['investigacao','3. Investigação'],['plano','4. Plano de Ação'],['pendencias','5. Pendências']]){
    const tab=document.createElement('button');tab.type='button';tab.className='rnc-tab';tab.textContent=label;tab.setAttribute('role','tab');
    const pane=document.createElement('div');pane.className='rnc-pane';pane.setAttribute('role','tabpanel');
    tabs.appendChild(tab);target.appendChild(pane);panes[key]=pane;tabButtons[key]=tab;
    tab.onclick=()=>selectTab(key);
  }
  function selectTab(key){activeTab=key;Object.keys(panes).forEach(k=>{panes[k].classList.toggle('active',k===key);tabButtons[k].classList.toggle('active',k===key);tabButtons[k].setAttribute('aria-selected',String(k===key));});}
  function block(pane,title,columns=2){const card=document.createElement('div');card.className='card issue-initial-block rnc-data-block';const h=document.createElement('h4');h.textContent=title;card.appendChild(h);const grid=document.createElement('div');grid.className=`grid-${columns}`;card.appendChild(grid);pane.appendChild(card);return grid;}
  function field(grid,label,name,type,value,options=[],readOnly=false){
    const wrap=document.createElement('div'),caption=document.createElement('label');caption.textContent=label;
    let input;
    if(type==='select'||type==='multiple'){
      input=document.createElement('select');input.multiple=type==='multiple';
      if(!input.multiple)input.appendChild(new Option('Não informado',''));
      options.forEach(([id,text])=>{const opt=new Option(text,id);opt.selected=input.multiple?(value||[]).includes(id):String(value||'')===String(id);input.appendChild(opt);});
    }else{input=document.createElement(type==='textarea'?'textarea':'input');if(type==='textarea')input.rows=3;else input.type=type;}
    if(type!=='multiple')input.value=value==null?'':String(value);
    input.dataset.field=name;input.setAttribute('aria-label',label);
    if(readOnly){input.readOnly=true;if(type==='select'||type==='multiple')input.disabled=true;}
    else input.disabled=!writable;
    caption.appendChild(input);wrap.appendChild(caption);grid.appendChild(wrap);return input;
  }
  function read(pane){const data={};pane.querySelectorAll('[data-field]').forEach(input=>{if(input.readOnly)return;const key=input.dataset.field;data[key]=input.multiple?Array.from(input.selectedOptions).map(o=>key==='metodologias'?o.value:Number(o.value)):key.endsWith('_id')?(input.value?Number(input.value):null):input.value;});return data;}
  async function mutate(path,body,method='PUT'){
    if(!writable)return;
    message.textContent='Salvando…';
    try{
      const updated=await api(`/api/rncs/${item.rnc_id}${path}`,{method,body});
      if(company!==state.empresaId || String(item.id)!==document.getElementById('rncSelect').value)return;
      rncRecords=rncRecords.map(row=>row.rnc_id===updated.rnc_id?updated:row);
      await renderRncTabs(target,updated,activeTab);
      await loadIssueKanban();
    }catch(error){message.textContent=error.message;}
  }
  function save(pane,body){const button=document.createElement('button');button.type='button';button.className='btn primary';button.textContent='Salvar registro';button.disabled=!writable;button.onclick=()=>mutate('',body?body():read(pane));pane.appendChild(button);}
  const registration=panes.registro;
  let grid=block(registration,'Identificação da RNC',3);
  field(grid,'Código da RNC','codigo','text',item.rnc_codigo,[],true);
  field(grid,'Issue de origem','codigo_issue','text',item.codigo,[],true);
  field(grid,'Data/hora da abertura','emitida_em','text',new Date(item.rnc_emitida_em).toLocaleString('pt-BR'),[],true);
  field(grid,'Emitida por','emitida_por_nome','text',item.rnc_emitida_por_nome,[],true);
  grid=block(registration,'Emitente e responsável',3);
  field(grid,'Emitente (usuário da empresa)','emitente_id','select',item.rnc_emitente_id,userOptions);
  field(grid,'Responsável pelo tratamento (usuário da empresa)','responsavel_id','select',item.rnc_responsavel_id,userOptions);
  field(grid,'Classificação (não conformidade)','criticidade','select',item.rnc_criticidade,[['maior','Maior'],['menor','Menor']]);
  grid=block(registration,'Fatos preservados da Issue',2);
  for(const [key,label] of [['comportamento_esperado','Comportamento esperado'],['comportamento_observado','Comportamento observado'],['evidencias_objetivas','Evidências objetivas'],['acao_emergencial','Ação emergencial na abertura'],['como_detectado','Como foi detectado'],['onde','Onde ocorreu']])field(grid,label,key,'textarea',item[key],[],true);
  grid=block(registration,'Contexto e rastreabilidade preservados',3);
  for(const [key,label] of [['detectado_em','Data/hora da detecção'],['codigo_material','Material'],['lote','Lote'],['ordem_producao','Ordem de produção'],['sn_inicio','Número de série inicial'],['sn_fim','Número de série final']])field(grid,label,key,'text',item[key],[],true);
  grid=block(registration,'Impacto e ambiente da RNC',2);
  for(const [key,label,choices] of [
    ['impacto','Impacto',[['baixo','Baixo'],['medio','Médio'],['alto','Alto'],['critico','Crítico']]],
    ['ambiente','Ambiente',[['producao','Produção'],['homologacao','Homologação'],['campo','Campo'],['linha','Linha'],['outro','Outro']]],
  ]){
    const value=item['rnc_'+key]??item[key];
    if(value&&!choices.some(([id])=>id===value))choices.push([value,value]);
    field(grid,label,key,'select',value,choices);
  }
  const notice=document.createElement('p');notice.className='hint';notice.textContent=item.rnc_fatos_snapshot_origem==='emissao'?'Fatos preservados na emissão. Edições da Issue não alteram este registro.':'Registro histórico: fatos recuperados na migração; a origem de triagem foi usada quando disponível e os demais dados vieram da Issue na data da migração.';registration.appendChild(notice);
  grid=block(registration,'Enquadramento',2);
  field(grid,'Requisito normativo / contratual','enquadramento_normativo','textarea',item.rnc_enquadramento_normativo);
  save(registration);
  const containment=panes.contencao;
  grid=block(containment,'Contenção',2);
  field(grid,'Contenção imediata','acao_contencao_imediata','textarea',item.rnc_acao_contencao_imediata);
  field(grid,'Contenção definitiva','acao_contencao_definitiva','textarea',item.rnc_acao_contencao_definitiva);
  grid=block(containment,'Responsáveis e datas',3);
  field(grid,'Responsável pela contenção','contencao_responsavel_id','select',item.rnc_contencao_responsavel_id,userOptions);
  field(grid,'Prazo da contenção','data_limite_contencao','datetime-local',(item.rnc_data_limite_contencao||'').slice(0,16));
  field(grid,'Conclusão da contenção','data_conclusao_contencao','datetime-local',(item.rnc_data_conclusao_contencao||'').slice(0,16));
  field(grid,'Validada por','contencao_validada_por_id','select',item.rnc_contencao_validada_por_id,userOptions);
  if(item.rnc_contencao_em)field(grid,'Data/hora da contenção (registro original)','contencao_em','text',item.rnc_contencao_em,[],true);
  field(grid,'Disposição do produto/serviço','disposicao_inicial','select',item.rnc_disposicao_inicial,[['refugo','Refugo'],['retrabalho','Retrabalho'],['devolucao_fornecedor','Devolução ao fornecedor'],['liberacao_concessao','Liberação por concessão'],['bloqueio_preventivo','Bloqueio preventivo']]);save(containment);
  const investigation=panes.investigacao;
  grid=block(investigation,'Investigação da causa',3);
  const methods=field(grid,'Metodologias','metodologias','multiple',item.rnc_metodologias || (item.rnc_metodologia?[item.rnc_metodologia]:[]),[['5_porques','5 Porquês'],['ishikawa','Ishikawa'],['fmea','FMEA']]);
  methods.size=3;
  const methodHint=document.createElement('small');methodHint.className='hint';methodHint.textContent='Use Ctrl (ou ⌘) para selecionar mais de uma.';methods.parentNode?.appendChild(methodHint);
  field(grid,'Líder da investigação','lider_investigacao_id','select',item.rnc_lider_investigacao_id,userOptions);
  field(grid,'Prazo da análise','prazo_analise','date',item.rnc_prazo_analise);
  grid=block(investigation,'Equipe e análise',2);
  field(grid,'Equipe de investigação','equipe_investigacao','multiple',item.rnc_equipe_investigacao,userOptions);
  const investigationData=item.rnc_investigacao_json||{};
  const notes=field(grid,'Notas da investigação','analise_texto','textarea',investigationData.analise||'');
  const observation=item.observacao||{},observationControls={};
  grid=block(investigation,'Observação — frequência e período',3);
  for(const [key,label,type] of [['inicio_ocorrencias','Início das ocorrências','datetime-local'],['periodo_inicio','Período analisado — início','date'],['periodo_fim','Período analisado — fim','date'],['frequencia','Histórico e frequência das ocorrências','textarea'],['turnos_horarios','Turnos, dias e horários afetados','textarea']])
    observationControls[key]=field(grid,label,'observacao_'+key,type,observation[key]||'');
  grid=block(investigation,'Localização e características do problema',2);
  for(const [key,label] of [['localizacao','Máquina, linha, unidade, sistema ou etapa'],['sintomas_condicoes','Sintomas e condições em que a falha aparece'],['condicoes_sem_falha','Condições em que a falha não ocorre']])
    observationControls[key]=field(grid,label,'observacao_'+key,'textarea',observation[key]||'');
  grid=block(investigation,'Pessoas envolvidas nas ocorrências',2);
  observationControls.operadores_ids=field(grid,'Operadores envolvidos','observacao_operadores_ids','multiple',observation.operadores_ids||[],userOptions);
  observationControls.equipes_envolvidas=field(grid,'Equipes envolvidas no momento da falha','observacao_equipes_envolvidas','textarea',observation.equipes_envolvidas||'');
  grid=block(investigation,'Impacto acumulado',3);
  const numberFields=['quantidade_afetada','horas_perdidas','prejuizo_financeiro'];
  for(const [key,label,type] of [['quantidade_afetada','Quantidade afetada','number'],['unidade_quantidade','Unidade (peças, pedidos, ocorrências...)','text'],['horas_perdidas','Horas perdidas / retrabalho','number'],['prejuizo_financeiro','Prejuízo financeiro','number'],['moeda','Moeda','text'],['impacto_periodo','Período de referência do impacto','text']]){
    const input=field(grid,label,'observacao_'+key,type,observation[key]??(key==='moeda'?'BRL':''));
    if(type==='number'){input.min='0';input.step='any';}observationControls[key]=input;
  }
  const hypothesesBlock=block(investigation,'Hipóteses e testes de validação',1);
  const hypothesisStates=[];
  function appendHypothesis(hypothesis={}){
    const card=document.createElement('div');card.className='card';hypothesesBlock.appendChild(card);
    const h=document.createElement('h4');h.textContent=`Hipótese ${hypothesisStates.length+1}`;card.appendChild(h);
    const hypothesisGrid=document.createElement('div');hypothesisGrid.className='grid-3';card.appendChild(hypothesisGrid);
    const controls={};const index=hypothesisStates.length;
    for(const [key,label] of [['descricao','Hipótese de causa'],['evidencias_favoraveis','Evidências favoráveis'],['evidencias_contrarias','Evidências contrárias']])controls[key]=field(hypothesisGrid,label,`hipotese_${index}_${key}`,'textarea',hypothesis[key]||'');
    const tests=[];hypothesisStates.push({controls,tests});
    function appendTest(test={}){
      const testGrid=block(card,`Teste ${tests.length+1}`,3),testControls={};
      for(const [key,label,type] of [['procedimento','Procedimento / teste realizado','textarea'],['responsavel_id','Responsável pelo teste','select'],['data','Data do teste','date'],['resultado','Resultado observado','textarea'],['conclusao','Conclusão da hipótese','select']]){
        const options=key==='responsavel_id'?userOptions:key==='conclusao'?[['confirmada','Confirmada'],['descartada','Descartada'],['inconclusiva','Inconclusiva']]:[];
        testControls[key]=field(testGrid,label,`teste_${index}_${tests.length}_${key}`,type,test[key]??'',options);
      }tests.push(testControls);
    }
    (hypothesis.testes||[]).forEach(test=>appendTest(test));
    const addTest=document.createElement('button');addTest.type='button';addTest.className='btn';addTest.textContent='Adicionar teste';addTest.disabled=!writable;addTest.onclick=()=>appendTest();card.appendChild(addTest);
  }
  (investigationData.hipoteses||[]).forEach(hypothesis=>appendHypothesis(hypothesis));
  const addHypothesis=document.createElement('button');addHypothesis.type='button';addHypothesis.className='btn';addHypothesis.textContent='Adicionar hipótese';addHypothesis.disabled=!writable;addHypothesis.onclick=()=>appendHypothesis();hypothesesBlock.appendChild(addHypothesis);
  save(investigation,()=>{
    const data=read(investigation);for(const key of Object.keys(data))if(key==='analise_texto'||/^(observacao_|hipotese_|teste_)/.test(key))delete data[key];
    data.observacao={};for(const [key,input] of Object.entries(observationControls))data.observacao[key]=input.multiple?Array.from(input.selectedOptions).map(option=>Number(option.value)):numberFields.includes(key)?(input.value===''?null:Number(input.value)):input.value;
    const hypotheses=hypothesisStates.map(({controls,tests})=>({
      ...Object.fromEntries(Object.entries(controls).map(([key,input])=>[key,input.value])),
      testes:tests.map(controls=>Object.fromEntries(Object.entries(controls).map(([key,input])=>[key,key==='responsavel_id'?(input.value?Number(input.value):null):input.value]))),
    }));
    data.investigacao_json={...investigationData,analise:notes.value,hipoteses:hypotheses};delete data.investigacao_json.porques;return data;
  });
  const evidenceGrid=block(investigation,'Arquivos de evidência',1);
  const evidenceList=document.createElement('div');evidenceList.className='rnc-evidence-list';evidenceGrid.appendChild(evidenceList);
  function appendEvidence(evidence){
    const entry=document.createElement('p'),link=document.createElement('a');link.textContent=evidence.nome;
    link.href=`/api/rncs/${item.rnc_id}/evidencias/${evidence.id}`;link.target='_blank';link.rel='noopener';
    entry.appendChild(link);const size=document.createElement('span');size.className='muted';size.textContent=` · ${(evidence.tamanho/1024).toFixed(1)} KB · ${new Date(evidence.carregado_em).toLocaleString('pt-BR')}`;entry.appendChild(size);
    if(writable){
      const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.textContent='Excluir';remove.setAttribute('aria-label',`Excluir evidência ${evidence.nome}`);
      remove.onclick=async()=>{
        if(remove.disabled || !confirm(`Excluir o arquivo de evidência "${evidence.nome}"?`))return;
        remove.disabled=true;
        try{
          await api(`/api/rncs/${item.rnc_id}/evidencias/${evidence.id}`,{method:'DELETE'});
          if(company!==state.empresaId || String(item.id)!==document.getElementById('rncSelect').value)return;
          item.evidencias_investigacao=(item.evidencias_investigacao||[]).filter(file=>file.id!==evidence.id);
          rncRecords=rncRecords.map(record=>record.rnc_id===item.rnc_id?{...record,evidencias_investigacao:item.evidencias_investigacao}:record);
          entry.remove();message.textContent='Evidência excluída.';
        }catch(error){message.textContent=error.message;remove.disabled=false;}
      };entry.appendChild(remove);
    }
    evidenceList.appendChild(entry);
  }
  (item.evidencias_investigacao||[]).forEach(evidence=>appendEvidence(evidence));
  const files=document.createElement('input');files.type='file';files.multiple=true;files.disabled=!writable;files.setAttribute('aria-label','Arquivos de evidência');evidenceGrid.appendChild(files);
  const upload=document.createElement('button');upload.type='button';upload.className='btn';upload.textContent='Carregar evidências';upload.disabled=!writable;evidenceGrid.appendChild(upload);
  upload.onclick=async()=>{
    if(upload.disabled || !files.files?.length)return;
    upload.disabled=true;files.disabled=true;
    try{
      for(const file of Array.from(files.files)){
        const body=new FormData();body.append('file',file);message.textContent=`Carregando ${file.name}…`;
        const response=await fetch(`/api/rncs/${item.rnc_id}/evidencias`,{method:'POST',credentials:'same-origin',body});
        const evidence=await response.json();if(!response.ok)throw new Error(evidence.detail||'Não foi possível carregar o arquivo');
        if(company!==state.empresaId || String(item.id)!==document.getElementById('rncSelect').value)return;
        appendEvidence(evidence);item.evidencias_investigacao=[...(item.evidencias_investigacao||[]),evidence];
        rncRecords=rncRecords.map(record=>record.rnc_id===item.rnc_id?{...record,evidencias_investigacao:item.evidencias_investigacao}:record);
      }
      files.value='';message.textContent='Evidências carregadas. Os dados da investigação são gravados em Salvar registro.';
    }catch(error){message.textContent=error.message;}
    finally{upload.disabled=!writable;files.disabled=!writable;}
  };
  const plan=panes.plano;
  grid=block(plan,'Aprovação e prazo do plano',2);
  const planApprover=field(grid,'Aprovador do plano 5W2H','plano_aprovador_id','select',item.rnc_plano_aprovador_id,userOptions);
  const planDeadline=field(grid,'Prazo do plano de ação','prazo_plano_acao','date',item.rnc_prazo_plano_acao);
  const approved=document.createElement('p');approved.className='hint';approved.textContent=item.rnc_plano_aprovado_em?`Aprovado em ${new Date(item.rnc_plano_aprovado_em).toLocaleString('pt-BR')}`:'Plano aguardando aprovação.';plan.appendChild(approved);save(plan,()=>({plano_aprovador_id:planApprover.value?Number(planApprover.value):null,prazo_plano_acao:planDeadline.value}));
  const approve=document.createElement('button');approve.type='button';approve.className='btn';approve.textContent='Aprovar plano';approve.disabled=!writable || item.rnc_plano_aprovador_id!==state.user.id;approve.onclick=()=>mutate('/aprovar-plano',{},'POST');plan.appendChild(approve);
  const matrix=document.createElement('div');matrix.className='rnc-plan-matrix';
  const table=document.createElement('table');table.setAttribute('aria-label','Matriz do plano de ação 5W2H');
  const colgroup=document.createElement('colgroup');
  [18,10,7,11,12,13,7,10,6,6].forEach(width=>{const column=document.createElement('col');column.style.width=width+'%';colgroup.appendChild(column);});table.appendChild(colgroup);
  const columns=[['descricao','O quê?','textarea'],['por_que','Por quê?','textarea'],['onde','Onde?','text'],['responsavel_id','Quem?','select'],['prazo_limite','Quando?','date'],['como','Como?','textarea'],['quanto','Quanto?','text'],['observacao','Observações','textarea']];
  const thead=document.createElement('thead'),headRow=document.createElement('tr');
  [...columns.map(([,label])=>label),'Status','Salvar'].forEach(label=>{const cell=document.createElement('th');cell.textContent=label;cell.setAttribute('scope','col');headRow.appendChild(cell);});thead.appendChild(headRow);
  const tbody=document.createElement('tbody');table.append(thead,tbody);matrix.appendChild(table);plan.appendChild(matrix);
  const rowStates=[];let taskBusy=false;
  const approvalAvailable=()=>{approve.disabled=!writable || item.rnc_plano_aprovador_id!==state.user.id || taskBusy || rowStates.some(row=>row.dirty);};
  const planSave=Array.from(plan.children).find(el=>el.textContent==='Salvar registro');
  const originalPlanSave=planSave.onclick;
  planSave.onclick=()=>{if(rowStates.some(row=>row.dirty)){message.textContent='Salve as linhas do plano antes de alterar o aprovador ou o prazo.';return;}originalPlanSave();};
  function appendTaskRow(task=null){
    const row=document.createElement('tr'),inputs={};const rowState={row,task,dirty:!task};rowStates.push(rowState);
    columns.forEach(([key,label,type])=>{
      const cell=document.createElement('td');let input;
      if(type==='select'){input=document.createElement('select');input.appendChild(new Option('Não informado',''));userOptions.forEach(([id,name])=>input.appendChild(new Option(name,id)));}
      else {input=document.createElement(type==='textarea'?'textarea':'input');if(type==='textarea')input.rows=3;else input.type=type;}
      input.value=task?.[key]??'';input.disabled=!writable;input.dataset.taskField=key;input.setAttribute('aria-label',label);
      const dirty=()=>{rowState.dirty=true;rowSave.textContent='Salvar linha';approvalAvailable();};input.addEventListener('input',dirty);input.addEventListener('change',dirty);
      inputs[key]=input;cell.appendChild(input);row.appendChild(cell);
    });
    const statusCell=document.createElement('td');statusCell.dataset.rncTaskStatus=String(task?.id||'');statusCell.textContent=task?(KANBAN_LABELS[task.status]||task.status):'Não salva';row.appendChild(statusCell);
    const actionsCell=document.createElement('td'),rowSave=document.createElement('button');rowSave.type='button';rowSave.className='btn primary';rowSave.textContent='Salvar linha';rowSave.disabled=!writable;actionsCell.appendChild(rowSave);row.appendChild(actionsCell);
    const discard=document.createElement('button');discard.type='button';discard.className='btn';discard.textContent='Descartar';discard.disabled=!writable;
    if(!task){actionsCell.appendChild(discard);discard.onclick=()=>{if(taskBusy)return;row.remove();rowStates.splice(rowStates.indexOf(rowState),1);approvalAvailable();};}
    rowSave.onclick=async()=>{
      if(taskBusy || !writable)return;
      const data={};for(const [key,input] of Object.entries(inputs))data[key]=key.endsWith('_id')?(input.value?Number(input.value):null):input.value;
      if(!data.descricao.trim()){message.textContent='Preencha O quê? antes de salvar a linha.';return;}
      taskBusy=true;rowSave.disabled=true;approvalAvailable();message.textContent='Salvando linha…';
      const previousIds=new Set((item.acoes||[]).map(action=>action.id));
      try{
        const updated=await api(`/api/rncs/${item.rnc_id}/acoes${rowState.task?'/'+rowState.task.id:''}`,{method:rowState.task?'PUT':'POST',body:data});
        if(company!==state.empresaId || String(item.id)!==document.getElementById('rncSelect').value)return;
        rowState.task=updated.acoes.find(action=>rowState.task?action.id===rowState.task.id:!previousIds.has(action.id));
        item=updated;rowState.dirty=false;rowSave.textContent='Salva';statusCell.dataset.rncTaskStatus=String(rowState.task.id);statusCell.textContent=KANBAN_LABELS[rowState.task.status]||rowState.task.status;
        discard.remove();
        rncRecords=rncRecords.map(record=>record.rnc_id===item.rnc_id?item:record);approved.textContent='Plano aguardando aprovação.';
        message.textContent='Linha salva.';await loadIssueKanban();
      }catch(error){message.textContent=error.message;}
      finally{taskBusy=false;rowSave.disabled=!writable;approvalAvailable();}
    };
    tbody.appendChild(row);approvalAvailable();
  }
  (item.acoes||[]).forEach(task=>appendTaskRow(task));
  const addTask=document.createElement('button');addTask.type='button';addTask.className='btn';addTask.textContent='Adicionar linha';addTask.disabled=!writable;addTask.onclick=()=>appendTaskRow();plan.appendChild(addTask);
  const pending=panes.pendencias;
  grid=block(pending,'Verificação de eficácia — agendamento',2);
  const efficacyAuditor=field(grid,'Auditor da eficácia','auditor_eficacia_id','select',item.rnc_auditor_eficacia_id,userOptions);
  const efficacyDeadline=field(grid,'Prazo de verificação da eficácia','prazo_verificacao_eficacia','date',item.rnc_prazo_verificacao_eficacia);
  save(pending,()=>({auditor_eficacia_id:efficacyAuditor.value?Number(efficacyAuditor.value):null,prazo_verificacao_eficacia:efficacyDeadline.value}));
  const missing=document.createElement('p');missing.className='hint';
  const gaps=[['Emitente',item.rnc_emitente_id],['Responsável',item.rnc_responsavel_id],['Contenção imediata',item.rnc_acao_contencao_imediata],['Prazo da contenção',item.rnc_data_limite_contencao],['Conclusão da contenção',item.rnc_data_conclusao_contencao],['Aprovador do plano',item.rnc_plano_aprovador_id]];
  missing.textContent='Campos ainda não preenchidos: '+(gaps.filter(([,value])=>!value).map(([label])=>label).join(', ')||'Nenhum destes campos.');pending.appendChild(missing);
  (item.pendencias||[]).forEach(p=>{const card=document.createElement('div');card.className='card';const text=document.createElement('p');text.textContent=`${p.descricao} · ${p.status==='aberta'?'Aberta':'Concluída'} · ${users.find(u=>u.id===p.responsavel_id)?.nome||'Sem responsável'} · ${p.prazo||'Sem prazo'}`;card.appendChild(text);const button=document.createElement('button');button.type='button';button.className='btn';button.textContent=p.status==='aberta'?'Concluir pendência':'Reabrir pendência';button.disabled=!writable;button.onclick=()=>mutate(`/pendencias/${p.id}`,{status:p.status==='aberta'?'concluida':'aberta'});card.appendChild(button);pending.appendChild(card);});
  grid=block(pending,'Nova pendência',3);
  const description=field(grid,'Descrição','pendencia_descricao','textarea','');
  const owner=field(grid,'Responsável','pendencia_responsavel_id','select','',userOptions);
  const deadline=field(grid,'Prazo','pendencia_prazo','date','');
  const add=document.createElement('button');add.type='button';add.className='btn primary';add.textContent='Adicionar pendência';add.disabled=!writable;add.onclick=()=>mutate('/pendencias',{descricao:description.value,responsavel_id:owner.value?Number(owner.value):null,prazo:deadline.value},'POST');pending.appendChild(add);
  selectTab(activeTab);
}
