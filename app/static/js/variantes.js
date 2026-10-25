// Variantes — consulta gráfica: por norma, requisito base → suas variantes (variante_de).
let varSeq = 0;
let varNormaId = null;
function varEl(id){ return document.getElementById("var-"+id); }

function resetVariantes(){
  varSeq++; varNormaId = null;
  const ws = document.getElementById("variantesWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadVariantes(){
  if (varEl("norma")) { varLoadNormas(); return; }
  document.getElementById("variantesWorkspace").innerHTML = `
    <div class="card">
      <label>Norma / Regulamento</label>
      <select id="var-norma"><option value="">Selecione…</option></select>
      <p class="hint">Mostra cada requisito <strong>base</strong> e as <strong>variantes</strong> ligadas a ele (relação "variante de"). Defina a variante no requisito e ligue-a ao base em Requisitos → Relações.</p>
    </div>
    <div id="var-mapa" class="card"><p class="muted">Selecione uma norma.</p></div>`;
  varEl("norma").onchange = ()=>{ varNormaId = Number(varEl("norma").value)||null; if(varNormaId) varDraw(); else varEl("mapa").innerHTML = `<p class="muted">Selecione uma norma.</p>`; };
  varLoadNormas();
}

async function varLoadNormas(){
  const seq = ++varSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ varEl("mapa").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== varSeq) return;
  varEl("norma").innerHTML = `<option value="">Selecione…</option>` +
    normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
}

async function varDraw(){
  const seq = ++varSeq;
  let d;
  try { d = await api(`/api/requisitos/variantes?norma_id=${varNormaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ varEl("mapa").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== varSeq) return;
  varEl("mapa").innerHTML = varHtml(d);
}

function varHtml(d){
  if (!d.grupos.length && !d.soltas.length)
    return `<div class="var-tree"><div class="rast-raiz">🔀 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)}</div><p class="muted">Nenhuma variante definida nesta norma. Marque a "Variante" de um requisito e ligue-o ao base com a relação "variante de".</p></div>`;
  const grupos = d.grupos.map(g=>`
    <div class="var-grupo">
      <div class="var-base">📦 <strong>${escapeHtml(g.base.codigo_clausula||"—")}</strong> ${escapeHtml(g.base.titulo)} <span class="var-count">${g.variantes.length} variante(s)</span></div>
      <div class="var-filhos">
        ${g.variantes.map(v=>`<div class="var-item"><span class="var-chip">${escapeHtml(v.variante||"variante")}</span> <strong>${escapeHtml(v.codigo_clausula||"—")}</strong> ${escapeHtml(v.titulo)}</div>`).join("")}
      </div>
    </div>`).join("");
  const soltas = d.soltas.length ? `
    <div class="var-grupo">
      <div class="var-base var-soltas">⚠ Variantes sem requisito base vinculado</div>
      <div class="var-filhos">
        ${d.soltas.map(v=>`<div class="var-item"><span class="var-chip">${escapeHtml(v.variante)}</span> <strong>${escapeHtml(v.codigo_clausula||"—")}</strong> ${escapeHtml(v.titulo)}</div>`).join("")}
      </div>
    </div>` : "";
  return `<div class="var-tree">
    <div class="rast-raiz">🔀 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)} <span class="muted">(${d.grupos.length} base(s) com variante)</span></div>
    ${grupos}${soltas}
  </div>`;
}
