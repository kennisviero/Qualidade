// Requisitos/cláusulas de uma Norma — sub-painel no detalhe da Norma.
// Fase A (IREB): prioridade (MoSCoW), atributos configuráveis, relações requisito↔requisito.
let reqNormaId = null;
let reqLista = [];
let reqSelId = null;
let reqClasses = [];

const REQ_CAT = [["normativo","Normativo"],["interno","Interno"],["cliente","Cliente"],["legal","Legal"]];
const REQ_OBR = [["obrigatorio","Obrigatório"],["recomendado","Recomendado"],["informativo","Informativo"]];
const REQ_PRIO = [["","—"],["must","Essencial"],["should","Importante"],["could","Desejável"],["wont","Não prioritário"]];
const REQ_ESTADO = [["ativo","Ativo"],["revogado","Revogado"]];
const REQ_RELTIPO = [["deriva_de","deriva de"],["refina","refina"],["depende","depende de"],["conflita","conflita com"],["duplica","duplica"],["variante_de","variante de"]];
function reqOpts(pairs){ return pairs.map(([v,l])=>`<option value="${v}">${escapeHtml(l)}</option>`).join(""); }
function reqLabel(pairs,v){ const f=pairs.find(p=>p[0]===v); return f?f[1]:v; }
function reqEl(id){ return document.getElementById("req-"+id); }

async function reqLoadForNorma(normaId, hostId){
  reqNormaId = normaId; reqSelId = null;
  const host = document.getElementById(hostId || "nor-requisitos");
  if (!host) return;
  host.innerHTML = `
    <h3>Requisitos / cláusulas</h3>
    ${isAdmin()?`<details id="req-cfg"><summary>Atributos (configuração)</summary><div id="req-cfg-body"></div></details>`:""}
    ${isEditor()?`<details id="req-classes-det"><summary>Classes da norma (agrupam os requisitos)</summary><div id="req-classes-body"></div></details>`:""}
    ${isEditor()?`<div class="grid-3">
      <input id="req-novo-clausula" placeholder="Cláusula (4.1)" maxlength="60" />
      <input id="req-novo-titulo" placeholder="Título do requisito" maxlength="300" />
      <select id="req-novo-cat">${reqOpts(REQ_CAT)}</select>
    </div>
    <div class="req-tools">
      <select id="req-novo-classe" title="Classe"><option value="">— sem classe —</option></select>
      <select id="req-novo-obr">${reqOpts(REQ_OBR)}</select>
      <select id="req-novo-prio" title="Prioridade (MoSCoW)">${reqOpts(REQ_PRIO)}</select>
      <button class="btn primary" id="req-novo-btn" type="button">Adicionar</button>
      <button class="btn" id="req-ia-btn" type="button">Sugerir requisitos (IA)</button>
      <label class="btn" style="cursor:pointer">Importar<input type="file" id="req-import" accept=".csv,.docx,.xlsx" style="display:none" /></label>
      <a class="btn" id="req-export" href="#">Exportar CSV</a>
    </div>`:""}
    <div class="req-tools"><label>Filtrar prioridade</label><select id="req-f-prio">${reqOpts([["","Todas"]].concat(REQ_PRIO.slice(1)))}</select></div>
    <div id="req-list" class="list"></div>
    <div id="req-edit"></div>
    <div id="req-ia-box"></div>`;
  if (isEditor()){
    reqEl("novo-btn").onclick = reqCreate;
    reqEl("import").onchange = (e)=>reqImport(e.target.files[0]);
    reqEl("export").onclick = (e)=>{ e.preventDefault(); window.open(`/api/requisitos/exportar?norma_id=${reqNormaId}&empresa_id=${state.empresaId||""}&formato=csv`, "_blank"); };
    reqEl("ia-btn").onclick = reqSugerirIA;
  }
  if (isAdmin()) reqConfigAtributos();
  reqEl("f-prio").onchange = reqLoadList;
  await reqLoadClasses();
  reqLoadList();
}

// --- Classes da norma ---
function reqClasseOpts(sel){
  const base = `<option value="">— sem classe —</option>`;
  return base + reqClasses.map(c=>`<option value="${c.id}"${String(sel||"")===String(c.id)?" selected":""}>${escapeHtml((c.codigo?c.codigo+" ":"")+c.nome)}</option>`).join("");
}

