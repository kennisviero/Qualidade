const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['versionamentoWorkspace'] = new Element();
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const data = {norma:{id:1,codigo:"NORMA-0001",titulo:"ISO"}, requisitos:[
  {id:5, codigo_clausula:"4.1", titulo:"<script>x</script>Contexto", versoes:[
    {numero:2, origem:"mudanca:9", criado_em:"2026-10-24T00:00:00", criado_por_nome:"A"},
    {numero:1, origem:"manual", criado_em:"2026-10-23T00:00:00", criado_por_nome:"A"}]}]};
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, escapeHtml, state:{empresaId:4},
  document:{getElementById:id=>elements[id], querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/requisitos/versoes-arvore')) return structuredClone(data);
    if(path.includes('/normas?')) return [{id:1,codigo:'NORMA-0001',titulo:'ISO'}]; return []; },
});
vm.runInContext(fs.readFileSync('app/static/js/versionamento.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="versionamento">/);
  assert.match(html, /id="section-versionamento"/);
  context.loadVersionamento(); await flush();
  assert.match(elements['ver-norma'].html, /NORMA-0001/);
  elements['ver-norma'].value='1'; elements['ver-norma'].onchange(); await flush();
  const m = elements['ver-mapa'].html;
  assert.match(m, /4\.1/, 'requisito');
  assert.match(m, /R02/, 'versão');
  assert.match(m, /mudança aprovada/, 'origem legível');
  assert.match(m, /&lt;script&gt;/, 'sanitizado');
  assert.doesNotMatch(m, /<script>x/, 'sem script cru');
  console.log('OK: menu/section, seleção de norma, árvore de versões (R01/R02 + origem), sanitizado.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
