const state = {
  user: null,
  empresas: [],
  empresaId: null,
  processoId: null,
  issueId: null,
  issue: null,
  editingAcaoId: null,
  issueUsuarios: [],
  issueView: "capturar",
  issueLimpezaPreview: null,
};

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function api(path, options = {}) {
  const opts = { credentials: "same-origin", headers: { "Content-Type": "application/json" }, ...options };
  if (opts.body && typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
  return fetch(path, opts).then(async (r) => {
    if (r.status === 204) return null;
    const data = await r.json().catch(() => null);
    if (!r.ok) {
      if (r.status === 401) showLogin();
      const err = new Error(data && data.detail ? data.detail : r.statusText);
      err.status = r.status;
      throw err;
    }
    return data;
  });
}

function isSuperuser() {
  return state.user && state.user.papel === "admin" && state.user.empresa_id === null;
}

function isAdmin() {
  return state.user && state.user.papel === "admin";
}

function isEditor() {
  return state.user && (state.user.papel === "admin" || state.user.papel === "editor");
}

function showLogin() {
  document.getElementById("loginOverlay").classList.remove("hidden");
}

function hideLogin() {
  document.getElementById("loginOverlay").classList.add("hidden");
  document.getElementById("loginError").classList.add("hidden");
}

function navigate(section) {
  if (section !== "issues") stopIssueSelecaoPolling();
  document.querySelectorAll(".section").forEach((s) => s.classList.remove("active"));
  const el = document.getElementById("section-" + section);
  if (el) el.classList.add("active");
  document.querySelectorAll(".sidebar a").forEach((a) => a.classList.remove("active"));
  document.querySelector(`.sidebar a[data-section="${section}"]`).classList.add("active");
}

function plot(target, layout, traces) {
  Plotly.newPlot(target, traces, layout, { responsive: true });
}

async function onAuth() {
  resetIssueSelecao();
  document.querySelectorAll(".editor-only").forEach((el) => el.classList.toggle("hidden", !isEditor()));
  resetLlmForm();
  document.getElementById("llmLista").innerHTML = "";
  hideLogin();
  document.getElementById("userInfo").textContent =
    `${state.user.nome} (${state.user.papel})`;
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("hidden", !isAdmin());
  });
  await initEmpresaGlobal();
  navigate("issues");
  await Promise.all([loadEmpresas(), loadUsuarios(), initSetores(), initProcessos(), initIssues()]);
}

async function initEmpresaGlobal() {
  const sel = document.getElementById("empresaSelect");
  sel.innerHTML = "";
  if (isSuperuser()) {
    const empresas = await api("/api/empresas");
    state.empresas = empresas;
    empresas.forEach((e) => sel.appendChild(new Option(e.razao_social, e.id)));
    sel.disabled = false;
    state.empresaId = empresas[0] ? empresas[0].id : null;
  } else {
    const empresas = await api("/api/empresas").catch(() => []);
    const emp = empresas.find((x) => x.id === state.user.empresa_id);
    sel.appendChild(new Option(emp ? emp.razao_social : "Minha empresa", state.user.empresa_id));
    sel.disabled = true;
    state.empresaId = state.user.empresa_id;
  }
  sel.value = state.empresaId || "";
}

async function login() {
  const email = document.getElementById("loginEmail").value.trim();
  const senha = document.getElementById("loginSenha").value;
  const errBox = document.getElementById("loginError");
  try {
    state.user = await api("/api/auth/login", { method: "POST", body: { email, senha } });
    await onAuth();
  } catch (e) {
    errBox.textContent = e.message;
    errBox.classList.remove("hidden");
  }
}

async function logout() {
  resetIssueSelecao();
  resetLlmForm();
  document.getElementById("llmLista").innerHTML = "";
  await api("/api/auth/logout", { method: "POST" }).catch(() => {});
  state.user = null;
  showLogin();
}

function fillEmpresaSelect(sel, empresas, includeEmpty) {
  sel.innerHTML = "";
  if (includeEmpty) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "—";
    sel.appendChild(opt);
  }
  empresas.forEach((e) => {
    const opt = document.createElement("option");
    opt.value = e.id;
    opt.textContent = e.razao_social;
    sel.appendChild(opt);
  });
}

async function loadEmpresas() {
  if (!isAdmin()) return;
  const empresas = await api("/api/empresas");
  state.empresas = empresas;
  renderEmpresaList(empresas);
  fillEmpresaSelect(document.getElementById("usuarioEmpresa"), empresas, true);
}

