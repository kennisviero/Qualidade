const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const elements = {};
class Element {
  constructor(){ this.children=[]; this.value=''; this.style={}; this.classes=new Set();
    this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),toggle:(c,v)=>v?this.classes.add(c):this.classes.delete(c)}; }
  querySelectorAll(){ return []; }
  querySelector(){ return null; }
  set innerHTML(v){ this.html=v; for(const m of String(v).matchAll(/id="([^"]+)"/g)) elements[m[1]]=new Element(); }
  get innerHTML(){ return this.html||''; }
}
elements['rastreabilidadeWorkspace'] = new Element();
function escapeHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const REQ_PRIO = [["","—"],["must","Essencial"]];
function reqLabel(p,v){ const f=p.find(x=>x[0]===v); return f?f[1]:v; }
let editor = true;
const arvore = {norma:{id:1, codigo:"NORMA-0002", titulo:"ISO 9001"}, requisitos:[
  {id:5, codigo_clausula:"ESP-1", titulo:"<script>x</script>Potência", categoria:"cliente", prioridade:"must", situacao:"conforme",
   vinculos:[{id:11, alvo_tipo:"processo", alvo_id:3, alvo_label:"Montagem", tipo_relacao:"satisfaz", observacao:"obs do vinculo"}],
   relacoes:[{id:22, destino_id:6, destino_clausula:"ESP-3", tipo:"depende", observacao:"obs da relacao"}],
   mudancas:[{id:33, situacao:"proposta", descricao:"mudar potencia", decisao_obs:"", solicitante_nome:"Carlos", aprovador_nome:null},
             {id:34, situacao:"aprovada", descricao:"ajuste de texto", decisao_obs:"ok aprovado", solicitante_nome:"Carlos", aprovador_nome:"Ana"}]}]};
const flush = ()=>new Promise(r=>setTimeout(r,10));
const context = vm.createContext({ console, escapeHtml, REQ_PRIO, reqLabel, state:{empresaId:4}, isEditor:()=>editor,
  document:{getElementById:id=>elements[id], querySelectorAll:()=>[]},
  window:{open(){}},
  api:async(path)=>{ if(path.includes('/requisitos/arvore')) return structuredClone(arvore);
    if(path.includes('/requisitos/auditoria')) return {resumo:{total:1,sem_fonte:1,sem_justificativa:0,sem_vinculo:1,sem_verificacao:1},
      itens:[{id:5,codigo_clausula:'ESP-1',titulo:'Potência',norma_codigo:'NORMA-0002',sem_fonte:true,sem_justificativa:false,sem_vinculo:true,sem_verificacao:true}]};
    if(path.includes('/normas?')) return [{id:1,codigo:'NORMA-0002',titulo:'ISO 9001'}]; return []; },
});
vm.runInContext(fs.readFileSync('app/static/js/rastreabilidade.js','utf8'), context);
(async()=>{
  const html = fs.readFileSync('app/static/index.html','utf8');
  assert.match(html, /data-section="rastreabilidade">/);
  assert.match(html, /id="section-rastreabilidade"/);
  context.loadRastreabilidade(); await flush();
  assert.match(elements['rast-norma'].html, /NORMA-0002/, 'seletor parte da norma');
  assert.ok(elements['rast-export'], 'botão de exportar CSV presente');
  // auditoria de rastreabilidade
  await context.rastDrawAuditoria(1); await flush();
  const au = elements['rast-audit'].html;
  assert.match(au, /Auditoria de rastreabilidade/, 'resumo de auditoria');
  assert.match(au, /sem fonte: 1/, 'contagem de sem fonte');
  assert.match(au, /ESP-1/, 'lista o requisito com lacuna');

  // --- editor ---
  await context.rastDrawArvore(1); await flush();
  let t = elements['rast-arvore'].html;
  assert.match(t, /rast-tree/, 'gera a árvore');
  assert.match(t, /NORMA-0002/, 'raiz é a norma');
  assert.match(t, /ESP-1/, 'requisito na árvore');
  assert.match(t, /Essencial/, 'prioridade pt-BR');
  assert.match(t, /Montagem/, 'vínculo a processo com rótulo');
  assert.match(t, /ESP-3/, 'relação a outro requisito');
  assert.match(t, /&lt;script&gt;/, 'título sanitizado');
  assert.doesNotMatch(t, /<script>x/, 'sem script cru');
  // observações + mudanças + controles de editor
  assert.match(t, /Mudanças \(change request\)/, 'bloco de mudanças');
  assert.match(t, /mudar potencia/, 'mudança listada');
  assert.match(t, /ok aprovado/, 'observação da decisão exibida');
  assert.match(t, /rast-obs-input[^>]*data-kind="vinculos"[^>]*value="obs do vinculo"/, 'editor edita obs do vínculo');
  assert.match(t, /rast-obs-input[^>]*data-kind="relacoes"[^>]*value="obs da relacao"/, 'editor edita obs da relação');
  assert.match(t, /rast-mud-add/, 'editor pode propor mudança');
  assert.match(t, /rast-mud-ok[^>]*data-id="33"/, 'editor pode aprovar proposta aberta');
  assert.doesNotMatch(t, /rast-mud-ok[^>]*data-id="34"/, 'não decide mudança já decidida');

  // --- visualizador ---
  editor = false;
  await context.rastDrawArvore(1); await flush();
  t = elements['rast-arvore'].html;
  assert.match(t, /obs do vinculo/, 'visualizador vê a observação (texto)');
  assert.match(t, /ok aprovado/, 'visualizador vê a observação da decisão');
  assert.doesNotMatch(t, /rast-obs-save/, 'visualizador não edita observação');
  assert.doesNotMatch(t, /rast-mud-add/, 'visualizador não propõe mudança');
  assert.doesNotMatch(t, /rast-mud-ok/, 'visualizador não decide mudança');
  editor = true;
  console.log('OK: árvore com observações e mudanças; editor registra obs/propõe/decide; visualizador só lê.');
})().catch(e=>{ console.error(e); process.exitCode=1; });
