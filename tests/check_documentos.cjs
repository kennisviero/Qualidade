const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['documentosWorkspace'] = new Element();
let editor = true;
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const docs = [
  {id:1, codigo:"DOC-0001", titulo:"<script>x</script>Proc", tipo:"procedimento", estado:"backlog", bloqueado:false},
  {id:2, codigo:"DOC-0002", titulo:"Lei de Licitações", tipo:"norma", estado:"em_aprovacao", bloqueado:false,
   norma_codigo:"NORMA-0002", norma_tipo_fonte:"regulamento_legal", norma_ident:"Lei 14.133/2021"},
  {id:3, codigo:"DOC-0003", titulo:"Velha", tipo:"norma", estado:"obsoleto", bloqueado:false}];
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, escapeHtml, isEditor:()=>editor, alert(){}, confirm:()=>true, state:{empresaId:4},
  document:{getElementById:id=>elements[id], querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/pdm/documentos?')) return structuredClone(docs); return {}; },
});
vm.runInContext(fs.readFileSync('app/static/js/documentos.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="documentos">Documentos \(Kanban\)/);
  assert.match(html, /id="section-documentos"/);
  context.loadDocumentos(); await flush();
  const b = elements['doc-board'].html;
  assert.match(b, /Backlog/); assert.match(b, /Em aprovação/); assert.match(b, /Aprovado/);
  assert.match(b, /DOC-0001/, 'card no backlog');
  assert.match(b, /NORMA-0002/, 'norma identificada pelo código no card');
  assert.match(b, /Regulamento legal/, 'tipo de fonte (regulamento) no card');
  assert.match(b, /Lei 14\.133\/2021/, 'identificador da norma');
  assert.match(b, /&lt;script&gt;/, 'sanitizado'); assert.doesNotMatch(b, /<script>x/, 'sem script cru');
  assert.match(b, /Obsoletar/, 'obsolescência como ação separada no cartão');
  assert.doesNotMatch(b, /DOC-0003/, 'obsoleto não aparece no board');
  assert.match(elements['doc-obsoletos'].html, /DOC-0003/, 'obsoleto no fluxo separado');
  assert.match(elements['doc-obsoletos'].html, /OBSOLETO/, 'status obsoleto visível');
  assert.match(elements['doc-obsoletos'].html, /Reativar/, 'ação de reativar no obsoleto');
  console.log('OK: menu/section, Kanban, cards sanitizados, obsolescência separada, status + reativar.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