async function reqLoadClasses(){
  try { reqClasses = await api(`/api/requisitos/classes?norma_id=${reqNormaId}&empresa_id=${state.empresaId||""}`); }
  catch(e){ reqClasses = []; }
  const nc = reqEl("novo-classe"); if (nc) nc.innerHTML = reqClasseOpts("");
  const body = reqEl("classes-body");
  if (body){
    body.innerHTML = reqClasses.map(c=>`<div class="req-cfg-item">${escapeHtml((c.codigo?c.codigo+" ":"")+c.nome)}
        <button class="btn req-classe-del" data-id="${c.id}" type="button">x</button></div>`).join("") +
      `<div class="req-tools">
        <input id="req-classe-cod" placeholder="código (8)" maxlength="60" style="max-width:90px" />
        <input id="req-classe-nome" placeholder="nome da classe (ex.: Operação)" maxlength="200" />
        <button class="btn primary" id="req-classe-add" type="button">Adicionar classe</button>
      </div>`;
    body.querySelectorAll(".req-classe-del").forEach(b=>{ b.onclick=()=>reqDelClasse(Number(b.dataset.id)); });
    reqEl("classe-add").onclick = reqAddClasse;
  }
}

async function reqAddClasse(){
  const nome = reqEl("classe-nome").value.trim();
  if (!nome){ alert("Informe o nome da classe."); return; }
  try {
    await api("/api/requisitos/classes", {method:"POST", body:{norma_id:reqNormaId, codigo:reqEl("classe-cod").value.trim(), nome, empresa_id:state.empresaId}});
    reqEl("classe-nome").value=""; reqEl("classe-cod").value="";
    await reqLoadClasses(); reqLoadList();
  } catch(e){ alert(e.message); }
}

async function reqDelClasse(id){
  if (!confirm("Excluir esta classe? Os requisitos dela ficam sem classe.")) return;
  try { await api(`/api/requisitos/classes/${id}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); await reqLoadClasses(); reqLoadList(); if(reqSelId) reqSelect(reqSelId); }
  catch(e){ alert(e.message); }
}

async function reqLoadList(){
  const prio = reqEl("f-prio") ? reqEl("f-prio").value : "";
  let rows;
  try { rows = await api(`/api/requisitos?norma_id=${reqNormaId}&empresa_id=${state.empresaId||""}${prio?`&prioridade=${prio}`:""}`); }
  catch(e){ reqEl("list").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  reqLista = rows;
  if (!rows.length){ reqEl("list").innerHTML = `<p class="muted">Nenhum requisito.</p>`; return; }
  const ed = isEditor();
  const item = (r)=>`
    <div class="req-item${r.id===reqSelId?" sel":""}" data-id="${r.id}">
      <strong>${escapeHtml(r.codigo_clausula||"—")}</strong> ${escapeHtml(r.titulo)}
      <span class="muted">· ${escapeHtml(reqLabel(REQ_CAT,r.categoria))}${r.prioridade?` · ${escapeHtml(reqLabel(REQ_PRIO,r.prioridade))}`:""}${r.estado==="revogado"?" · revogado":""}</span>
      ${ed?`<button class="btn req-del" data-id="${r.id}" type="button">excluir</button>`:""}
    </div>`;
  // Agrupa por classe da norma (ordem das classes) + bucket "Sem classe".
  let html = "";
  if (reqClasses.length){
    reqClasses.forEach(c=>{
      const doGrupo = rows.filter(r=>r.classe_id===c.id);
      if (doGrupo.length) html += `<div class="req-classe-grupo"><div class="req-classe-tit">📂 ${escapeHtml((c.codigo?c.codigo+" ":"")+c.nome)} <span class="muted">(${doGrupo.length})</span></div>${doGrupo.map(item).join("")}</div>`;
    });
    const sem = rows.filter(r=>!r.classe_id);
    if (sem.length) html += `<div class="req-classe-grupo"><div class="req-classe-tit req-sem-classe">📂 Sem classe <span class="muted">(${sem.length})</span></div>${sem.map(item).join("")}</div>`;
  } else {
    html = rows.map(item).join("");
  }
  reqEl("list").innerHTML = html;
  reqEl("list").querySelectorAll(".req-item").forEach(el=>{ el.onclick=(ev)=>{ if(ev.target.classList.contains("req-del"))return; reqSelect(Number(el.dataset.id)); }; });
  if (ed) reqEl("list").querySelectorAll(".req-del").forEach(b=>{ b.onclick=()=>reqDelete(Number(b.dataset.id)); });
}

async function reqCreate(){
  const titulo = reqEl("novo-titulo").value.trim();
  if (!titulo){ alert("Informe o título do requisito."); return; }
  const body = {norma_id: reqNormaId, empresa_id: state.empresaId, titulo,
    codigo_clausula: reqEl("novo-clausula").value.trim(),
    categoria: reqEl("novo-cat").value, obrigatoriedade: reqEl("novo-obr").value, prioridade: reqEl("novo-prio").value,
    classe_id: Number(reqEl("novo-classe") && reqEl("novo-classe").value) || null};
  try { await api("/api/requisitos", {method:"POST", body}); ["novo-clausula","novo-titulo"].forEach(id=>{reqEl(id).value="";}); reqLoadList(); }
  catch(e){ alert(e.message); }
}

async function reqDelete(id){
  if (!confirm("Excluir este requisito?")) return;
  try { await api(`/api/requisitos/${id}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); if(reqSelId===id){reqSelId=null;reqEl("edit").innerHTML="";} reqLoadList(); }
  catch(e){ alert(e.message); }
}

