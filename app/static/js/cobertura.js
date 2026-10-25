// Matriz de Conformidade — tabela editável + mapa (heatmap) de requisito × situação/cobertura.
let cobSeq = 0;
let cobNormaId = null;
let cobLast = null;
let cobView = "tabela";

const COB_SIT = [["nao_avaliado","Não avaliado"],["conforme","Conforme"],["nao_conforme","Não conforme"]];
const COB_ALVOS = [["processo","Processo"],["issue","Issue"],["rnc","RNC"],["acao","Ação"],["familia","Família"],["grupo","Grupo"],["produto","Produto"]];
function cobEl(id){ return document.getElementById("cob-"+id); }
function cobSitLabel(v){ const f=COB_SIT.find(p=>p[0]===v); return f?f[1]:v; }
function cobAlvoLabel(k){ const f=COB_ALVOS.find(a=>a[0]===k); return f?f[1]:k; }
function cobVincChips(vinc){
  const e = Object.entries(vinc||{}).filter(([k,n])=>n>0);
  if (!e.length) return `<span class="cob-sem">— sem vínculo</span>`;
  return e.map(([k,n])=>`<span class="cob-chip cob-chip-${escapeHtml(k)}">${escapeHtml(cobAlvoLabel(k))} ×${n}</span>`).join(" ");
}

function resetCobertura(){
  cobNormaId = null; cobLast = null; cobView = "tabela";
  cobSeq++;
  const ws = document.getElementById("coberturaWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadCobertura(){
  if (cobEl("norma")) { cobLoadNormas(); return; }
  buildCobertura();
  cobLoadNormas();
}

function buildCobertura(){
  const prioOpts = `<option value="">Todas</option>` + (typeof REQ_PRIO!=="undefined"?REQ_PRIO.slice(1):[]).map(([v,l])=>`<option value="${v}">${escapeHtml(l)}</option>`).join("");
  const catOpts = `<option value="">Todas</option>` + (typeof REQ_CAT!=="undefined"?REQ_CAT:[]).map(([v,l])=>`<option value="${v}">${escapeHtml(l)}</option>`).join("");
  document.getElementById("coberturaWorkspace").innerHTML = `
    <div class="card">
      <div class="grid-3">
        <div><label>Norma</label><select id="cob-norma"><option value="">Selecione…</option></select></div>
        <div><label>Prioridade</label><select id="cob-f-prio">${prioOpts}</select></div>
        <div><label>Categoria</label><select id="cob-f-cat">${catOpts}</select></div>
      </div>
      <div class="req-tools">
        <button class="btn primary" id="cob-view-tabela" type="button">Tabela</button>
        <button class="btn" id="cob-view-mapa" type="button">Mapa</button>
        <button class="btn" id="cob-ia" type="button">Consultar IA (lacunas)</button>
      </div>
    </div>
    <details class="card cob-ajuda">
      <summary>Como ler esta matriz (e o que são os vínculos)</summary>
      <p>Cada linha é um <strong>requisito</strong> da norma. A matriz responde duas perguntas:</p>
      <ul>
        <li><strong>Situação</strong> — o requisito está sendo atendido? 🟩 <em>Conforme</em> · 🟥 <em>Não conforme</em> · ⬜ <em>Não avaliado</em>.</li>
        <li><strong>Vínculos (cobertura)</strong> — a quais <em>controles</em> o requisito está ligado, ou seja, <strong>onde ele é cumprido/verificado</strong>:
          <span class="cob-chip cob-chip-processo">Processo</span> onde o requisito é executado ·
          <span class="cob-chip cob-chip-issue">Issue</span> / <span class="cob-chip cob-chip-rnc">RNC</span> desvio tratado ·
          <span class="cob-chip cob-chip-acao">Ação</span> ação que o atende.
          Sem nenhum vínculo = <span class="cob-sem">lacuna de cobertura</span>.</li>
      </ul>
      <p><strong>Exemplos:</strong> <span class="cob-chip cob-chip-processo">Processo ×1</span> = coberto por 1 processo ·
        <span class="cob-chip cob-chip-issue">Issue ×2</span> = ligado a 2 Issues ·
        <span class="cob-sem">— sem vínculo</span> = ninguém cumpre/verifica este requisito ainda (lacuna).</p>
      <p class="hint">Para criar um vínculo: botão <strong>+vínculo</strong> na linha. Para ver o desenho completo (quem liga a quê), use a aba <strong>Rastreabilidade (árvore)</strong>.</p>
    </details>
    <div id="cob-resumo" class="hint"></div>
    <div id="cob-tabela" class="card"></div>
    <div id="cob-map" class="card" style="display:none"></div>`;
  cobEl("norma").onchange = ()=>{ cobNormaId = Number(cobEl("norma").value)||null; if(cobNormaId) cobLoadMatriz(); else { cobLast=null; cobEl("tabela").innerHTML=""; cobEl("map").innerHTML=""; cobEl("resumo").innerHTML=""; } };
  cobEl("f-prio").onchange = cobRenderCurrent;
  cobEl("f-cat").onchange = cobRenderCurrent;
  cobEl("view-tabela").onclick = ()=>cobSetView("tabela");
  cobEl("view-mapa").onclick = ()=>cobSetView("mapa");
  cobEl("ia").onclick = cobConsultarIA;
}

async function cobLoadNormas(){
  const seq = ++cobSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ cobEl("tabela").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq!==cobSeq) return;
  cobEl("norma").innerHTML = `<option value="">Selecione…</option>` +
    normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
}

