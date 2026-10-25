const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements.coberturaWorkspace = new Element();
let editor = true;
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const matriz = {norma_id:1, requisitos:[{id:5, codigo_clausula:'4.1', titulo:'<script>y</script>Contexto',
  categoria:'normativo', obrigatoriedade:'obrigatorio', estado:'ativo', situacao:'nao_avaliado', evidencia:'', vinculos:{}, total_vinculos:0}],
  resumo:{total:1, conformes:0, nao_conformes:0, nao_avaliados:1, sem_vinculo:1},
  lacunas:{sem_vinculo:[5], nao_avaliados:[5], nao_conformes:[]}};
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, URLSearchParams, escapeHtml, isEditor:()=>editor, alert(){}, prompt:()=>'',
  state:{empresaId:4, user:{id:1}},
  document:{getElementById:id=>elements[id], createElement:()=>new Element(), querySelectorAll:()=>[]},
  api:async(path)=>{ if(path.includes('/normas?')) return [{id:1,codigo:'NORMA-0001',titulo:'ISO'}];
    if(path.includes('/conformidade/matriz')) return structuredClone(matriz); return {}; },
});
vm.runInContext(fs.readFileSync('app/static/js/cobertura.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="cobertura">Matriz de Conformidade/);
  assert.match(html, /id="section-cobertura"/);
  context.loadCobertura(); await flush();
  assert.match(elements['cob-norma'].html, /NORMA-0001/);
  elements['cob-norma'].value = '1';
  elements['cob-norma'].onchange(); await flush();
  assert.match(elements['cob-tabela'].html, /Contexto/);
  assert.match(elements['cob-tabela'].html, /&lt;script&gt;/, 'sanitizado');
  assert.match(elements['cob-tabela'].html, /cob-warn/, 'lacuna sem vínculo destacada');
  assert.match(elements['cob-resumo'].html, /Total/);
  assert.match(elements['cob-tabela'].html, /cob-sit/, 'editor edita situação');
  // visualizador vê situação como texto
  editor = false;
  elements['cob-norma'].onchange(); await flush();
  assert.doesNotMatch(elements['cob-tabela'].html, /class="cob-sit"/);
  assert.match(elements['cob-tabela'].html, /Não avaliado/);
  console.log('OK: menu/section, seleção de norma, matriz sanitizada, lacunas destacadas, edição por papel.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
