const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Element {
  constructor(){this.children=[];this.value='';this.attributes={};this.listeners={};this.classes=new Set();this.classList={add:c=>this.classes.add(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)};}
  append(...items){this.children.push(...items);}
  appendChild(item){this.append(item);}
  replaceChildren(...items){this.children=items;}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this.attributes[name]=value;}
  getAttribute(name){return this.attributes[name];}
}
const source=fs.readFileSync('app/static/js/app.js','utf8');
const html=fs.readFileSync('app/static/index.html','utf8');
const elements={};for(const m of html.matchAll(/id="([^"]+)"/g)){assert.ok(!elements[m[1]]);elements[m[1]]=new Element();}
const layout=new Element(),stored=new Map(),requests=[],opened=[];
let records=[{id:1,rnc_id:null},{id:2,rnc_id:7,rnc_codigo:'RNC-2026-001',codigo:'ISSUE-0002',comportamento_observado:'<script>exemplo</script>'}];
let kanbanLoads=0;
const context=vm.createContext({document:{getElementById:id=>elements[id],querySelector:()=>layout,createElement:()=>new Element()},
  Option:function(text,value){const e=new Element();e.textContent=text;e.value=String(value);return e;},
  state:{empresaId:4},api:async path=>{requests.push(path);return records;},issueApiUrl:path=>path+'?empresa_id=4',
  loadIssueKanban:async()=>kanbanLoads++,navigate:view=>opened.push(view),showIssueView:async view=>opened.push(view),selectIssue:async id=>opened.push(id),
  localStorage:{getItem:key=>stored.get(key),setItem:(key,value)=>stored.set(key,value)},window:{dispatchEvent(){}},Event:function(){}});
vm.runInContext(source.slice(source.indexOf('let rncRecords ='),source.indexOf('document.querySelectorAll(".sidebar a").forEach((a) => {')),context);
(async()=>{
  const menu=elements.btnMenuToggle;assert.equal(menu.getAttribute('aria-expanded'),'true');menu.listeners.click();
  assert.ok(layout.classes.has('menu-collapsed'));assert.equal(stored.get('qualidade.menuCollapsed'),'true');
  menu.listeners.click();assert.ok(!layout.classes.has('menu-collapsed'));
  await context.loadRncs();assert.equal(elements.rncSelect.children.length,2);assert.equal(kanbanLoads,1);assert.match(requests[0],/empresa_id=4/);
  elements.rncFilter.value='inexistente';context.filterRncSelect();assert.equal(elements.rncSelect.children.length,1);assert.match(elements.rncMensagem.textContent,/corresponde ao filtro/);
  elements.rncFilter.value='rnc-2026';context.filterRncSelect();assert.equal(elements.rncSelect.children.length,2);
  elements.rncFilter.value='EXEMPLO';context.filterRncSelect();assert.equal(elements.rncSelect.children.length,2);
  for(const pattern of ['RNC-2026-*','RNC-2026-00?','ISSUE-000?','*exemplo*','*']){
    elements.rncFilter.value=pattern;context.filterRncSelect();assert.equal(elements.rncSelect.children.length,2,pattern);
  }
  for(const pattern of ['RNC-2026-0?','ISSUE-?????','[exemplo]','(exemplo)','RNC-2026-.*']){
    elements.rncFilter.value=pattern;context.filterRncSelect();assert.equal(elements.rncSelect.children.length,1,pattern);
  }
  elements.rncFilter.value='';context.filterRncSelect();
  elements.rncSelect.value='2';context.renderRncDetail();assert.ok(!elements.rncDetail.classes.has('hidden'));
  const detail=elements.rncDetail.children;assert.equal(detail[0].children[0].textContent,'RNC-2026-001');
  const flatten=e=>[e,...e.children.flatMap(flatten)];
  const all=flatten(elements.rncDetail);
  assert.ok(all.some(e=>e.readOnly && e.value==='<script>exemplo</script>'));
  assert.ok(all.some(e=>e.textContent==='Registro da ocorrência'));
  assert.equal(all.filter(e=>e.readOnly).length,24);
  await detail[0].children[3].onclick();assert.deepEqual(opened,['issues','capturar',2]);
  records=[];await context.loadRncs();assert.ok(elements.rncDetail.classes.has('hidden'));assert.match(elements.rncMensagem.textContent,/Nenhuma RNC/);
  console.log('OK: menu retrátil, RNCs emitidas, filtro de empresa, consulta segura, lista vazia e Kanban.');
})().catch(e=>{console.error(e);process.exitCode=1;});
