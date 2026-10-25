// Normas e Regulamentos — catálogo sobre /api/normas (consumidor do PDM).
let normasSeq = 0;
let normaSelId = null;

const NOR_TIPOS = [["norma_tecnica","Norma técnica"],["regulamento_legal","Regulamento legal"],
  ["requisito_contratual","Requisito contratual"],["requisito_cliente","Requisito de cliente"],
  ["politica_interna","Política interna"],["outro","Outro"]];
const NOR_STATUS = [["vigente","Vigente"],["em_revisao","Em revisão"],["obsoleta","Obsoleta"]];

function norEl(id){ return document.getElementById("nor-"+id); }
function norOpts(pairs){ return pairs.map(([v,l])=>`<option value="${v}">${l}</option>`).join(""); }
function norLabel(pairs,v){ const f=pairs.find(p=>p[0]===v); return f?f[1]:v; }

function resetNormas(){
  normaSelId = null;
  normasSeq++;
  const ws = document.getElementById("normasWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadNormas(){
  if (norEl("list")) { normasLoadList(); return; }
  buildNormas();
  normasLoadList();
}

function buildNormas(){
  document.getElementById("normasWorkspace").innerHTML = `
    <div class="nor-layout">
      <div class="nor-col-list">
        <div class="card ${isEditor()?"":"hidden"}" id="nor-novo-card">
          <h3>Nova norma / regulamento</h3>
          <label>Tipo de fonte</label><select id="nor-novo-tipo">${norOpts(NOR_TIPOS)}</select>
          <label>Título</label><input id="nor-novo-titulo" maxlength="200" />
          <label>Identificador externo</label><input id="nor-novo-ident" maxlength="200" placeholder="ISO 9001:2015, Lei 14.133/2021…" />
          <label>Emissor</label><input id="nor-novo-emissor" maxlength="200" />
          <label><input type="checkbox" id="nor-novo-doc" checked /> Criar documento controlado (PDM) para anexar o arquivo</label>
          <button class="btn primary" id="nor-novo-btn" type="button">Cadastrar</button>
        </div>
        <div class="card">
          <h3>Filtros</h3>
          <div class="grid-2">
            <div><label>Tipo</label><select id="nor-f-tipo"><option value="">Todos</option>${norOpts(NOR_TIPOS)}</select></div>
            <div><label>Status</label><select id="nor-f-status"><option value="">Todos</option>${norOpts(NOR_STATUS)}</select></div>
          </div>
          <label>Busca (código/título/identificador)</label><input id="nor-f-q" />
        </div>
        <div class="card"><div id="nor-list" class="list"></div></div>
      </div>
      <div class="nor-col-detail"><div id="nor-detail" class="card"><p class="muted">Selecione uma norma.</p></div></div>
    </div>`;
  if (isEditor()) norEl("novo-btn").onclick = normaCreate;
  norEl("f-tipo").onchange = normasLoadList;
  norEl("f-status").onchange = normasLoadList;
  norEl("f-q").oninput = normasLoadList;
}

function norQuery(){
  const p = new URLSearchParams({empresa_id: state.empresaId || ""});
  if (norEl("f-tipo").value) p.set("tipo_fonte", norEl("f-tipo").value);
  if (norEl("f-status").value) p.set("status", norEl("f-status").value);
  if (norEl("f-q").value.trim()) p.set("q", norEl("f-q").value.trim());
  return p.toString();
}

async function normasLoadList(){
  const seq = ++normasSeq;
  let rows;
  try { rows = await api("/api/normas?"+norQuery()); }
  catch(e){ if(seq===normasSeq) norEl("list").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq!==normasSeq) return;
  if (!rows.length){ norEl("list").innerHTML = `<p class="muted">Nenhuma norma.</p>`; return; }
  norEl("list").innerHTML = rows.map(n=>`
    <div class="nor-item${n.id===normaSelId?" sel":""}" data-id="${n.id}">
      <strong>${escapeHtml(n.codigo)}</strong> — ${escapeHtml(n.titulo)}
      <div class="muted">${escapeHtml(norLabel(NOR_TIPOS,n.tipo_fonte))} · ${escapeHtml(norLabel(NOR_STATUS,n.status))}${n.identificador_externo?` · ${escapeHtml(n.identificador_externo)}`:""}</div>
    </div>`).join("");
  norEl("list").querySelectorAll(".nor-item").forEach(el=>{ el.onclick = ()=>normaSelect(Number(el.dataset.id)); });
}

async function normaSelect(id){
  const seq = ++normasSeq;
  let n;
  try { n = await api(`/api/normas/${id}?empresa_id=${state.empresaId||""}`); }
  catch(e){ norEl("detail").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq!==normasSeq) return;
  normaSelId = id;
  normaRenderDetail(n);
  normasLoadList();
}

function normaRenderDetail(n){
  const ed = isEditor();
  const ro = ed ? "" : "disabled";
  const campo = (id,label,val,extra="")=>`<label>${label}</label><input id="nor-d-${id}" value="${escapeHtml(val||"")}" ${ro} ${extra} />`;
  const doc = n.documento;
  norEl("detail").innerHTML = `
    <h3>${escapeHtml(n.codigo)}</h3>
    <label>Tipo de fonte</label><select id="nor-d-tipo" ${ro}>${norOpts(NOR_TIPOS)}</select>
    ${campo("titulo","Título",n.titulo)}
    ${campo("ident","Identificador externo",n.identificador_externo)}
    ${campo("emissor","Emissor",n.emissor)}
    <div class="grid-2">
      <div>${campo("edicao","Edição/versão",n.edicao_versao)}</div>
      <div><label>Status ${doc?'<span class="muted">(segue o ciclo do documento)</span>':''}</label><select id="nor-d-status" ${doc?'disabled':ro}>${norOpts(NOR_STATUS)}</select></div>
    </div>
    <div class="grid-2">
      <div>${campo("pub","Publicação",n.data_publicacao,'placeholder="AAAA-MM-DD"')}</div>
      <div>${campo("vig","Vigência",n.data_vigencia,'placeholder="AAAA-MM-DD"')}</div>
    </div>
    <label>Escopo/aplicabilidade</label><textarea id="nor-d-escopo" rows="2" ${ro}>${escapeHtml(n.escopo||"")}</textarea>
    <label>Observações</label><textarea id="nor-d-obs" rows="2" ${ro}>${escapeHtml(n.observacoes||"")}</textarea>
    <h5>Documento (fonte)</h5>
    <div id="nor-doc" class="card"><p class="muted">—</p></div>
    ${ed?`<button class="btn primary" id="nor-d-salvar" type="button">Salvar</button>
      <button class="btn" id="nor-d-excluir" type="button">Excluir</button>`:""}
    <p id="nor-d-msg" class="hint" role="status"></p>
    <div id="nor-requisitos" class="card"></div>`;
  norEl("d-tipo").value = n.tipo_fonte;
  norEl("d-status").value = n.status;
  if (ed){
    norEl("d-salvar").onclick = ()=>normaSave(n.id);
    norEl("d-excluir").onclick = ()=>{ if(confirm("Excluir esta norma?")) normaDelete(n.id); };
  }
  norLoadDocumento(n.id);
  if (typeof reqLoadForNorma === "function") reqLoadForNorma(n.id);
}

async function normaCreate(){
  const titulo = norEl("novo-titulo").value.trim();
  if (!titulo){ alert("Informe o título."); return; }
  const body = {
    tipo_fonte: norEl("novo-tipo").value, titulo,
    identificador_externo: norEl("novo-ident").value.trim(),
    emissor: norEl("novo-emissor").value.trim(),
    criar_documento: norEl("novo-doc").checked,
    empresa_id: state.empresaId,
  };
  try {
    const n = await api("/api/normas", {method:"POST", body});
    ["novo-titulo","novo-ident","novo-emissor"].forEach(id=>{ norEl(id).value=""; });
    await normasLoadList();
    normaSelect(n.id);
  } catch(e){ alert(e.message); }
}

async function normaSave(id){
  const body = {
    tipo_fonte: norEl("d-tipo").value,
    titulo: norEl("d-titulo").value.trim(),
    identificador_externo: norEl("d-ident").value.trim(),
    emissor: norEl("d-emissor").value.trim(),
    edicao_versao: norEl("d-edicao").value.trim(),
    data_publicacao: norEl("d-pub").value.trim(),
    data_vigencia: norEl("d-vig").value.trim(),
    escopo: norEl("d-escopo").value.trim(),
    observacoes: norEl("d-obs").value.trim(),
  };
  // Status só é editável quando a norma não tem documento (senão segue o ciclo do documento).
  if (!norEl("d-status").disabled) body.status = norEl("d-status").value;
  try {
    await api(`/api/normas/${id}?empresa_id=${state.empresaId||""}`, {method:"PUT", body});
    norEl("d-msg").textContent = "Salvo.";
    normasLoadList();
  } catch(e){ norEl("d-msg").textContent = e.message; }
}

async function normaDelete(id){
  try {
    await api(`/api/normas/${id}?empresa_id=${state.empresaId||""}`, {method:"DELETE"});
    normaSelId = null;
    norEl("detail").innerHTML = `<p class="muted">Selecione uma norma.</p>`;
    normasLoadList();
  } catch(e){ alert(e.message); }
}

const NOR_FONTE = {arquivo:"Arquivo (PDF/DOCX)", link:"Link (Google Docs/URL)", cadastrado:"Cadastrado (sem arquivo)"};
async function norLoadDocumento(id){
  const host = document.getElementById("nor-doc");
  if (!host) return;
  let d;
  try { d = await api(`/api/normas/${id}/documento?empresa_id=${state.empresaId||""}`); }
  catch(e){ host.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  const ed = isEditor();
  const rev = d.revisao;
  const fonte = rev ? (NOR_FONTE[rev.fonte]||rev.fonte) : "Cadastrado (sem arquivo)";
  const abrir = rev && rev.tem_link
    ? `<a href="${escapeHtml(rev.url)}" target="_blank" rel="noopener">abrir link</a>`
    : (rev && rev.tem_arquivo ? `<a href="/api/pdm/documentos/${d.documento_id}/revisoes/${rev.numero}/arquivo" target="_blank">abrir arquivo</a>` : "—");
  host.innerHTML = `
    <div><strong>Fonte:</strong> ${escapeHtml(fonte)} · ${abrir}${d.codigo?` · <span class="muted">${escapeHtml(d.codigo)}</span>`:""}</div>
    ${ed?`<div class="req-tools" style="margin-top:6px">
      <label class="btn" style="cursor:pointer">Enviar PDF/DOCX<input type="file" id="nor-doc-file" accept=".pdf,.docx,.txt" style="display:none" /></label>
      <button class="btn" id="nor-doc-link" type="button">Definir link (Google Docs/URL)</button>
    </div>`:""}`;
  if (ed){
    const f = document.getElementById("nor-doc-file"); if(f) f.onchange = (e)=>norUploadDoc(id, e.target.files[0]);
    const lb = document.getElementById("nor-doc-link"); if(lb) lb.onclick = ()=>norSetDocLink(id);
  }
}

async function norUploadDoc(id, file){
  if (!file) return;
  const fd = new FormData(); fd.append("file", file);
  if (state.empresaId) fd.append("empresa_id", state.empresaId);
  try {
    const r = await fetch(`/api/normas/${id}/documento/arquivo`, {method:"POST", body:fd, credentials:"same-origin"});
    const d = await r.json().catch(()=>null);
    if (!r.ok) throw new Error(apiErrorMessage(d?.detail, "Falha no envio"));
    norLoadDocumento(id);
  } catch(e){ alert(e.message); }
}

async function norSetDocLink(id){
  const url = prompt("Cole o link da norma (ex.: Google Docs, SharePoint, URL):");
  if (!url) return;
  try { await api(`/api/normas/${id}/documento/link`, {method:"POST", body:{url:url.trim(), empresa_id:state.empresaId}}); norLoadDocumento(id); }
  catch(e){ alert(e.message); }
}
