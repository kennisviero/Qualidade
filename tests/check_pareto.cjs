const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Element {
  constructor(){this.children=[];this.value='';this.disabled=false;this.classes=new Set();this.listeners={};this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)};}
  append(...v){this.children.push(...v);} replaceChildren(...v){this.children=v;this.value='';}
  add(v){this.children.push(v);if(this.children.length===1)this.value=v.value;}
  addEventListener(k,v){this.listeners[k]=v;} on(k,v){this.listeners[k]=v;} removeAllListeners(k){delete this.listeners[k];}
  set innerHTML(html){this.html=html;for(const match of html.matchAll(/id="([^"]+)"/g))elements[match[1]]=new Element();}
}
const elements={paretoWorkspace:new Element()},radio={value:'issues'},requests=[],plots=[];
const source=fs.readFileSync('app/static/js/pareto.js','utf8'),html=fs.readFileSync('app/static/index.html','utf8');
assert.match(html,/aria-label="Submenu de Ferramentas"/);assert.match(html,/data-section="pareto">1-Pareto/);
const choices={};for(const k of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao','unidade','moeda'])choices[k]=[{valor:k==='unidade'?'pecas':k==='moeda'?'brl':'etiqueta',rotulo:k==='unidade'?'peças':k==='moeda'?'BRL':'Etiqueta'}];
const result={opcoes:choices,base:'issues',selecionados:2,incluidos:2,sem_medida:0,sem_data:0,unidade:'registros',dados:{total:2,itens:[{rotulo:'<img src=x>',chave:'etiqueta',frequencia:2,percentual:100,acumulado:100}]},registros:[{codigo:'ISSUE-0001',issue_codigo:'ISSUE-0001',descricao:'<script>conteúdo</script>',contribuicao:1,grupo:'etiqueta'},{codigo:'ISSUE-0002',issue_codigo:'ISSUE-0002',descricao:'Outra ocorrência',contribuicao:1,grupo:'etiqueta'}]};
let handler=async()=>result;
const context=vm.createContext({URLSearchParams,console,state:{empresaId:4},document:{getElementById:id=>elements[id],querySelector:q=>q.includes('[name="base"]')?radio:new Element(),querySelectorAll:()=>[],createElement:()=>new Element()},
  Option:function(rotulo,valor){this.textContent=rotulo;this.value=valor;},
  FormData:function(){this[Symbol.iterator]=function*(){yield ['base',radio.value];for(const [id,el] of Object.entries(elements))if(id.startsWith('pareto-')&&!id.endsWith('-block')&&!el.disabled)yield [id.slice(7),el.value];};},
  api:async path=>{requests.push(path);return handler(path);},Plotly:{purge(){},newPlot:async(...args)=>plots.push(args)}});
context.resetToolAI=()=>{};context.openToolAI=()=>{};
vm.runInContext(source,context);
(async()=>{
  await context.loadPareto();assert.match(requests[0],/empresa_id=4/);
  assert.equal(elements['pareto-vinculo'].disabled,true);assert.equal(elements['pareto-classificacao'].disabled,true);
  assert.ok(elements['pareto-vinculo-block'].classes.has('hidden'));
  assert.match(elements.paretoElegibilidade.textContent,/sem RNC vinculada/);
  assert.equal(elements['pareto-medida'].children.length,1);
  await context.generatePareto();assert.equal(plots.length,1);assert.equal(plots[0][1][1].y[0],100);
  assert.equal(elements.paretoTabela.children[0].children[0].children[0].textContent,'<img src=x>');
  assert.equal(elements.paretoRegistros.children[0].children[2].textContent,'<script>conteúdo</script>');
  context.renderParetoRecords('etiqueta','Etiqueta');assert.match(elements.paretoRegistrosTitulo.textContent,/Etiqueta \(2\)/);
  radio.value='rncs';await context.loadPareto(true);
  assert.equal(elements['pareto-vinculo'].disabled,true);assert.equal(elements['pareto-classificacao'].disabled,false);
  assert.equal(elements['pareto-medida'].children.length,4);
  elements['pareto-medida'].value='quantidade';context.paretoMetric();
  const count=requests.length;await context.generatePareto();assert.equal(requests.length,count);assert.match(elements.paretoMensagem.textContent,/unidade ou moeda/);
  elements['pareto-unidade'].value='pecas';await context.generatePareto();assert.match(requests.at(-1),/unidade=pecas/);assert.doesNotMatch(requests.at(-1),/vinculo=/);
  let resolve;handler=()=>new Promise(r=>resolve=r);const pending=context.generatePareto();context.invalidatePareto();resolve(result);await pending;
  assert.ok(elements.paretoResultado.classes.has('hidden'),'Resposta atrasada não deve reapresentar resultados obsoletos');
  context.resetPareto();assert.equal(elements.paretoWorkspace.children.length,0);
  console.log('OK: menu, seleção Issues/RNCs, filtros, unidades, gráfico/tabelas, conteúdo seguro e resposta obsoleta.');
})().catch(error=>{console.error(error);process.exitCode=1;});