function renderEmpresaList(empresas) {
  const list = document.getElementById("empresaList");
  list.innerHTML = "";
  const form = document.getElementById("empresaForm");
  form.classList.toggle("hidden", !isSuperuser());
  empresas.forEach((e) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<span class="title">${escapeHtml(e.razao_social)}</span><span class="sub">CNPJ: ${escapeHtml(e.cnpj || "—")} · ${e.ativo ? "ativa" : "inativa"}</span>`;
    item.appendChild(meta);
    const edit = document.createElement("button");
    edit.className = "btn";
    edit.textContent = "Editar";
    edit.onclick = () => editarEmpresaInline(item, e);
    item.appendChild(edit);
    const tog = document.createElement("button");
    tog.className = "btn";
    tog.textContent = e.ativo ? "Desativar" : "Ativar";
    tog.onclick = async () => {
      if (e.ativo && !confirm(`Desativar a empresa "${e.razao_social}"? Os usuários dela não conseguirão acessar.`)) return;
      await api(`/api/empresas/${e.id}`, { method: "PUT", body: { ativo: e.ativo ? 0 : 1 } });
      loadEmpresas();
    };
    if (isSuperuser()) item.appendChild(tog);
    if (isSuperuser()) {
      const del = document.createElement("button");
      del.className = "btn";
      del.textContent = "Excluir";
      del.onclick = async () => {
        if (!confirm(`Excluir a empresa "${e.razao_social}"? Esta ação não pode ser desfeita.`)) return;
        await api(`/api/empresas/${e.id}`, { method: "DELETE" });
        loadEmpresas();
      };
      item.appendChild(del);
    }
    list.appendChild(item);
  });
}

function inlineInput(labelText, value, type = "text") {
  const wrap = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  const input = document.createElement("input");
  input.type = type;
  input.value = value == null ? "" : value;
  wrap.appendChild(label);
  wrap.appendChild(input);
  return { wrap, input };
}

function inlineSelect(labelText, options, value) {
  const wrap = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  const sel = document.createElement("select");
  options.forEach(([v, t]) => sel.appendChild(new Option(t, v)));
  sel.value = value == null ? "" : String(value);
  wrap.appendChild(label);
  wrap.appendChild(sel);
  return { wrap, input: sel };
}

function inlineForm(item, fields, onSave, onCancel) {
  item.innerHTML = "";
  const form = document.createElement("div");
  form.className = "grid-2";
  form.style.flex = "1";
  fields.forEach((f) => form.appendChild(f.wrap));
  const actions = document.createElement("div");
  const salvar = document.createElement("button");
  salvar.className = "btn primary";
  salvar.textContent = "Salvar";
  salvar.onclick = async () => {
    try {
      await onSave();
    } catch (err) {
      alert(err.message);
    }
  };
  const cancelar = document.createElement("button");
  cancelar.className = "btn";
  cancelar.textContent = "Cancelar";
  cancelar.onclick = onCancel;
  actions.appendChild(salvar);
  actions.appendChild(cancelar);
  form.appendChild(actions);
  item.appendChild(form);
}

function editarEmpresaInline(item, e) {
  const razao = inlineInput("Razão social", e.razao_social);
  const cnpj = inlineInput("CNPJ", e.cnpj);
  inlineForm(item, [razao, cnpj], async () => {
    const razao_social = razao.input.value.trim();
    if (!razao_social) { alert("Informe a razão social."); return; }
    await api(`/api/empresas/${e.id}`, {
      method: "PUT",
      body: { razao_social, cnpj: cnpj.input.value.trim() },
    });
    loadEmpresas();
  }, loadEmpresas);
}

async function createEmpresa(e) {
  e.preventDefault();
  const razao_social = document.getElementById("empresaRazao").value.trim();
  const cnpj = document.getElementById("empresaCnpj").value.trim();
  await api("/api/empresas", { method: "POST", body: { razao_social, cnpj } });
  document.getElementById("empresaRazao").value = "";
  document.getElementById("empresaCnpj").value = "";
  loadEmpresas();
}

async function loadUsuarios() {
  if (!isAdmin()) return;
  const usuarios = await api("/api/usuarios");
  renderUsuarioList(usuarios);
  document.getElementById("usuarioEmpresaLabel").classList.toggle("hidden", !isSuperuser());
  document.getElementById("usuarioEmpresa").classList.toggle("hidden", !isSuperuser());
  await loadUsuarioSetores();
}

async function loadUsuarioSetores() {
  const sel = document.getElementById("usuarioSetor");
  sel.innerHTML = "";
  const empId = isSuperuser()
    ? (Number(document.getElementById("usuarioEmpresa").value) || state.empresaId)
    : state.empresaId;
  if (!empId) return;
  const setores = await api(`/api/setores?empresa_id=${empId}`);
  sel.appendChild(new Option("—", ""));
  setores.forEach((s) => sel.appendChild(new Option(s.nome, s.id)));
}

function renderUsuarioList(usuarios) {
  const list = document.getElementById("usuarioList");
  list.innerHTML = "";
  usuarios.forEach((u) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    const setor = u.setor_nome ? ` · ${escapeHtml(u.setor_nome)}` : "";
    const posicao = u.posicao ? ` · ${escapeHtml(u.posicao)}` : "";
    meta.innerHTML = `<span class="title">${escapeHtml(u.nome)}</span><span class="sub">${escapeHtml(u.email)} · ${escapeHtml(u.papel)}${posicao}${setor}${u.ativo ? "" : " · desativado"}</span>`;
    const edit = document.createElement("button");
    edit.className = "btn";
    edit.textContent = "Editar";
    edit.onclick = () => editarUsuarioInline(item, u);
    const tog = document.createElement("button");
    tog.className = "btn";
    tog.textContent = u.ativo ? "Desativar" : "Ativar";
    tog.onclick = async () => {
      if (u.ativo && !confirm(`Desativar o usuário "${u.nome}"?`)) return;
      await api(`/api/usuarios/${u.id}`, { method: "PUT", body: { ativo: u.ativo ? 0 : 1 } });
      loadUsuarios();
    };
    const del = document.createElement("button");
    del.className = "btn";
    del.textContent = "Excluir";
    del.onclick = async () => {
      if (!confirm(`Excluir o usuário "${u.nome}"? Esta ação não pode ser desfeita.`)) return;
      await api(`/api/usuarios/${u.id}`, { method: "DELETE" });
      loadUsuarios();
    };
    item.appendChild(meta);
    item.appendChild(edit);
    if (u.id !== state.user.id) item.appendChild(tog);
    item.appendChild(del);
    list.appendChild(item);
  });
}

const POSICOES = ["Presidente", "Diretoria", "Gerente", "Supervisor", "Encarregado", "Colaborador"];

async function editarUsuarioInline(item, u) {
  const setores = u.empresa_id ? await api(`/api/setores?empresa_id=${u.empresa_id}`) : [];
  const nome = inlineInput("Nome", u.nome);
  const email = inlineInput("Email", u.email);
  const senha = inlineInput("Nova senha (deixe vazio para manter)", "", "password");
  const papel = inlineSelect("Papel", [["admin", "admin"], ["editor", "editor"], ["visualizador", "visualizador"]], u.papel);
  const posicao = inlineSelect("Posição", [["", "—"], ...POSICOES.map((p) => [p, p])], u.posicao);
  const setor = inlineSelect("Setor", [["", "—"], ...setores.map((s) => [s.id, s.nome])], u.setor_id);
  inlineForm(item, [nome, email, senha, papel, posicao, setor], async () => {
    const body = {
      nome: nome.input.value.trim(),
      email: email.input.value.trim(),
      papel: papel.input.value,
      posicao: posicao.input.value,
    };
    if (!body.nome || !body.email) { alert("Informe nome e email."); return; }
    if (senha.input.value) body.senha = senha.input.value;
    const setorId = Number(setor.input.value) || null;
    if (setorId) body.setor_id = setorId;
    await api(`/api/usuarios/${u.id}`, { method: "PUT", body });
    loadUsuarios();
  }, loadUsuarios);
}

async function createUsuario(e) {
  e.preventDefault();
  const body = {
    nome: document.getElementById("usuarioNome").value.trim(),
    email: document.getElementById("usuarioEmail").value.trim(),
    senha: document.getElementById("usuarioSenha").value,
    papel: document.getElementById("usuarioPapel").value,
    setor_id: Number(document.getElementById("usuarioSetor").value) || null,
    posicao: document.getElementById("usuarioPosicao").value,
  };
  if (isSuperuser()) {
    body.empresa_id = Number(document.getElementById("usuarioEmpresa").value) || null;
  }
  await api("/api/usuarios", { method: "POST", body });
  document.getElementById("usuarioNome").value = "";
  document.getElementById("usuarioEmail").value = "";
  document.getElementById("usuarioSenha").value = "";
  loadUsuarios();
}

function fmtData(iso) {
  return iso ? new Date(iso).toLocaleDateString("pt-BR") : "—";
}

// ===== CRUD Setores e Processos =====
function fillCrudEmpresas(sel, includeEmpty) {
  sel.innerHTML = "";
  if (includeEmpty) sel.appendChild(new Option("—", ""));
  if (isSuperuser()) {
    state.empresas.forEach((e) => sel.appendChild(new Option(e.razao_social, e.id)));
    sel.disabled = false;
  } else {
    const emp = state.empresas.find((x) => x.id === state.user.empresa_id);
    sel.appendChild(new Option(emp ? emp.razao_social : "Minha empresa", state.user.empresa_id));
    sel.disabled = true;
  }
  sel.value = state.empresaId || "";
}

async function loadCrudSetores() {
  const list = document.getElementById("setorList");
  const sel = document.getElementById("setorEmpresa");
  fillCrudEmpresas(sel, isSuperuser());
  const empId = Number(sel.value) || null;
  const setores = await api(`/api/setores?empresa_id=${empId}`);
  list.innerHTML = "";
  if (!setores.length) {
    list.innerHTML = '<p class="hint">Nenhum setor.</p>';
    return;
  }
  setores.forEach((s) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<span class="title">${escapeHtml(s.nome)}</span>`;
    item.appendChild(meta);
    const ren = document.createElement("button");
    ren.className = "btn";
    ren.textContent = "Renomear";
    ren.onclick = async () => {
      const novo = prompt("Novo nome:", s.nome);
      if (!novo || !novo.trim()) return;
      await api(`/api/setores/${s.id}`, { method: "PUT", body: { nome: novo.trim() } });
      loadCrudSetores();
    };
    const del = document.createElement("button");
    del.className = "btn";
    del.textContent = "Excluir";
    del.onclick = async () => {
      if (!confirm(`Excluir o setor "${s.nome}"?`)) return;
      await api(`/api/setores/${s.id}`, { method: "DELETE" });
      loadCrudSetores();
    };
    item.appendChild(ren);
    item.appendChild(del);
    list.appendChild(item);
  });
}

async function loadCrudProcessos() {
  const list = document.getElementById("processoList");
  const empSel = document.getElementById("processoEmpresa");
  fillCrudEmpresas(empSel, isSuperuser());
  const empId = Number(empSel.value) || null;
  const setorSel = document.getElementById("processoSetor");
  setorSel.innerHTML = '<option value="">—</option>';
  const setores = await api(`/api/setores?empresa_id=${empId}`);
  setores.forEach((s) => setorSel.appendChild(new Option(s.nome, s.id)));
  const processos = await api(`/api/processos?empresa_id=${empId}`);
  list.innerHTML = "";
  if (!processos.length) {
    list.innerHTML = '<p class="hint">Nenhum processo.</p>';
    return;
  }
  processos.forEach((p) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.style.cursor = "pointer";
    meta.innerHTML = `<span class="title">${escapeHtml(p.nome)}</span><span class="sub">Setor: ${escapeHtml(p.setor_nome || "—")} · ${escapeHtml(p.status || "")}</span>`;
    meta.onclick = () => selectProcesso(p.id);
    item.appendChild(meta);
    const del = document.createElement("button");
    del.className = "btn";
    del.textContent = "Excluir";
    del.onclick = async () => {
      if (!confirm(`Excluir o processo "${p.nome}"?`)) return;
      await api(`/api/processos/${p.id}`, { method: "DELETE" });
      if (state.processoId === p.id) {
        state.processoId = null;
        document.getElementById("processoDetail").classList.add("hidden");
      }
      loadCrudProcessos();
    };
    item.appendChild(del);
    list.appendChild(item);
  });
}

async function createSetorCRUD(e) {
  e.preventDefault();
  const nome = document.getElementById("setorNome").value.trim();
  if (!nome) return;
  const body = { nome };
  if (isSuperuser()) body.empresa_id = Number(document.getElementById("setorEmpresa").value) || null;
  try {
    await api("/api/setores", { method: "POST", body });
  } catch (err) {
    alert(err.message || "Erro ao criar o setor.");
    return;
  }
  document.getElementById("setorNome").value = "";
  await loadCrudSetores();
}

