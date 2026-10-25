const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['impactoWorkspace'] = new Element();
let editor = true;
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const imp = {requisitos:[
  {id:1, codigo_clausula:"ESP-1", titulo:"<script>x</script>Descarte", custo_atual:150, custo_projetado:50, volume:1000000, economia:100000000},
  {id:2, codigo_clausula:"ESP-2", titulo:"Sem dados", custo_atual:null, custo_projetado:null, volume:null, economia:null}],
  resumo:{requisitos:2, requisitos_com_dados:1, economia_total:100000000}};
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, escapeHtml, isEditor:()=>editor, alert(){}, state:{empresaId:4},
  document:{getElementById:id=>elements[id], querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/requisitos/impacto')) return structuredClone(imp);
    if(path.includes('/normas?')) return [{id:9,codigo:'NORMA-0002',titulo:'ISO'}]; return []; },
  // Plotly ausente no harness -> impGrafico deve ocultar o gráfico sem quebrar
});
vm.runInContext(fs.readFileSync('app/static/js/impacto.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="impacto">Análise de impacto/);
  assert.match(html, /id="section-impacto"/);
  context.loadImpacto(); await flush();
  assert.match(elements['imp-norma'].html, /NORMA-0002/);
  elements['imp-norma'].value = '9';
  elements['imp-norma'].onchange(); await flush();
  const t = elements['imp-tabela'].html;
  assert.match(t, /ESP-1/, 'requisito na tabela');
  assert.match(t, /Descarte/);
  assert.match(t, /imp-in/, 'editor edita custos inline');
  assert.match(elements['imp-resumo'].html, /Economia total/);
  assert.match(t, /&lt;script&gt;/, 'sanitizado');
  assert.doesNotMatch(t, /<script>x/, 'sem script cru');
  // visualizador: sem inputs editáveis
  editor = false;
  elements['imp-norma'].onchange(); await flush();
  assert.doesNotMatch(elements['imp-tabela'].html, /imp-in/);
  console.log('OK: menu/section, seleção de norma, tabela com economia + total, edição por papel, sanitizado.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
