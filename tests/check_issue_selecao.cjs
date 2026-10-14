const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.style={};this.children=[];this.dataset={};this.value='';this.checked=false;this.disabled=false;this.selected=false;this.listeners={};this.classList={add(){},remove(){},contains:()=>true};}
  append(...items){items.forEach(item=>{item.parent=this;this.children.push(item);});}
  appendChild(item){this.append(item);return item;}
  replaceChildren(...items){this.children=[];this.append(...items);}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(){}
  get selectedOptions(){return this.children.filter(c=>c.selected);}
  matches(selector){
    if(selector==='[data-rnc-field]')return this.dataset.rncField!==undefined;
    if(selector==='[data-candidate-check]:checked')return this.dataset.candidateCheck!==undefined && this.checked;
    if(selector==='[data-candidate-check]')return this.dataset.candidateCheck!==undefined;
    if(selector==='[data-candidate-id]')return this.dataset.candidateId!==undefined;
    const match=selector.match(/^\[data-candidate-id="(\d+)"\]$/);
    if(match)return String(this.dataset.candidateId)===match[1];
    return selector.split(',').includes(this.tag);
  }
  querySelectorAll(selector){return this.children.flatMap(c=>[...(c.matches(selector)?[c]:[]),...c.querySelectorAll(selector)]);}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  closest(selector){let node=this;while(node){if(node.matches(selector))return node;node=node.parent;}return null;}
}
const elements={};
const html=fs.readFileSync('app/static/index.html','utf8');
const script=fs.readFileSync('app/static/js/issue_selecao.js','utf8');
for(const match of html.matchAll(/id="([^"]+)"/g)){assert.ok(!elements[match[1]],'ID duplicado '+match[1]);elements[match[1]]=new Element();}
for(const match of script.matchAll(/selEl\('([^']+)'\)/g))assert.ok(elements[match[1]],'Elemento ausente '+match[1]);
assert.ok(html.indexOf('/static/js/issue_selecao.js')<html.indexOf('/static/js/app.js'));
const requests=[];
elements.selecaoCandidatasBloco.append(Object.assign(new Element('h4'),{}),Object.assign(new Element('p'),{}));
const originalQuery=elements.selecaoCandidatasBloco.querySelector.bind(elements.selecaoCandidatasBloco);
elements.selecaoCandidatasBloco.querySelector=selector=>selector==='.hint' ? elements.selecaoCandidatasBloco.children[1] : originalQuery(selector);
const opened=[];
const candidate={id:11,id_issue:101,codigo_issue:'ISSUE-0101',resumo:'Desvio <script>alert(1)</script>',criticidade_sugerida:'ALTA',
  justificativa:{requisito_violado:'IT-04',fato_e_evidencia:'Inspeção',criterios_ia:'Tríade presente'}};
const analysis={id:1,status:'concluida',candidatas_rnc:[candidate],ultima_geracao:null};
const result={geracao_id:7,status:'concluida',itens:[{candidata_id:11,codigo_issue:'ISSUE-0101',codigo_rnc:'RNC-2026-001',status:'gerada'}]};
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag),createTextNode:text=>Object.assign(new Element('text'),{textContent:text})},
  Option:function(text,value){return Object.assign(new Element('option'),{textContent:text,value:String(value)});},
  URLSearchParams,Set,clearTimeout,setTimeout,crypto:{getRandomValues:array=>require('crypto').webcrypto.getRandomValues(array)},confirm:()=>true,
  state:{empresaId:4,issueView:'selecao'},isEditor:()=>true,issueApiUrl:path=>path,
  ISSUE_STATUS_LABELS:{cadastrada:'Cadastrada',em_tratamento:'Em tratamento'},loadIssueList:async()=>{},loadIssueKanban:async()=>{},
  showIssueView:async(view)=>opened.push(view),selectIssue:async(id)=>opened.push(id),
  api:async(path,options={})=>{requests.push({path,options});
    if(path==='/api/issues/selecao/manual/103/gerar')return {rnc_codigo:'RNC-2026-002'};
    if(path.endsWith('/validacao'))return {permitida:!path.includes('/104/'),pendencias:['suporte factual'],entrada_hash:'a'.repeat(64),justificativa:{requisito_violado:'Padrão',fato_e_evidencia:'Medição',criterios_ia:'Campos preenchidos'}};
    if(path.endsWith('/geracoes'))return result;
    if(path==='/api/issues/selecao/analises/1')return analysis;
    if(path.startsWith('/api/issues/selecao/elegiveis'))return {itens:[],total:0};
    if(path.endsWith('/acessos-llm'))return [{id:1,nome:'GeracaoRNC',provedor:'OpenRouter',modelo:'teste'}];
    if(path.endsWith('/usuarios'))return [];
    if(path.endsWith('/prompt'))return {prompt:'Prompt padrão'};
    if(path==='/api/issues/selecao/analises' && options.method==='POST')return analysis;
    if(path==='/api/issues/selecao/analises')return [];
    throw new Error('Route inattendue '+path);
  }});
