const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
class Element{
  constructor(){this.children=[];this.value='';this.disabled=false;this.classes=new Set();this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)};}
  append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;this.value='';}add(o){this.children.push(o);if(this.children.length===1)this.value=o.value;}
  setAttribute(k,v){this[k]=v;}
  set innerHTML(v){for(const m of v.matchAll(/id="([^"]+)"/g))elements[m[1]]=new Element();}
}
elements.afinidadesWorkspace=new Element();
const radio={value:'issues'},calls=[],ai=[];
const result={base:'issues',registros:[{id:1,codigo:'ISSUE-1',descricao:'<script>texto seguro</script>'},{id:2,codigo:'ISSUE-2',descricao:'Outro relato'}],sem_data:0,opcoes:{},consulta_ia:{snapshot:JSON.stringify({parametros:{}}),assinatura:'x'}};
for(const k of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao'])result.opcoes[k]=[];
const context=vm.createContext({console,URLSearchParams,state:{empresaId:4},isEditor:()=>true,resetToolAI(){},openToolAI:async(...args)=>ai.push(args),confirm:()=>true,prompt:()=> 'Renomeado',
  document:{getElementById:id=>elements[id],createElement:()=>new Element(),querySelector:()=>radio,querySelectorAll:()=>[]},
  Option:function(t,v){this.textContent=t;this.value=v;},FormData:function(){return [['base',radio.value],['inicio',''],['fim',''],['categoria','']];},
  api:async(path,opts)=>{calls.push({path,opts});if(path.includes('/preparar'))return result;if(path.includes('/diagramas'))return opts?{...result,id:3,revisao:1,grupos:opts.body.grupos}:[];return result;}
});
vm.runInContext(fs.readFileSync('app/static/js/pareto.js','utf8').split('function resetPareto()')[0],context);
vm.runInContext(fs.readFileSync('app/static/js/afinidades.js','utf8'),context);
(async()=>{
  await context.loadAfinidades();assert.match(calls[0].path,/empresa_id=4/);
  elements['afin-tab-ajuda'].onclick();assert.equal(elements['afin-tab-ajuda']['aria-selected'],'true');assert.ok(elements['afin-quadro'].classes.has('hidden'));
  elements['afin-tab-quadro'].onclick();await context.afinLoadCards();
  const loaded=new URL(calls.at(-1).path,'http://localhost');
  assert.equal(loaded.searchParams.has('inicio'),false);assert.equal(loaded.searchParams.has('fim'),false);
  const board=elements['afin-board'];assert.equal(board.children.length,1);
  assert.equal(board.children[0].children[1].children[1].textContent,'<script>texto seguro</script>');
  elements['afin-novo'].value='Instruções';elements['afin-adicionar'].onclick();assert.equal(board.children.length,2);
  let select=board.children[0].children[1].children[3].children[0];select.value='0';select.onchange();
  assert.match(elements['afin-resumo'].textContent,/1 sem grupo/);
  await context.afinSubmit(true);assert.equal(ai[0][0],'afinidades');assert.deepEqual(Array.from(calls.at(-1).opts.body.grupos[0].registros),[1]);
  await context.afinSubmit(false);assert.equal(calls.find(c=>c.path.endsWith('/diagramas')&&c.opts).opts.method,'POST');
  const count=calls.length;await context.loadAfinidades();assert.equal(calls.length,count); // navegar preserva o quadro
  board.children[1].children[2].onclick();assert.equal(board.children.length,1);assert.match(elements['afin-resumo'].textContent,/2 sem grupo/);
  context.resetAfinidades();assert.equal(elements.afinidadesWorkspace.children.length,0);
  console.log('OK: abas, filtros, texto seguro, grupos, movimentação, salvar, consulta IA e preservação ao navegar.');
})().catch(e=>{console.error(e);process.exitCode=1;});
