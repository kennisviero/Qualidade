// Análise de impacto econômico — custo atual/projetado × volume → economia por requisito.
let impSeq = 0;
let impNormaId = null;

function impEl(id){ return document.getElementById("imp-"+id); }
function impMoeda(v){ return (v==null) ? "—" : Number(v).toLocaleString("pt-BR", {maximumFractionDigits:2}); }

function resetImpacto(){
  impSeq++; impNormaId = null;
  const ws = document.getElementById("impactoWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadImpacto(){
  if (impEl("norma")) { impLoadNormas(); return; }
  document.getElementById("impactoWorkspace").innerHTML = `
    <div class="card">
      <label>Norma / Regulamento</label>
      <select id="imp-norma"><option value="">Selecione…</option></select>
      <p class="hint">Economia = (custo atual − custo projetado) × volume. Preencha os valores por requisito (admin/editor).</p>
    </div>
    <div id="imp-resumo" class="hint"></div>
    <div id="imp-graf" class="card" style="display:none"></div>
    <div id="imp-tabela" class="card"></div>`;
  impEl("norma").onchange = ()=>{ impNormaId = Number(impEl("norma").value)||null; if(impNormaId) impLoad(); else { impEl("tabela").innerHTML=""; impEl("resumo").innerHTML=""; impEl("graf").style.display="none"; } };
  impLoadNormas();
}

async function impLoadNormas(){
  const seq = ++impSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ impEl("tabela").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== impSeq) return;
  impEl("norma").innerHTML = `<option value="">Selecione…</option>` +
    normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
}

async function impLoad(){
  const seq = ++impSeq;
  let d;
  try { d = await api(`/api/requisitos/impacto?norma_id=${impNormaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ impEl("tabela").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== impSeq) return;
  impRender(d);
}

function impRender(d){
  const ed = isEditor();
  const rows = d.requisitos || [];
  impEl("resumo").innerHTML = `Economia total estimada: <strong>${impMoeda(d.resumo.economia_total)}</strong> · Requisitos com dados: ${d.resumo.requisitos_com_dados}/${d.resumo.requisitos}`;
  if (!rows.length){ impEl("tabela").innerHTML = `<p class="muted">Nenhum requisito.</p>`; impEl("graf").style.display="none"; return; }
  const campo = (rid, nome, val)=> ed
    ? `<input type="number" min="0" step="any" data-req="${rid}" data-f="${nome}" value="${val==null?"":val}" class="imp-in" style="width:110px" />`
    : impMoeda(val);
  impEl("tabela").innerHTML = `<table class="pdm-revs">
    <thead><tr><th>Cláusula</th><th>Requisito</th><th>Custo atual</th><th>Custo projetado</th><th>Volume</th><th>Economia</th></tr></thead>
    <tbody>${rows.map(r=>`<tr>
      <td>${escapeHtml(r.codigo_clausula||"—")}</td>
      <td>${escapeHtml(r.titulo)}</td>
      <td>${campo(r.id,"custo_atual",r.custo_atual)}</td>
      <td>${campo(r.id,"custo_projetado",r.custo_projetado)}</td>
      <td>${campo(r.id,"volume",r.volume)}</td>
      <td><strong>${impMoeda(r.economia)}</strong></td>
    </tr>`).join("")}</tbody></table>`;
  if (ed) impEl("tabela").querySelectorAll(".imp-in").forEach(inp=>{ inp.onchange = ()=>impSalvar(Number(inp.dataset.req), inp.dataset.f, inp.value); });
  impGrafico(rows);
}

async function impSalvar(reqId, campo, valor){
  const body = {empresa_id: state.empresaId};
  body[campo] = valor === "" ? null : Number(valor);
  try { await api(`/api/requisitos/${reqId}?empresa_id=${state.empresaId||""}`, {method:"PUT", body}); impLoad(); }
  catch(e){ alert(e.message); impLoad(); }
}

function impGrafico(rows){
  const host = impEl("graf");
  const com = rows.filter(r=>r.economia!=null && r.economia!==0);
  if (!com.length || typeof Plotly === "undefined"){ host.style.display="none"; return; }
  host.style.display = "";
  const dados = com.slice().sort((a,b)=>(b.economia||0)-(a.economia||0));
  const trace = {type:"bar", x:dados.map(r=>r.codigo_clausula||("#"+r.id)), y:dados.map(r=>r.economia),
    marker:{color:"#2563eb"}, hovertemplate:"%{x}<br>Economia: %{y:,.2f}<extra></extra>"};
  Plotly.newPlot("imp-graf", [trace], {height:260, margin:{l:60,r:10,t:20,b:40}, yaxis:{title:"Economia"}}, {responsive:true, displayModeBar:false});
}
