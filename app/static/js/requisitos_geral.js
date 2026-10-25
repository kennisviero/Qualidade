// Telas próprias do menu: Requisitos (por norma) e Configuração de atributos (admin).

// --- Requisitos (item próprio): escolhe a norma e abre o painel completo de requisitos ---
let reqgSeq = 0;

function resetRequisitosGeral(){
  reqgSeq++;
  const ws = document.getElementById("requisitosWorkspace");
  if (ws) ws.innerHTML = "";
}

function loadRequisitosGeral(){
  if (document.getElementById("reqg-norma")) { reqgLoadNormas(); return; }
  document.getElementById("requisitosWorkspace").innerHTML = `
    <div class="card">
      <label>Norma</label>
      <select id="reqg-norma"><option value="">Selecione uma norma…</option></select>
    </div>
    ${isEditor()?`<div class="card">
      <h4>Clonar requisitos (reuso)</h4>
      <p class="hint">Copia todos os requisitos (campos + atributos) de uma norma para outra, da mesma empresa. Estratégia de reuso / like-item.</p>
      <div class="req-tools">
        <select id="reqg-clone-origem"><option value="">Norma de origem…</option></select>
        <span>→</span>
        <select id="reqg-clone-destino"><option value="">Norma de destino…</option></select>
        <button class="btn" id="reqg-clone-btn" type="button">Clonar</button>
      </div>
    </div>`:""}
    <div id="reqg-host"></div>`;
  document.getElementById("reqg-norma").onchange = (e)=>{
    const id = Number(e.target.value) || null;
    const host = document.getElementById("reqg-host");
    if (id) reqLoadForNorma(id, "reqg-host"); else host.innerHTML = "";
  };
  if (isEditor()) document.getElementById("reqg-clone-btn").onclick = reqgClone;
  reqgLoadNormas();
}

async function reqgLoadNormas(){
  const seq = ++reqgSeq;
  let normas;
  try { normas = await api(`/api/normas?empresa_id=${state.empresaId||""}`); }
  catch(e){ document.getElementById("reqg-host").innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`; return; }
  if (seq !== reqgSeq) return;
  const opts = normas.map(n=>`<option value="${n.id}">${escapeHtml(n.codigo)} — ${escapeHtml(n.titulo)}</option>`).join("");
  const sel = document.getElementById("reqg-norma");
  sel.innerHTML = `<option value="">Selecione uma norma…</option>` + opts;
  const co = document.getElementById("reqg-clone-origem"), cd = document.getElementById("reqg-clone-destino");
  if (co) co.innerHTML = `<option value="">Norma de origem…</option>` + opts;
  if (cd) cd.innerHTML = `<option value="">Norma de destino…</option>` + opts;
}

async function reqgClone(){
  const origem = Number(document.getElementById("reqg-clone-origem").value) || null;
  const destino = Number(document.getElementById("reqg-clone-destino").value) || null;
  if (!origem || !destino){ alert("Selecione a norma de origem e a de destino."); return; }
  if (origem === destino){ alert("Origem e destino devem ser normas diferentes."); return; }
  if (!confirm("Clonar todos os requisitos da origem para a norma de destino?")) return;
  try {
    const r = await api("/api/requisitos/clonar", {method:"POST", body:{origem_norma_id:origem, destino_norma_id:destino, empresa_id:state.empresaId}});
    alert(`${r.criados} requisito(s) clonado(s).`);
    if (Number(document.getElementById("reqg-norma").value) === destino) reqLoadForNorma(destino, "reqg-host");
  } catch(e){ alert(e.message); }
}

// --- Configuração de atributos (admin) como item próprio ---
function resetReqAtributos(){
  const ws = document.getElementById("reqAtributosWorkspace");
  if (ws) ws.innerHTML = "";
}

function reqAtributosExplicacao(){
  return `<div class="card req-explica">
    <h3>Como funcionam os atributos configuráveis (IREB)</h3>
    <p>Além dos campos fixos do requisito (categoria, obrigatoriedade, prioridade), você define <strong>atributos próprios</strong>
    que valem para <strong>todos os requisitos desta empresa</strong>. É o <em>attribute schema</em> do IREB (cap. 3): defina uma vez, preencha por requisito.</p>
    <div class="req-flow">
      <div class="req-flow-step"><strong>1. Admin define</strong><span>Cria o atributo aqui: nome, tipo, opções (se lista) e se é obrigatório.</span></div>
      <div class="req-flow-arrow">→</div>
      <div class="req-flow-step"><strong>2. Vale para todos</strong><span>O atributo passa a aparecer em cada requisito da empresa, como um campo no painel de edição.</span></div>
      <div class="req-flow-arrow">→</div>
      <div class="req-flow-step"><strong>3. Preenche por requisito</strong><span>O valor é salvo em cada requisito e validado pelo tipo/opções e pela obrigatoriedade.</span></div>
    </div>
    <h4>Exemplos de atributos</h4>
    <table class="pdm-revs">
      <thead><tr><th>Atributo</th><th>Tipo</th><th>Opções / formato</th><th>Exemplo de valor</th></tr></thead>
      <tbody>
        <tr><td>Risco</td><td>lista</td><td>baixo, medio, alto</td><td>alto</td></tr>
        <tr><td>Criticidade</td><td>lista</td><td>baixa, média, alta</td><td>alta</td></tr>
        <tr><td>Método de verificação</td><td>texto</td><td>livre</td><td>Auditoria interna anual</td></tr>
        <tr><td>Fonte / cláusula</td><td>texto</td><td>livre</td><td>ISO 9001:2015 — 8.5.1</td></tr>
        <tr><td>Prazo de verificação</td><td>data</td><td>AAAA-MM-DD</td><td>2026-12-31</td></tr>
        <tr><td>Esforço estimado (h)</td><td>número</td><td>numérico</td><td>16</td></tr>
        <tr><td>Aplicável?</td><td>booleano</td><td>Sim / Não</td><td>Sim</td></tr>
      </tbody>
    </table>
    <p class="hint">Regras: <strong>obrigatório</strong> impede salvar vazio · <strong>lista</strong> só aceita uma das opções ·
    <strong>número/data</strong> validam o formato · excluir um atributo remove os valores já preenchidos nos requisitos.
    No exemplo da ISO 9001:2015 (empresa "Empresa teste"), a cláusula 8.5.1 tem Risco=alto e a 9.2 tem Método="Auditoria interna anual".</p>
  </div>`;
}

function loadReqAtributos(){
  const ws = document.getElementById("reqAtributosWorkspace");
  if (!ws) return;
  if (!isAdmin()){ ws.innerHTML = reqAtributosExplicacao() + `<p class="muted">Somente administradores editam o esquema de atributos.</p>`; return; }
  ws.innerHTML = reqAtributosExplicacao() + `<div class="card"><h3>Esquema de atributos (configuração)</h3>
    <p class="hint">Atributos aplicados a todos os requisitos da empresa selecionada no cabeçalho.</p>
    <div id="reqatr-host"></div></div>`;
  reqConfigAtributos(document.getElementById("reqatr-host"));
}
