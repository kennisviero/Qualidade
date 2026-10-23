const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
class Element{
  constructor(){this.children=[];this.value='';this.disabled=false;this.style={};this.classes=new Set();this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)};}
  append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this.value='';}add(o){this.children.push(o);if(this.children.length===1)this.value=o.value;}
  setAttribute(k,v){this[k]=v;}focus(){}get selectedOptions(){return this.children.filter(o=>o.selected);}
  set innerHTML(v){for(const m of v.matchAll(/id="([^"]+)"/g))elements[m[1]]=new Element();}
}
elements.relacoesWorkspace=new Element();const calls=[],ai=[],radio={value:'issues'};
const result={base:'issues',registros:[{id:1,codigo:'ISSUE-1',descricao:'<script>relato</script>'},{id:2,codigo:'ISSUE-2',descricao:'Outro'}],fatores:[],relacoes:[],sem_data:0,opcoes:{},consulta_ia:{snapshot:JSON.stringify({parametros:{}}),assinatura:'x'}};
for(const key of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao'])result.opcoes[key]=[];
let pending=null;
const context=vm.createContext({console,URLSearchParams,state:{empresaId:4},isEditor:()=>true,resetToolAI(){},openToolAI:async(...a)=>ai.push(a),confirm:()=>true,prompt:()=> 'Renomeado',
 document:{getElementById:id=>elements[id],createElement:()=>new Element(),createElementNS:()=>new Element(),querySelector:()=>radio,querySelectorAll:()=>[]},
 Option:function(text,value){this.textContent=text;this.value=value;},FormData:function(){return [['base',radio.value],['inicio',''],['fim','']];},
 api:async(path,opts)=>{calls.push({path,opts});if(pending)return pending(path,opts);if(path.endsWith('/preparar'))return {...result,...opts.body};if(path.includes('/diagramas'))return opts?{...result,...opts.body,id:3,revisao:1}:[];return {...result,base:radio.value};}
});
vm.runInContext(fs.readFileSync('app/static/js/pareto.js','utf8').split('function resetPareto()')[0],context);
vm.runInContext(fs.readFileSync('app/static/js/relacoes.js','utf8'),context);
const el=id=>elements['rel-'+id];
function setEdge(from,to,type='hipotese',reason='Verificar influência',evidence=''){
  for(const [key,value] of Object.entries({origem:from,destino:to,tipo:type,justificativa:reason,evidencia:evidence}))el(key).value=String(value);
  context.relAddEdge();
}
(async()=>{
  const html=fs.readFileSync('app/static/index.html','utf8');assert.match(html,/data-section="relacoes">5-Diagrama de Relações/);
  const ids=Array.from(html.matchAll(/id="([^"]+)"/g),m=>m[1]);assert.equal(ids.length,new Set(ids).size);
  await context.loadRelacoes();assert.match(calls[0].path,/empresa_id=4/);
  el('tab-ajuda').onclick();assert.equal(el('tab-ajuda')['aria-selected'],'true');el('tab-quadro').onclick();
  await context.relLoadCards();assert.ok(!calls.at(-1).path.includes('inicio='));assert.ok(!calls.at(-1).path.includes('fim='));
  assert.match(el('registros').children[0].children[0].textContent,/<script>relato/);
  el('novo').value='<script>Fator A</script>';context.relAddFactor();el('novo').value='Fator B';context.relAddFactor();
  assert.equal(el('fatores').children.length,2);assert.equal(el('fatores').children[0].children[0].textContent,'<script>Fator A</script>');
  setEdge(1,1);assert.match(el('mensagem').textContent,/diferentes/);
  setEdge(1,2,'evidenciada');assert.match(el('mensagem').textContent,/evidência/);
  setEdge(1,2);assert.equal(el('setas').children.length,1);assert.match(el('fatores').children[0].children[1].textContent,/Saídas: 1/);
  setEdge(1,2);assert.match(el('mensagem').textContent,/Já existe/);
  setEdge(2,1,'evidenciada','Verificar retorno','Referência ISSUE-2');assert.equal(el('setas').children.length,2);
  const svg=el('grafico').children[0];assert.equal(svg.role,'img');assert.ok(svg.children.some(c=>c['stroke-dasharray']==='7 5'));assert.ok(svg.children.some(c=>c['marker-end']==='url(#rel-arrow-evidenciada)'));
  await context.relSubmit(true);assert.equal(ai[0][0],'relacoes');assert.equal(calls.at(-1).opts.body.relacoes.length,2);
  await context.relSubmit(false);assert.equal(calls.find(c=>c.path.endsWith('/diagramas')&&c.opts).opts.method,'POST');
  const count=calls.length;await context.loadRelacoes();assert.equal(calls.length,count);
  el('setas').children[0].children[3].onclick();assert.equal(el('incluir-seta').textContent,'Atualizar relação');setEdge(1,2,'evidenciada','Revisado','Log 1');assert.match(el('setas').children[0].children[1].textContent,/Revisado/);
  el('fatores').children[0].children[4].onclick();assert.equal(el('setas').children.length,0);assert.equal(el('fatores').children.length,1);
  let resolve;pending=()=>new Promise(r=>resolve=r);const loading=context.relLoadCards();context.relChanged();resolve(result);await loading;assert.equal(el('fatores').children.length,1);
  pending=null;radio.value='rncs';await context.loadRelacoes(true);assert.equal(el('classificacao').disabled,false);
  context.resetRelacoes();assert.equal(elements.relacoesWorkspace.children.length,0);
  console.log('OK: abas, fontes, filtros sem datas vazias, fatores, setas, SVG seguro, ciclos, validação, edição, salvamento, IA e respostas obsoletas.');
})().catch(e=>{console.error(e);process.exitCode=1;});