async function createProcessoCRUD(e) {
  e.preventDefault();
  const nome = document.getElementById("processoNome").value.trim();
  if (!nome) return;
  const body = {
    nome,
    descricao: document.getElementById("processoDescricao").value,
    setor_id: Number(document.getElementById("processoSetor").value) || null,
  };
  if (isSuperuser()) body.empresa_id = Number(document.getElementById("processoEmpresa").value) || null;
  try {
    await api("/api/processos", { method: "POST", body });
  } catch (err) {
    alert(err.message || "Erro ao criar o processo.");
    return;
  }
  document.getElementById("processoNome").value = "";
  document.getElementById("processoDescricao").value = "";
  await loadCrudProcessos();
}

function initSetores() {
  return loadCrudSetores();
}

// ===== Gestão do processo (guardião/aprovador/status/revisões) + documentos =====
async function loadProcessoUsuarios() {
  const respSel = document.getElementById("processoGestResponsavel");
  const aprovSel = document.getElementById("processoGestAprovador");
  respSel.innerHTML = '<option value="">—</option>';
  aprovSel.innerHTML = '<option value="">—</option>';
  let usuarios = [];
  try {
    usuarios = await api("/api/usuarios");
  } catch (e) {
    return;
  }
  usuarios.forEach((u) => {
    const label = `${u.nome} (${u.papel})`;
    respSel.appendChild(new Option(label, u.id));
    aprovSel.appendChild(new Option(label, u.id));
  });
}

async function selectProcesso(id) {
  state.processoId = id;
  await loadProcessoDetail();
}

async function loadProcessoDetail() {
  const card = document.getElementById("processoDetail");
  if (!state.processoId) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  const p = await api(`/api/processos/${state.processoId}`);
  renderProcessoMeta(p);
  const revisoes = await api(`/api/processos/${state.processoId}/revisoes`);
  renderProcessoRevisoes(revisoes);
  await loadDocsTree();
}

function renderProcessoMeta(p) {
  document.getElementById("processoDetailTitulo").textContent = p.nome || "—";
  document.getElementById("processoStatus").textContent = p.status || "";
  document.getElementById("processoGestNome").value = p.nome || "";
  document.getElementById("processoGestDescricao").value = p.descricao || "";
  document.getElementById("processoGestAtivo").value = p.ativo || "";
  document.getElementById("processoGestResponsavel").value = p.responsavel_id || "";
  document.getElementById("processoGestAprovador").value = p.aprovador_id || "";
  document.getElementById("processoGestStatus").value = p.status || "rascunho";
  document.getElementById("processoDatas").innerHTML = [
    `Criação: ${fmtData(p.criado_em)} — ${escapeHtml(p.criado_por_nome || "—")}`,
    `Revisão: ${fmtData(p.revisao_em)} — ${escapeHtml(p.revisado_por_nome || "—")}`,
    `Aprovação: ${fmtData(p.aprovacao_em)} — ${escapeHtml(p.aprovado_por_nome || "—")}`,
  ].map((t) => `<span class="meta-chip">${t}</span>`).join("");
}

