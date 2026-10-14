let dispersaoSequence=0,dispersaoResult=null;
const dispElement=key=>document.getElementById(`disp-${key}`);
const dispNumber=value=>Number(value).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
function resetDispersao(){
  resetToolAI();dispersaoSequence++;dispersaoResult=null;
  if(typeof Plotly!=='undefined'&&dispElement('grafico'))Plotly.purge('disp-grafico');
  document.getElementById('dispersaoWorkspace').replaceChildren();
}
function dispSelect(key,options,empty='Todos'){
  const el=dispElement(key);el.replaceChildren();if(empty!==null)el.add(new Option(empty,''));
  options.forEach(option=>el.add(new Option(option.rotulo,option.valor)));
}
function buildDispersao(){
  const select=(key,label)=>`<div id="disp-${key}-block"><label for="disp-${key}">${label}</label><select id="disp-${key}" name="${key}"></select></div>`;
  document.getElementById('dispersaoWorkspace').innerHTML=`<form id="disp-form" class="card">
  <fieldset class="pareto-source"><legend>Base da análise</legend><label><input type="radio" name="base" value="issues" checked> Issues</label><label><input type="radio" name="base" value="rncs"> RNCs</label></fieldset>
  <p id="disp-elegibilidade" class="hint"></p><div class="pareto-filters">${select('data_referencia','Data de referência')}
  <div><label for="disp-inicio">De</label><input id="disp-inicio" name="inicio" type="date"></div><div><label for="disp-fim">Até</label><input id="disp-fim" name="fim" type="date"></div>
  ${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([key,label])=>select(key,label)).join('')}
  ${select('eixo_x','Eixo X')}${select('eixo_y','Eixo Y')}${select('unidade','Unidade da quantidade')}${select('moeda','Moeda do prejuízo')}</div>
  <p class="hint">Cada ponto reúne duas medidas do mesmo registro. Valores ausentes ou inválidos são excluídos. Pontos coincidentes podem se sobrepor.</p>
  <div class="pareto-actions"><button id="disp-gerar" type="submit" class="btn primary">Gerar Diagrama de Dispersão</button><button id="disp-limpar" type="button" class="btn">Limpar filtros</button></div></form>
  <p id="disp-mensagem" role="status" aria-live="polite"></p><div id="disp-resultado" class="card hidden"><p id="disp-resumo"></p><p id="disp-correlacao"></p>
  <button id="disp-consultarIA" type="button" class="btn">Consultar IA</button><div id="disp-grafico" aria-label="Diagrama de Dispersão"></div>
  <p class="hint">Correlação não comprova causalidade. Nos exemplos simulados, o prejuízo foi calculado a partir da quantidade e das horas. Clique em um ponto para consultar seu registro.</p>
  <h3 id="disp-registrosTitulo">Registros da análise</h3><button id="disp-todos" type="button" class="btn">Mostrar todos</button>
  <div class="pareto-table-wrap"><table class="pareto-table"><thead><tr><th>Código</th><th>Issue de origem</th><th>Descrição</th><th id="disp-xLabel">X</th><th id="disp-yLabel">Y</th></tr></thead><tbody id="disp-registros"></tbody></table></div></div>`;
  dispElement('form').addEventListener('submit',event=>{event.preventDefault();generateDispersao();});
  document.querySelectorAll('#disp-form [name="base"]').forEach(input=>input.addEventListener('change',()=>loadDispersao(true)));
  dispElement('form').addEventListener('change',event=>{if(event.target.name!=='base'){dispersaoUnits();invalidateDispersao();}});
  dispElement('limpar').addEventListener('click',()=>loadDispersao(true));
  dispElement('todos').addEventListener('click',()=>dispersaoRecords());
  dispElement('consultarIA').addEventListener('click',()=>openToolAI('dispersao',dispersaoResult));
}
function invalidateDispersao(){
  resetToolAI();dispersaoSequence++;dispersaoResult=null;dispElement('resultado').classList.add('hidden');
  dispElement('mensagem').textContent='Filtros alterados. Clique em Gerar Diagrama de Dispersão.';dispElement('gerar').disabled=false;
}
function dispersaoUnits(){
  const axes=[dispElement('eixo_x').value,dispElement('eixo_y').value];
  for(const [key,metric] of [['unidade','quantidade'],['moeda','prejuizo']]){
    const visible=axes.includes(metric);dispElement(`${key}-block`).classList.toggle('hidden',!visible);dispElement(key).disabled=!visible;
  }
}
async function loadDispersao(clear=false){
  resetToolAI();if(!dispElement('form'))buildDispersao();
  const base=document.querySelector('#disp-form [name="base"]:checked').value;
  const sequence=++dispersaoSequence;dispersaoResult=null;
  dispElement('resultado').classList.add('hidden');dispElement('gerar').disabled=true;dispElement('mensagem').textContent='Carregando filtros…';
  if(clear)for(const key of ['inicio','fim'])dispElement(key).value='';
  try{
    const params=new URLSearchParams({base});if(state.empresaId)params.set('empresa_id',state.empresaId);
    const result=await api(`/api/ferramentas/dispersao?${params}`);if(sequence!==dispersaoSequence)return;
    for(const key of Object.keys(paretoDimensions))dispSelect(key,result.opcoes[key]);
    for(const key of ['unidade','moeda'])dispSelect(key,result.opcoes[key],'Selecione');
    for(const key of ['eixo_x','eixo_y'])dispSelect(key,result.medidas,null);
    dispElement('eixo_x').value=base==='rncs'?'quantidade':'idade_dias';dispElement('eixo_y').value=base==='rncs'?'horas':'registro_horas';
    dispSelect('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:base==='issues'?'criado_em':'emitida_em',rotulo:base==='issues'?'Cadastro da Issue':'Emissão da RNC'}],null);
    dispSelect('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados identificados'}],null);
    dispElement('classificacao-block').classList.toggle('hidden',base==='issues');dispElement('classificacao').disabled=base==='issues';
    document.querySelector('label[for="disp-pessoa"]').textContent=base==='issues'?'Autor do registro':'Responsável (ou líder)';
    dispElement('elegibilidade').textContent=base==='issues'?'Issues: somente cadastradas ou em tratamento, sem RNC vinculada. Issues finalizadas ficam fora desta análise.':'RNCs: registros emitidos, conforme os filtros selecionados.';
    dispersaoUnits();dispElement('mensagem').textContent='Selecione duas medidas diferentes e clique em Gerar Diagrama de Dispersão.';
  }catch(error){if(sequence===dispersaoSequence)dispElement('mensagem').textContent=error.message;}
  finally{if(sequence===dispersaoSequence)dispElement('gerar').disabled=false;}
}
async function generateDispersao(){
  resetToolAI();const params=new URLSearchParams();for(const [key,value] of new FormData(dispElement('form')))if(value)params.set(key,value);
  if(state.empresaId)params.set('empresa_id',state.empresaId);
  if(params.get('eixo_x')===params.get('eixo_y')){dispElement('mensagem').textContent='Selecione medidas diferentes para os eixos X e Y.';return;}
  const axes=[params.get('eixo_x'),params.get('eixo_y')];
  if(axes.includes('quantidade')&&!params.has('unidade')||axes.includes('prejuizo')&&!params.has('moeda')){dispElement('mensagem').textContent='Selecione a unidade ou moeda das medidas escolhidas.';return;}
  const sequence=++dispersaoSequence;dispElement('gerar').disabled=true;dispElement('resultado').classList.add('hidden');dispElement('mensagem').textContent='Gerando Diagrama de Dispersão…';
  try{
    const result=await api(`/api/ferramentas/dispersao?${params}`);if(sequence!==dispersaoSequence)return;
    dispersaoResult=result;dispElement('resultado').classList.remove('hidden');dispElement('mensagem').textContent=result.incluidos?'':'Nenhum par de medidas válido para os filtros selecionados.';
    dispElement('resumo').textContent=`${result.selecionados} registros selecionados · ${result.incluidos} pares incluídos · sem par completo: ${result.sem_par} · inválidos: ${result.invalidos} · sem data para o período: ${result.sem_data}.`;
    dispElement('correlacao').textContent=result.correlacao===null?'Correlação de Pearson: não disponível (menos de dois pares ou eixo sem variação).':`Correlação de Pearson (r): ${dispNumber(result.correlacao)} · ${result.incluidos} pares. Correlação não comprova causalidade.`;
    const axisLabel=axis=>`${axis.rotulo} (${axis.unidade})`;
    dispElement('xLabel').textContent=axisLabel(result.eixo_x);dispElement('yLabel').textContent=axisLabel(result.eixo_y);dispersaoRecords();
    if(typeof Plotly==='undefined'){dispElement('mensagem').textContent='Gráfico indisponível. Os pares estão na tabela.';return;}
    const graph=dispElement('grafico'),points=result.pontos;
    await Plotly.newPlot(graph,[{type:'scatter',mode:'markers',x:points.map(p=>p.x),y:points.map(p=>p.y),customdata:points.map(p=>p.id),text:points.map(p=>p.codigo),marker:{color:'#2563eb',size:10,opacity:0.75},hovertemplate:'%{text}<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>'}],
      {height:450,margin:{t:25,b:80,l:80,r:25},xaxis:{title:axisLabel(result.eixo_x),tickformat:'.2f'},yaxis:{title:axisLabel(result.eixo_y),tickformat:'.2f'}},{responsive:true,displaylogo:false});
    if(sequence!==dispersaoSequence)return;
    if(graph.removeAllListeners)graph.removeAllListeners('plotly_click');graph.on('plotly_click',event=>dispersaoRecords(event.points[0].customdata));
  }catch(error){if(sequence===dispersaoSequence)dispElement('mensagem').textContent=error.message;}
  finally{if(sequence===dispersaoSequence)dispElement('gerar').disabled=false;}
}
function dispersaoRecords(id=null){
  if(!dispersaoResult)return;
  const rows=dispersaoResult.registros.filter(r=>id===null||r.id===id);dispElement('registrosTitulo').textContent=`Registros da análise (${rows.length})`;
  dispElement('registros').replaceChildren();
  for(const row of rows){const tr=document.createElement('tr');for(const value of [row.codigo,row.issue_codigo,row.descricao,dispNumber(row.x),dispNumber(row.y)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}dispElement('registros').append(tr);}
}
