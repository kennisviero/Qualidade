let histogramaSequence=0;
let histogramaResult=null;
const histogramNumber=value=>Number(value).toLocaleString('pt-BR',{maximumFractionDigits:6});
const histogramStatistic=value=>Number(value).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
const histElement=key=>document.getElementById(`hist-${key}`);
function resetHistograma(){
  resetToolAI();
  histogramaSequence++;histogramaResult=null;
  if(typeof Plotly!=='undefined'&&histElement('grafico'))Plotly.purge('hist-grafico');
  document.getElementById('histogramaWorkspace').replaceChildren();
}
function histSelect(key,options,empty='Todos'){
  const el=histElement(key);el.replaceChildren();
  if(empty!==null)el.add(new Option(empty,''));
  options.forEach(option=>el.add(new Option(option.rotulo,option.valor)));
}
function buildHistograma(){
  const select=(key,label)=>`<div id="hist-${key}-block"><label for="hist-${key}">${label}</label><select id="hist-${key}" name="${key}"></select></div>`;
  document.getElementById('histogramaWorkspace').innerHTML=`<form id="hist-form" class="card">
    <fieldset class="pareto-source"><legend>Base da análise</legend><label><input type="radio" name="base" value="issues" checked> Issues</label><label><input type="radio" name="base" value="rncs"> RNCs</label></fieldset>
    <p id="hist-elegibilidade" class="hint"></p><div class="pareto-filters">
    ${select('data_referencia','Data de referência')}<div><label for="hist-inicio">De</label><input id="hist-inicio" name="inicio" type="date"></div><div><label for="hist-fim">Até</label><input id="hist-fim" name="fim" type="date"></div>
    ${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([key,label])=>select(key,label)).join('')}
    ${select('medida','Medida numérica')}${select('unidade','Unidade')}${select('moeda','Moeda')}
    <div><label for="hist-classes">Número de intervalos</label><input id="hist-classes" name="classes" type="number" min="1" max="50" step="1" placeholder="Automático"></div></div>
    <p class="hint">Cada registro fornece uma medida. Campos ausentes e tempos negativos são excluídos e informados no resultado. Intervalos automáticos ou de 1 a 50; valores iguais formam um único intervalo.</p>
    <div class="pareto-actions"><button id="hist-gerar" type="submit" class="btn primary">Gerar Histograma</button><button id="hist-limpar" type="button" class="btn">Limpar filtros</button></div></form>
    <p id="hist-mensagem" role="status" aria-live="polite"></p><div id="hist-resultado" class="card hidden"><p id="hist-resumo"></p><p id="hist-estatisticas"></p><button id="hist-consultarIA" type="button" class="btn">Consultar IA</button><div id="hist-grafico" aria-label="Histograma"></div>
    <p class="hint">Intervalos em ordem numérica, com início incluído e fim excluído; o último inclui o valor máximo. Clique numa barra ou intervalo para consultar seus registros.</p>
    <div class="pareto-table-wrap"><table class="pareto-table"><thead><tr><th>Intervalo</th><th>Frequência</th><th>%</th></tr></thead><tbody id="hist-tabela"></tbody></table></div>
    <h3 id="hist-registrosTitulo">Registros da análise</h3><button id="hist-todos" type="button" class="btn">Mostrar todos</button>
    <div class="pareto-table-wrap"><table class="pareto-table"><thead><tr><th>Código</th><th>Issue de origem</th><th>Descrição</th><th>Valor</th></tr></thead><tbody id="hist-registros"></tbody></table></div></div>`;
  histElement('form').addEventListener('submit',event=>{event.preventDefault();generateHistograma();});
  document.querySelectorAll('#hist-form [name="base"]').forEach(input=>input.addEventListener('change',()=>loadHistograma(true)));
  histElement('form').addEventListener('change',event=>{if(event.target.name!=='base'){histogramMetric();invalidateHistograma();}});
  histElement('limpar').addEventListener('click',()=>loadHistograma(true));
  histElement('todos').addEventListener('click',()=>histogramRecords());
  histElement('consultarIA').addEventListener('click',()=>openToolAI('histograma',histogramaResult));
}
function invalidateHistograma(){
  resetToolAI();
  histogramaSequence++;histogramaResult=null;histElement('resultado').classList.add('hidden');
  histElement('mensagem').textContent='Filtros alterados. Clique em Gerar Histograma.';histElement('gerar').disabled=false;
}
function histogramMetric(){
  for(const key of ['unidade','moeda']){
    const visible=histElement('medida').value===(key==='unidade'?'quantidade':'prejuizo');
    histElement(`${key}-block`).classList.toggle('hidden',!visible);histElement(key).disabled=!visible;
  }
}
async function loadHistograma(clear=false){
  resetToolAI();
  if(!histElement('form'))buildHistograma();
  const base=document.querySelector('#hist-form [name="base"]:checked').value;
  const sequence=++histogramaSequence;histogramaResult=null;
  histElement('resultado').classList.add('hidden');histElement('gerar').disabled=true;histElement('mensagem').textContent='Carregando filtros…';
  if(clear)for(const key of ['inicio','fim','classes'])histElement(key).value='';
  try{
    const params=new URLSearchParams({base});if(state.empresaId)params.set('empresa_id',state.empresaId);
    const result=await api(`/api/ferramentas/histograma?${params}`);if(sequence!==histogramaSequence)return;
    for(const key of Object.keys(paretoDimensions))histSelect(key,result.opcoes[key]);
    for(const key of ['unidade','moeda'])histSelect(key,result.opcoes[key],'Selecione');
    histSelect('medida',result.medidas,null);
    histSelect('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:base==='issues'?'criado_em':'emitida_em',rotulo:base==='issues'?'Cadastro da Issue':'Emissão da RNC'}],null);
    histSelect('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados identificados'}],null);
    histElement('classificacao-block').classList.toggle('hidden',base==='issues');histElement('classificacao').disabled=base==='issues';
    document.querySelector('label[for="hist-pessoa"]').textContent=base==='issues'?'Autor do registro':'Responsável (ou líder)';
    histElement('elegibilidade').textContent=base==='issues'?'Issues: somente cadastradas ou em tratamento, sem RNC vinculada. Issues finalizadas ficam fora desta análise.':'RNCs: registros emitidos, conforme os filtros selecionados.';
    histogramMetric();histElement('mensagem').textContent='Escolha os filtros e a medida, depois clique em Gerar Histograma.';
  }catch(error){if(sequence===histogramaSequence)histElement('mensagem').textContent=error.message;}
  finally{if(sequence===histogramaSequence)histElement('gerar').disabled=false;}
}
function histogramInterval(item){return `[${histogramNumber(item.inicio)}; ${histogramNumber(item.fim)}${item.inclui_fim?']':')'}`;}
async function generateHistograma(){
  resetToolAI();
  const params=new URLSearchParams();for(const [key,value] of new FormData(histElement('form')))if(value)params.set(key,value);
  if(state.empresaId)params.set('empresa_id',state.empresaId);
  if(params.get('medida')==='quantidade'&&!params.has('unidade')||params.get('medida')==='prejuizo'&&!params.has('moeda')){histElement('mensagem').textContent='Selecione uma unidade ou moeda para comparar medidas compatíveis.';return;}
  if(params.has('classes')&&(!Number.isInteger(Number(params.get('classes')))||Number(params.get('classes'))<1||Number(params.get('classes'))>50)){histElement('mensagem').textContent='Informe de 1 a 50 intervalos ou deixe vazio para cálculo automático.';return;}
  const sequence=++histogramaSequence;histElement('gerar').disabled=true;histElement('resultado').classList.add('hidden');histElement('mensagem').textContent='Gerando Histograma…';
  try{
    const result=await api(`/api/ferramentas/histograma?${params}`);if(sequence!==histogramaSequence)return;
    histogramaResult=result;histElement('resultado').classList.remove('hidden');
    histElement('mensagem').textContent=result.incluidos?'':'Nenhuma medida válida para os filtros selecionados.';
    histElement('resumo').textContent=`${result.rotulo} (${result.unidade}) · ${result.selecionados} registros selecionados · ${result.incluidos} incluídos · sem medida: ${result.sem_medida} · inválidos: ${result.invalidos} · sem data para o período: ${result.sem_data}.`;
    const stats=result.estatisticas;
    histElement('estatisticas').textContent=stats.n?`Mínimo: ${histogramStatistic(stats.minimo)} · máximo: ${histogramStatistic(stats.maximo)} · média: ${histogramStatistic(stats.media)} · mediana: ${histogramStatistic(stats.mediana)} · desvio padrão amostral: ${stats.desvio_padrao===null?'não disponível':histogramStatistic(stats.desvio_padrao)}.`:'';
    histElement('tabela').replaceChildren();
    for(const item of result.intervalos){
      const tr=document.createElement('tr'),td=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='pareto-category';button.textContent=histogramInterval(item);button.onclick=()=>histogramRecords(item.indice);td.append(button);tr.append(td);
      for(const value of [item.frequencia,item.percentual]){const cell=document.createElement('td');cell.textContent=histogramNumber(value);tr.append(cell);}histElement('tabela').append(tr);
    }
    histogramRecords();
    if(typeof Plotly==='undefined'){histElement('mensagem').textContent='Gráfico indisponível. Os resultados estão nas tabelas.';return;}
    const graph=histElement('grafico'),bins=result.intervalos;
    await Plotly.newPlot(graph,[{type:'bar',x:bins.map(b=>(b.inicio+b.fim)/2),y:bins.map(b=>b.frequencia),width:bins.map(b=>b.fim-b.inicio),customdata:bins.map(histogramInterval),marker:{color:'#2563eb',line:{color:'white',width:1}},hovertemplate:'%{customdata}<br>%{y} registros<extra></extra>'}],
      {height:430,margin:{t:25,b:70,l:65,r:25},bargap:0,xaxis:{title:`${result.rotulo} (${result.unidade})`},yaxis:{title:'Frequência de registros',rangemode:'tozero',dtick:1}}, {responsive:true,displaylogo:false});
    if(sequence!==histogramaSequence)return;
    if(graph.removeAllListeners)graph.removeAllListeners('plotly_click');graph.on('plotly_click',event=>histogramRecords(event.points[0].pointNumber));
  }catch(error){if(sequence===histogramaSequence)histElement('mensagem').textContent=error.message;}
  finally{if(sequence===histogramaSequence)histElement('gerar').disabled=false;}
}
function histogramRecords(index=null){
  if(!histogramaResult)return;
  const rows=histogramaResult.registros.filter(r=>index===null||r.intervalo===index);
  histElement('registrosTitulo').textContent=`${index===null?'Registros da análise':histogramInterval(histogramaResult.intervalos[index])} (${rows.length})`;
  histElement('registros').replaceChildren();
  for(const row of rows){const tr=document.createElement('tr');for(const value of [row.codigo,row.issue_codigo,row.descricao,histogramNumber(row.valor)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}histElement('registros').append(tr);}
}
