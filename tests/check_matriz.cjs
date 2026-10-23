const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
class Element{
 constructor(){this.children=[];this.value='';this.disabled=false;this.classes=new Set();this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)};}
 append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this.value='';}add(o){this.children.push(o);if(this.children.length===1)this.value=o.value;}
 setAttribute(k,v){this[k]=v;}focus(){}get options(){return this.children;}get selectedOptions(){return this.children.filter(o=>o.selected);}
 set innerHTML(v){this.html=v;for(const m of v.matchAll(/id="([^"]+)"/g))elements[m[1]]=new Element();}
}
elements.matrizWorkspace=new Element();const calls=[],ai=[],radio={value:'rnc'};let editor=true,pending=null;
const result={titulo:'Matriz QA',contexto:'rnc',registros:[{id:1,codigo:'RNC-1',issue_codigo:'ISSUE-1',status:'emitida',fatos:{comportamento_observado:'<script>Relato</script>'},observacao:{},investigacao:{}}],acoes:[{id:10,rnc_id:1,rnc_codigo:'RNC-1',descricao:'Ação original'}],linhas:[{id:1,nome:'<script>Problema</script>',rnc_ids:[1],situacao:'problema',evidencia:''}],colunas:[10],celulas:[],consulta_ia:{snapshot:'{}',assinatura:'x'}};
const opcoes={};for(const key of ['categoria','impacto','ambiente','local','status','pessoa','envolvidos','classificacao'])opcoes[key]=[];
const context=vm.createContext({console,URLSearchParams,state:{empresaId:4},isEditor:()=>editor,resetToolAI(){},openToolAI:async(...a)=>ai.push(a),confirm:()=>true,
 document:{getElementById:id=>elements[id],createElement:()=>new Element(),querySelector:()=>radio,querySelectorAll:()=>[]},
 Option:function(text,value){this.textContent=text;this.value=String(value);},FormData:function(){return [['contexto',radio.value],['inicio',''],['fim','']];},
 api:async(path,opts)=>{calls.push({path,opts});if(pending)return pending(path,opts);if(path.includes('/fontes'))return {registros:[{id:1,codigo:'RNC-1',descricao:'Relato'}],opcoes,sem_data:0};if(path.endsWith('/preparar'))return {...result,...opts.body};if(path.includes('/diagramas'))return opts?{...result,...opts.body,id:3,revisao:opts.method==='PUT'?2:1}:[];return structuredClone(result);}
});
vm.runInContext(fs.readFileSync('app/static/js/pareto.js','utf8').split('function resetPareto()')[0],context);
vm.runInContext(fs.readFileSync('app/static/js/matriz.js','utf8'),context);
const el=id=>elements['mat-'+id];
(async()=>{
 const html=fs.readFileSync('app/static/index.html','utf8');assert.match(html,/data-section="matriz">6-Diagrama de Matriz/);
 await context.loadMatriz();assert.ok(!calls[0].path.includes('inicio='));assert.ok(!calls[0].path.includes('fim='));
 assert.match(elements.matrizWorkspace.html,/não avaliada não significa ausência de relação/);
 el('tab-ajuda').onclick();assert.equal(el('tab-ajuda')['aria-selected'],'true');el('tab-quadro').onclick();
 radio.value='geral';el('rncs').children[0].selected=true;await context.matGenerate();assert.match(el('mensagem').textContent,/Geral/);assert.equal(calls.filter(c=>c.path.includes('rnc_ids=')).length,0);
 radio.value='rnc';await context.matGenerate();assert.match(el('resumo').textContent,/0\/1 cruzamentos avaliados/);
 assert.match(el('tabela').children[0].children[2].children[0].children[0].textContent,/<script>Problema/);
 context.matEditCell(1,10);el('intensidade').value='nenhuma';el('justificativa').value=' ';context.matApplyCell();assert.match(el('mensagem').textContent,/Justifique/);
 el('justificativa').value='Sem relação neste contexto';context.matApplyCell();assert.match(el('resumo').textContent,/1\/1 cruzamentos avaliados/);assert.match(el('resumo').textContent,/1 linhas sem relação/);
 await context.matSubmit(false);assert.match(el('mensagem').textContent,/revisão 1/);await context.matSubmit(false);assert.match(el('mensagem').textContent,/revisão 2/);assert.equal(calls.filter(c=>c.opts?.method==='PUT').length,1);
 context.matEditCell(1,10);el('justificativa').oninput();const count=calls.length;await context.matSubmit(true);assert.equal(calls.length,count);assert.match(el('mensagem').textContent,/Aplique ou cancele/);
 context.matCloseCell();await context.matSubmit(true);assert.equal(ai[0][0],'matriz');assert.equal(calls.at(-1).opts.body.celulas[0].intensidade,'nenhuma');
 const loaded=calls.length;await context.loadMatriz();assert.equal(calls.length,loaded);
 editor=false;context.matRender();assert.ok(el('salvar').classes.has('hidden'));
 let resolve;pending=()=>new Promise(r=>resolve=r);const loading=context.matGenerate();context.matChanged();assert.equal(el('gerar').disabled,false);assert.equal(el('filtrar').disabled,false);resolve({...result,titulo:'Resposta obsoleta'});await loading;assert.notEqual(el('titulo').value,'Resposta obsoleta');
 context.resetMatriz();assert.equal(elements.matrizWorkspace.children.length,0);
 console.log('OK: contextos, abas, filtros sem datas vazias, células, justificativas, pendente versus nenhuma, texto seguro, salvar/revisão, IA explícita, visualizador e respostas obsoletas.');
})().catch(e=>{console.error(e);process.exitCode=1;});
