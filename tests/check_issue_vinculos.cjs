// Verifica o bloco "Normas/Requisitos aplicáveis" da Issue (fatia de app.js).
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');

class Element {
  constructor(){ this.children=[]; this.value=''; this._html=''; }
  set innerHTML(v){ this._html=String(v); }
  get innerHTML(){ return this._html; }
  querySelectorAll(){ return []; }   // onclick-wiring é ignorado; asserção é sobre o HTML
  querySelector(){ return null; }
}
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

const host = new Element();
let editor = true;
const VINC_ROWS = [{vinculo_id:7, requisito_id:3, codigo_clausula:'4.1', titulo:'Requisito de potência',
  tipo_relacao:'viola', observacao:'fora do limite', norma_id:1, norma_codigo:'NORMA-0002', norma_titulo:'ISO X'}];
const REQS = [{id:3, codigo_clausula:'4.1', titulo:'Requisito de potência', norma_codigo:'NORMA-0002'},
  {id:4, codigo_clausula:'4.2', titulo:'Requisito de ruído', norma_codigo:'NORMA-0002'}];

const ctx = vm.createContext({ console, escapeHtml, state:{empresaId:4, issueId:55}, isEditor:()=>editor,
  document:{ getElementById:id=> id==='issueVinculos'?host:null },
  api:async(path)=>{ if(path.includes('vinculos-por-alvo')) return JSON.parse(JSON.stringify(VINC_ROWS));
    if(path.includes('/api/requisitos?')) return JSON.parse(JSON.stringify(REQS)); return []; },
});
const source = fs.readFileSync('app/static/js/app.js','utf8');
vm.runInContext(source.slice(source.indexOf('const VINC_TIPOS'), source.indexOf('async function refreshIssue(')), ctx);

(async()=>{
  // Editor: lista vínculo + formulário
  await ctx.loadIssueVinculos();
  let h = host.innerHTML;
  assert.match(h, /NORMA-0002/, 'mostra a norma do requisito vinculado');
  assert.match(h, /Requisito de potência/, 'mostra o título do requisito');
  assert.match(h, /vinc-del/, 'editor pode remover vínculo');
  assert.match(h, /vinc-add/, 'editor tem botão Vincular');
  assert.match(h, /Requisito de ruído/, 'seletor lista requisitos da empresa');
  assert.match(h, /Viola/, 'tipos de relação incluem Viola');

  // Visualizador: sem controles de escrita
  editor = false; ctx.resetReqVincCache();
  await ctx.loadIssueVinculos();
  h = host.innerHTML;
  assert.match(h, /NORMA-0002/, 'visualizador vê o vínculo');
  assert.doesNotMatch(h, /vinc-add/, 'visualizador não tem botão Vincular');
  assert.doesNotMatch(h, /vinc-del/, 'visualizador não remove');
  editor = true;

  // Sem issue salva: pede para salvar
  ctx.state.issueId = null;
  await ctx.loadIssueVinculos();
  assert.match(host.innerHTML, /Salve a Issue/, 'sem issue salva, orienta salvar');

  console.log('OK: bloco de vínculos da Issue — lista norma/requisito, form de editor, visualizador só lê, exige issue salva.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
