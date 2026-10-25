// Verifica a tela de Produtos (árvore Família/Grupo/Produto) — app/static/js/produtos.js
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c),contains:c=>this.classes.has(c)}; }
  querySelectorAll(){ return []; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['produtosWorkspace'] = new Element();
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const flush = ()=>new Promise(r=>setTimeout(r,10));
let editor = true;
const arv = {familias:[{id:1,nome:'Linha Branca',grupos:[
  {id:10,nome:'Liquidificadores',familia_id:1,produtos:[{id:100,codigo:'LIQ-500',nome:'ProMix 500',grupo_id:10}]}]}]};
const ctx = vm.createContext({ console, escapeHtml, state:{empresaId:4}, isEditor:()=>editor,
  document:{getElementById:id=>elements[id]},
  api:async(path)=>{ if(path.includes('/produtos/arvore')) return JSON.parse(JSON.stringify(arv)); return {}; },
});
vm.runInContext(fs.readFileSync('app/static/js/produtos.js','utf8'), ctx);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="produtos"/, 'item de menu Produtos');
  assert.match(html, /id="section-produtos"/, 'seção Produtos');
  assert.match(html, /src="\/static\/js\/produtos\.js"/, 'script incluído');

  // editor: árvore com níveis + controles
  ctx.loadProdutos(); await flush();
  let t = elements['prod-arvore'].html;
  assert.match(t, /Linha Branca/, 'família');
  assert.match(t, /Liquidificadores/, 'grupo');
  assert.match(t, /ProMix 500/, 'produto');
  assert.match(t, /prod-del/, 'editor pode excluir');
  assert.match(t, /prod-add-grupo/, 'editor adiciona grupo');
  assert.match(t, /prod-add-prod/, 'editor adiciona produto');
  assert.ok(elements['prod-add-familia'], 'editor adiciona família');

  // visualizador: só leitura (re-renderiza a árvore com isEditor()=false)
  editor = false;
  await ctx.prodDraw(); await flush();
  t = elements['prod-arvore'].html;
  assert.match(t, /ProMix 500/, 'visualizador vê a árvore');
  assert.doesNotMatch(t, /prod-del/, 'visualizador não exclui');
  assert.doesNotMatch(t, /prod-add-grupo/, 'visualizador não adiciona');
  editor = true;
  console.log('OK: tela Produtos — árvore Família/Grupo/Produto, controles de editor, visualizador só lê.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
