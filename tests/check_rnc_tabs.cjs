const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.style={};this.children=[];this.value='';this.dataset={};this.listeners={};this.readOnly=false;this.disabled=false;this.multiple=false;this.selected=false;this.classes=new Set();this.classList={add:name=>this.classes.add(name),remove:name=>this.classes.delete(name),toggle:(name,on)=>on?this.classes.add(name):this.classes.delete(name)};}
  append(...children){children.forEach(child=>{child.parent=this;this.children.push(child);});}
  appendChild(child){this.append(child);}
  replaceChildren(...children){this.children=children;}
  setAttribute(){}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(child=>child!==this);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  set innerHTML(value){this.children=[];this.html=value;}
  get innerHTML(){return this.html||'';}
  querySelectorAll(){return this.children.flatMap(child=>[...(child.dataset.field?[child]:[]),...child.querySelectorAll()]);}
  get selectedOptions(){return this.children.filter(child=>child.selected);}
}
const target=new Element(),select=new Element();select.value='6';
const flatten=node=>[node,...node.children.flatMap(flatten)];
const requests=[];
const item={id:6,rnc_id:1,rnc_empresa_id:4,rnc_codigo:'RNC-2026-001',codigo:'ISSUE-0005',rnc_status:'emitida',
  rnc_emitida_em:'2026-10-11T10:00:00Z',rnc_fatos_snapshot_origem:'emissao',comportamento_observado:'Fato preservado',
  rnc_investigacao_json:{},rnc_plano_aprovador_id:2,acoes:[],pendencias:[]};
const ctx=vm.createContext({document:{createElement:tag=>new Element(tag),getElementById:()=>select},
  Option:function(text,id){const e=new Element('option');e.textContent=text;e.value=String(id);return e;},
  state:{empresaId:4,user:{id:1}},isEditor:()=>true,rncRecords:[item],KANBAN_LABELS:{},loadIssueKanban:async()=>{},
  api:async(path,options)=>{if(path==='/api/usuarios')return [{id:1,nome:'A',empresa_id:4},{id:2,nome:'B',empresa_id:4},{id:3,nome:'Outro',empresa_id:5}];requests.push({path,options});const updated={...item};for(const [key,value] of Object.entries(options.body))updated['rnc_'+key]=value;return updated;}});
