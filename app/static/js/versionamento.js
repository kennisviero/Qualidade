// Versionamento — árvore por norma: cada requisito e seu histórico de versões (R01/R02…).
let verSeq = 0;
let verNormaId = null;
function verEl(id){ return document.getElementById("ver-"+id); }

function resetVersionamento(){
  verSeq++; verNormaId = null;
  const ws = document.getElementById("versionamentoWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadVersionamento(){
  if (verEl("norma")) { verLoadNormas(); return; }
  document.getElementById("versionamentoWorkspace").innerHTML = `
    <div class="card">
      <label>Norma / Regulamento</label>
      <select id="ver-norma"><option value="">Selecione…</option></select>
      <p class="hint">Cada requisito e suas versões (R01, R02…). Versões são criadas manualmente em Requisitos → "Registrar versão" ou automaticamente ao aprovar uma mudança.</p>
    </div>
    <div id="ver-mapa" class="card"><p class="muted">Selecione uma norma.</p></div>`;
  verEl("norma").onchange = ()=>{ verNormaId = Number(verEl("norma").value)||null; if(verNormaId) verDraw(); else verEl("mapa").innerHTML = `<p class="muted">Selecione uma norma.</p>`; };
  verLoadNormas();
}

async function verLoadNormas(){
  const seq = ++verSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ verEl("mapa").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== verSeq) return;
  verEl("norma").innerHTML = `<option value="">Selecione…</option>` +
    normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
}

async function verDraw(){
  const seq = ++verSeq;
  let d;
  try { d = await api(`/api/requisitos/versoes-arvore?norma_id=${verNormaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ verEl("mapa").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== verSeq) return;
  verEl("mapa").innerHTML = verHtml(d);
}

function verOrigem(o){ return (o||"").startsWith("mudanca:") ? "mudança aprovada" : (o||"manual"); }

function verHtml(d){
  const reqs = d.requisitos || [];
  if (!reqs.length) return `<div class="var-tree"><div class="rast-raiz">🗂 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)}</div><p class="muted">Esta norma não tem requisitos.</p></div>`;
  const itens = reqs.map(r=>{
    const vs = r.versoes||[];
    const corpo = vs.length
      ? `<div class="var-filhos">${vs.map(v=>`<div class="var-item"><span class="var-chip">R${String(v.numero).padStart(2,"0")}</span>
          <span class="muted">${escapeHtml(verOrigem(v.origem))} · ${escapeHtml((v.criado_em||"").slice(0,10))} · ${escapeHtml(v.criado_por_nome||"—")}</span></div>`).join("")}</div>`
      : `<p class="var-vazio muted">Sem versões registradas.</p>`;
    return `<details class="rast-req"${vs.length?" open":""}>
      <summary><strong>${escapeHtml(r.codigo_clausula||"—")}</strong> ${escapeHtml(r.titulo)} <span class="var-count">${vs.length} versão(ões)</span></summary>
      ${corpo}
    </details>`;
  }).join("");
  return `<div class="var-tree">
    <div class="rast-raiz">🗂 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)}</div>
    <div class="rast-reqs">${itens}</div>
  </div>`;
}