function renderProcessoRevisoes(revisoes) {
  const list = document.getElementById("processoRevisoes");
  list.innerHTML = "";
  revisoes.forEach((r) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<span class="title">Revisão ${r.numero}</span><span class="sub">${fmtData(r.revisao_em)} · ${escapeHtml(r.revisado_por_nome || "—")}${r.aprovado_por_nome ? " · Aprovada por " + escapeHtml(r.aprovado_por_nome) : ""}</span>`;
    const ver = document.createElement("button");
    ver.className = "btn";
    ver.textContent = "Ver";
    ver.onclick = () => {
      alert(r.sintaxe || "(sem sintaxe)");
    };
    item.appendChild(meta);
    item.appendChild(ver);
    list.appendChild(item);
  });
}

async function saveProcessoMeta() {
  if (!state.processoId) return;
  const body = {
    nome: document.getElementById("processoGestNome").value.trim(),
    descricao: document.getElementById("processoGestDescricao").value,
    ativo: document.getElementById("processoGestAtivo").value,
    responsavel_id: Number(document.getElementById("processoGestResponsavel").value) || null,
    aprovador_id: Number(document.getElementById("processoGestAprovador").value) || null,
    status: document.getElementById("processoGestStatus").value,
  };
  await api(`/api/processos/${state.processoId}`, { method: "PUT", body });
  await loadProcessoDetail();
  await loadCrudProcessos();
}

async function aprovarProcesso() {
  if (!state.processoId) return;
  await api(`/api/processos/${state.processoId}/aprovar`, { method: "POST" });
  await loadProcessoDetail();
  await loadCrudProcessos();
}

// ===== Documentos do processo (explorador filesystem-first) =====
let selectedTreePath = null;
let treeFlat = {};
let treePasta = "";

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  if (["png", "jpg", "jpeg", "gif", "bmp", "svg"].includes(ext)) return "🖼️";
  if (ext === "pdf") return "📕";
  if (["doc", "docx"].includes(ext)) return "📘";
  if (["xls", "xlsx", "csv"].includes(ext)) return "📗";
  if (["ppt", "pptx"].includes(ext)) return "📙";
  if (["zip", "rar", "7z"].includes(ext)) return "🗜️";
  return "📄";
}

function buildTreeFlat(node) {
  treeFlat = {};
  (function walk(n, base) {
    if (n.tipo !== "dir") return;
    n.filhos.forEach((c) => {
      const p = base ? base + "/" + c.nome : c.nome;
      treeFlat[p] = c;
      if (c.tipo === "dir") walk(c, p);
    });
  })(node, "");
}

async function loadDocsTree() {
  const container = document.getElementById("docsTree");
  if (!state.processoId) {
    container.innerHTML = "";
    selectedTreePath = null;
    treeFlat = {};
    treePasta = "";
    window.fileTreeSelected = false;
    return;
  }
  const resp = await api(`/api/processos/${state.processoId}/arvore`);
  treePasta = resp.pasta || "";
  buildTreeFlat(resp.arvore);
  renderTree(resp.arvore);
}

function renderTree(tree) {
  const container = document.getElementById("docsTree");
  container.innerHTML = "";
  const root = document.createElement("div");
  root.className = "tree-root";
  root.appendChild(renderTreeNode(tree, ""));
  container.appendChild(root);
}

function renderTreeNode(node, relPath) {
  const el = document.createElement("div");
  el.className = "tree-item";
  el.dataset.path = relPath;
  if (node.tipo === "dir") {
    const head = document.createElement("div");
    head.className = "tree-row tree-dir" + (selectedTreePath === relPath ? " selected" : "");
    const toggle = document.createElement("span");
    toggle.className = "tree-toggle";
    toggle.textContent = "▾";
    const icon = document.createElement("span");
    icon.className = "tree-icon";
    icon.textContent = relPath ? "📁" : "🗂️";
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.nome;
    head.appendChild(toggle);
    head.appendChild(icon);
    head.appendChild(name);
    el.appendChild(head);
    const kids = document.createElement("div");
    kids.className = "tree-children";
    node.filhos.forEach((c) => kids.appendChild(renderTreeNode(c, relPath ? relPath + "/" + c.nome : c.nome)));
    el.appendChild(kids);
    let open = true;
    head.addEventListener("click", (ev) => {
      ev.stopPropagation();
      open = !open;
      kids.style.display = open ? "" : "none";
      toggle.textContent = open ? "▾" : "▸";
      selectTreeItem(relPath);
    });
    head.addEventListener("dragover", (ev) => { ev.preventDefault(); ev.stopPropagation(); head.classList.add("drag-over"); });
    head.addEventListener("dragleave", () => head.classList.remove("drag-over"));
    head.addEventListener("drop", (ev) => { ev.preventDefault(); ev.stopPropagation(); head.classList.remove("drag-over"); handleDrop(ev, relPath); });
  } else {
    const row = document.createElement("div");
    row.className = "tree-row tree-file" + (selectedTreePath === relPath ? " selected" : "");
    const icon = document.createElement("span");
    icon.className = "tree-icon";
    icon.textContent = fileIcon(node.nome);
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.nome;
    const size = document.createElement("span");
    size.className = "tree-size";
    size.textContent = formatSize(node.tamanho);
    row.appendChild(icon);
    row.appendChild(name);
    row.appendChild(size);
    el.appendChild(row);
    row.addEventListener("click", (ev) => { ev.stopPropagation(); selectTreeItem(relPath); });
    row.addEventListener("dblclick", (ev) => { ev.stopPropagation(); openFile(relPath); });
  }
  return el;
}

function selectTreeItem(relPath) {
  selectedTreePath = relPath;
  window.fileTreeSelected = true;
  document.querySelectorAll("#docsTree .tree-item").forEach((item) => {
    const row = item.querySelector(".tree-row");
    if (row) row.classList.toggle("selected", item.dataset.path === relPath);
  });
}

function openFile(relPath) {
  const a = document.createElement("a");
  a.href = `/api/processos/${state.processoId}/arquivo?caminho=${encodeURIComponent(opPath(relPath))}`;
  a.target = "_blank";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function opPath(full) {
  if (!treePasta) return full;
  if (full === treePasta) return "";
  if (full.startsWith(treePasta + "/")) return full.slice(treePasta.length + 1);
  return "";
}

function isInsideProcess(full) {
  return !!treePasta && full.startsWith(treePasta + "/");
}

async function handleDrop(ev, targetRelPath) {
  const files = ev.dataTransfer.files;
  if (!files.length) return;
  const subpasta = isInsideProcess(targetRelPath) ? opPath(targetRelPath) : "";
  for (const f of files) {
    const fd = new FormData();
    fd.append("file", f);
    fd.append("subpasta", subpasta);
    const r = await fetch(`/api/processos/${state.processoId}/arquivos`, {
      method: "POST",
      body: fd,
      credentials: "same-origin",
    });
    if (r.status === 401) { showLogin(); return; }
    if (!r.ok) {
      const d = await r.json().catch(() => null);
      alert(d && d.detail ? d.detail : "Erro ao enviar " + f.name);
    }
  }
  await loadDocsTree();
}

function targetOpDir() {
  if (!selectedTreePath) return "";
  const n = treeFlat[selectedTreePath];
  if (!n || n.tipo !== "dir") return "";
  if (isInsideProcess(selectedTreePath)) return opPath(selectedTreePath);
  return "";
}

async function createPasta() {
  if (!state.processoId) return;
  const nome = document.getElementById("docsNovaPasta").value.trim();
  if (!nome) return;
  await api(`/api/processos/${state.processoId}/pastas`, { method: "POST", body: { nome, subpasta: targetOpDir() } });
  document.getElementById("docsNovaPasta").value = "";
  await loadDocsTree();
}

async function createArquivo() {
  if (!state.processoId) return;
  const nome = document.getElementById("docsNovoNome").value.trim();
  if (!nome) return;
  await api(`/api/processos/${state.processoId}/arquivos/criar`, { method: "POST", body: { nome, subpasta: targetOpDir() } });
  document.getElementById("docsNovoNome").value = "";
  await loadDocsTree();
}

async function deleteTreeItem() {
  const p = selectedTreePath;
  if (!p) { alert("Selecione um arquivo ou pasta para excluir."); return; }
  if (!isInsideProcess(p)) { alert("Selecione um arquivo ou subpasta dentro do processo para excluir."); return; }
  const node = treeFlat[p];
  if (node && node.tipo === "dir" && !confirm(`Excluir a pasta "${node.nome}" e todo o seu conteúdo?`)) return;
  await api(`/api/processos/${state.processoId}/objetos?caminho=${encodeURIComponent(opPath(p))}`, { method: "DELETE" });
  selectedTreePath = null;
  window.fileTreeSelected = false;
  await loadDocsTree();
}

function initProcessos() {
  return Promise.all([loadProcessoUsuarios(), loadCrudProcessos()]);
}

// ===== Módulo Issues (PDCA) =====








const KANBAN_COLS = ["backlog", "iniciada", "em_andamento", "em_revisao", "finalizada"];
const KANBAN_LABELS = {
  backlog: "Backlog",
  iniciada: "Início",
  em_andamento: "Em andamento",
  em_revisao: "Revisão",
  finalizada: "Finalizado",
};


const ISSUE_STATUS_LABELS = { cadastrada: "Cadastrada", em_tratamento: "Em tratamento", fechada: "Fechada" };

function issueApiUrl(path) {
  return state.empresaId ? `${path}${path.includes("?") ? "&" : "?"}empresa_id=${state.empresaId}` : path;
}

async function showIssueView(view) {
  if (view === "limpeza" && !isAdmin()) return;
  if (view === "selecao" && !isEditor()) return;
  stopIssueSelecaoPolling();
  state.issueView = view;
  document.querySelectorAll(".issue-view").forEach((pane) => pane.classList.toggle("hidden", pane.id !== `issue-view-${view}`));
  document.querySelectorAll(".sidebar [data-issue-view]").forEach((link) => link.classList.toggle("active", link.dataset.issueView === view));
  try {
    if (view === "dashboard") await loadIssueDashboard();
    if (view === "limpeza") await loadIssueLimpeza();
    if (view === "capturar") await loadIssueList();
    if (view === "selecao") await loadIssueSelecao();
  } catch (e) {
    alert(e.message || "Erro ao carregar a seção de Issues.");
  }
}

function dashboardIssueKpis(kpis) {
  return [["Cadastradas", kpis.cadastradas], ["Em andamento", kpis.em_andamento],
    ["Fechadas no mês", kpis.fechadas_mes], ["Abertas >15 dias", kpis.abertas_mais_15_dias],
    ["Tratativa >15 dias", kpis.tratativa_mais_15_dias]]
    .map(([label, value]) => `<div class="issue-kpi"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
}

function issueDashboardDistribution(items, field) {
  const labels = {
    envolvidos_afetados: {cliente: "Cliente", operador: "Operador", equipe_interna: "Equipe interna", fornecedor: "Fornecedor", sistema_processo: "Sistema/Processo", multiplos: "Múltiplos envolvidos"},
    ambiente: {producao: "Produção", homologacao: "Homologação", campo: "Campo", linha: "Linha", outro: "Outro"},
  };
  const groups = new Map();
  items.forEach((item) => {
    if (!ISSUE_STATUS_LABELS[item.status]) return;
    let key, label;
    if (field === "usuario") {
      key = item.autor_registro_id || item.criado_por_id || "nao_informado";
      label = item.autor_registro_nome || item.criado_por_nome || "Não informado";
    } else {
      key = String(item[field] || "").trim() || "nao_informado";
      const normalized = key.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
      if (labels[field] && labels[field][normalized]) key = normalized;
      label = key === "nao_informado" ? "Não informado" : ((labels[field] && labels[field][key]) || key);
    }
    if (!groups.has(key)) groups.set(key, {key, label, total: 0, cadastrada: 0, em_tratamento: 0, fechada: 0});
    const group = groups.get(key);
    group[item.status] += 1;
    group.total += 1;
  });
  const result = Array.from(groups.values()).sort((a, b) => b.total - a.total || a.label.localeCompare(b.label, "pt-BR"));
  if (field === "usuario") {
    const names = new Map();
    result.forEach((group) => names.set(group.label, (names.get(group.label) || 0) + 1));
    result.forEach((group) => { if (names.get(group.label) > 1) group.label += ` (ID ${group.key})`; });
  }
  return result;
}

async function loadIssueDashboard() {
  const empresaId = state.empresaId;
  const [kpis, stats, trends, items] = await Promise.all([
    api(issueApiUrl("/api/issues/kpis")), api(issueApiUrl("/api/issues/stats")),
    api(issueApiUrl("/api/issues/trends")), api(issueApiUrl("/api/issues")),
  ]);
  if (empresaId !== state.empresaId) return;
  document.getElementById("issueDashboardKpis").innerHTML = dashboardIssueKpis(kpis);
  const status = stats.dimensoes.find((d) => d.chave === "status").dados.itens;
  const impacto = stats.dimensoes.find((d) => d.chave === "impacto").dados.itens;
  const layout = { margin: { t: 20, b: 50, l: 45, r: 20 }, font: { size: 12 } };
  const chart = (id, traces, extra = {}) => {
    if (!window.Plotly) { document.getElementById(id).innerHTML = '<p class="hint">Gráfico indisponível. Verifique a conexão.</p>'; return; }
    plot(id, { ...layout, ...extra }, traces);
  };
  const distribution = (id, field) => {
    const groups = issueDashboardDistribution(items, field);
    if (!groups.length) {
      document.getElementById(id).innerHTML = '<p class="hint">Nenhuma Issue para apresentar.</p>';
      return;
    }
    const colors = {cadastrada: "#64748b", em_tratamento: "#2563eb", fechada: "#16a34a"};
    const traces = Object.keys(ISSUE_STATUS_LABELS).map((status) => ({
      type: "bar", orientation: "h", name: ISSUE_STATUS_LABELS[status],
      y: groups.map((group) => group.label), x: groups.map((group) => group[status]),
      text: groups.map((group) => group[status] > 0 ? String(group[status]) : ""),
      texttemplate: "%{text}", textposition: "inside", insidetextanchor: "middle",
      textfont: {color: "#fff", size: 12}, constraintext: "inside",
      marker: {color: colors[status]}, hovertemplate: "%{y}: %{x} Issues<extra>%{fullData.name}</extra>",
    }));
    chart(id, traces, {barmode: "stack", height: Math.max(260, groups.length * 34 + 100),
      margin: {t: 15, b: 70, l: 130, r: 20}, legend: {orientation: "h", y: -0.2},
      xaxis: {title: "Quantidade de Issues", dtick: 1}, yaxis: {autorange: "reversed", automargin: true}});
  };
  distribution("issueDashboardEnvolvidos", "envolvidos_afetados");
  distribution("issueDashboardAmbiente", "ambiente");
  distribution("issueDashboardUsuario", "usuario");
  chart("issueDashboardStatus", [{type: "pie", hole: 0.55,
    textinfo: "value", textposition: "inside",
    labels: status.map((i) => ISSUE_STATUS_LABELS[i.rotulo] || i.rotulo), values: status.map((i) => i.frequencia)}]);
  const impactos = {baixo: "Baixo", medio: "Médio", alto: "Alto", critico: "Crítico"};
  chart("issueDashboardImpacto", [{type: "bar", x: impacto.map((i) => impactos[i.rotulo] || i.rotulo), y: impacto.map((i) => i.frequencia),
    text: impacto.map((i) => i.frequencia > 0 ? String(i.frequencia) : ""), texttemplate: "%{text}",
    textposition: "inside", insidetextanchor: "middle", textfont: {color: "#fff", size: 12}, constraintext: "inside"}]);
  const periods = trends.por_criacao.map((p) => p.periodo);
  chart("issueDashboardTendencia", [
    {type: "scatter", mode: "lines+markers", name: "Abertas", x: periods, y: trends.por_criacao.map((p) => p.total)},
    {type: "scatter", mode: "lines+markers", name: "Fechadas", x: periods, y: trends.por_finalizacao.map((p) => p.total)},
  ], {yaxis: {rangemode: "tozero", dtick: 1}});
  const older = items.filter((i) => i.status !== "fechada" && Date.now() - new Date(i.criado_em).getTime() > 15 * 86400000);
  const container = document.getElementById("issueDashboardAtrasadas");
  container.innerHTML = older.length ? "" : '<p class="hint">Nenhuma Issue aberta há mais de 15 dias.</p>';
  older.sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em) || b.id - a.id).forEach((i) => {
    const button = document.createElement("button");
    button.className = "btn";
    const title = document.createElement("strong");
    title.textContent = i.codigo;
    const age = document.createElement("span");
    age.textContent = `${Math.floor((Date.now() - new Date(i.criado_em)) / 86400000)} dias aberta`;
    const phase = document.createElement("span");
    phase.textContent = `Fase: ${ISSUE_STATUS_LABELS[i.status] || i.status}`;
    button.append(title, age, phase);
    if (i.status === "em_tratamento") {
      const treatment = document.createElement("span");
      const started = new Date(i.tratamento_iniciado_em).getTime();
      treatment.textContent = i.tratamento_iniciado_em && Number.isFinite(started)
        ? `${Math.max(0, Math.floor((Date.now() - started) / 86400000))} dias em tratamento`
        : "Início da tratativa não informado";
      button.appendChild(treatment);
    }
    button.onclick = async () => { await showIssueView("capturar"); await selectIssue(i.id); };
    container.appendChild(button);
  });
}

