const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['variantesWorkspace'] = new Element();
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const data = {norma:{id:1,codigo:"NORMA-0002",titulo:"ISO"},
  grupos:[{base:{id:4,codigo_clausula:"ESP-4",titulo:"Tensão"}, variantes:[
    {id:5,codigo_clausula:"ESP-4a",titulo:"<script>x</script>127V",variante:"127V"},
    {id:6,codigo_clausula:"ESP-4b",titulo:"220V",variante:"220V"}]}],
  soltas:[{id:7,codigo_clausula:"ESP-9",titulo:"BR",variante:"BR"}]};
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, escapeHtml, state:{empresaId:4},
  document:{getElementById:id=>elements[id], querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/requisitos/variantes')) return structuredClone(data);
    if(path.includes('/normas?')) return [{id:1,codigo:'NORMA-0002',titulo:'ISO'}]; return []; },
});
vm.runInContext(fs.readFileSync('app/static/js/variantes.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="variantes">Variantes/);
  assert.match(html, /id="section-variantes"/);
  context.loadVariantes(); await flush();
  assert.match(elements['var-norma'].html, /NORMA-0002/);
  elements['var-norma'].value = '1'; elements['var-norma'].onchange(); await flush();
  const m = elements['var-mapa'].html;
  assert.match(m, /ESP-4/, 'base');
  assert.match(m, /127V/, 'chip da variante');
  assert.match(m, /ESP-4a/, 'variante');
  assert.match(m, /sem requisito base/, 'seção de variantes soltas');
  assert.match(m, /&lt;script&gt;/, 'sanitizado');
  assert.doesNotMatch(m, /<script>x/, 'sem script cru');
  console.log('OK: menu/section, seleção de norma, grupos base→variantes com chip, soltas, sanitizado.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