async function cobLoadMatriz(){
  const seq = ++cobSeq;
  let m;
  try { m = await api(`/api/conformidade/matriz?norma_id=${cobNormaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ cobEl("tabela").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq!==cobSeq) return;
  cobLast = m;
  cobRenderCurrent();
}

function cobSetView(v){
  cobView = v;
  cobEl("view-tabela").classList.toggle("primary", v==="tabela");
  cobEl("view-mapa").classList.toggle("primary", v==="mapa");
  cobRenderCurrent();
}

function cobFiltrados(){
  if (!cobLast) return [];
  const fp = cobEl("f-prio").value, fc = cobEl("f-cat").value;
  return cobLast.requisitos.filter(r => (!fp || r.prioridade===fp) && (!fc || r.categoria===fc));
}

function cobRenderCurrent(){
  if (!cobLast){ return; }
  const rows = cobFiltrados();
  const nc = rows.filter(r=>r.situacao==="nao_conforme").length;
  const co = rows.filter(r=>r.situacao==="conforme").length;
  const na = rows.filter(r=>r.situacao==="nao_avaliado").length;
  const sv = rows.filter(r=>r.total_vinculos===0).length;
  cobEl("resumo").innerHTML = `Total: <strong>${rows.length}</strong> · Conformes: ${co} · Não conformes: <strong>${nc}</strong> · Não avaliados: ${na} · Sem vínculo: <strong>${sv}</strong>`;
  const mapa = cobView==="mapa";
  cobEl("tabela").style.display = mapa ? "none" : "";
  cobEl("map").style.display = mapa ? "" : "none";
  if (mapa) cobRenderMapa(rows); else cobRenderTabela(rows);
}

function cobRenderTabela(rows){
  if (!rows.length){ cobEl("tabela").innerHTML = `<p class="muted">Nenhum requisito.</p>`; return; }
  const ed = isEditor();
  const linhas = rows.map(req=>{
    const vtxt = cobVincChips(req.vinculos);
    const sit = ed
      ? `<select data-req="${req.id}" class="cob-sit">${COB_SIT.map(([v,l])=>`<option value="${v}"${v===req.situacao?" selected":""}>${l}</option>`).join("")}</select>`
      : cobSitLabel(req.situacao);
    const cls = req.situacao==="nao_conforme" ? ' class="cob-bad"' : (req.total_vinculos===0 ? ' class="cob-warn"' : '');
    return `<tr${cls}>
      <td>${escapeHtml(req.codigo_clausula||"—")}</td>
      <td>${escapeHtml(req.titulo)}</td>
      <td>${escapeHtml(req.categoria)}</td>
      <td>${sit}</td>
      <td>${escapeHtml(vtxt)}${ed?` <button class="btn cob-addv" data-req="${req.id}" type="button">+vínculo</button>`:""}</td>
    </tr>`;
  }).join("");
  cobEl("tabela").innerHTML = `<table class="pdm-revs"><thead><tr><th>Cláusula</th><th>Requisito</th><th>Categoria</th><th>Situação</th><th>Vínculos</th></tr></thead><tbody>${linhas}</tbody></table>`;
  if (ed){
    cobEl("tabela").querySelectorAll(".cob-sit").forEach(s=>{ s.onchange = ()=>cobSetSituacao(Number(s.dataset.req), s.value); });
    cobEl("tabela").querySelectorAll(".cob-addv").forEach(b=>{ b.onclick = ()=>cobAddVinculo(Number(b.dataset.req)); });
  }
}

function cobRenderMapa(rows){
  const host = cobEl("map");
  if (!rows.length){ host.innerHTML = `<p class="muted">Nenhum requisito.</p>`; return; }
  if (typeof Plotly === "undefined"){ host.innerHTML = `<p class="muted">Gráfico indisponível.</p>`; return; }
  const statusCode = {conforme:2, nao_avaliado:1, nao_conforme:0};
  const cols = ["Conformidade", ...COB_ALVOS.map(a=>a[1])];
  const y = rows.map(r => (r.total_vinculos===0 ? "⚠ " : "") + (r.codigo_clausula || "—"));
  const z = [], text = [];
  rows.forEach(r=>{
    const zrow = [statusCode[r.situacao]], trow = [cobSitLabel(r.situacao)];
    COB_ALVOS.forEach(([k])=>{ const n = (r.vinculos||{})[k]||0; zrow.push(n>0?2:null); trow.push(n>0?String(n):""); });
    z.push(zrow); text.push(trow);
  });
  const legenda = `<div class="cob-legenda"><span class="cob-lg cob-lg-conf">Conforme</span>
    <span class="cob-lg cob-lg-na">Não avaliado</span><span class="cob-lg cob-lg-nc">Não conforme</span>
    <span>⚠ sem vínculo · número = qtd. de vínculos</span></div>`;
  host.innerHTML = legenda + `<div id="cob-plot"></div>`;
  const trace = {
    type: "heatmap", x: cols, y, z, text,
    texttemplate: "%{text}", textfont: {size: 11},
    xgap: 3, ygap: 3, zmin: 0, zmax: 2,
    colorscale: [[0, "#ef4444"], [0.5, "#cbd5e1"], [1, "#22c55e"]],
    showscale: false,
    hovertemplate: "%{y} · %{x}<br>%{text}<extra></extra>",
  };
  const layout = {
    height: Math.max(220, 90 + rows.length * 30),
    margin: {l: 70, r: 10, t: 28, b: 10},
    xaxis: {side: "top", fixedrange: true},
    yaxis: {autorange: "reversed", automargin: true, fixedrange: true},
  };
  Plotly.newPlot("cob-plot", [trace], layout, {responsive: true, displayModeBar: false});
}

async function cobSetSituacao(reqId, situacao){
  const evidencia = situacao === "nao_avaliado" ? "" : (prompt("Evidência (opcional):") || "");
  try { await api("/api/conformidade", {method:"POST", body:{requisito_id:reqId, situacao, evidencia, empresa_id:state.empresaId}}); cobLoadMatriz(); }
  catch(e){ alert(e.message); cobLoadMatriz(); }
}

async function cobAddVinculo(reqId){
  const tipo = prompt("Tipo do alvo: processo, issue, rnc, acao, familia, grupo ou produto"); if(!tipo) return;
  if (!COB_ALVOS.some(a=>a[0]===tipo)){ alert("Tipo inválido."); return; }
  const alvo = Number(prompt("ID do alvo (número):")); if(!alvo) return;
  const rel = (prompt("Relação: satisfaz, verifica, implementa, mitiga ou outro", "satisfaz") || "satisfaz").trim();
  try { await api(`/api/requisitos/${reqId}/vinculos`, {method:"POST", body:{alvo_tipo:tipo, alvo_id:alvo, tipo_relacao:rel, empresa_id:state.empresaId}}); cobLoadMatriz(); }
  catch(e){ alert(e.message); }
}

async function cobConsultarIA(){
  if (!cobNormaId){ alert("Selecione uma norma."); return; }
  try {
    const result = await api("/api/conformidade/matriz/preparar", {method:"POST", body:{norma_id:cobNormaId, empresa_id:state.empresaId}});
    openToolAI("conformidade", result);
  } catch(e){ alert(e.message); }
}