async function loadIssueLimpeza() {
  const button = document.getElementById("btnIssueLimpeza");
  button.disabled = true;
  state.issueLimpezaPreview = null;
  if (!state.empresaId) {
    document.getElementById("issueLimpezaResumo").textContent = "Selecione uma empresa.";
    return;
  }
  const scope = document.getElementById("issueLimpezaEscopo").value;
  const preview = await api(issueApiUrl(`/api/issues/limpeza?escopo=${scope}`));
  if (preview.empresa_id !== state.empresaId || scope !== document.getElementById("issueLimpezaEscopo").value) return;
  state.issueLimpezaPreview = preview;
  document.getElementById("issueLimpezaResumo").textContent = `${preview.issues} Issues e ${preview.acoes} ações serão removidas. ${preview.vinculadas_rnc_preservadas} Issues vinculadas a RNCs serão preservadas. Os arquivos físicos serão mantidos.`;
  button.disabled = preview.issues === 0;
}

async function limparBaseIssues() {
  const preview = state.issueLimpezaPreview;
  if (preview && (preview.empresa_id !== state.empresaId || preview.escopo !== document.getElementById("issueLimpezaEscopo").value)) return;
  if (!preview || !preview.issues || !confirm(`Remover ${preview.issues} Issues e ${preview.acoes} ações da empresa selecionada? Uma cópia do banco será criada antes da limpeza.`)) return;
  const button = document.getElementById("btnIssueLimpeza");
  button.disabled = true;
  try {
    const result = await api("/api/issues/limpeza", {method: "POST", body: {...preview, confirmar: true}});
    document.getElementById("issueLimpezaResultado").textContent = `${result.removidas} Issues removidas. Cópia de segurança criada.`;
    state.issueId = null;
    state.issue = null;
    document.getElementById("issueDetail").classList.add("hidden");
    await Promise.all([loadIssueList(), loadIssueKanban(), loadIssueLimpeza()]);
  } catch (e) {
    document.getElementById("issueLimpezaResultado").textContent = e.message || "Erro ao limpar a base.";
    await loadIssueLimpeza();
  }
}

function syncIssueStatus() {
  document.getElementById("issueStatus").textContent = state.issue ? (ISSUE_STATUS_LABELS[state.issue.status] || state.issue.status || "") : "";
  document.getElementById("btnIssueFechar").disabled = !state.issueId || !isEditor() || (state.issue && state.issue.status === "fechada");
}

async function loadIssueList() {
  const list = document.getElementById("issueList");
  const [allItems, kpis] = await Promise.all([api(issueApiUrl("/api/issues")), api(issueApiUrl("/api/issues/kpis"))]);
  document.getElementById("issueKpiCadastradas").textContent = kpis.cadastradas;
  document.getElementById("issueKpiAndamento").textContent = kpis.em_andamento;
  document.getElementById("issueKpiFechadas").textContent = kpis.fechadas_mes;
  document.getElementById("issueKpiAbertas15").textContent = kpis.abertas_mais_15_dias;
  document.getElementById("issueKpiTratativa15").textContent = kpis.tratativa_mais_15_dias;
  const items = allItems.filter((d) => d.status !== "fechada");
  list.innerHTML = '<option value="">Selecione uma Issue</option>';
  list.onchange = () => { if (list.value) selectIssue(Number(list.value)).catch((e) => alert(e.message)); };
  if (!items.length) {
    list.innerHTML = '<option value="">Nenhuma Issue aberta</option>';
    return;
  }
  items.forEach((d) => {
    const option = document.createElement("option");
    option.value = d.id;
    option.textContent = `${d.codigo} · ${d.comportamento_observado || ""} · ${ISSUE_STATUS_LABELS[d.status] || d.status || ""}`;
    list.appendChild(option);
  });
  list.value = state.issueId || "";
}


function issueNowLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function loadIssueAutores() {
  state.issueUsuarios = await api("/api/usuarios");
  fillIssueAutor(state.issue);
}

function fillIssueAutor(r) {
  const sel = document.getElementById("issueAutor");
  const selectedId = r ? (r.autor_registro_id || r.criado_por_id) : state.user && state.user.id;
  const empresaId = r ? r.empresa_id : state.empresaId;
  const usuarios = state.issueUsuarios.filter((u) => u.empresa_id === empresaId || u.id === selectedId || (state.user && u.id === state.user.id));
  sel.innerHTML = "";
  usuarios.forEach((u) => sel.appendChild(new Option(`${u.nome}${u.posicao ? ` (${u.posicao})` : ""}`, u.id)));
  if (selectedId && !usuarios.some((u) => u.id === selectedId)) {
    const nome = r && (r.autor_registro_nome || r.criado_por_nome);
    sel.appendChild(new Option(nome || "Autor original", selectedId));
  }
  sel.value = selectedId ? String(selectedId) : "";
}

function toggleIssueAmbienteOutro() {
  document.getElementById("issueAmbienteOutroBlock").classList.toggle("hidden", document.getElementById("issueAmbiente").value !== "outro");
}

function fillIssueAmbiente(value) {
  const sel = document.getElementById("issueAmbiente");
  const conhecido = Array.from(sel.options).some((o) => o.value === value);
  sel.value = value && !conhecido ? "outro" : (value || "");
  document.getElementById("issueAmbienteOutro").value = value && !conhecido ? value : "";
  toggleIssueAmbienteOutro();
}

function readIssueAmbiente() {
  const value = document.getElementById("issueAmbiente").value;
  return value === "outro" ? (document.getElementById("issueAmbienteOutro").value.trim() || "outro") : value;
}

