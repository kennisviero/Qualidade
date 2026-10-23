let matResult=null,matRows=[],matColumns=[],matCells=[],matId=null,matRevision=1,matSequence=0,matDirty=false,matCell=null,matCellDirty=false;
const matEl=id=>document.getElementById(`mat-${id}`);
const matMode=()=>document.querySelector('#mat-form [name="contexto"]:checked').value;
const matLevels={nao_avaliada:'— Não avaliada',nenhuma:'Ø Nenhuma',fraca:'● Fraca',media:'●● Média',forte:'●●● Forte'};
function resetMatriz(){matSequence++;matResult=null;matRows=[];matColumns=[];matCells=[];matId=null;matDirty=false;matCell=null;matCellDirty=false;resetToolAI();document.getElementById('matrizWorkspace').replaceChildren();}
function matChanged(){matSequence++;matDirty=true;resetToolAI();for(const key of ['salvar','ia','gerar','filtrar'])matEl(key).disabled=false;matEl('mensagem').textContent='Alterações da matriz ainda não salvas.';}
function matOptionList(key,options,empty='Todos'){
  const el=matEl(key);el.replaceChildren();if(empty!==null)el.add(new Option(empty,''));options.forEach(o=>el.add(new Option(o.rotulo,o.valor)));
}
function buildMatriz(){
  const select=(k,label)=>`<div><label for="mat-${k}">${label}</label><select id="mat-${k}" name="${k}"></select></div>`;
  document.getElementById('matrizWorkspace').innerHTML=`
  <div class="pareto-actions" role="tablist" aria-label="Diagrama de Matriz"><button id="mat-tab-quadro" class="btn primary" role="tab" aria-selected="true" aria-controls="mat-quadro">Diagrama</button><button id="mat-tab-ajuda" class="btn" role="tab" aria-selected="false" aria-controls="mat-ajuda">Como funciona — RNC e Geral</button></div>
  <div id="mat-ajuda" class="card hidden" role="tabpanel" aria-labelledby="mat-tab-ajuda"><h3>O que a matriz analisa?</h3><p>As linhas representam problemas ou fatores investigados. As colunas representam ações dos planos. Cada cruzamento registra como uma ação contribui para tratar um problema, com intensidade, justificativa e evidência opcional. A matriz ajuda a revisar coerência e cobertura do plano; não comprova causa raiz nem eficácia.</p>
  <h3>Uma RNC</h3><p>Selecione uma RNC e examine a ligação entre seu relato, os fatores da investigação e as ações do seu plano. A linha inicial reproduz o problema observado na emissão. Você pode acrescentar hipóteses ou fatores, identificando a situação e as evidências.</p>
  <h3>Geral — várias RNCs</h3><p>Selecione de duas a vinte RNCs comparáveis da mesma empresa. Cada linha e coluna mostra sua origem. Investigue lacunas, sobreposições e possíveis ações comuns. Relatos semelhantes podem ter causas diferentes; justifique cada associação. Cruzar uma ação com problema de outra RNC representa cobertura proposta nesta análise e não transfere nem vincula a ação ao outro plano.</p>
  <h3>Como usar</h3><ol><li>Escolha contexto, aplique filtros e selecione as RNCs. Gere a matriz.</li><li>Confira os relatos/investigação e os planos em Registros de origem. Revise ou adicione linhas. Selecione as ações que deseja considerar nas colunas.</li><li>Clique em cada cruzamento: Não avaliada, Nenhuma, Fraca, Média ou Forte. Justifique toda avaliação, inclusive Nenhuma. Use a força da contribuição esperada como critério, com consistência entre cruzamentos.</li><li>Aplique a avaliação do cruzamento e revise os indicadores. Uma célula não avaliada não significa ausência de relação.</li><li>Salve manualmente e reabra pelos diagramas salvos. A análise preserva uma fotografia dos relatos e planos; mudanças posteriores nas RNCs não atualizam essa fotografia.</li></ol>
  <p>Intensidades são avaliações qualitativas do usuário, sem pontuação automática de prioridade. Linhas sem relação indicada ainda podem ter avaliações pendentes. Ações fora da matriz não foram consideradas. Verificar eficácia exige execução e avaliação posterior dos resultados.</p>
  <h3>Interação com a IA</h3><p>Consultar IA abre instruções editáveis e a prévia da matriz atual, com RNCs, investigação, ações, intensidades e justificativas. O prompt considera o contexto Uma RNC ou Geral. Só Enviar à IA chama o provedor. A resposta aparece na janela; revise as sugestões e ajuste manualmente a matriz. Ela não muda registros nem é salva como parte da análise.</p>
  <p>Admin/editor salvam. Visualizadores podem consultar e explorar temporariamente. Limites: 20 RNCs, 40 linhas e 60 ações por matriz. As origens, aprovações e planos permanecem intactos.</p></div>
  <div id="mat-quadro" role="tabpanel" aria-labelledby="mat-tab-quadro"><form id="mat-form" class="card"><fieldset class="pareto-source"><legend>Contexto da análise</legend><label><input type="radio" name="contexto" value="rnc" checked> Uma RNC</label><label><input type="radio" name="contexto" value="geral"> Geral — várias RNCs</label></fieldset>
  <div class="pareto-filters">${select('data_referencia','Data de referência')}<div><label for="mat-inicio">De</label><input id="mat-inicio" name="inicio" type="date"></div><div><label for="mat-fim">Até</label><input id="mat-fim" name="fim" type="date"></div>${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([k,v])=>select(k,v)).join('')}</div><button id="mat-filtrar" type="button" class="btn">Filtrar RNCs</button><label for="mat-rncs">RNCs para analisar</label><select id="mat-rncs" size="6"></select><p id="mat-fontes-resumo" class="hint"></p><button id="mat-gerar" class="btn primary" type="submit">Gerar matriz</button></form>
  <div class="card"><label for="mat-salvos">Matrizes salvas deste contexto</label><select id="mat-salvos"></select><button id="mat-abrir" class="btn">Abrir matriz</button></div><p id="mat-mensagem" role="status" aria-live="polite"></p>
  <div id="mat-editor" class="hidden"><div class="card"><label for="mat-titulo">Título da análise</label><input id="mat-titulo" maxlength="160"><div class="pareto-actions"><button id="mat-salvar" class="btn primary">Salvar matriz</button><button id="mat-ia" class="btn">Consultar IA</button></div><p id="mat-resumo"></p><p id="mat-alertas" class="hint"></p><label for="mat-colunas">Ações consideradas nas colunas (Ctrl/Cmd para selecionar várias)</label><select id="mat-colunas" multiple size="5"></select></div>
  <div id="mat-cell-editor" class="card hidden"><h3 id="mat-cell-title"></h3><label for="mat-intensidade">Intensidade da relação</label><select id="mat-intensidade"></select><label for="mat-justificativa">Justificativa (obrigatória para cruzamento avaliado)</label><textarea id="mat-justificativa" maxlength="3000" rows="3"></textarea><label for="mat-evidencia">Evidência / referência</label><textarea id="mat-evidencia" maxlength="3000" rows="2"></textarea><button id="mat-aplicar" class="btn primary">Aplicar cruzamento</button><button id="mat-cancelar" class="btn">Cancelar edição</button></div>
  <div id="mat-tabela" class="card mat-table-wrap"></div>
  <div class="card"><h3>Problemas e fatores (linhas)</h3><form id="mat-linha-form"><label for="mat-nova-linha">Descrição da nova linha</label><textarea id="mat-nova-linha" maxlength="2000" rows="2" required></textarea><label for="mat-linha-fontes">RNCs de origem da linha</label><select id="mat-linha-fontes" multiple size="4"></select><button id="mat-adicionar-linha" class="btn" type="submit">Adicionar hipótese/fator</button></form><div id="mat-linhas"></div></div>
  <details class="card"><summary>Registros de origem: relatos, investigação e planos</summary><div id="mat-origens"></div></details></div></div>`;
  for(const tab of ['quadro','ajuda'])matEl(`tab-${tab}`).onclick=()=>{for(const key of ['quadro','ajuda']){matEl(key).classList.toggle('hidden',key!==tab);matEl(`tab-${key}`).setAttribute('aria-selected',String(key===tab));matEl(`tab-${key}`).classList.toggle('primary',key===tab);}};
  matOptionList('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:'emitida_em',rotulo:'Emissão da RNC'}],null);
  matOptionList('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados'}],null);
  matOptionList('intensidade',Object.entries(matLevels).map(([valor,rotulo])=>({valor,rotulo})),null);
  matEl('form').onsubmit=e=>{e.preventDefault();matGenerate();};matEl('filtrar').onclick=()=>matLoadSources(false);
  matEl('form').onchange=e=>{
    if(e.target.name==='contexto'){
      if((matDirty||matCellDirty)&&!confirm('Descartar as alterações da matriz e trocar o contexto?')){document.querySelectorAll('#mat-form [name="contexto"]').forEach(r=>r.checked=r.value===(matResult?.contexto||'rnc'));return;}
      matResult=null;matId=null;matDirty=false;matCloseCell();matEl('editor').classList.add('hidden');matLoadSources(false);
    }else{matSequence++;resetToolAI();matEl('gerar').disabled=false;matEl('filtrar').disabled=false;matEl('salvar').disabled=false;matEl('ia').disabled=false;matEl('mensagem').textContent='Seleção/filtros alterados. Filtre as RNCs e gere outra matriz para usar o novo contexto. A matriz atual conserva seus dados.';}
  };
  matEl('titulo').oninput=matChanged;matEl('salvar').onclick=()=>matSubmit(false);matEl('ia').onclick=()=>matSubmit(true);matEl('abrir').onclick=matOpen;
  matEl('colunas').onchange=()=>{
    const selected=Array.from(matEl('colunas').selectedOptions,o=>Number(o.value));
    if(matCells.some(c=>!selected.includes(c.acao_id))&&!confirm('Retirar estas ações e suas avaliações da matriz?')){Array.from(matEl('colunas').options).forEach(o=>o.selected=matColumns.includes(Number(o.value)));return;}
    matColumns=selected;matCells=matCells.filter(c=>selected.includes(c.acao_id));matCloseCell();matChanged();matRenderTable();
  };
  matEl('linha-form').onsubmit=e=>{e.preventDefault();matAddRow();};
  for(const id of ['intensidade','justificativa','evidencia'])matEl(id).oninput=()=>{matCellDirty=true;resetToolAI();};
  matEl('aplicar').onclick=matApplyCell;matEl('cancelar').onclick=matCloseCell;
}
function matCloseCell(){matCell=null;matCellDirty=false;if(matEl('cell-editor'))matEl('cell-editor').classList.add('hidden');}
function matSourceParams(){const p=new URLSearchParams();for(const [key,value] of new FormData(matEl('form')))if(value&&key!=='contexto')p.set(key,value);p.set('empresa_id',state.empresaId);return p;}
async function loadMatriz(){if(matEl('form'))return;buildMatriz();await matLoadSources(true);}
async function matList(sequence=matSequence){
  const list=await api(`/api/ferramentas/matriz/diagramas?empresa_id=${state.empresaId}&contexto=${matMode()}`);
  if(sequence!==matSequence)return;matEl('salvos').replaceChildren(new Option('Selecione uma matriz',''));list.forEach(d=>matEl('salvos').add(new Option(`${d.titulo} · revisão ${d.revisao}`,d.id)));
}
async function matLoadSources(initial=false){
  if(!state.empresaId){matEl('mensagem').textContent='Selecione uma empresa.';return;}
  const seq=++matSequence;resetToolAI();matEl('gerar').disabled=true;matEl('filtrar').disabled=true;matEl('mensagem').textContent='Carregando RNCs…';
  try{
    const result=await api(`/api/ferramentas/matriz/fontes?${matSourceParams()}`);if(seq!==matSequence)return;
    if(initial)for(const key of Object.keys(paretoDimensions))matOptionList(key,result.opcoes[key]);
    const selector=matEl('rncs');selector.multiple=matMode()==='geral';selector.replaceChildren();
    result.registros.forEach(r=>selector.add(new Option(`${r.codigo} · ${r.descricao||'Sem relato'}`,r.id)));
    matEl('fontes-resumo').textContent=`${result.registros.length} RNCs disponíveis · sem data para o período: ${result.sem_data}. ${selector.multiple?'Selecione de 2 a 20 RNCs (Ctrl/Cmd).':'Selecione uma RNC.'}`;
    await matList(seq);if(seq===matSequence)matEl('mensagem').textContent='Selecione as RNCs e clique em Gerar matriz, ou abra uma matriz salva.';
  }catch(e){if(seq===matSequence)matEl('mensagem').textContent=e.message;}
  finally{if(seq===matSequence){matEl('gerar').disabled=false;matEl('filtrar').disabled=false;}}
}
async function matGenerate(){
  if((matDirty||matCellDirty)&&!confirm('Descartar alterações e gerar outra matriz?'))return;
  const ids=Array.from(matEl('rncs').selectedOptions,o=>Number(o.value));const mode=matMode();
  if(!ids.length||ids.length>20||(mode==='rnc'&&ids.length!==1)||(mode==='geral'&&ids.length<2)){matEl('mensagem').textContent='Uma RNC: selecione um registro. Geral: selecione de 2 a 20 RNCs.';return;}
  const seq=++matSequence;resetToolAI();matEl('gerar').disabled=true;
  try{
    const result=await api(`/api/ferramentas/matriz?${new URLSearchParams({empresa_id:state.empresaId,contexto:mode,rnc_ids:ids.join(',')})}`);if(seq!==matSequence)return;
    matAccept(result);matEl('mensagem').textContent='Matriz carregada. Clique nos cruzamentos para avaliar. Os dados originais não são alterados.';
  }catch(e){if(seq===matSequence)matEl('mensagem').textContent=e.message;}
  finally{if(seq===matSequence)matEl('gerar').disabled=false;}
}
function matAccept(result){matResult=result;matRows=result.linhas;matColumns=result.colunas;matCells=result.celulas;matId=result.id||null;matRevision=result.revisao||1;matDirty=false;matCloseCell();matEl('titulo').value=result.titulo;matRender();}
function matButton(text,handler){const b=document.createElement('button');b.type='button';b.className='btn';b.textContent=text;b.onclick=handler;return b;}
function matRncNames(ids){return ids.map(id=>matResult.registros.find(r=>r.id===id)?.codigo||String(id)).join(', ');}
function matRender(){
  matEl('editor').classList.remove('hidden');matEl('salvar').classList.toggle('hidden',!isEditor());
  matEl('colunas').replaceChildren();for(const a of matResult.acoes){const o=new Option(`Ação #${a.id} · ${a.rnc_codigo} · ${a.descricao}`,a.id);o.selected=matColumns.includes(a.id);matEl('colunas').add(o);}
  matEl('linha-fontes').replaceChildren();for(const r of matResult.registros){const o=new Option(r.codigo,r.id);o.selected=matResult.registros.length===1;matEl('linha-fontes').add(o);}
  matEl('linhas').replaceChildren();
  for(const row of matRows){
    const card=document.createElement('article');card.className='mat-row-card';const label=document.createElement('label');label.textContent=`Linha #${row.id} · ${matRncNames(row.rnc_ids)}`;
    const name=document.createElement('textarea');name.maxLength=2000;name.rows=2;name.value=row.nome;name.setAttribute('aria-label',`Descrição da linha ${row.id}`);name.oninput=()=>{row.nome=name.value;matChanged();matRenderTable();};
    const situation=document.createElement('select');situation.setAttribute('aria-label','Situação do problema/fator');for(const [v,t] of [['problema','Problema observado'],['hipotese','Hipótese'],['fator_evidenciado','Fator com evidência declarada']])situation.add(new Option(t,v));situation.value=row.situacao;situation.onchange=()=>{row.situacao=situation.value;matChanged();matRenderTable();};
    const evidence=document.createElement('textarea');evidence.maxLength=3000;evidence.rows=2;evidence.value=row.evidencia;evidence.placeholder='Evidência / referência do fator';evidence.setAttribute('aria-label','Evidência do fator');evidence.oninput=()=>{row.evidencia=evidence.value;matChanged();};
    const sources=document.createElement('select');sources.multiple=true;sources.size=3;sources.setAttribute('aria-label','RNCs de origem da linha');for(const r of matResult.registros){const o=new Option(r.codigo,r.id);o.selected=row.rnc_ids.includes(r.id);sources.add(o);}sources.onchange=()=>{row.rnc_ids=Array.from(sources.selectedOptions,o=>Number(o.value));matChanged();matRenderTable();};
    card.append(label,name,situation,evidence,sources,matButton('Remover linha',()=>{if(matRows.length===1){matEl('mensagem').textContent='Mantenha pelo menos uma linha.';return;}if(confirm('Remover a linha e suas avaliações?')){matRows=matRows.filter(l=>l.id!==row.id);matCells=matCells.filter(c=>c.linha_id!==row.id);matCloseCell();matChanged();matRender();}}));matEl('linhas').append(card);
  }
  matEl('origens').replaceChildren();
  for(const r of matResult.registros){const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=`${r.codigo} · origem ${r.issue_codigo} · ${r.status}`;details.append(summary);
    for(const [label,value] of [['Relato',r.fatos.comportamento_observado],['Esperado',r.fatos.comportamento_esperado],['Evidências factuais',r.fatos.evidencias_objetivas],['Observações da investigação',r.observacao.sintomas_condicoes],['Notas de análise',r.investigacao.analise]])if(value){const p=document.createElement('p');p.textContent=`${label}: ${value}`;details.append(p);}
    for(const h of r.investigacao.hipoteses||[]){const p=document.createElement('p');p.textContent=`Hipótese da investigação: ${h.descricao||''}`;details.append(p);}
    for(const a of matResult.acoes.filter(a=>a.rnc_id===r.id)){const p=document.createElement('p');p.textContent=`Ação #${a.id}: ${a.descricao} · status ${a.status} · prazo ${a.prazo_limite||'não informado'} · Por quê: ${a.por_que||'não informado'} · Como: ${a.como||'não informado'} · Quanto: ${a.quanto||'não informado'}`;details.append(p);}matEl('origens').append(details);
  }
  matRenderTable();
}
function matRenderTable(){
  const host=matEl('tabela');host.replaceChildren();const table=document.createElement('table');table.className='mat-table';const caption=document.createElement('caption');caption.textContent=`${matResult.contexto==='rnc'?'Uma RNC':'Geral — várias RNCs'}: problemas/fatores × ações · ${matResult.registros.map(r=>r.codigo).join(', ')}`;table.append(caption);
  const head=document.createElement('thead'),tr=document.createElement('tr'),corner=document.createElement('th');corner.textContent='Problema / fator e origem';corner.scope='col';tr.append(corner);
  for(const id of matColumns){const a=matResult.acoes.find(a=>a.id===id);const th=document.createElement('th');th.scope='col';th.textContent=`Ação #${id} · ${a.rnc_codigo}`;th.title=a.descricao;tr.append(th);}head.append(tr);table.append(head);
  const body=document.createElement('tbody');let assessed=0;const covered=new Set(),used=new Set(),pendingRows=[];
  for(const row of matRows){const tr=document.createElement('tr'),th=document.createElement('th');th.scope='row';th.textContent=`${row.nome} · ${row.situacao==='hipotese'?'Hipótese':row.situacao==='problema'?'Problema':'Fator com evidência declarada'} · ${matRncNames(row.rnc_ids)}`;tr.append(th);let rowAssessed=0;
    for(const id of matColumns){const cell=matCells.find(c=>c.linha_id===row.id&&c.acao_id===id);const level=cell?.intensidade||'nao_avaliada';if(level!=='nao_avaliada'){assessed++;rowAssessed++;}if(['fraca','media','forte'].includes(level)){covered.add(row.id);used.add(id);}
      const td=document.createElement('td');const button=matButton(matLevels[level],()=>matEditCell(row.id,id));button.className=`btn mat-cell mat-${level}`;button.title=cell?.justificativa||'Clique para avaliar';button.setAttribute('aria-label',`Linha ${row.id}, ação ${id}: ${matLevels[level]}`);td.append(button);tr.append(td);
    }if(rowAssessed<matColumns.length)pendingRows.push(row.id);body.append(tr);
  }table.append(body);host.append(table);
  const noCoverage=matRows.filter(r=>!covered.has(r.id)),confirmed=noCoverage.filter(r=>matColumns.length&&!pendingRows.includes(r.id));
  matEl('resumo').textContent=`${matRows.length} linhas · ${matColumns.length}/${matResult.acoes.length} ações consideradas · ${assessed}/${matRows.length*matColumns.length} cruzamentos avaliados · ${noCoverage.length} linhas sem relação indicada · ${confirmed.length} sem cobertura após avaliação completa.`;
  matEl('alertas').textContent=`${pendingRows.length} linhas ainda têm avaliação pendente; ${matColumns.filter(id=>!used.has(id)).length} ações não têm relação positiva indicada; ${matResult.acoes.length-matColumns.length} ações ficaram fora da matriz. ${matColumns.length?'Nenhuma relação e Não avaliada são situações distintas.':'Não há ações consideradas: inclua um plano na RNC e gere outra fotografia, ou selecione ações disponíveis.'}`;
}
function matAddRow(){
  const name=matEl('nova-linha').value.trim(),ids=Array.from(matEl('linha-fontes').selectedOptions,o=>Number(o.value));
  if(!name||!ids.length||matRows.length>=40){matEl('mensagem').textContent='Descreva a linha, selecione sua origem e respeite o limite de 40 linhas.';return;}
  matRows.push({id:Math.max(0,...matRows.map(l=>l.id))+1,nome:name,rnc_ids:ids,situacao:'hipotese',evidencia:''});matEl('nova-linha').value='';matChanged();matRender();
}
function matEditCell(line,action){
  if(matCellDirty&&!confirm('Descartar a edição do cruzamento atual?'))return;
  matCell={linha_id:line,acao_id:action};const cell=matCells.find(c=>c.linha_id===line&&c.acao_id===action);matCellDirty=false;
  matEl('cell-title').textContent=`Linha: ${matRows.find(l=>l.id===line).nome} × Ação #${action}: ${matResult.acoes.find(a=>a.id===action).descricao}`;
  matEl('intensidade').value=cell?.intensidade||'nao_avaliada';matEl('justificativa').value=cell?.justificativa||'';matEl('evidencia').value=cell?.evidencia||'';matEl('cell-editor').classList.remove('hidden');matEl('intensidade').focus();
}
function matApplyCell(){
  if(!matCell)return;const cell={...matCell,intensidade:matEl('intensidade').value,justificativa:matEl('justificativa').value.trim(),evidencia:matEl('evidencia').value.trim()};
  if(cell.intensidade!=='nao_avaliada'&&!cell.justificativa){matEl('mensagem').textContent='Justifique o cruzamento avaliado.';return;}
  matCells=matCells.filter(c=>c.linha_id!==cell.linha_id||c.acao_id!==cell.acao_id);matCells.push(cell);matCloseCell();matChanged();matRenderTable();
}
async function matOpen(){
  const id=matEl('salvos').value;if(!id)return;if((matDirty||matCellDirty)&&!confirm('Descartar alterações e abrir outra matriz?'))return;
  const seq=++matSequence;resetToolAI();try{const result=await api(`/api/ferramentas/matriz/diagramas/${id}`);if(seq!==matSequence)return;matAccept(result);matEl('mensagem').textContent='Matriz salva aberta: fotografia dos relatos e planos na data de carregamento.';}catch(e){if(seq===matSequence)matEl('mensagem').textContent=e.message;}
}
async function matSubmit(ai){
  if(!matResult)return;if(matCellDirty){matEl('mensagem').textContent='Aplique ou cancele a edição do cruzamento antes de continuar.';return;}
  const seq=matSequence;const body={titulo:matEl('titulo').value,...matResult.consulta_ia,linhas:matRows,colunas:matColumns,celulas:matCells,revisao:matRevision};matEl('salvar').disabled=true;matEl('ia').disabled=true;
  try{const result=await api(ai?'/api/ferramentas/matriz/preparar':`/api/ferramentas/matriz/diagramas${matId?'/'+matId:''}`,{method:ai||!matId?'POST':'PUT',body});if(seq!==matSequence)return;
    if(ai)await openToolAI('matriz',result);else{matResult=result;matId=result.id;matRevision=result.revisao;matDirty=false;matEl('mensagem').textContent=`Matriz salva · revisão ${matRevision}`;await matList(seq);}
  }catch(e){if(seq===matSequence)matEl('mensagem').textContent=e.message;}
  finally{if(seq===matSequence){matEl('salvar').disabled=false;matEl('ia').disabled=false;}}
}
