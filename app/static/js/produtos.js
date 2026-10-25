// Produtos — cadastro em árvore Família → Grupo → Produto (por empresa).
let prodSeq = 0;

function prodEl(id){ return document.getElementById("prod-"+id); }

function resetProdutos(){
  prodSeq++;
  const ws = document.getElementById("produtosWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadProdutos(){
  const ws = document.getElementById("produtosWorkspace");
  if (!ws) return;
  if (!prodEl("arvore")){
    ws.innerHTML = `
      <div class="card">
        <p class="hint">Hierarquia de produto da empresa selecionada. Requisitos podem ser ligados a qualquer nível (Família, Grupo ou Produto) na tela de Requisitos.</p>
        ${isEditor()?`<div class="req-tools"><input id="prod-nova-familia" placeholder="Nova família (ex.: Linha Branca)" maxlength="200" />
          <button class="btn primary" id="prod-add-familia" type="button">Adicionar família</button></div>`:""}
        <div id="prod-arvore" class="rast-tree"></div>
      </div>`;
    if (isEditor()) prodEl("add-familia").onclick = prodAddFamilia;
  }
  prodDraw();
}

async function prodDraw(){
  const seq = ++prodSeq;
  let arv;
  try { arv = await api(`/api/produtos/arvore?empresa_id=${state.empresaId||""}`); }
  catch(e){ prodEl("arvore").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== prodSeq) return;
  const ed = isEditor();
  const fams = arv.familias || [];
  if (!fams.length){ prodEl("arvore").innerHTML = `<p class="muted">Nenhuma família cadastrada.</p>`; return; }
  prodEl("arvore").innerHTML = fams.map(f=>`
    <details class="rast-req" open>
      <summary>📦 <strong>${escapeHtml(f.nome)}</strong> <span class="muted">(família)</span>
        ${ed?`<button class="btn prod-del" data-kind="familias" data-id="${f.id}" type="button">x</button>`:""}</summary>
      <ul class="rast-filhos">
        ${(f.grupos||[]).map(g=>`<li class="rast-li">
          📁 <strong>${escapeHtml(g.nome)}</strong> <span class="muted">(grupo)</span>
          ${ed?`<button class="btn prod-del" data-kind="grupos" data-id="${g.id}" type="button">x</button>`:""}
          <ul class="rast-filhos">
            ${(g.produtos||[]).map(p=>`<li class="rast-li">🔧 ${escapeHtml((p.codigo?p.codigo+" — ":"")+p.nome)}
              ${ed?`<button class="btn prod-del" data-kind="produtos" data-id="${p.id}" type="button">x</button>`:""}</li>`).join("")}
            ${ed?`<li class="rast-li rast-mud-add-wrap"><input class="prod-novo-prod" data-grupo="${g.id}" placeholder="Novo produto (código / nome)" maxlength="200" />
              <button class="btn prod-add-prod" data-grupo="${g.id}" type="button">+ produto</button></li>`:""}
          </ul></li>`).join("")}
        ${ed?`<li class="rast-li rast-mud-add-wrap"><input class="prod-novo-grupo" data-familia="${f.id}" placeholder="Novo grupo" maxlength="200" />
          <button class="btn prod-add-grupo" data-familia="${f.id}" type="button">+ grupo</button></li>`:""}
      </ul>
    </details>`).join("");
  if (!ed) return;
  const host = prodEl("arvore");
  host.querySelectorAll(".prod-del").forEach(b=>{ b.onclick=()=>prodDel(b.dataset.kind, Number(b.dataset.id)); });
  host.querySelectorAll(".prod-add-grupo").forEach(b=>{ b.onclick=()=>{
    const inp = host.querySelector(`.prod-novo-grupo[data-familia="${b.dataset.familia}"]`);
    prodAddGrupo(Number(b.dataset.familia), inp ? inp.value : ""); }; });
  host.querySelectorAll(".prod-add-prod").forEach(b=>{ b.onclick=()=>{
    const inp = host.querySelector(`.prod-novo-prod[data-grupo="${b.dataset.grupo}"]`);
    prodAddProduto(Number(b.dataset.grupo), inp ? inp.value : ""); }; });
}

async function prodAddFamilia(){
  const nome = prodEl("nova-familia").value.trim();
  if (!nome){ alert("Informe o nome da família."); return; }
  try { await api("/api/produtos/familias", {method:"POST", body:{nome, empresa_id:state.empresaId}}); prodEl("nova-familia").value=""; prodDraw(); }
  catch(e){ alert(e.message); }
}
async function prodAddGrupo(familiaId, nome){
  nome = (nome||"").trim(); if (!nome){ alert("Informe o nome do grupo."); return; }
  try { await api("/api/produtos/grupos", {method:"POST", body:{familia_id:familiaId, nome, empresa_id:state.empresaId}}); prodDraw(); }
  catch(e){ alert(e.message); }
}
async function prodAddProduto(grupoId, texto){
  texto = (texto||"").trim(); if (!texto){ alert("Informe o produto."); return; }
  // "COD / Nome" opcional: separa código do nome por "/" ou "—"
  let codigo = "", nome = texto;
  const m = texto.split(/\s*[\/—-]\s*/);
  if (m.length >= 2 && m[0].length <= 60){ codigo = m[0]; nome = m.slice(1).join(" - "); }
  try { await api("/api/produtos", {method:"POST", body:{grupo_id:grupoId, codigo, nome, empresa_id:state.empresaId}}); prodDraw(); }
  catch(e){ alert(e.message); }
}
async function prodDel(kind, id){
  const rotulo = {familias:"família (e seus grupos/produtos)", grupos:"grupo (e seus produtos)", produtos:"produto"}[kind] || "item";
  if (!confirm(`Excluir ${rotulo}?`)) return;
  const path = kind === "produtos" ? `/api/produtos/${id}` : `/api/produtos/${kind}/${id}`;
  try { await api(`${path}?empresa_id=${state.empresaId||""}`, {method:"DELETE"}); prodDraw(); }
  catch(e){ alert(e.message); }
}