function fillIssueCadastroInicial(r) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value == null ? "" : value;
  };
  set("issueCodigo", r && r.codigo);
  set("issueDetectadoEm", r && r.detectado_em ? String(r.detectado_em).slice(0, 16) : "");
  fillIssueAutor(r);
  set("issueComportamentoEsperado", r && r.comportamento_esperado);
  set("issueComportamentoObservado", r && r.comportamento_observado);
  set("issueEvidencias", r && r.evidencias_objetivas);
  set("issueCodigoErro", r && r.codigo_erro);
  fillIssueAmbiente(r && r.ambiente);
  set("issueEnvolvidos", r && r.envolvidos_afetados);
  set("issueImpacto", r && r.impacto);
  set("issueAcaoEmergencial", r && r.acao_emergencial);
  set("issueOQue", r && r.o_que);
  set("issueOnde", r && r.onde);
  set("issueQuando", r && r.quando);
  set("issueQuem", r && r.quem);
  set("issuePorQueInicial", r && r.por_que_inicial);
  set("issueComoDetectado", r && r.como_detectado);
}

function fillIssueRnc(r) {
  const status = document.getElementById("issueRncStatus");
  if (status) status.textContent = r && r.rnc_codigo ? `RNC ${r.rnc_codigo}` : "";
}

function novaIssue() {
  state.issueId = null;
  state.issue = null;
  fillIssueCadastroInicial(null);
  fillIssueRnc(null);
  document.getElementById("issueDetail").classList.remove("hidden");
  document.getElementById("issueTitulo").textContent = "Nova issue";
  document.getElementById("issueStatus").textContent = "";
  syncIssueStatus();
  document.getElementById("issueDetectadoEm").value = issueNowLocal();
  document.getElementById("issueDocsTree").innerHTML = "";
}


async function selectIssue(id) {
  state.issue = await api(`/api/issues/${id}`);
  state.issueId = id;
  document.getElementById("issueDetail").classList.remove("hidden");
  document.getElementById("issueTitulo").textContent = state.issue.codigo;
  syncIssueStatus();
  fillIssueCadastroInicial(state.issue);
  fillIssueRnc(state.issue);
  const envolvidos = document.getElementById("issueEnvolvidos");
  if (state.issue.envolvidos_afetados && !Array.from(envolvidos.options).some((o) => o.value === state.issue.envolvidos_afetados)) {
    envolvidos.value = "multiplos";
  }
  await loadIssueDocsTree();
}

function readCaptura() {
  const detectadoEm = document.getElementById("issueDetectadoEm").value;
  const impacto = document.getElementById("issueImpacto").value;
  const envolvidos = document.getElementById("issueEnvolvidos").value;
  const observado = document.getElementById("issueComportamentoObservado").value;
  const body = {
    autor_registro_id: Number(document.getElementById("issueAutor").value) || null,
    data: detectadoEm ? detectadoEm.slice(0, 10) : "",
    detectado_em: detectadoEm,
    comportamento_esperado: document.getElementById("issueComportamentoEsperado").value,
    comportamento_observado: document.getElementById("issueComportamentoObservado").value,
    evidencias_objetivas: document.getElementById("issueEvidencias").value,
    codigo_erro: document.getElementById("issueCodigoErro").value,
    ambiente: readIssueAmbiente(),
    envolvidos_afetados: envolvidos,
    impacto,
    acao_emergencial: document.getElementById("issueAcaoEmergencial").value,
    o_que: observado,
    onde: document.getElementById("issueOnde").value,
    quando: detectadoEm,
    quem: envolvidos,
    por_que_inicial: document.getElementById("issuePorQueInicial").value,
    como_detectado: document.getElementById("issueComoDetectado").value,
  };
  if (isSuperuser()) body.empresa_id = state.empresaId || null;
  return body;
}


async function salvarIssueCaptura() {
  const body = readCaptura();
  try {
    if (state.issueId) {
      state.issue = await api(`/api/issues/${state.issueId}`, { method: "PUT", body });
    } else {
      state.issue = await api("/api/issues", { method: "POST", body });
      state.issueId = state.issue.id;
    }
  } catch (e) {
    alert(e.message || "Erro ao salvar o registro.");
    return;
  }
  document.getElementById("issueTitulo").textContent = state.issue.codigo;
  syncIssueStatus();
  fillIssueCadastroInicial(state.issue);
  fillIssueRnc(state.issue);
  await loadIssueList();
  await loadIssueKanban();
}














async function refreshIssue() {
  state.issue = await api(`/api/issues/${state.issueId}`);
  fillIssueCadastroInicial(state.issue);
  fillIssueRnc(state.issue);
  syncIssueStatus();
}

let issueTratamentoPending = false;
async function iniciarIssueTratamento() {
  if (issueTratamentoPending || !isEditor() || !state.issueId || !state.issue || state.issue.status !== "cadastrada") return;
  const id = state.issueId;
  issueTratamentoPending = true;
  try {
    const updated = await api(`/api/issues/${id}/iniciar-tratamento`, { method: "POST" });
    if (state.issueId === id) {
      state.issue.status = updated.status;
      syncIssueStatus();
    }
    await loadIssueList();
  } catch (e) {
    alert(e.message || "Erro ao iniciar o tratamento.");
  } finally {
    issueTratamentoPending = false;
  }
}

async function fecharIssue() {
  if (!state.issueId || !confirm("Fechar esta Issue? Ela sairá da lista de Issues abertas.")) return;
  try {
    state.issue = await api(`/api/issues/${state.issueId}/fechar`, { method: "POST" });
    syncIssueStatus();
    document.getElementById("issueDetail").classList.add("hidden");
    await loadIssueList();
  } catch (e) {
    alert(e.message || "Erro ao fechar a Issue.");
  }
}


async function excluirIssue() {
  if (!state.issueId) return;
  if (!confirm("Excluir esta issue, suas ações, Ishikawa vinculado e documentos?")) return;
  await api(`/api/issues/${state.issueId}`, { method: "DELETE" });
  state.issueId = null;
  state.issue = null;
  document.getElementById("issueDetail").classList.add("hidden");
  await loadIssueList();
  await loadIssueKanban();
}

async function loadIssueKanban() {
  const company=state.empresaId;
  const items = await api(issueApiUrl("/api/issues/kanban"));
  if(company!==state.empresaId)return;
  for (const id of ["issueKanban", "rncKanban"]) renderIssueKanban(document.getElementById(id), id==='rncKanban'?items.filter(action=>action.rnc_id && action.rnc_codigo):items);
  if(typeof updateRncKanbanStatus==='function')updateRncKanbanStatus(items);
}

function renderIssueKanban(container, items) {
  container.innerHTML = "";
  KANBAN_COLS.forEach((col) => {
    const colEl = document.createElement("div");
    colEl.className = "kanban-col";
    colEl.dataset.col = col;
    const h = document.createElement("h4");
    h.textContent = KANBAN_LABELS[col] || col;
    h.title = col.replaceAll("_", " ");
    colEl.appendChild(h);
    colEl.addEventListener("dragover", (ev) => { ev.preventDefault(); colEl.classList.add("drag-over"); });
    colEl.addEventListener("dragleave", () => colEl.classList.remove("drag-over"));
    colEl.addEventListener("drop", async (ev) => {
      ev.preventDefault();
      colEl.classList.remove("drag-over");
      const acaoId = Number(ev.dataTransfer.getData("text/plain"));
      if (!acaoId) return;
      const acao = items.find((a) => a.id === acaoId);
      if (!acao) return;
      await api(`/api/issues/${acao.issue_id}/acoes/${acao.id}/status`, { method: "PUT", body: { status: col } });
      if (state.issueId && state.issueId === acao.issue_id) refreshIssue();
      await loadIssueKanban();
    });
    items.filter((a) => a.status === col).forEach((a) => {
      const card = document.createElement("div");
      card.className = "kanban-card";
      card.draggable = true;
      const descricao = a.descricao || a.issue_descricao || "";
      const codigo = a.rnc_codigo || a.codigo;
      card.title = `${codigo} · ${a.codigo} — ${descricao}\nResponsável: ${a.responsavel_nome || "—"}`;
      card.innerHTML = `<div class="kc-title">${escapeHtml(codigo)}</div>${container.id==='rncKanban'?'':`<div class="kc-sub">${escapeHtml(descricao)}</div>`}`;
      card.addEventListener("dragstart", (ev) => ev.dataTransfer.setData("text/plain", String(a.id)));
      colEl.appendChild(card);
    });
    container.appendChild(colEl);
  });
}

let issueTreeSelectedPath = null;

async function loadIssueDocsTree() {
  const container = document.getElementById("issueDocsTree");
  if (!state.issueId) {
    container.innerHTML = "";
    return;
  }
  const resp = await api(`/api/issues/${state.issueId}/arvore`);
  state.issueTree = resp.arvore;
  renderIssueTree(resp.arvore, container);
}