vm.runInContext(script,context);
assert.equal(context.issueRegisteredTime(new Date(Date.now()-2*86400000).toISOString()),'Cadastrada há 2 dias');
assert.equal(context.issueRegisteredTime(new Date(Date.now()-86400000).toISOString()),'Cadastrada há 1 dia');
assert.equal(context.issueRegisteredTime(new Date().toISOString()),'Cadastrada hoje');
assert.equal(context.issueRegisteredTime(null),'Data de cadastro não informada');
(async()=>{
  assert.match(html,/<form id="selecaoAnaliseForm" novalidate>/);
  await context.loadIssueSelecao();
  assert.equal(elements.selecaoAnalisar.disabled,true);
  vm.runInContext("selecaoState.mode='ia'",context);
  assert.equal(elements.selecaoAcesso.value,'1');
  vm.runInContext('for(let id=101;id<119;id++)selecaoState.selected.add(id);',context);
  context.selecaoCount();assert.equal(elements.selecaoAnalisar.disabled,false);
  elements.selecaoPrompt.value='Prompt ajustado pelo usuário';
  await context.selecaoAnalyze({preventDefault(){}});
  const submitted=requests.find(r=>r.options.method==='POST' && r.path.endsWith('/analises'));
  assert.equal(submitted.options.body.prompt,'Prompt ajustado pelo usuário');
  assert.equal(submitted.options.body.issue_ids.length,18);
  assert.match(submitted.options.headers['Idempotency-Key'],/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.match(elements.selecaoMensagem.textContent,/concluída/);
  assert.equal(elements.selecaoProgresso.children.length,3);
  assert.ok(elements.selecaoProgresso.children.every(step=>step.textContent.startsWith('✓')));
  assert.match(context.selecaoProgress('aguardando','processando'),/Aguardando a IA processar/);
  assert.match(context.selecaoProgress('recebendo','processando'),/Recebendo dados da IA/);
  elements.selecaoPrompt.value=' ';
  await context.selecaoAnalyze({preventDefault(){}});
  assert.match(elements.selecaoMensagem.textContent,/Informe o prompt/);
  elements.selecaoAcesso.value='';elements.selecaoPrompt.value='Prompt preenchido';
  context.selecaoCount();assert.equal(elements.selecaoAnalisar.disabled,false);
  await context.selecaoAnalyze({preventDefault(){}});
  assert.match(elements.selecaoMensagem.textContent,/Selecione o acesso LLM/);
  vm.runInContext('resetIssueSelecao(); selecaoState.mode="ia"; selecaoState.users=[{id:1,nome:"A"},{id:2,nome:"B"}];',context);
  context.renderSelecaoCandidates([candidate]);
  const card=elements.selecaoCandidatas.children[0], check=card.querySelector('[data-candidate-check]');
  assert.equal(check.checked,false);
  const code=card.querySelector('a');assert.equal(code.textContent,'ISSUE-0101');
  await code.ondblclick({preventDefault(){}});
  assert.deepEqual(opened,['capturar',101]);assert.equal(check.checked,false);
  const fields=card.querySelectorAll('[data-rnc-field]');assert.equal(fields.length,13);assert.ok(fields.every(f=>f.disabled && !f.required));
  assert.ok(fields.every(f=>f.dataset.rncField!=='origem_gatilho'));
  check.checked=true;check.onchange();assert.ok(fields.every(f=>!f.disabled));
  for(const field of fields){
    field.value=field.dataset.rncField.endsWith('_id')?'1':field.type==='date'?'2026-10-20':'preenchido';
    if(field.dataset.rncField==='criticidade')field.value='menor';
    if(field.multiple)field.children.forEach(o=>o.selected=true);
  }
  vm.runInContext('selecaoState.analysis={id:1}; selecaoState.selected.add(101);',context);
  await context.selecaoGenerate({preventDefault(){}});
  const request=requests.find(r=>r.path.endsWith('/geracoes'));
  assert.equal(request.options.body.itens.length,1);
  assert.equal(request.options.body.itens[0].dados_rnc.criticidade,'menor');
  assert.equal(request.options.body.itens[0].dados_rnc.equipe_investigacao.length,2);
  assert.ok(check.disabled && !check.checked);
  assert.equal(elements.selecaoResultado.children.length,1);
  context.resetIssueSelecao();assert.equal(vm.runInContext('selecaoState.selected.size',context),0);
  context.renderSelecaoCandidates([]);assert.match(elements.selecaoCandidatas.textContent,/Nenhuma Issue/);
  vm.runInContext('selecaoState.mode="manual"; selecaoState.items=[{id:102,codigo:"ISSUE-0102",resumo:"Teste manual"}];',context);
  context.selecaoCount();assert.equal(elements.selecaoAnalisar.disabled,true);
  const requestCount=requests.length;
  await context.selecaoAnalyze({preventDefault(){}});
  assert.equal(requests.length,requestCount,'Modo manual bloqueia chamadas à IA');
  await context.selecaoManualMove(102,true);
  assert.equal(vm.runInContext('selecaoState.candidates.length',context),1);
  assert.equal(elements.selecaoCandidatas.children[0].draggable,true);
  await context.selecaoManualMove(102,false);
  assert.equal(vm.runInContext('selecaoState.candidates.length',context),0);
  vm.runInContext('selecaoState.items=[{id:103,codigo:"ISSUE-0103",resumo:"Emissão manual"}];',context);
  await context.selecaoManualMove(103,true);
  const manualCheck=elements.selecaoCandidatas.children[0].querySelector('[data-candidate-check]');
  manualCheck.checked=true;manualCheck.onchange();
  await context.selecaoGenerate({preventDefault(){}});
  assert.ok(requests.some(r=>r.path==='/api/issues/selecao/manual/103/gerar' && r.options.method==='POST' && r.options.body.confirmar && r.options.body.entrada_hash==='a'.repeat(64)));
  assert.ok(manualCheck.disabled && !manualCheck.checked);
  vm.runInContext('selecaoState.items=[{id:104,codigo:"ISSUE-0104",resumo:"Sem evidência"}];',context);
  await context.selecaoManualMove(104,true);
  assert.equal(vm.runInContext('selecaoState.candidates.length',context),1,'Issue sem evidência não entra');
  assert.match(elements.selecaoMensagem.textContent,/bloqueada/);
  await elements.selecaoModoIA.onchange();
  assert.equal(vm.runInContext('selecaoState.mode',context),'ia');
  assert.equal(vm.runInContext('selecaoState.candidates.length',context),0);
  const dragCard=new Element();context.selecaoDrag(dragCard,{id:102},'right');assert.equal(dragCard.draggable,false);
  console.log('OK: IDs, ordem dos scripts, checklist, campos obrigatórios, aprovação explícita, geração e reset de empresa.');
})().catch(e=>{console.error(e);process.exitCode=1;});
