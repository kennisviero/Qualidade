let paretoSequence = 0;
let paretoResult = null;
let paretoOptions = null;
const paretoDimensions = {categoria:'Categoria do problema (O que)',impacto:'Impacto',ambiente:'Ambiente',local:'Local',status:'Status',pessoa:'Autor / responsável',envolvidos:'Envolvidos / afetados',classificacao:'Classificação maior/menor'};
const paretoNumber = value => Number(value).toLocaleString('pt-BR', {maximumFractionDigits:2});

function resetPareto() {
  resetToolAI();
  paretoSequence++;
  paretoResult = null;
  paretoOptions = null;
  const workspace = document.getElementById('paretoWorkspace');
  if (typeof Plotly !== 'undefined' && document.getElementById('paretoGrafico')) Plotly.purge('paretoGrafico');
  workspace.replaceChildren();
}

function buildPareto() {
  const select = (key,label) => `<div id="pareto-${key}-block"><label for="pareto-${key}">${label}</label><select id="pareto-${key}" name="${key}"></select></div>`;
  document.getElementById('paretoWorkspace').innerHTML = `<form id="paretoForm" class="card">
    <fieldset class="pareto-source"><legend>Base da análise</legend><label><input type="radio" name="base" value="issues" checked> Issues</label><label><input type="radio" name="base" value="rncs"> RNCs</label></fieldset>
    <p id="paretoElegibilidade" class="hint">Issues: somente cadastradas ou em tratamento, sem RNC vinculada. Issues finalizadas ficam fora desta análise.</p>
    <div class="pareto-filters">${select('data_referencia','Data de referência')}
    <div><label for="pareto-inicio">De</label><input type="date" id="pareto-inicio" name="inicio"></div><div><label for="pareto-fim">Até</label><input type="date" id="pareto-fim" name="fim"></div>
    ${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([k,v])=>select(k,v)).join('')}
    ${select('vinculo','Vínculo com RNC')}${select('agrupar','Agrupar por')}${select('medida','Medida')}${select('unidade','Unidade')}${select('moeda','Moeda')}</div>
    <p class="hint">Categoria usa “O que aconteceu” da Issue; na RNC, os fatos preservados na emissão. Textos iguais são agrupados sem distinguir acentos e maiúsculas. Padronize as descrições para reunir problemas semelhantes.</p>
    <div class="pareto-actions"><button id="paretoGerar" class="btn primary" type="submit">Gerar Pareto</button><button id="paretoLimpar" class="btn" type="button">Limpar filtros</button></div></form>
    <p id="paretoMensagem" role="status" aria-live="polite"></p><div id="paretoResultado" class="card hidden"><p id="paretoResumo"></p><button id="paretoConsultarIA" type="button" class="btn">Consultar IA</button>
    <div id="paretoGrafico" aria-label="Gráfico de Pareto"></div><p class="hint">Clique numa barra ou categoria para consultar os registros. A linha de 80% é uma referência de priorização.</p>
    <div class="pareto-table-wrap"><table class="pareto-table"><thead><tr><th>Categoria</th><th>Contribuição</th><th>%</th><th>% acumulado</th></tr></thead><tbody id="paretoTabela"></tbody></table></div>
    <h3 id="paretoRegistrosTitulo">Registros da análise</h3><button id="paretoTodos" class="btn" type="button">Mostrar todos</button>
    <div class="pareto-table-wrap"><table class="pareto-table"><thead><tr><th>Código</th><th>Issue de origem</th><th>Descrição</th><th>Contribuição</th></tr></thead><tbody id="paretoRegistros"></tbody></table></div></div>`;
  document.getElementById('paretoForm').addEventListener('submit',ev=>{ev.preventDefault();generatePareto();});
  document.querySelectorAll('#paretoForm [name="base"]').forEach(input=>input.addEventListener('change',()=>loadPareto(true)));
  document.getElementById('pareto-medida').addEventListener('change',()=>{paretoMetric();invalidatePareto();});
  document.getElementById('paretoForm').addEventListener('change',ev=>{if(ev.target.name!=='base')invalidatePareto();});
  document.getElementById('paretoLimpar').addEventListener('click',()=>loadPareto(true));
  document.getElementById('paretoTodos').addEventListener('click',()=>renderParetoRecords());
  document.getElementById('paretoConsultarIA').addEventListener('click',()=>openToolAI('pareto',paretoResult));
}

