const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Element{
  constructor(){this.children=[];this.value='';this.disabled=false;this.classes=new Set();this.listeners={};this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)};}
  append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this.value='';}add(v){this.children.push(v);if(this.children.length===1)this.value=v.value;}
  addEventListener(k,v){this.listeners[k]=v;}on(k,v){this.listeners[k]=v;}removeAllListeners(k){delete this.listeners[k];}
  set innerHTML(value){for(const match of value.matchAll(/id="([^"]+)"/g))elements[match[1]]=new Element();}
}
const html=fs.readFileSync('app/static/index.html','utf8');
assert.match(html,/data-section="pareto">1-Pareto/);assert.match(html,/data-section="histograma">2-Histograma/);
assert.match(fs.readFileSync('app/static/js/pareto.js','utf8'),/querySelector\('#paretoForm \[name="base"\]:checked'\)/);
const elements={histogramaWorkspace:new Element()},radio={value:'issues'},requests=[],plots=[];
const options={};for(const key of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao','unidade','moeda'])options[key]=[{valor:key==='unidade'?'pecas':key==='moeda'?'brl':'teste',rotulo:'Teste'}];
const result={base:'issues',opcoes:options,medidas:[{valor:'idade_dias',rotulo:'Tempo desde cadastro'}],rotulo:'Idade',unidade:'dias',selecionados:2,incluidos:2,sem_medida:0,invalidos:0,sem_data:0,
  intervalos:[{indice:0,inicio:0,fim:1,frequencia:1,percentual:50,inclui_fim:false},{indice:1,inicio:1,fim:2,frequencia:1,percentual:50,inclui_fim:true}],
  estatisticas:{n:2,minimo:0,maximo:2,media:1,mediana:1,desvio_padrao:1.414},registros:[{codigo:'ISSUE-0001',issue_codigo:'ISSUE-0001',descricao:'<script>seguro</script>',valor:0,intervalo:0},{codigo:'ISSUE-0002',issue_codigo:'ISSUE-0002',descricao:'Outro',valor:2,intervalo:1}]};
let handler=async()=>result;
const context=vm.createContext({URLSearchParams,state:{empresaId:4},console,document:{getElementById:id=>elements[id],createElement:()=>new Element(),querySelector:q=>{if(q.includes('[name="base"]')){assert.match(q,/#hist-form/);return radio;}return new Element();},querySelectorAll:()=>[]},
  Option:function(text,value){this.textContent=text;this.value=value;},FormData:function(){this[Symbol.iterator]=function*(){yield ['base',radio.value];for(const [id,el]of Object.entries(elements))if(id.startsWith('hist-')&&!id.endsWith('-block')&&el.value&&!el.disabled)yield [id.slice(5),el.value];};},
  api:async path=>{requests.push(path);return handler(path);},Plotly:{purge(){},newPlot:async(...args)=>plots.push(args)}});
context.resetToolAI=()=>{};context.openToolAI=()=>{};
vm.runInContext(fs.readFileSync('app/static/js/pareto.js','utf8').split('function resetPareto()')[0],context);
vm.runInContext(fs.readFileSync('app/static/js/histograma.js','utf8'),context);
(async()=>{
  await context.loadHistograma();assert.match(requests[0],/empresa_id=4/);assert.match(elements['hist-elegibilidade'].textContent,/sem RNC/);
  assert.equal(elements['hist-classificacao'].disabled,true);
  await context.generateHistograma();assert.equal(plots[0][1].length,1);assert.deepEqual(Array.from(plots[0][1][0].y),[1,1]);
  assert.equal(elements['hist-registros'].children[0].children[2].textContent,'<script>seguro</script>');
  context.histogramRecords(1);assert.equal(elements['hist-registros'].children.length,1);assert.equal(elements['hist-registros'].children[0].children[0].textContent,'ISSUE-0002');
  elements['hist-classes'].value='51';let before=requests.length;await context.generateHistograma();assert.equal(requests.length,before);assert.match(elements['hist-mensagem'].textContent,/1 a 50/);elements['hist-classes'].value='';
  radio.value='rncs';result.medidas=[{valor:'idade_dias',rotulo:'Idade'},{valor:'quantidade',rotulo:'Quantidade'}];await context.loadHistograma(true);assert.equal(elements['hist-classificacao'].disabled,false);
  elements['hist-medida'].value='quantidade';context.histogramMetric();before=requests.length;await context.generateHistograma();assert.equal(requests.length,before);assert.match(elements['hist-mensagem'].textContent,/unidade ou moeda/);
  elements['hist-unidade'].value='pecas';await context.generateHistograma();assert.match(requests.at(-1),/unidade=pecas/);
  let resolve;handler=()=>new Promise(r=>resolve=r);const pending=context.generateHistograma();context.invalidateHistograma();resolve(result);await pending;assert.ok(elements['hist-resultado'].classes.has('hidden'));
  context.resetHistograma();assert.equal(elements.histogramaWorkspace.children.length,0);
  console.log('OK: menus numerados, bases independentes, filtros, medidas, intervalos, gráfico, detalhamento seguro e respostas obsoletas.');
})().catch(error=>{console.error(error);process.exitCode=1;});