// --- Painel de edição por requisito (campos + prioridade + atributos + relações) ---
async function reqSelect(id){
  let d;
  try { d = await api(`/api/requisitos/${id}?empresa_id=${state.empresaId||""}`); }
  catch(e){ reqEl("edit").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  reqSelId = id;
  const ed = isEditor();
  const ro = ed ? "" : "disabled";
  const atr = (d.atributos||[]).map(a=>{
    let campo;
    if (a.tipo==="lista") campo = `<select data-def="${a.id}" ${ro}>${reqOpts([["",""]].concat((a.opcoes||[]).map(o=>[o,o])))}</select>`;
    else if (a.tipo==="booleano") campo = `<select data-def="${a.id}" ${ro}><option value="">—</option><option value="1">Sim</option><option value="0">Não</option></select>`;
    else campo = `<input data-def="${a.id}" value="${escapeHtml(a.valor||"")}" ${ro} ${a.tipo==="numero"?'inputmode="decimal"':""} ${a.tipo==="data"?'placeholder="AAAA-MM-DD"':""} />`;
    return `<div><label>${escapeHtml(a.rotulo)}${a.obrigatorio?" *":""}</label>${campo}</div>`;
  }).join("");
  const rels = (d.relacoes||[]).map(r=>`<div class="req-rel">${escapeHtml(reqLabel(REQ_RELTIPO,r.tipo))} <strong>${escapeHtml(r.destino_clausula||"—")}</strong> ${escapeHtml(r.destino_titulo||"")}
      ${ed?`<button class="btn req-rel-del" data-id="${r.id}" type="button">x</button>`:""}</div>`).join("") || '<p class="muted">Sem relações.</p>';
  const outros = reqLista.filter(x=>x.id!==id);
  reqEl("edit").innerHTML = `
    <div class="card">
      <h4>Editar ${escapeHtml(d.codigo_clausula||"")} ${escapeHtml(d.titulo)}</h4>
      <div class="grid-3">
        <div><label>Cláusula</label><input id="req-e-clausula" value="${escapeHtml(d.codigo_clausula||"")}" ${ro} /></div>
        <div><label>Prioridade</label><select id="req-e-prio" ${ro}>${reqOpts(REQ_PRIO)}</select></div>
        <div><label>Variante</label><input id="req-e-variante" value="${escapeHtml(d.variante||"")}" ${ro} placeholder="ex.: 127V, BR" /></div>
      </div>
      <label>Classe (agrupador na norma)</label><select id="req-e-classe" ${ro}>${reqClasseOpts(d.classe_id)}</select>
      <label>Título</label><input id="req-e-titulo" value="${escapeHtml(d.titulo)}" ${ro} />
      <label>Texto</label><textarea id="req-e-texto" rows="2" ${ro}>${escapeHtml(d.texto||"")}</textarea>
      <label>Fonte (origem do requisito)</label><input id="req-e-fonte" value="${escapeHtml(d.fonte||"")}" ${ro} placeholder="ex.: ISO 9001:2015 §8.5, contrato cliente, requisito legal" />
      <label>Justificativa (por que existe)</label><textarea id="req-e-justif" rows="2" ${ro} placeholder="Racional: por que este requisito existe / o que o motiva">${escapeHtml(d.justificativa||"")}</textarea>
      <div class="grid-3">
        <div><label>Categoria</label><select id="req-e-cat" ${ro}>${reqOpts(REQ_CAT)}</select></div>
        <div><label>Obrigatoriedade</label><select id="req-e-obr" ${ro}>${reqOpts(REQ_OBR)}</select></div>
        <div><label>Estado</label><select id="req-e-estado" ${ro}>${reqOpts(REQ_ESTADO)}</select></div>
      </div>
      ${atr?`<h5>Atributos</h5><div class="grid-2" id="req-e-atrs">${atr}</div>`:""}
      ${ed?`<button class="btn primary" id="req-e-salvar" type="button">Salvar</button>`:""}
      <p id="req-e-msg" class="hint" role="status"></p>
      <h5>Relações (requisito ↔ requisito)</h5>
      <div id="req-rel-list">${rels}</div>
      ${ed?`<div class="req-tools">
        <select id="req-rel-tipo">${reqOpts(REQ_RELTIPO)}</select>
        <select id="req-rel-destino"><option value="">destino…</option>${outros.map(o=>`<option value="${o.id}">${escapeHtml(o.codigo_clausula||"")} ${escapeHtml(o.titulo)}</option>`).join("")}</select>
        <button class="btn" id="req-rel-add" type="button">Relacionar</button>
      </div>`:""}
      <h5>Mudanças (change request)</h5>
      <div id="req-mud-list"><p class="muted">—</p></div>
      ${ed?`<div class="req-tools"><input id="req-mud-desc" placeholder="Descreva a mudança proposta" maxlength="4000" style="flex:1" /><button class="btn" id="req-mud-add" type="button">Propor mudança</button></div>`:""}
      <h5>Aplicabilidade a produtos</h5>
      <div id="req-prod-box"><p class="muted">—</p></div>
      <h5>Versões</h5>
      <div id="req-ver-list"><p class="muted">—</p></div>
      ${ed?`<button class="btn" id="req-ver-add" type="button">Registrar versão</button>`:""}
    </div>`;
  reqEl("e-prio").value = d.prioridade||"";
  reqEl("e-cat").value = d.categoria; reqEl("e-obr").value = d.obrigatoriedade; reqEl("e-estado").value = d.estado;
  (d.atributos||[]).forEach(a=>{ const inp = reqEl("e-atrs") && reqEl("e-atrs").querySelector(`[data-def="${a.id}"]`); if(inp && (a.tipo==="lista"||a.tipo==="booleano")) inp.value = a.valor||""; });
  if (ed){
    reqEl("e-salvar").onclick = ()=>reqSalvarEdicao(id);
    const addb = reqEl("rel-add"); if(addb) addb.onclick = ()=>reqAddRelacao(id);
    reqEl("rel-list").querySelectorAll(".req-rel-del").forEach(b=>{ b.onclick=()=>reqDelRelacao(id, Number(b.dataset.id)); });
    const mb = reqEl("mud-add"); if(mb) mb.onclick = ()=>reqProporMudanca(id);
    const vb = reqEl("ver-add"); if(vb) vb.onclick = ()=>reqRegistrarVersao(id);
  }
  reqLoadMudancas(id);
  reqLoadVersoes(id);
  reqLoadAplicabilidade(id);
  reqLoadList();
}

// --- Aplicabilidade a produtos (vínculo requisito → família/grupo/produto) ---
const REQ_PROD_NIVEIS = [["familia","Família"],["grupo","Grupo"],["produto","Produto"]];
async function reqLoadAplicabilidade(id){
  const host = reqEl("prod-box");
  if (!host) return;
  const ed = isEditor();
  let vincs = [], arv = {familias:[]};
  try {
    [vincs, arv] = await Promise.all([
      api(`/api/requisitos/${id}/vinculos?empresa_id=${state.empresaId||""}`),
      api(`/api/produtos/arvore?empresa_id=${state.empresaId||""}`),
    ]);
  } catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  // mapa id->rótulo por nível
  const lbl = {familia:{}, grupo:{}, produto:{}};
  (arv.familias||[]).forEach(f=>{ lbl.familia[f.id]=f.nome;
    (f.grupos||[]).forEach(g=>{ lbl.grupo[g.id]=g.nome;
      (g.produtos||[]).forEach(p=>{ lbl.produto[p.id]=(p.codigo?p.codigo+" — ":"")+p.nome; }); }); });
  const prodVincs = (vincs||[]).filter(v=>["familia","grupo","produto"].includes(v.alvo_tipo));
  const linhas = prodVincs.length ? prodVincs.map(v=>{
    const nivel = reqLabel(REQ_PROD_NIVEIS, v.alvo_tipo);
    const nome = (lbl[v.alvo_tipo]||{})[v.alvo_id] || ("#"+v.alvo_id);
    return `<div class="req-rel"><strong>${escapeHtml(nivel)}:</strong> ${escapeHtml(nome)} <span class="muted">(${escapeHtml(v.tipo_relacao||"")})</span>
      ${ed?`<button class="btn req-prod-del" data-id="${v.id}" type="button">x</button>`:""}</div>`;
  }).join("") : `<p class="muted">Nenhum produto vinculado.</p>`;
  const famOpts = `<option value="">Família…</option>` + (arv.familias||[]).map(f=>`<option value="${f.id}">${escapeHtml(f.nome)}</option>`).join("");
  const form = ed ? `<div class="req-tools">
      <select id="req-prod-fam" data-arv='1'>${famOpts}</select>
      <select id="req-prod-grp"><option value="">Grupo…</option></select>
      <select id="req-prod-prod"><option value="">Produto…</option></select>
      <select id="req-prod-tipo">${reqOpts([["satisfaz","satisfaz"],["verifica","verifica"],["implementa","implementa"],["mitiga","mitiga"],["outro","outro"]])}</select>
      <button class="btn" id="req-prod-add" type="button">Vincular</button>
    </div><p class="hint">Liga ao nível mais específico escolhido (Produto, senão Grupo, senão Família).</p>` : "";
  host.innerHTML = linhas + form;
  if (!ed) return;
  reqAplicArv = arv;
  host.querySelectorAll(".req-prod-del").forEach(b=>{ b.onclick=()=>reqDelAplic(id, Number(b.dataset.id)); });
  reqEl("prod-fam").onchange = reqAplicFamChange;
  reqEl("prod-grp").onchange = reqAplicGrpChange;
  reqEl("prod-add").onclick = ()=>reqAddAplic(id);
}

let reqAplicArv = {familias:[]};
function reqAplicFamChange(){
  const fid = Number(reqEl("prod-fam").value)||null;
  const fam = (reqAplicArv.familias||[]).find(f=>f.id===fid);
  const grp = reqEl("prod-grp"), prod = reqEl("prod-prod");
  grp.innerHTML = `<option value="">Grupo…</option>` + (fam?(fam.grupos||[]).map(g=>`<option value="${g.id}">${escapeHtml(g.nome)}</option>`).join(""):"");
  prod.innerHTML = `<option value="">Produto…</option>`;
}
function reqAplicGrpChange(){
  const fid = Number(reqEl("prod-fam").value)||null, gid = Number(reqEl("prod-grp").value)||null;
  const fam = (reqAplicArv.familias||[]).find(f=>f.id===fid);
  const grp = fam && (fam.grupos||[]).find(g=>g.id===gid);
  reqEl("prod-prod").innerHTML = `<option value="">Produto…</option>` + (grp?(grp.produtos||[]).map(p=>`<option value="${p.id}">${escapeHtml((p.codigo?p.codigo+" — ":"")+p.nome)}</option>`).join(""):"");
}
async function reqAddAplic(id){
  const prod = Number(reqEl("prod-prod").value)||null, grp = Number(reqEl("prod-grp").value)||null, fam = Number(reqEl("prod-fam").value)||null;
  let alvo_tipo, alvo_id;
  if (prod){ alvo_tipo="produto"; alvo_id=prod; } else if (grp){ alvo_tipo="grupo"; alvo_id=grp; } else if (fam){ alvo_tipo="familia"; alvo_id=fam; }
  else { alert("Escolha uma família, grupo ou produto."); return; }
  try { await api(`/api/requisitos/${id}/vinculos`, {method:"POST", body:{alvo_tipo, alvo_id, tipo_relacao:reqEl("prod-tipo").value, empresa_id:state.empresaId}}); reqLoadAplicabilidade(id); }
  catch(e){ alert(e.message); }
}
async function reqDelAplic(id, vinculoId){
  try { await api(`/api/requisitos/${id}/vinculos/${vinculoId}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); reqLoadAplicabilidade(id); }
  catch(e){ alert(e.message); }
}

async function reqLoadVersoes(id){
  const host = reqEl("ver-list");
  if (!host) return;
  let rows;
  try { rows = await api(`/api/requisitos/${id}/versoes?empresa_id=${state.empresaId||""}`); }
  catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (!rows.length){ host.innerHTML = `<p class="muted">Sem versões registradas.</p>`; return; }
  host.innerHTML = rows.map(v=>`<div class="req-ver">
      <strong>R${String(v.numero).padStart(2,"0")}</strong> — ${escapeHtml((v.snapshot&&v.snapshot.titulo)||"")}
      <span class="muted">· ${escapeHtml(v.origem||"")} · ${escapeHtml((v.criado_em||"").slice(0,10))} · ${escapeHtml(v.criado_por_nome||"—")}</span>
    </div>`).join("");
}

async function reqRegistrarVersao(id){
  try { await api(`/api/requisitos/${id}/versoes?empresa_id=${state.empresaId||""}`, {method:"POST"}); reqLoadVersoes(id); }
  catch(e){ alert(e.message); }
}

const REQ_MUD_SIT = {proposta:"Proposta", aprovada:"Aprovada", rejeitada:"Rejeitada"};
async function reqLoadMudancas(id){
  const host = reqEl("mud-list");
  if (!host) return;
  let rows;
  try { rows = await api(`/api/requisitos/${id}/mudancas?empresa_id=${state.empresaId||""}`); }
  catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (!rows.length){ host.innerHTML = `<p class="muted">Sem solicitações de mudança.</p>`; return; }
  const ed = isEditor();
  host.innerHTML = rows.map(m=>`
    <div class="req-mud req-mud-${escapeHtml(m.situacao)}">
      <strong>${escapeHtml(REQ_MUD_SIT[m.situacao]||m.situacao)}</strong> — ${escapeHtml(m.descricao)}
      <div class="muted">por ${escapeHtml(m.solicitante_nome||"—")}${m.aprovador_nome?` · decidido por ${escapeHtml(m.aprovador_nome)}`:""}${m.decisao_obs?` · ${escapeHtml(m.decisao_obs)}`:""}</div>
      ${ed&&m.situacao==="proposta"?`<button class="btn req-mud-ok" data-id="${m.id}" type="button">Aprovar</button>
        <button class="btn req-mud-no" data-id="${m.id}" type="button">Rejeitar</button>`:""}
    </div>`).join("");
  if (ed){
    host.querySelectorAll(".req-mud-ok").forEach(b=>{ b.onclick=()=>reqDecidirMudanca(id, Number(b.dataset.id), "aprovada"); });
    host.querySelectorAll(".req-mud-no").forEach(b=>{ b.onclick=()=>reqDecidirMudanca(id, Number(b.dataset.id), "rejeitada"); });
  }
}

async function reqProporMudanca(id){
  const desc = (reqEl("mud-desc").value||"").trim();
  if (!desc){ alert("Descreva a mudança proposta."); return; }
  try { await api(`/api/requisitos/${id}/mudancas`, {method:"POST", body:{descricao:desc, empresa_id:state.empresaId}}); reqEl("mud-desc").value=""; reqLoadMudancas(id); }
  catch(e){ alert(e.message); }
}

async function reqDecidirMudanca(id, mid, situacao){
  const obs = prompt(`Observação da decisão (${situacao}):`) || "";
  try { await api(`/api/requisitos/${id}/mudancas/${mid}/decidir`, {method:"POST", body:{situacao, decisao_obs:obs, empresa_id:state.empresaId}}); reqLoadMudancas(id); }
  catch(e){ alert(e.message); }
}

async function reqSalvarEdicao(id){
  const body = {empresa_id: state.empresaId,
    codigo_clausula: reqEl("e-clausula").value.trim(), titulo: reqEl("e-titulo").value.trim(),
    texto: reqEl("e-texto").value.trim(), categoria: reqEl("e-cat").value,
    obrigatoriedade: reqEl("e-obr").value, estado: reqEl("e-estado").value, prioridade: reqEl("e-prio").value,
    variante: reqEl("e-variante").value.trim(),
    fonte: reqEl("e-fonte").value.trim(), justificativa: reqEl("e-justif").value.trim(),
    classe_id: Number(reqEl("e-classe") && reqEl("e-classe").value) || null};
  try {
    await api(`/api/requisitos/${id}?empresa_id=${state.empresaId||""}`, {method:"PUT", body});
    const atrs = reqEl("e-atrs");
    if (atrs){
      const valores = {};
      atrs.querySelectorAll("[data-def]").forEach(el=>{ valores[el.dataset.def] = el.value; });
      await api(`/api/requisitos/${id}/atributos`, {method:"PUT", body:{valores, empresa_id:state.empresaId}});
    }
    reqEl("e-msg").textContent = "Salvo.";
    reqLoadList();
  } catch(e){ reqEl("e-msg").textContent = e.message; }
}

async function reqAddRelacao(id){
  const destino = Number(reqEl("rel-destino").value); if(!destino){ alert("Escolha o requisito de destino."); return; }
  try { await api(`/api/requisitos/${id}/relacoes`, {method:"POST", body:{destino_id:destino, tipo:reqEl("rel-tipo").value, empresa_id:state.empresaId}}); reqSelect(id); }
  catch(e){ alert(e.message); }
}

async function reqDelRelacao(id, relId){
  try { await api(`/api/requisitos/${id}/relacoes/${relId}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); reqSelect(id); }
  catch(e){ alert(e.message); }
}

// --- Configuração do esquema de atributos (admin) ---
const REQ_ATR_TIPOS = [["texto","Texto"],["numero","Número"],["data","Data"],["lista","Lista"],["booleano","Booleano"]];
let reqCfgHost = null;
async function reqConfigAtributos(hostEl){
  reqCfgHost = hostEl || reqCfgHost || reqEl("cfg-body");
  const host = reqCfgHost; if(!host) return;
  let defs;
  try { defs = await api(`/api/requisitos/atributos/defs?empresa_id=${state.empresaId||""}`); }
  catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  host.innerHTML = defs.map(d=>`<div class="req-cfg-item">${escapeHtml(d.rotulo)} <span class="muted">(${escapeHtml(d.chave)} · ${escapeHtml(d.tipo)}${d.obrigatorio?" · obrigatório":""})</span>
      <button class="btn req-cfg-del" data-id="${d.id}" type="button">x</button></div>`).join("") +
    `<div class="req-tools">
      <input id="req-cfg-chave" placeholder="chave" maxlength="60" />
      <input id="req-cfg-rotulo" placeholder="rótulo" maxlength="120" />
      <select id="req-cfg-tipo">${reqOpts(REQ_ATR_TIPOS)}</select>
      <input id="req-cfg-opcoes" placeholder="opções (vírgula)" />
      <label><input type="checkbox" id="req-cfg-obr" /> obrigatório</label>
      <button class="btn primary" id="req-cfg-add" type="button">Adicionar atributo</button>
    </div>
    <div class="req-tools"><button class="btn" id="req-cfg-qualidade" type="button">Adicionar conjunto de qualidade padrão</button>
      <span class="muted">Verificável · Não ambíguo · Singular · Mensurável · Viável · Rastreável (checklist de "bom requisito")</span></div>`;
  host.querySelectorAll(".req-cfg-del").forEach(b=>{ b.onclick=()=>reqDelDef(Number(b.dataset.id)); });
  reqEl("cfg-add").onclick = reqAddDef;
  reqEl("cfg-qualidade").onclick = reqSemearQualidade;
}

async function reqSemearQualidade(){
  try {
    const r = await api(`/api/requisitos/atributos/defs/semear-qualidade?empresa_id=${state.empresaId||""}`, {method:"POST", body:{}});
    alert(r.criados ? `${r.criados} atributo(s) de qualidade criado(s).` : "Conjunto de qualidade já existia (nada a criar).");
    reqConfigAtributos(); if(reqSelId) reqSelect(reqSelId);
  } catch(e){ alert(e.message); }
}

async function reqAddDef(){
  const chave = reqEl("cfg-chave").value.trim(), rotulo = reqEl("cfg-rotulo").value.trim();
  if (!chave || !rotulo){ alert("Informe chave e rótulo."); return; }
  const opcoes = reqEl("cfg-opcoes").value.split(",").map(s=>s.trim()).filter(Boolean);
  const body = {empresa_id:state.empresaId, chave, rotulo, tipo:reqEl("cfg-tipo").value, opcoes, obrigatorio:reqEl("cfg-obr").checked};
  try { await api("/api/requisitos/atributos/defs", {method:"POST", body}); reqConfigAtributos(); if(reqSelId) reqSelect(reqSelId); }
  catch(e){ alert(e.message); }
}

async function reqDelDef(defId){
  if (!confirm("Excluir este atributo do esquema? Os valores preenchidos serão removidos.")) return;
  try { await api(`/api/requisitos/atributos/defs/${defId}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); reqConfigAtributos(); if(reqSelId) reqSelect(reqSelId); }
  catch(e){ alert(e.message); }
}

async function reqImport(file){
  if (!file) return;
  const fd = new FormData(); fd.append("norma_id", reqNormaId); fd.append("file", file);
  if (state.empresaId) fd.append("empresa_id", state.empresaId);
  try {
    const r = await fetch("/api/requisitos/importar", {method:"POST", body:fd, credentials:"same-origin"});
    const d = await r.json().catch(()=>null);
    if (!r.ok) throw new Error(apiErrorMessage(d?.detail, "Falha na importação"));
    alert(`${d.importados} requisito(s) importado(s).`);
    reqLoadList();
  } catch(e){ alert(e.message); }
}

// --- Sugestão por IA (Fase 5) ---
let reqCandidatos = [];
async function reqSugerirIA(){
  const box = reqEl("ia-box");
  box.innerHTML = "Carregando acessos LLM…";
  let acessos;
  try { acessos = await api(`/api/ferramentas/ia/acessos?empresa_id=${state.empresaId||""}`); }
  catch(e){ box.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (!acessos.length){ box.innerHTML = `<p class="muted">Nenhum acesso LLM ativo. Cadastre um modelo (OpenRouter) em Configuração.</p>`; return; }
  box.innerHTML = "Consultando a IA (pode levar alguns segundos)…";
  let res;
  try { res = await api("/api/requisitos/sugerir", {method:"POST", body:{norma_id:reqNormaId, acesso_id:acessos[0].id, empresa_id:state.empresaId}}); }
  catch(e){ box.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  reqCandidatos = res.sugestoes || [];
  if (!reqCandidatos.length){ box.innerHTML = `<p class="muted">A IA não sugeriu requisitos para este texto.</p>`; return; }
  box.innerHTML = `<h4>Sugestões da IA (revise antes de aprovar)</h4>` + reqCandidatos.map((s,i)=>`
    <div class="req-cand">
      <strong>${escapeHtml(s.codigo_clausula||"—")}</strong> ${escapeHtml(s.titulo)}
      <span class="muted">· ${escapeHtml(s.categoria)} · ${escapeHtml(s.obrigatoriedade)}</span>
      <button class="btn req-aprovar" data-i="${i}" type="button">Aprovar</button>
    </div>`).join("");
  box.querySelectorAll(".req-aprovar").forEach(b=>{ b.onclick = ()=>reqAprovarCandidato(Number(b.dataset.i), b); });
}

async function reqAprovarCandidato(i, btn){
  const s = reqCandidatos[i];
  if (!s) return;
  try {
    await api("/api/requisitos", {method:"POST", body:{norma_id:reqNormaId, empresa_id:state.empresaId,
      codigo_clausula:s.codigo_clausula, titulo:s.titulo, texto:s.texto, categoria:s.categoria, obrigatoriedade:s.obrigatoriedade}});
    btn.disabled = true; btn.textContent = "Aprovado";
    reqLoadList();
  } catch(e){ alert(e.message); }
}
