// Rastreabilidade — parte da seleção da Norma/Regulamento e gera a árvore:
// Norma → Requisitos → vínculos (processo/Issue/RNC/ação) e relações (requisito↔requisito).
// Exibe e permite registrar observações: nos vínculos/relações e nas mudanças (change request).
let rastSeq = 0;
let rastNormaId = null;

const RAST_SIT = {conforme:["🟩","Conforme"], nao_conforme:["🟥","Não conforme"], nao_avaliado:["⬜","Não avaliado"]};
const RAST_ALVO = {processo:"Processo", issue:"Issue", rnc:"RNC", acao:"Ação"};
const RAST_MUD_SIT = (typeof REQ_MUD_SIT !== "undefined") ? REQ_MUD_SIT : {proposta:"Proposta", aprovada:"Aprovada", rejeitada:"Rejeitada"};
function rastEl(id){ return document.getElementById("rast-"+id); }
function rastPrio(v){ return (typeof REQ_PRIO!=="undefined") ? reqLabel(REQ_PRIO, v) : v; }

function resetRastreabilidade(){
  rastSeq++; rastNormaId = null;
  const ws = document.getElementById("rastreabilidadeWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadRastreabilidade(){
  if (rastEl("norma")) { rastLoadNormas(); return; }
  document.getElementById("rastreabilidadeWorkspace").innerHTML = `
    <div class="card">
      <label>Norma / Regulamento</label>
      <select id="rast-norma"><option value="">Selecione uma norma…</option></select>
      <div class="req-tools"><button class="btn" id="rast-export" type="button" disabled>Exportar rastreabilidade (CSV)</button></div>
      <p class="hint">A árvore mostra a norma, seus requisitos e, em cada um, os vínculos (processo/Issue/RNC/ação), as relações com outros requisitos e as mudanças (change request). As observações podem ser registradas aqui (editor/admin).</p>
    </div>
    <div id="rast-audit" class="card"><p class="muted">Selecione uma norma para ver a auditoria de rastreabilidade.</p></div>
    <div id="rast-arvore" class="card"><p class="muted">Selecione uma norma.</p></div>`;
  rastEl("norma").onchange = ()=>{
    rastNormaId = Number(rastEl("norma").value)||null;
    rastEl("export").disabled = !rastNormaId;
    if(rastNormaId){ rastDrawArvore(rastNormaId); rastDrawAuditoria(rastNormaId); }
    else { rastEl("arvore").innerHTML = `<p class="muted">Selecione uma norma.</p>`; rastEl("audit").innerHTML = `<p class="muted">Selecione uma norma para ver a auditoria de rastreabilidade.</p>`; }
  };
  rastEl("export").onclick = ()=>{ if(rastNormaId) window.open(`/api/requisitos/rastreabilidade-export?norma_id=${rastNormaId}&empresa_id=${state.empresaId||""}`, "_blank"); };
  rastLoadNormas();
}

async function rastLoadNormas(){
  const seq = ++rastSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ rastEl("arvore").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== rastSeq) return;
  rastEl("norma").innerHTML = `<option value="">Selecione uma norma…</option>` +
    normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
}