vm.runInContext(fs.readFileSync('app/static/js/rncs.js','utf8'),ctx);
(async()=>{
  await ctx.renderRncTabs(target,item);
  let all=flatten(target);
  assert.deepEqual(all.filter(e=>e.className==='rnc-tab').map(e=>e.textContent),['1. Registro','2. Contenção','3. Investigação','4. Plano de Ação','5. Pendências']);
  const factual=all.find(e=>e.dataset.field==='comportamento_observado');assert.ok(factual.readOnly);assert.equal(factual.value,'Fato preservado');
  const emitente=all.find(e=>e.dataset.field==='emitente_id');assert.equal(emitente.children.length,3);emitente.value='2';
  const impact=all.find(e=>e.dataset.field==='impacto'),environment=all.find(e=>e.dataset.field==='ambiente');
  assert.equal(impact.tag,'select');assert.equal(environment.tag,'select');
  impact.value='alto';environment.value='homologacao';
  await all.find(e=>e.textContent==='Salvar registro').onclick();
  assert.equal(requests[0].options.body.emitente_id,2);assert.ok(!('comportamento_observado' in requests[0].options.body));
  assert.equal(requests[0].options.body.impacto,'alto');assert.equal(requests[0].options.body.ambiente,'homologacao');
  assert.ok(flatten(target).find(e=>e.textContent==='Aprovar plano').disabled);
  await ctx.renderRncTabs(target,item,'investigacao');all=flatten(target);
  const methods=all.find(e=>e.dataset.field==='metodologias');assert.ok(methods.multiple);
  methods.children[0].selected=true;methods.children[1].selected=true;
  assert.ok(!all.some(e=>['porques_texto','causa_raiz'].includes(e.dataset.field)));
  all.find(e=>e.dataset.field==='analise_texto').value='Falha de revisão';
  all.find(e=>e.dataset.field==='observacao_frequencia').value='3 ocorrências por turno';
  all.find(e=>e.dataset.field==='observacao_quantidade_afetada').value='12';
  all.find(e=>e.dataset.field==='observacao_horas_perdidas').value='2.5';
  all.find(e=>e.textContent==='Adicionar hipótese').onclick();all=flatten(target);
  all.find(e=>e.dataset.field==='hipotese_0_descricao').value='Limite de memória';
  all.find(e=>e.textContent==='Adicionar teste').onclick();all=flatten(target);
  all.find(e=>e.dataset.field==='teste_0_0_procedimento').value='Importar 12 MB';
  all.find(e=>e.dataset.field==='teste_0_0_responsavel_id').value='2';
  all.find(e=>e.dataset.field==='teste_0_0_conclusao').value='confirmada';
  await all.filter(e=>e.textContent==='Salvar registro')[2].onclick();
  assert.equal(requests[1].options.body.investigacao_json.analise,'Falha de revisão');
  assert.deepEqual(Array.from(requests[1].options.body.metodologias),['5_porques','ishikawa']);
  assert.ok(!('porques' in requests[1].options.body.investigacao_json));
  assert.equal(requests[1].options.body.observacao.frequencia,'3 ocorrências por turno');
  assert.equal(requests[1].options.body.observacao.quantidade_afetada,12);
  assert.equal(requests[1].options.body.observacao.horas_perdidas,2.5);
  assert.equal(requests[1].options.body.investigacao_json.hipoteses[0].testes[0].responsavel_id,2);
  assert.equal(requests[1].options.body.investigacao_json.hipoteses[0].testes[0].conclusao,'confirmada');
  const uploads=[];
  ctx.FormData=class {constructor(){this.entries=[];}append(key,value){this.entries.push([key,value]);}};
  ctx.fetch=async(path,options)=>{uploads.push({path,options});return {ok:true,json:async()=>({id:42,nome:'teste.pdf',tamanho:100,carregado_em:'2026-10-11T10:00:00Z'})};};
  all=flatten(target);const files=all.find(e=>e.type==='file');files.files=[{name:'teste.pdf'}];
  const draft=all.find(e=>e.dataset.field==='analise_texto');draft.value='Rascunho de análise';
  await all.find(e=>e.textContent==='Carregar evidências').onclick();
  assert.equal(uploads[0].path,'/api/rncs/1/evidencias');
  assert.equal(uploads[0].options.body.entries[0][0],'file');
  assert.equal(draft.value,'Rascunho de análise');
  assert.ok(flatten(target).some(e=>e.tag==='a'&&e.textContent==='teste.pdf'));
  const oldApi=ctx.api;let deleted=false;
  ctx.api=async(path,options)=>{if(options?.method==='DELETE'){assert.equal(path,'/api/rncs/1/evidencias/42');deleted=true;return null;}return oldApi(path,options);};
  ctx.confirm=()=>false;await flatten(target).find(e=>e.textContent==='Excluir').onclick();assert.equal(deleted,false);
  ctx.confirm=()=>true;await flatten(target).find(e=>e.textContent==='Excluir').onclick();assert.ok(deleted);
  assert.ok(!flatten(target).some(e=>e.tag==='a'&&e.textContent==='teste.pdf'));assert.equal(draft.value,'Rascunho de análise');ctx.api=oldApi;
  assert.ok(!('porques_texto' in requests[1].options.body));
  all=flatten(target);all.find(e=>e.dataset.field==='plano_aprovador_id').value='2';
  await all.filter(e=>e.textContent==='Salvar registro')[3].onclick();
  assert.equal(requests[2].options.body.plano_aprovador_id,2);
  assert.ok(!('descricao' in requests[2].options.body));
  const persisted=[];
  ctx.api=async(path,options)=>{if(path==='/api/usuarios')return [{id:1,nome:'A',empresa_id:4},{id:2,nome:'B',empresa_id:4}];
    if(path.includes('/acoes')){if(options.method==='POST')persisted.push({...options.body,id:persisted.length+1,rnc_id:1,status:'backlog'});else Object.assign(persisted.find(row=>row.id===Number(path.split('/').pop())),options.body);return {...item,acoes:persisted};}return item;};
  await ctx.renderRncTabs(target,item,'plano');all=flatten(target);
  const addLine=all.find(e=>e.textContent==='Adicionar linha');addLine.onclick();addLine.onclick();
  const table=flatten(target).find(e=>e.tag==='table');assert.equal(table.children.find(e=>e.tag==='thead').children[0].children.length,10);
  const rows=table.children.find(e=>e.tag==='tbody').children;assert.equal(rows.length,2);
  const first=flatten(rows[0]),second=flatten(rows[1]);
  first.find(e=>e.dataset.taskField==='descricao').value='Treinar equipe';
  first.find(e=>e.dataset.taskField==='por_que').value='Eliminar falha';
  first.find(e=>e.dataset.taskField==='responsavel_id').value='2';
  second.find(e=>e.dataset.taskField==='descricao').value='Outro rascunho';
  await first.find(e=>e.textContent==='Salvar linha').onclick();
  assert.equal(persisted.length,1);assert.equal(persisted[0].por_que,'Eliminar falha');assert.equal(persisted[0].responsavel_id,2);
  assert.equal(second.find(e=>e.dataset.taskField==='descricao').value,'Outro rascunho');
  first.find(e=>e.dataset.taskField==='descricao').value='Treinar equipe revisado';
  await first.find(e=>e.tag==='button').onclick();assert.equal(persisted.length,1);assert.equal(persisted[0].descricao,'Treinar equipe revisado');
  ctx.isEditor=()=>false;await ctx.renderRncTabs(target,item);all=flatten(target);
  assert.ok(all.filter(e=>e.dataset.field&&!e.readOnly).every(e=>e.disabled));
  ctx.isEditor=()=>true;
  ctx.KANBAN_LABELS={backlog:'Backlog',iniciada:'Início',em_andamento:'Em andamento',em_revisao:'Revisão',finalizada:'Finalizado'};
  ctx.KANBAN_COLS=Object.keys(ctx.KANBAN_LABELS);ctx.escapeHtml=value=>String(value||'');
  const cards=[{id:101,rnc_id:1,issue_id:6,status:'backlog',codigo:'ISSUE-0005',rnc_codigo:'RNC-2026-001'},
    {id:102,rnc_id:null,issue_id:9,status:'backlog',codigo:'ISSUE-0009',descricao:'Tarefa sem RNC'}];
  ctx.rncRecords=[{...item,acoes:cards.map(card=>({...card}))}];
  const issueBoard=new Element(),rncBoard=new Element();issueBoard.id='issueKanban';rncBoard.id='rncKanban';
  ctx.document.getElementById=id=>id==='issueKanban'?issueBoard:id==='rncKanban'?rncBoard:select;
  ctx.document.querySelector=()=>flatten(target).find(e=>e.dataset.rncKanbanStatus);
  ctx.document.querySelectorAll=()=>flatten(target).filter(e=>e.dataset.rncTaskStatus!==undefined);
  ctx.api=async(path,options)=>{if(path==='/api/usuarios')return [{id:1,nome:'A',empresa_id:4}];if(options?.method==='PUT'){cards[0].status=options.body.status;return cards[0];}return cards;};
  ctx.issueApiUrl=path=>path;
  const source=fs.readFileSync('app/static/js/app.js','utf8');
  vm.runInContext(source.slice(source.indexOf('async function loadIssueKanban()'),source.indexOf('let issueTreeSelectedPath')),ctx);
  await ctx.renderRncTabs(target,{...item,acoes:cards});
  await ctx.loadIssueKanban();
  assert.equal(rncBoard.children[0].children.length,2);assert.equal(issueBoard.children[0].children.length,3);
  assert.ok(!rncBoard.children[0].children[1].innerHTML.includes('kc-sub'));
  assert.ok(issueBoard.children[0].children[1].innerHTML.includes('kc-sub'));
  let status=ctx.document.querySelector();assert.equal(status.textContent,'Status no Kanban: Backlog');
  const unsaved=flatten(target).find(e=>e.dataset.field==='enquadramento_normativo');unsaved.value='Rascunho sem salvar';
  await rncBoard.children.find(e=>e.dataset.col==='iniciada').listeners.drop({preventDefault(){},dataTransfer:{getData:()=> '101'}});
  assert.equal(status.textContent,'Status no Kanban: Início');assert.equal(unsaved.value,'Rascunho sem salvar');
  assert.equal(flatten(target).find(e=>e.dataset.rncTaskStatus==='101').textContent,'Início');
  assert.equal(issueBoard.children.find(e=>e.dataset.col==='iniciada').children.length,2);
  assert.equal(ctx.rncRecords[0].acoes[0].status,'iniciada');
  assert.equal(ctx.rncKanbanLabel([{status:'backlog'},{status:'iniciada'}]),'Backlog (1) · Início (1)');
  console.log('OK: abas RNC, usuários da empresa, fatos readonly, salvamento, investigação, aprovador e visualizador.');
})().catch(error=>{console.error(error);process.exitCode=1;});
