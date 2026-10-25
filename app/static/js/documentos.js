// Documentos — Kanban do ciclo de vida (Backlog → Em revisão → Em aprovação → Aprovado).
// Obsolescência é fluxo separado (ação própria), não é coluna do Kanban.
let docSeq = 0;
let docDragId = null;

const DOC_COLS = [["backlog","Backlog"],["em_revisao","Em revisão"],["em_aprovacao","Em aprovação"],["aprovado","Aprovado"]];
const DOC_TIPOS = {norma:"Norma", procedimento:"Procedimento", instrucao:"Instrução", formulario:"Formulário", politica:"Política", contrato:"Contrato", outro:"Outro"};
const DOC_FONTE = {norma_tecnica:"Norma técnica", regulamento_legal:"Regulamento legal", requisito_contratual:"Requisito contratual", requisito_cliente:"Requisito de cliente", politica_interna:"Política interna", outro:"Outro"};
function docEl(id){ return document.getElementById("doc-"+id); }

function resetDocumentos(){
  docSeq++;
  const ws = document.getElementById("documentosWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadDocumentos(){
  if (docEl("board")) { docLoad(); return; }
  document.getElementById("documentosWorkspace").innerHTML = `
    <p class="hint">Arraste um documento entre as colunas para avançar no ciclo. Aprovar exige o aprovador definido. <strong>Obsolescência é um fluxo à parte</strong> (botão no cartão).</p>
    <div id="doc-board" class="doc-board"></div>
    <div class="card"><h3>Obsoletos (fluxo separado)</h3><div id="doc-obsoletos" class="list"></div></div>`;
  docLoad();
}

async function docLoad(){
  const seq = ++docSeq;
  let docs;
  try { docs = await api(`/api/pdm/documentos?empresa_id=${state.empresaId||""}`); }
  catch(e){ docEl("board").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== docSeq) return;
  docRender(docs);
}

function docCard(d){
  const ed = isEditor();
  const ehNorma = !!d.norma_codigo;
  const codigo = ehNorma ? d.norma_codigo : d.codigo;
  const classe = ehNorma ? (DOC_FONTE[d.norma_tipo_fonte] || "Norma") : (DOC_TIPOS[d.tipo] || d.tipo);
  const ident = ehNorma && d.norma_ident ? ` · ${escapeHtml(d.norma_ident)}` : "";
  return `<div class="doc-card${ehNorma?" doc-norma":""}" draggable="${ed}" data-id="${d.id}" title="Clique para abrir o documento">
    <span class="doc-tag">${escapeHtml(classe)}</span>
    <strong>${escapeHtml(codigo)}</strong> ${escapeHtml(d.titulo)}${ident}
    <div class="muted">${escapeHtml(d.codigo)}${d.bloqueado?` · 🔒 ${escapeHtml(d.checkout_por_nome||"")}`:""}</div>
    ${ed?`<button class="btn doc-obs" data-id="${d.id}" type="button">Obsoletar</button>`:""}
  </div>`;
}

function docFonteAtual(d){
  const revs = d.revisoes || [];
  if (!revs.length) return null;
  return revs.reduce((a,b)=> (b.numero>a.numero?b:a), revs[0]);
}

function docAbrir(d){
  const rev = docFonteAtual(d);
  if (rev && rev.tem_link && rev.url){ window.open(rev.url, "_blank", "noopener"); return; }
  if (rev && rev.tem_arquivo){ window.open(`/api/pdm/documentos/${d.id}/revisoes/${rev.numero}/arquivo`, "_blank"); return; }
  // Sem arquivo/link: se for uma norma, abre a Norma (onde se define a fonte); senão avisa.
  if (d.norma_id){
    navigate("normas");
    if (typeof loadNormas === "function") loadNormas();
    if (typeof normaSelect === "function") normaSelect(d.norma_id);
    return;
  }
  alert("Documento cadastrado (sem arquivo/link). Defina a fonte na Norma: Enviar PDF/DOCX ou Definir link (Google Docs).");
}

function docRender(docs){
  const ed = isEditor();
  const porEstado = {}; DOC_COLS.forEach(([e])=>porEstado[e]=[]);
  const obsoletos = [];
  docs.forEach(d=>{ if (d.estado==="obsoleto") obsoletos.push(d); else if (porEstado[d.estado]) porEstado[d.estado].push(d); else porEstado.backlog.push(d); });
  docEl("board").innerHTML = DOC_COLS.map(([estado,label])=>`
    <div class="doc-col" data-estado="${estado}">
      <h4>${label} <span class="muted">(${porEstado[estado].length})</span></h4>
      <div class="doc-col-body" data-estado="${estado}">${porEstado[estado].map(docCard).join("")}</div>
    </div>`).join("");
  docEl("obsoletos").innerHTML = obsoletos.length
    ? obsoletos.map(d=>`<div class="doc-obsoleto" data-id="${d.id}">
        <span class="doc-status-obsoleto">OBSOLETO</span>
        <strong>${escapeHtml(d.norma_codigo||d.codigo)}</strong> ${escapeHtml(d.titulo)}
        <a href="#" class="doc-abrir" data-id="${d.id}">abrir</a>
        ${ed?`<button class="btn doc-reativar" data-id="${d.id}" type="button">Reativar</button>`:""}</div>`).join("")
    : `<p class="muted">Nenhum documento obsoleto.</p>`;
  // abrir obsoletos (click no "abrir")
  docEl("obsoletos").querySelectorAll(".doc-abrir").forEach(a=>{ a.onclick = (e)=>{ e.preventDefault(); const d=docs.find(x=>x.id===Number(a.dataset.id)); if(d) docAbrir(d); }; });
  if (ed) docEl("obsoletos").querySelectorAll(".doc-reativar").forEach(b=>{ b.onclick = ()=>docReativar(Number(b.dataset.id)); });
  // clicar no cartão abre o documento (ignora clique em botão)
  docEl("board").querySelectorAll(".doc-card").forEach(c=>{
    c.onclick = (e)=>{ if(e.target.closest("button")) return; const d=docs.find(x=>x.id===Number(c.dataset.id)); if(d) docAbrir(d); };
  });
  if (!ed) return;
  // obsoletar (fluxo separado)
  docEl("board").querySelectorAll(".doc-obs").forEach(b=>{ b.onclick = (e)=>{ e.stopPropagation(); if(confirm("Tornar este documento obsoleto? (fluxo separado)")) docObsoletar(Number(b.dataset.id)); }; });
  // drag and drop
  docEl("board").querySelectorAll(".doc-card").forEach(c=>{
    c.ondragstart = (e)=>{ docDragId = Number(c.dataset.id); if(e.dataTransfer) e.dataTransfer.effectAllowed="move"; };
  });
  docEl("board").querySelectorAll(".doc-col-body").forEach(col=>{
    col.ondragover = (e)=>{ e.preventDefault(); };
    col.ondrop = (e)=>{ e.preventDefault(); if(docDragId!=null) docMover(docDragId, col.dataset.estado); docDragId=null; };
  });
}

async function docMover(id, estado){
  try { await api(`/api/pdm/documentos/${id}/mover`, {method:"POST", body:{estado}}); docLoad(); }
  catch(e){ alert(e.message); docLoad(); }
}

async function docObsoletar(id){
  try { await api(`/api/pdm/documentos/${id}/obsoletar`, {method:"POST"}); docLoad(); }
  catch(e){ alert(e.message); }
}

async function docReativar(id){
  if (!confirm("Reativar este documento obsoleto? Ele volta ao Backlog.")) return;
  try { await api(`/api/pdm/documentos/${id}/reativar`, {method:"POST"}); docLoad(); }
  catch(e){ alert(e.message); }
}