function renderIssueTree(tree, container) {
  container.innerHTML = "";
  container.appendChild(renderIssueTreeNode(tree, ""));
}

function renderIssueTreeNode(node, relPath) {
  const el = document.createElement("div");
  el.className = "tree-item";
  el.dataset.path = relPath;
  if (node.tipo === "dir") {
    const head = document.createElement("div");
    head.className = "tree-row tree-dir" + (issueTreeSelectedPath === relPath ? " selected" : "");
    const toggle = document.createElement("span");
    toggle.className = "tree-toggle";
    toggle.textContent = "▾";
    const icon = document.createElement("span");
    icon.className = "tree-icon";
    icon.textContent = relPath ? "📁" : "🗂️";
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.nome;
    head.appendChild(toggle);
    head.appendChild(icon);
    head.appendChild(name);
    head.addEventListener("click", () => {
      issueTreeSelectedPath = relPath;
      renderIssueTree(state.issueTree, document.getElementById("issueDocsTree"));
    });
    head.addEventListener("dragover", (ev) => { ev.preventDefault(); head.classList.add("drag-over"); });
    head.addEventListener("dragleave", () => head.classList.remove("drag-over"));
    head.addEventListener("drop", async (ev) => {
      ev.preventDefault();
      head.classList.remove("drag-over");
      const files = ev.dataTransfer.files;
      if (!files || !files.length) return;
      for (const f of files) {
        const fd = new FormData();
        fd.append("file", f);
        fd.append("subpasta", relPath);
        await fetch(`/api/issues/${state.issueId}/arquivos`, { method: "POST", body: fd, credentials: "same-origin" });
      }
      loadIssueDocsTree();
    });
    el.appendChild(head);
    const kids = document.createElement("div");
    kids.className = "tree-children";
    node.filhos.forEach((c) => kids.appendChild(renderIssueTreeNode(c, relPath ? relPath + "/" + c.nome : c.nome)));
    el.appendChild(kids);
  } else {
    const row = document.createElement("div");
    row.className = "tree-row" + (issueTreeSelectedPath === relPath ? " selected" : "");
    const icon = document.createElement("span");
    icon.className = "tree-icon";
    icon.textContent = "📄";
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.nome;
    row.appendChild(icon);
    row.appendChild(name);
    row.addEventListener("click", () => { issueTreeSelectedPath = relPath; renderIssueTree(state.issueTree, document.getElementById("issueDocsTree")); });
    row.addEventListener("dblclick", () => {
      window.open(`/api/issues/${state.issueId}/arquivo?caminho=${encodeURIComponent(relPath)}`, "_blank");
    });
    el.appendChild(row);
  }
  return el;
}

async function issueCreatePasta() {
  if (!state.issueId) return;
  const nome = document.getElementById("issueDocsNovaPasta").value.trim();
  if (!nome) return;
  await api(`/api/issues/${state.issueId}/pastas`, { method: "POST", body: { nome, subpasta: issueTreeSelectedPath || "" } });
  document.getElementById("issueDocsNovaPasta").value = "";
  await loadIssueDocsTree();
}

async function issueCreateArquivo() {
  if (!state.issueId) return;
  const nome = document.getElementById("issueDocsNovoNome").value.trim();
  if (!nome) return;
  await api(`/api/issues/${state.issueId}/arquivos/criar`, { method: "POST", body: { nome, subpasta: issueTreeSelectedPath || "" } });
  document.getElementById("issueDocsNovoNome").value = "";
  await loadIssueDocsTree();
}

async function issueDeleteObjeto() {
  if (!state.issueId || !issueTreeSelectedPath) return;
  await api(`/api/issues/${state.issueId}/objetos?caminho=${encodeURIComponent(issueTreeSelectedPath)}`, { method: "DELETE" });
  issueTreeSelectedPath = null;
  await loadIssueDocsTree();
}



async function bindIssueTabs() {
  document.querySelectorAll(".rnc-tab[data-issue-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".rnc-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".rnc-pane").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const pane = document.getElementById("issue-tab-" + tab.dataset.issueTab);
      if (pane) pane.classList.add("active");
    });
  });
}

async function initIssues() {
  state.issueId = null;
  state.issue = null;
  state.issueLimpezaPreview = null;
  document.getElementById("issueDetail").classList.add("hidden");
  bindIssueTabs();
  await loadIssueAutores();
  await showIssueView("capturar");
  await loadIssueKanban();
}

async function transcreverArquivo(ev, targetId) {
  const f = ev.target.files && ev.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  try {
    const resp = await fetch("/api/transcricao", { method: "POST", body: fd, credentials: "same-origin" });
    if (!resp.ok) {
      const d = await resp.json().catch(() => null);
      throw new Error(d && d.detail ? d.detail : "Erro ao transcrever");
    }
    const data = await resp.json();
    document.getElementById(targetId).value = data.texto || "";
  } catch (e) {
    alert(e.message);
  }
  ev.target.value = "";
}

let rncRecords = [];
let rncLoadEpoch = 0;
async function loadRncs() {
  const epoch = ++rncLoadEpoch;
  const company = state.empresaId;
  const select = document.getElementById("rncSelect");
  const previous = select.value;
  select.replaceChildren(new Option("Selecione uma RNC", ""));
  document.getElementById("rncDetail").classList.add("hidden");
  document.getElementById("rncMensagem").textContent = "Carregando RNCs…";
  rncRecords = [];
  const records = await api(issueApiUrl("/api/rncs"));
  if (epoch !== rncLoadEpoch || company !== state.empresaId) return;
  rncRecords = records.filter(item => item.rnc_id);
  filterRncSelect(previous,false);
  renderRncDetail();
  await loadIssueKanban();
}