async function rastDrawArvore(normaId){
  const seq = ++rastSeq;
  let d;
  try { d = await api(`/api/requisitos/arvore?norma_id=${normaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ rastEl("arvore").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== rastSeq) return;
  rastEl("arvore").innerHTML = rastArvoreHtml(d);
  rastWire();
}

const RAST_AUDIT_FLAGS = [["sem_fonte","sem fonte"],["sem_justificativa","sem justificativa"],["sem_vinculo","sem vínculo"],["sem_verificacao","sem verificação"]];
async function rastDrawAuditoria(normaId){
  const host = rastEl("audit");
  if (!host) return;
  let d;
  try { d = await api(`/api/requisitos/auditoria?norma_id=${normaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  const r = d.resumo || {total:0};
  const resumo = `<div class="rast-audit-resumo">
    <strong>Auditoria de rastreabilidade</strong> — ${r.total} requisito(s):
    ${RAST_AUDIT_FLAGS.map(([k,l])=>`<span class="rast-audit-chip${r[k]?" alerta":""}">${escapeHtml(l)}: ${r[k]||0}</span>`).join("")}</div>`;
  const problem = (d.itens||[]).filter(it=>it.sem_fonte||it.sem_justificativa||it.sem_vinculo||it.sem_verificacao);
  const linhas = problem.length
    ? problem.map(it=>`<div class="rast-audit-item">
        <strong>${escapeHtml(it.codigo_clausula||"—")}</strong> ${escapeHtml(it.titulo)}
        ${RAST_AUDIT_FLAGS.filter(([k])=>it[k]).map(([,l])=>`<span class="rast-tag rast-audit-alerta">${escapeHtml(l)}</span>`).join("")}
      </div>`).join("")
    : `<p class="muted">Nenhuma lacuna: todos os requisitos têm fonte, justificativa, vínculo e verificação.</p>`;
  host.innerHTML = resumo + linhas;
}

// Observação de um vínculo/relação: texto para visualizador; campo + salvar para editor.
function rastObsHtml(kind, reqId, itemId, obs, ed){
  if (!ed) return `<span class="rast-obs muted">📝 ${escapeHtml(obs||"—")}</span>`;
  return `<span class="rast-obs-edit">
    <input class="rast-obs-input" data-kind="${kind}" data-req="${reqId}" data-id="${itemId}" value="${escapeHtml(obs||"")}" placeholder="Observação…" maxlength="2000" />
    <button class="btn rast-obs-save" data-kind="${kind}" data-req="${reqId}" data-id="${itemId}" type="button">salvar</button>
  </span>`;
}

function rastMudHtml(reqId, muds, ed){
  const linhas = (muds||[]).map(m=>`
    <li class="rast-li rast-mud rast-mud-${escapeHtml(m.situacao)}">
      <strong>${escapeHtml(RAST_MUD_SIT[m.situacao]||m.situacao)}</strong> — ${escapeHtml(m.descricao)}
      <div class="muted">por ${escapeHtml(m.solicitante_nome||"—")}${m.aprovador_nome?` · decidido por ${escapeHtml(m.aprovador_nome)}`:""}${m.decisao_obs?` · 📝 ${escapeHtml(m.decisao_obs)}`:""}</div>
      ${ed&&m.situacao==="proposta"?`<button class="btn rast-mud-ok" data-req="${reqId}" data-id="${m.id}" type="button">Aprovar</button>
        <button class="btn rast-mud-no" data-req="${reqId}" data-id="${m.id}" type="button">Rejeitar</button>`:""}
    </li>`).join("");
  const vazio = linhas ? "" : `<li class="rast-li muted">Sem solicitações de mudança.</li>`;
  const add = ed ? `<li class="rast-li rast-mud-add-wrap">
      <input class="rast-mud-desc" data-req="${reqId}" placeholder="Descreva a mudança proposta" maxlength="4000" />
      <button class="btn rast-mud-add" data-req="${reqId}" type="button">Propor mudança</button>
    </li>` : "";
  return `<li class="rast-li rast-mud-bloco"><span class="rast-mud-titulo">Mudanças (change request)</span>
    <ul class="rast-mud-lista">${linhas}${vazio}${add}</ul></li>`;
}

function rastReqHtml(r, ed){
  const [dot, sitLabel] = RAST_SIT[r.situacao] || RAST_SIT.nao_avaliado;
  const prio = rastPrio(r.prioridade);
  const filhos = [];
  (r.vinculos||[]).forEach(v=>{
    filhos.push(`<li class="rast-li rast-vinc"><span class="rast-ico rast-${escapeHtml(v.alvo_tipo)}">🔗</span>
      ${escapeHtml(v.tipo_relacao||"")} → <strong>${escapeHtml(v.alvo_label||"")}</strong>
      <span class="rast-tag rast-${escapeHtml(v.alvo_tipo)}">${escapeHtml(RAST_ALVO[v.alvo_tipo]||v.alvo_tipo)}</span>
      <div class="rast-obs-linha">${rastObsHtml("vinculos", r.id, v.id, v.observacao, ed)}</div></li>`);
  });
  (r.relacoes||[]).forEach(rel=>{
    filhos.push(`<li class="rast-li rast-rel">↔ ${escapeHtml(rel.tipo)} → <strong>${escapeHtml(rel.destino_clausula||("#"+rel.destino_id))}</strong>
      <span class="rast-tag rast-requisito">Requisito</span>
      <div class="rast-obs-linha">${rastObsHtml("relacoes", r.id, rel.id, rel.observacao, ed)}</div></li>`);
  });
  const vincRel = filhos.length ? filhos.join("") : `<li class="rast-li rast-vazio muted">Sem vínculos ou relações.</li>`;
  const corpo = `<ul class="rast-filhos">${vincRel}${rastMudHtml(r.id, r.mudancas, ed)}</ul>`;
  return `<details class="rast-req" open>
    <summary><span class="rast-dot">${dot}</span> <strong>${escapeHtml(r.codigo_clausula||"—")}</strong> ${escapeHtml(r.titulo)}
      ${prio?`<span class="rast-tag rast-prio">${escapeHtml(prio)}</span>`:""}
      <span class="rast-tag rast-cat">${escapeHtml(r.categoria)}</span>
      <span class="rast-sit muted">${escapeHtml(sitLabel)}</span></summary>
    ${corpo}
  </details>`;
}

function rastGrupoHtml(titulo, reqs, ed){
  if (!reqs.length) return "";
  return `<div class="rast-classe"><div class="rast-classe-tit">📂 ${escapeHtml(titulo)} <span class="muted">(${reqs.length})</span></div>
    <div class="rast-reqs">${reqs.map(r=>rastReqHtml(r, ed)).join("")}</div></div>`;
}

function rastArvoreHtml(d){
  const ed = isEditor();
  const reqs = d.requisitos || [];
  if (!reqs.length) return `<div class="rast-tree"><div class="rast-raiz">📚 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)}</div><p class="muted">Esta norma ainda não tem requisitos.</p></div>`;
  const classes = d.classes || [];
  let corpo = "";
  if (classes.length){
    // Agrupa por classe (na ordem definida) + bucket "Sem classe".
    classes.forEach(c=>{ corpo += rastGrupoHtml((c.codigo?c.codigo+" ":"")+c.nome, reqs.filter(r=>r.classe_id===c.id), ed); });
    corpo += rastGrupoHtml("Sem classe", reqs.filter(r=>!r.classe_id), ed);
  } else {
    corpo = `<div class="rast-reqs">${reqs.map(r=>rastReqHtml(r, ed)).join("")}</div>`;
  }
  return `<div class="rast-tree">
    <div class="rast-raiz">📚 ${escapeHtml(d.norma.codigo)} — ${escapeHtml(d.norma.titulo)} <span class="muted">(${reqs.length} requisito(s)${classes.length?`, ${classes.length} classe(s)`:""})</span></div>
    ${corpo}
  </div>`;
}

function rastWire(){
  const host = rastEl("arvore");
  if (!host) return;
  host.querySelectorAll(".rast-obs-save").forEach(b=>{
    b.onclick = ()=>{
      const inp = host.querySelector(`.rast-obs-input[data-kind="${b.dataset.kind}"][data-id="${b.dataset.id}"][data-req="${b.dataset.req}"]`);
      rastSalvarObs(b.dataset.kind, Number(b.dataset.req), Number(b.dataset.id), inp ? inp.value : "");
    };
  });
  host.querySelectorAll(".rast-mud-add").forEach(b=>{
    b.onclick = ()=>{
      const inp = host.querySelector(`.rast-mud-desc[data-req="${b.dataset.req}"]`);
      rastProporMudanca(Number(b.dataset.req), inp ? inp.value : "");
    };
  });
  host.querySelectorAll(".rast-mud-ok").forEach(b=>{ b.onclick = ()=>rastDecidirMudanca(Number(b.dataset.req), Number(b.dataset.id), "aprovada"); });
  host.querySelectorAll(".rast-mud-no").forEach(b=>{ b.onclick = ()=>rastDecidirMudanca(Number(b.dataset.req), Number(b.dataset.id), "rejeitada"); });
}

async function rastSalvarObs(kind, reqId, itemId, obs){
  try {
    await api(`/api/requisitos/${reqId}/${kind}/${itemId}`, {method:"PUT", body:{observacao:(obs||"").trim(), empresa_id:state.empresaId}});
    if (rastNormaId) rastDrawArvore(rastNormaId);
  } catch(e){ alert(e.message); }
}

async function rastProporMudanca(reqId, desc){
  desc = (desc||"").trim();
  if (!desc){ alert("Descreva a mudança proposta."); return; }
  try {
    await api(`/api/requisitos/${reqId}/mudancas`, {method:"POST", body:{descricao:desc, empresa_id:state.empresaId}});
    if (rastNormaId) rastDrawArvore(rastNormaId);
  } catch(e){ alert(e.message); }
}

async function rastDecidirMudanca(reqId, mid, situacao){
  const obs = prompt(`Observação da decisão (${situacao}):`) || "";
  try {
    await api(`/api/requisitos/${reqId}/mudancas/${mid}/decidir`, {method:"POST", body:{situacao, decisao_obs:obs, empresa_id:state.empresaId}});
    if (rastNormaId) rastDrawArvore(rastNormaId);
  } catch(e){ alert(e.message); }
}
