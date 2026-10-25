const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.checked=true; this.disabled=false; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  append(...v){ this.children.push(...v); }
  querySelectorAll(){ return []; }
  setAttribute(k,v){ this[k]=v; }
  set innerHTML(v){ this.html=v; this.children=v===''?[]:this.children; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements.normasWorkspace = new Element();
let editor = true;
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const flush = ()=>new Promise(r=>setTimeout(r,10));
const norma1 = {id:1, codigo:'NORMA-0001', titulo:'<script>x</script>ISO 9001', tipo_fonte:'norma_tecnica',
  status:'vigente', identificador_externo:'ISO 9001:2015', emissor:'ISO', edicao_versao:'2015',
  data_publicacao:'', data_vigencia:'', escopo:'', observacoes:'', documento:{id:7}};
const docInfo = {documento_id:7, codigo:'DOC-0001', estado:'rascunho',
  revisao:{numero:1, fonte:'link', url:'https://docs.google.com/x', arquivo_nome:'', tem_arquivo:false, tem_link:true}};
const context = vm.createContext({ console, URLSearchParams, escapeHtml, isEditor:()=>editor, navigate(){},
  alert(){}, confirm:()=>true, prompt:()=>'',
  apiErrorMessage:(d,f)=>typeof d==='string'?d:(f||'erro'),
  state:{empresaId:4, user:{id:1}},
  document:{getElementById:id=>elements[id], createElement:()=>new Element(), querySelectorAll:()=>[]},
  api:async(path)=>{ if(/\/normas\/1\/documento/.test(path)) return structuredClone(docInfo);
    if(/\/normas\/1(\?|$)/.test(path)) return structuredClone(norma1);
    if(path.includes('/normas?')) return [structuredClone(norma1)]; return structuredClone(norma1); },
});
vm.runInContext(fs.readFileSync('app/static/js/normas.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="normas">Normas e Regulamentos/);
  assert.match(html, /id="section-normas"/);
  assert.doesNotMatch(html, /data-section="pdm"/, 'opção Documentos removida');
  context.loadNormas();
  assert.match(elements.normasWorkspace.html, /Nova norma/);
  await context.normasLoadList();
  assert.match(elements['nor-list'].html, /NORMA-0001/);
  await context.normaSelect(1); await flush();
  assert.match(elements['nor-detail'].html, /&lt;script&gt;/, 'título sanitizado');
  assert.doesNotMatch(elements['nor-detail'].html, /<script>x/, 'sem script cru');
  assert.match(elements['nor-detail'].html, /Documento \(fonte\)/, 'bloco de fonte do documento');
  assert.match(elements['nor-detail'].html, /Salvar/, 'editor vê salvar');
  assert.match(elements['nor-doc'].html, /abrir link/, 'fonte link renderizada dentro da norma');
  // visualizador
  editor = false;
  context.buildNormas();
  assert.match(elements.normasWorkspace.html, /card hidden" id="nor-novo-card"/);
  await context.normaSelect(1); await flush();
  assert.doesNotMatch(elements['nor-detail'].html, /id="nor-d-salvar"/, 'visualizador sem salvar');
  context.resetNormas();
  assert.equal(elements.normasWorkspace.html, '');
  console.log('OK: menu/section, build, lista, detalhe sanitizado, documento(fonte) na norma, visualizador sem escrita, reset.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