function filterRncSelect(previous=document.getElementById('rncSelect').value,refresh=true) {
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const query=normalize(document.getElementById('rncFilter').value.trim());
  const expression=Array.from(query).map(char=>char==='*'?'.*':char==='?'?'.':char.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('');
  const pattern=new RegExp(/[?*]/.test(query)?`^${expression}$`:expression,'su');
  const visible=rncRecords.filter(item=>[item.rnc_codigo,item.codigo,item.comportamento_observado].some(value=>pattern.test(normalize(value))));
  const select=document.getElementById('rncSelect');
  select.replaceChildren(new Option('Selecione uma RNC',''));
  visible.forEach(item=>select.appendChild(new Option(`${item.rnc_codigo} · ${item.codigo} · ${item.comportamento_observado||''}`,item.id)));
  select.value=visible.some(item=>String(item.id)===previous)?previous:'';
  document.getElementById('rncMensagem').textContent=!rncRecords.length?'Nenhuma RNC emitida nesta empresa.':!visible.length?'Nenhuma RNC corresponde ao filtro.':`${visible.length} de ${rncRecords.length} RNC(s).`;
  if(refresh && previous!==select.value)renderRncDetail();
}

function renderRncDetail() {
  const target = document.getElementById("rncDetail");
  target.replaceChildren();
  const item = rncRecords.find(row => String(row.id) === document.getElementById("rncSelect").value);
  target.classList.toggle("hidden", !item);
  if (!item) return;
  if (typeof renderRncTabs === 'function') { renderRncTabs(target,item); return; }
  const header=document.createElement("div");header.className="rnc-header";
  const heading = document.createElement("h3");heading.textContent=item.rnc_codigo;
  const status=document.createElement("span");status.className="meta-chip";status.textContent=item.rnc_status==='emitida'?'Emitida':item.rnc_status;
  const spacer=document.createElement("span");spacer.className="spacer";
  const button=document.createElement("button");button.type="button";button.className="btn";button.textContent="Consultar Issue de origem";
  button.onclick=async()=>{navigate("issues");await showIssueView("capturar");await selectIssue(item.id);};
  header.append(heading,status,spacer,button);target.appendChild(header);
  const fields = [
    ["Issue de origem", item.codigo], ["Situação da RNC", item.rnc_status],
    ["Emitida em", item.rnc_emitida_em], ["Emitida por", item.rnc_emitida_por_nome],
    ["Comportamento esperado", item.comportamento_esperado], ["Comportamento observado", item.comportamento_observado],
    ["Evidências", item.evidencias_objetivas], ["Como foi detectado", item.como_detectado],
    ["Classificação", item.rnc_criticidade], ["Enquadramento", item.rnc_enquadramento_normativo],
    ["Contenção definitiva", item.rnc_acao_contencao_definitiva], ["Responsável pela contenção", item.rnc_contencao_responsavel_nome],
    ["Data/hora da contenção", item.rnc_contencao_em], ["Disposição inicial", item.rnc_disposicao_inicial],
    ["Líder da investigação", item.rnc_lider_investigacao_nome], ["Equipe", (item.rnc_equipe_investigacao_nomes || []).join(", ")],
    ["Metodologia", item.rnc_metodologia], ["Prazo de análise", item.rnc_prazo_analise],
    ["Prazo do plano", item.rnc_prazo_plano_acao], ["Prazo de eficácia", item.rnc_prazo_verificacao_eficacia],
    ["Auditor da eficácia", item.rnc_auditor_eficacia_nome],
  ];
  const formatDate=value=>{
    if(!value)return '';
    const date=new Date(value);
    return Number.isNaN(date.getTime())?value:date.toLocaleString('pt-BR');
  };
  const names={maior:'Maior',menor:'Menor',emitida:'Emitida',refugo:'Refugo',retrabalho:'Retrabalho',
    devolucao_fornecedor:'Devolução ao fornecedor',liberacao_concessao:'Liberação por concessão',
    '5_porques':'5 Porquês',ishikawa:'Ishikawa',fmea:'FMEA'};
  function block(title,entries,columns=2,textareas=false) {
    const section=document.createElement('div');section.className='card issue-initial-block rnc-data-block';
    const heading=document.createElement('h4');heading.textContent=title;section.appendChild(heading);
    const grid=document.createElement('div');grid.className=`grid-${columns}`;
    entries.forEach(([caption,value])=>{
      const wrap=document.createElement('div'),label=document.createElement('label');label.textContent=caption;
      const input=document.createElement(textareas?'textarea':'input');
      if(textareas)input.rows=3;else input.type='text';
      input.readOnly=true;input.setAttribute('aria-label',caption);input.placeholder='Não informado';
      input.value=names[value] || value || '';
      label.appendChild(input);wrap.appendChild(label);grid.appendChild(wrap);
    });
    section.appendChild(grid);target.appendChild(section);
  }
  block('Identificação da RNC',[
    ['Código da RNC',item.rnc_codigo],fields[0],fields[8],
    ['Data/hora da emissão',formatDate(item.rnc_emitida_em)],fields[3],
    ['Data/hora da detecção',formatDate(item.detectado_em)],
  ],3);
  block('Registro da ocorrência',[fields[4],fields[5],fields[6],
    ['Ação emergencial adotada',item.acao_emergencial],fields[7],['Onde ocorreu',item.onde]],2,true);
  block('Enquadramento e contenção',[fields[9],fields[10]],2,true);
  block('Responsabilidade pela contenção',[fields[11],['Data/hora da contenção',formatDate(item.rnc_contencao_em)],fields[13]],3);
  block('Investigação e eficácia',[fields[14],fields[15],fields[16],fields[20]],2);
  block('Prazos',[fields[17],fields[18],fields[19]].map(([caption,value])=>[caption,value?(/^\d{4}-\d{2}-\d{2}$/.test(value)?value.split('-').reverse().join('/'):value):'']),3);
}

document.getElementById("rncSelect").addEventListener("change", renderRncDetail);
document.getElementById("rncFilter").addEventListener("input",()=>filterRncSelect());
const menuButton = document.getElementById("btnMenuToggle");
function setMenuCollapsed(collapsed) {
  document.querySelector(".layout").classList.toggle("menu-collapsed", collapsed);
  menuButton.setAttribute("aria-expanded", String(!collapsed));
  menuButton.title = collapsed ? "Expandir menu" : "Recolher menu";
  window.dispatchEvent(new Event("resize"));
}
try { setMenuCollapsed(localStorage.getItem("qualidade.menuCollapsed") === "true"); } catch (_) {}
menuButton.addEventListener("click", () => {
  const collapsed = menuButton.getAttribute("aria-expanded") === "true";
  setMenuCollapsed(collapsed);
  try { localStorage.setItem("qualidade.menuCollapsed", String(collapsed)); } catch (_) {}
});

document.querySelectorAll(".sidebar a").forEach((a) => {
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    navigate(a.dataset.section);
    if (a.dataset.section === "issues") showIssueView(a.dataset.issueView || "capturar");
    if (a.dataset.section === "configuracao") loadLlmAcessos().catch((e) => alert(e.message));
    if (a.dataset.section === "rncs") loadRncs().catch((e) => { document.getElementById("rncMensagem").textContent=e.message; });
  });
});

document.getElementById("btnLogin").addEventListener("click", login);
document.getElementById("btnLogout").addEventListener("click", logout);
document.getElementById("empresaForm").addEventListener("submit", createEmpresa);
document.getElementById("usuarioForm").addEventListener("submit", createUsuario);
document.getElementById("usuarioEmpresa").addEventListener("change", loadUsuarioSetores);
document.getElementById("empresaSelect").addEventListener("change", async (e) => {
  state.empresaId = Number(e.target.value) || null;
  resetIssueSelecao();
  if (state.issueView === "selecao") await loadIssueSelecao();
  resetLlmForm();
  if (document.getElementById("section-configuracao").classList.contains("active")) await loadLlmAcessos().catch((err) => alert(err.message));
  state.issueLimpezaPreview = null;
  document.getElementById("btnIssueLimpeza").disabled = true;
  document.getElementById("issueLimpezaResultado").textContent = "";
  state.processoId = null;
  document.getElementById("processoDetail").classList.add("hidden");
  await Promise.all([loadCrudSetores(), loadCrudProcessos(), loadUsuarioSetores()]);
  await loadIssueAutores();
  state.issueId = null;
  state.issue = null;
  document.getElementById("issueDetail").classList.add("hidden");
  await loadIssueList();
  await loadIssueKanban();
  if (document.getElementById("section-rncs").classList.contains("active")) await loadRncs();
  if (state.issueView === "dashboard") await loadIssueDashboard();
  if (state.issueView === "limpeza" && isAdmin()) await loadIssueLimpeza();
});

document.getElementById("setorForm").addEventListener("submit", createSetorCRUD);
document.getElementById("processoForm").addEventListener("submit", createProcessoCRUD);
document.getElementById("setorEmpresa").addEventListener("change", loadCrudSetores);
document.getElementById("processoEmpresa").addEventListener("change", loadCrudProcessos);

document.getElementById("btnProcessoSalvarMeta").addEventListener("click", saveProcessoMeta);
document.getElementById("btnProcessoAprovar").addEventListener("click", aprovarProcesso);
document.getElementById("btnProcessoExcluir").addEventListener("click", async () => {
  if (!state.processoId) return;
  if (!confirm("Excluir este processo e todos os seus arquivos/pastas? Esta ação não pode ser desfeita.")) return;
  await api(`/api/processos/${state.processoId}`, { method: "DELETE" });
  state.processoId = null;
  document.getElementById("processoDetail").classList.add("hidden");
  await loadCrudProcessos();
});

document.getElementById("btnNovaPasta").addEventListener("click", createPasta);
document.getElementById("btnCriarDoc").addEventListener("click", createArquivo);
document.getElementById("btnRefreshDocs").addEventListener("click", loadDocsTree);

document.getElementById("docsTree").addEventListener("dragover", (ev) => { ev.preventDefault(); });
document.getElementById("docsTree").addEventListener("drop", (ev) => { ev.preventDefault(); handleDrop(ev, ""); });

document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Delete" && ev.key !== "Backspace") return;
  if (!window.fileTreeSelected) return;
  const active = document.querySelector(".section.active");
  if (!active || active.id !== "section-processos") return;
  const ae = document.activeElement;
  if (ae && (ae.tagName === "TEXTAREA" || ae.tagName === "INPUT" || ae.tagName === "SELECT")) return;
  ev.preventDefault();
  deleteTreeItem();
});

document.getElementById("btnIssueNova").addEventListener("click", novaIssue);
document.getElementById("btnIssueSalvar").addEventListener("click", salvarIssueCaptura);
document.getElementById("btnIssueFechar").addEventListener("click", fecharIssue);
document.getElementById("issue-tab-captura").addEventListener("input", iniciarIssueTratamento);
document.getElementById("issue-tab-captura").addEventListener("change", iniciarIssueTratamento);
document.getElementById("issueAmbiente").addEventListener("change", toggleIssueAmbienteOutro);
document.getElementById("btnIssueExcluir").addEventListener("click", excluirIssue);
document.getElementById("btnIssueNovaPasta").addEventListener("click", issueCreatePasta);
document.getElementById("btnIssueCriarDoc").addEventListener("click", issueCreateArquivo);
document.getElementById("btnIssueRefreshDocs").addEventListener("click", loadIssueDocsTree);
document.getElementById("issueLimpezaEscopo").addEventListener("change", () => {
  document.getElementById("issueLimpezaResultado").textContent = "";
  loadIssueLimpeza().catch((e) => alert(e.message));
});
document.getElementById("btnIssueLimpeza").addEventListener("click", limparBaseIssues);
(async function init() {
  try {
    state.user = await api("/api/auth/me");
    await onAuth();
  } catch (e) {
    showLogin();
  }
})();
