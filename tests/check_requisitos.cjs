const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.checked=false; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)}; }
  append(...v){ this.children.push(...v); }
  querySelector(){ return null; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['nor-requisitos'] = new Element();
let editor = true;
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const req1 = {id:1, codigo_clausula:'4.1', titulo:'<script>x</script>Contexto', categoria:'normativo', obrigatoriedade:'obrigatorio', estado:'ativo', prioridade:'must'};
const det1 = {...req1, texto:'', atributos:[], vinculos:[], relacoes:[]};
const context = vm.createContext({ console, URLSearchParams, escapeHtml, isEditor:()=>editor, isAdmin:()=>editor, alert(){}, confirm:()=>true, prompt:()=>'',
  apiErrorMessage:(d,f)=>typeof d==='string'?d:(f||'erro'), state:{empresaId:4, user:{id:1}},
  document:{getElementById:id=>elements[id], createElement:()=>new Element(), querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/atributos/defs')) return [];
    if(/\/requisitos\/1\?/.test(path)) return structuredClone(det1);
    if(path.includes('/requisitos?')) return [structuredClone(req1)]; return []; },
});
vm.runInContext(fs.readFileSync('app/static/js/requisitos.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /src="\/static\/js\/requisitos\.js"/);
  await context.reqLoadForNorma(1);
  assert.match(elements['nor-requisitos'].html, /Requisitos \/ cláusulas/);
  assert.match(elements['nor-requisitos'].html, /Adicionar/);
  assert.match(elements['nor-requisitos'].html, /Atributos \(configuração\)/, 'config de atributos p/ admin');
  assert.match(elements['nor-requisitos'].html, /Prioridade/, 'prioridade MoSCoW');
  await context.reqLoadList();
  assert.match(elements['req-list'].html, /Contexto/);
  assert.match(elements['req-list'].html, /Essencial/, 'prioridade (pt-BR) exibida na lista');
  assert.match(elements['req-list'].html, /&lt;script&gt;/, 'título sanitizado');
  assert.doesNotMatch(elements['req-list'].html, /<script>x/, 'sem script cru');
  // painel de edição
  await context.reqSelect(1);
  assert.match(elements['req-edit'].html, /Salvar/);
  assert.match(elements['req-edit'].html, /Relações \(requisito ↔ requisito\)/);
  assert.match(elements['req-edit'].html, /id="req-e-fonte"/, 'campo Fonte no painel');
  assert.match(elements['req-edit'].html, /id="req-e-justif"/, 'campo Justificativa no painel');
  // visualizador não vê form de adicionar nem config
  editor = false;
  await context.reqLoadForNorma(1);
  assert.doesNotMatch(elements['nor-requisitos'].html, /Adicionar/);
  assert.doesNotMatch(elements['nor-requisitos'].html, /Atributos \(configuração\)/);
  console.log('OK: script, prioridade, config de atributos (admin), painel de edição + relações, lista sanitizada, visualizador sem escrita.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