function paretoSelect(key,choices,empty='Todos') {
  const el=document.getElementById(`pareto-${key}`);el.replaceChildren();
  if(empty!==null)el.add(new Option(empty,''));
  choices.forEach(choice=>el.add(new Option(choice.rotulo,choice.valor)));
}
function invalidatePareto() {
  resetToolAI();
  paretoSequence++;
  paretoResult=null;
  document.getElementById('paretoResultado').classList.add('hidden');
  document.getElementById('paretoMensagem').textContent='Filtros alterados. Clique em Gerar Pareto.';
  document.getElementById('paretoGerar').disabled=false;
}
function paretoMetric() {
  const metric=document.getElementById('pareto-medida').value;
  for(const key of ['unidade','moeda']) {
    const visible=metric===(key==='unidade'?'quantidade':'prejuizo');
    document.getElementById(`pareto-${key}-block`).classList.toggle('hidden',!visible);
    document.getElementById(`pareto-${key}`).disabled=!visible;
  }
}
async function loadPareto(clear=false) {
  resetToolAI();
  if(!document.getElementById('paretoForm'))buildPareto();
  const base=document.querySelector('#paretoForm [name="base"]:checked').value;
  const sequence=++paretoSequence;
  paretoResult=null;
  document.getElementById('paretoResultado').classList.add('hidden');
  document.getElementById('paretoMensagem').textContent='Carregando filtros…';
  document.getElementById('paretoGerar').disabled=true;
  if(clear)for(const key of ['inicio','fim'])document.getElementById(`pareto-${key}`).value='';
  try {
    const params=new URLSearchParams({base});
    if(state.empresaId)params.set('empresa_id',state.empresaId);
    const result=await api(`/api/ferramentas/pareto?${params}`);
    if(sequence!==paretoSequence)return;
    paretoOptions=result.opcoes;
    for(const key of Object.keys(paretoDimensions))paretoSelect(key,result.opcoes[key]);
    for(const key of ['unidade','moeda'])paretoSelect(key,result.opcoes[key], 'Selecione');
    paretoSelect('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados identificados'}],null);
    paretoSelect('vinculo',[{valor:'sem',rotulo:'Somente Issues sem RNC'}],null);
    paretoSelect('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:base==='rncs'?'emitida_em':'criado_em',rotulo:base==='rncs'?'Emissão da RNC':'Cadastro da Issue'}],null);
    paretoSelect('agrupar',Object.entries(paretoDimensions).filter(([key])=>base==='rncs'||key!=='classificacao').map(([valor,rotulo])=>({valor,rotulo})),null);
    paretoSelect('medida',(base==='rncs'?[['registros','Número de RNCs'],['quantidade','Quantidade afetada'],['horas','Horas perdidas'],['prejuizo','Prejuízo financeiro']]:[['registros','Número de Issues']]).map(([valor,rotulo])=>({valor,rotulo})),null);
    document.querySelector('label[for="pareto-pessoa"]').textContent=base==='rncs'?'Responsável (ou líder)':'Autor do registro';
    document.getElementById('paretoElegibilidade').textContent=base==='issues'
      ?'Issues: somente cadastradas ou em tratamento, sem RNC vinculada. Issues finalizadas ficam fora desta análise.'
      :'RNCs: análise dos registros emitidos, conforme os filtros selecionados.';
    for(const [key,visible] of [['classificacao',base==='rncs'],['vinculo',false]]) {
      document.getElementById(`pareto-${key}-block`).classList.toggle('hidden',!visible);
      document.getElementById(`pareto-${key}`).disabled=!visible;
    }
    paretoMetric();
    document.getElementById('paretoMensagem').textContent='Escolha os filtros e clique em Gerar Pareto.';
  } catch(error) {if(sequence===paretoSequence)document.getElementById('paretoMensagem').textContent=error.message;}
  finally {if(sequence===paretoSequence)document.getElementById('paretoGerar').disabled=false;}
}
async function generatePareto() {
  resetToolAI();
  const form=document.getElementById('paretoForm');
  const params=new URLSearchParams();
  for(const [key,value] of new FormData(form))if(value)params.set(key,value);
  if(state.empresaId)params.set('empresa_id',state.empresaId);
  const metric=params.get('medida');
  if(metric==='quantidade'&&!params.has('unidade') || metric==='prejuizo'&&!params.has('moeda')) {
    document.getElementById('paretoMensagem').textContent='Selecione uma unidade ou moeda para somar valores comparáveis.';return;
  }
  const sequence=++paretoSequence;
  document.getElementById('paretoGerar').disabled=true;
  document.getElementById('paretoResultado').classList.add('hidden');
  document.getElementById('paretoMensagem').textContent='Gerando Pareto…';
  try {
    const result=await api(`/api/ferramentas/pareto?${params}`);
    if(sequence!==paretoSequence)return;
    paretoResult=result;
    const items=result.dados.itens;
    document.getElementById('paretoMensagem').textContent=items.length?'':'Nenhum registro com contribuição disponível para os filtros selecionados.';
    document.getElementById('paretoResultado').classList.remove('hidden');
    document.getElementById('paretoResumo').textContent=`${result.selecionados} registros selecionados · ${result.incluidos} incluídos · total: ${paretoNumber(result.dados.total)} ${result.unidade}. Sem medida válida: ${result.sem_medida}; sem data para o período: ${result.sem_data}.`;
    const tbody=document.getElementById('paretoTabela');tbody.replaceChildren();
    items.forEach(item=>{
      const tr=document.createElement('tr');
      const td=document.createElement('td');const button=document.createElement('button');button.className='pareto-category';button.type='button';button.textContent=item.rotulo;button.onclick=()=>renderParetoRecords(item.chave,item.rotulo);td.append(button);tr.append(td);
      for(const value of [item.frequencia,item.percentual,item.acumulado]){const cell=document.createElement('td');cell.textContent=paretoNumber(value);tr.append(cell);}tbody.append(tr);
    });
    renderParetoRecords();
    if(typeof Plotly==='undefined') {document.getElementById('paretoMensagem').textContent='Gráfico indisponível. Os resultados estão nas tabelas.';return;}
    const graph=document.getElementById('paretoGrafico');
    await Plotly.newPlot(graph,[{type:'bar',name:result.unidade,x:items.map((_,i)=>i),y:items.map(x=>x.frequencia),customdata:items.map(x=>x.chave),text:items.map(x=>x.rotulo),hovertemplate:'%{text}<br>%{y}<extra></extra>',marker:{color:'#2563eb'}},
      {type:'scatter',mode:'lines+markers',name:'% acumulado',x:items.map((_,i)=>i),y:items.map(x=>x.acumulado),yaxis:'y2',line:{color:'#d97706'},hovertemplate:'%{y:.2f}%<extra></extra>'}],
      {margin:{t:35,r:65,b:130,l:65},height:450,xaxis:{tickmode:'array',tickvals:items.map((_,i)=>i),ticktext:items.map(x=>x.rotulo),tickangle:-30,automargin:true},yaxis:{title:result.unidade,rangemode:'tozero'},yaxis2:{title:'% acumulado',overlaying:'y',side:'right',range:[0,100]},legend:{orientation:'h',y:1.15},shapes:[{type:'line',xref:'paper',x0:0,x1:1,yref:'y2',y0:80,y1:80,line:{color:'#94a3b8',dash:'dot'}}]}, {responsive:true,displaylogo:false});
    if(sequence!==paretoSequence)return;
    if(graph.removeAllListeners)graph.removeAllListeners('plotly_click');
    graph.on('plotly_click',event=>{const point=event.points[0];if(point.curveNumber===0)renderParetoRecords(point.customdata,items[point.pointNumber].rotulo);});
  } catch(error) {if(sequence===paretoSequence)document.getElementById('paretoMensagem').textContent=error.message;}
  finally {if(sequence===paretoSequence)document.getElementById('paretoGerar').disabled=false;}
}
function renderParetoRecords(group=null,label='') {
  if(!paretoResult)return;
  const rows=paretoResult.registros.filter(r=>group===null||r.grupo===group);
  document.getElementById('paretoRegistrosTitulo').textContent=`${label||'Registros da análise'} (${rows.length})`;
  const tbody=document.getElementById('paretoRegistros');tbody.replaceChildren();
  rows.forEach(row=>{
    const tr=document.createElement('tr');
    for(const value of [row.codigo,row.issue_codigo,row.descricao,paretoNumber(row.contribuicao)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}
    tbody.append(tr);
  });
}
