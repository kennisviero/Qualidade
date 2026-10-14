const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={dispersaoWorkspace:null};
class Element{
  constructor(){this.children=[];this.value='';this.disabled=false;this.classes=new Set();this.listeners={};this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)};}
  append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this.value='';}add(v){this.children.push(v);if(this.children.length===1)this.value=v.value;}
  addEventListener(k,v){this.listeners[k]=v;}on(k,v){this.listeners[k]=v;}removeAllListeners(k){delete this.listeners[k];}
  set innerHTML(value){for(const match of value.matchAll(/id="([^"]+)"/g))elements[match[1]]=new Element();}
}
elements.dispersaoWorkspace=new Element();const radio={value:'issues'},requests=[],plots=[],ai=[];
const options={};for(const key of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao','unidade','moeda'])options[key]=[{valor:key==='unidade'?'pecas':key==='moeda'?'brl':'teste',rotulo:'Teste'}];
const points=[{id:1,codigo:'ISSUE-1',issue_codigo:'ISSUE-1',descricao:'<script>seguro</script>',x:1,y:2},{id:2,codigo:'ISSUE-2',issue_codigo:'ISSUE-2',descricao:'Outro',x:2,y:4}];
const result={opcoes:options,medidas:[{valor:'idade_dias',rotulo:'Idade'},{valor:'registro_horas',rotulo:'Registro'},{valor:'quantidade',rotulo:'Quantidade'},{valor:'horas',rotulo:'Horas'}],eixo_x:{rotulo:'X',unidade:'dias'},eixo_y:{rotulo:'Y',unidade:'horas'},pontos:points,registros:points,correlacao:1,selecionados:2,incluidos:2,sem_par:0,invalidos:0,sem_data:0};
let handler=async()=>result;
const context=vm.createContext({console,URLSearchParams,state:{empresaId:4},resetToolAI(){},openToolAI:(...args)=>ai.push(args),document:{getElementById:id=>elements[id],createElement:()=>new Element(),querySelector:q=>{if(q.includes('[name="base"]')){assert.match(q,/#disp-form/);return radio;}return new Element();},querySelectorAll:()=>[]},
  Option:function(text,value){this.textContent=text;this.value=value;},FormData:function(){this[Symbol.iterator]=function*(){yield ['base',radio.value];for(const [id,el]of Object.entries(elements))if(id.startsWith('disp-')&&!id.endsWith('-block')&&el.value&&!el.disabled)yield [id.slice(5),el.value];};},
  api:async path=>{requests.push(path);return handler(path);},Plotly:{purge(){},newPlot:async(...args)=>plots.push(args)}});
assert.match(fs.readFileSync('app/static/index.html','utf8'),/data-section="dispersao">3-Diagrama de Dispersão/);
vm.runInContext(fs.readFileSync('app/static/js/pareto.js','utf8').split('function resetPareto()')[0],context);
vm.runInContext(fs.readFileSync('app/static/js/dispersao.js','utf8'),context);
(async()=>{
  await context.loadDispersao();assert.match(requests[0],/empresa_id=4/);assert.match(elements['disp-elegibilidade'].textContent,/sem RNC/);
  await context.generateDispersao();assert.equal(plots[0][1][0].mode,'markers');assert.match(elements['disp-correlacao'].textContent,/1,00/);
  assert.equal(elements['disp-registros'].children[0].children[2].textContent,'<script>seguro</script>');
  context.dispersaoRecords(2);assert.equal(elements['disp-registros'].children.length,1);
  elements['disp-consultarIA'].listeners.click();assert.equal(ai[0][0],'dispersao');assert.equal(ai[0][1],result);
  elements['disp-eixo_y'].value='idade_dias';let before=requests.length;await context.generateDispersao();assert.equal(requests.length,before);assert.match(elements['disp-mensagem'].textContent,/diferentes/);
  radio.value='rncs';await context.loadDispersao(true);assert.equal(elements['disp-eixo_x'].value,'quantidade');assert.equal(elements['disp-classificacao'].disabled,false);
  before=requests.length;await context.generateDispersao();assert.equal(requests.length,before);assert.match(elements['disp-mensagem'].textContent,/unidade ou moeda/);
  elements['disp-unidade'].value='pecas';await context.generateDispersao();assert.match(requests.at(-1),/unidade=pecas/);
  let resolve;handler=()=>new Promise(r=>resolve=r);const pending=context.generateDispersao();context.invalidateDispersao();resolve(result);await pending;assert.ok(elements['disp-resultado'].classes.has('hidden'));
  context.resetDispersao();assert.equal(elements.dispersaoWorkspace.children.length,0);
  console.log('OK: menu, bases, eixos, filtros, pares, correlação, detalhamento seguro, consulta IA e respostas obsoletas.');
})().catch(error=>{console.error(error);process.exitCode=1;});
