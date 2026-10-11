const state = {
  user: null,
  empresas: [],
  empresaId: null,
  processoId: null,
  issueId: null,
  issue: null,
  editingAcaoId: null,
  issueUsuarios: [],
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
  hideLogin();
  document.getElementById("userInfo").textContent =
    `${state.user.nome} (${state.user.papel})`;
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("hidden", !isAdmin());
  });
  await initEmpresaGlobal();
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
      loadIssueSetores();
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
  await loadIssueSetores();
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
const ISSUE_ISHI_KEYS = [
  { key: "metodo", label: "Método", inputId: "issueIshiMetodo", catInputId: "issueCatMetodo", labelId: "issueIshiLabelMetodo" },
  { key: "maquina", label: "Máquina", inputId: "issueIshiMaquina", catInputId: "issueCatMaquina", labelId: "issueIshiLabelMaquina" },
  { key: "medida", label: "Medida", inputId: "issueIshiMedida", catInputId: "issueCatMedida", labelId: "issueIshiLabelMedida" },
  { key: "meio", label: "Meio Ambiente", inputId: "issueIshiMeio", catInputId: "issueCatMeio", labelId: "issueIshiLabelMeio" },
  { key: "material", label: "Material", inputId: "issueIshiMaterial", catInputId: "issueCatMaterial", labelId: "issueIshiLabelMaterial" },
  { key: "mao", label: "Mão de Obra", inputId: "issueIshiMao", catInputId: "issueCatMao", labelId: "issueIshiLabelMao" },
];

let issueIshiCategorias = {};

function issueCurrentCats() {
  return ISSUE_ISHI_KEYS.map((cat) => ({
    ...cat,
    label: (issueIshiCategorias && issueIshiCategorias[cat.key]) || cat.label,
  }));
}

function syncIssueCatLabels() {
  issueCurrentCats().forEach((cat) => {
    const lbl = document.getElementById(cat.labelId);
    if (lbl) lbl.textContent = cat.label;
  });
}

function readIssueCategorias() {
  const c = {};
  ISSUE_ISHI_KEYS.forEach(({ key, catInputId, label }) => {
    const el = document.getElementById(catInputId);
    c[key] = el && el.value.trim() ? el.value.trim() : label;
  });
  return c;
}

function fillIssueCategorias(categorias) {
  ISSUE_ISHI_KEYS.forEach(({ key, catInputId, label }) => {
    const el = document.getElementById(catInputId);
    if (el) el.value = (categorias && categorias[key]) || label;
  });
  issueIshiCategorias = categorias || {};
  syncIssueCatLabels();
}

function readIssueCausas() {
  const c = {};
  ISSUE_ISHI_KEYS.forEach(({ key, inputId }) => {
    c[key] = document.getElementById(inputId).value.split("\n").map((s) => s.trim()).filter(Boolean);
  });
  return c;
}

function renderIssueIshikawa() {
  const efeito = document.getElementById("issueIshiEfeito").value || "Defeito";
  const causes = issueCurrentCats().map(({ label, inputId }) => ({
    nome: label,
    causas: document.getElementById(inputId).value.split("\n").map((s) => s.trim()).filter(Boolean),
  }));

  const top = causes.slice(0, 3);
  const bottom = causes.slice(3);
  const maxCauses = Math.max(1, ...causes.map((c) => c.causas.length));
  const COLORS = ["#dc2626", "#2563eb", "#16a34a"];

  const width = 1800;
  const lineGap = 26;
  const boneLen = 70;
  const topRoom = boneLen + 40 + (maxCauses - 1) * lineGap;
  const height = Math.max(480, topRoom * 2 + 40);
  const cy = height / 2;
  const left = 300;
  const effectW = 160;
  const effectX = width - effectW - 40;
  const right = effectX - 80;
  const spineLen = right - left;
  const xs = [left + spineLen * 0.08, left + spineLen * 0.5, left + spineLen * 0.9];

  let svg = `<svg class="ishikawa" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
  svg += `<line class="spine" x1="${left}" y1="${cy}" x2="${right}" y2="${cy}"/>`;
  svg += `<rect x="${effectX}" y="${cy - 16}" width="${effectW}" height="32" rx="4" fill="#2563eb"/>`;
  svg += `<text x="${effectX + effectW / 2}" y="${cy + 4}" text-anchor="middle" fill="#fff" font-size="12">${escapeHtml(efeito)}</text>`;

  const boneTop = cy - boneLen;
  const boneBottom = cy + boneLen;

  top.forEach((cat, i) => {
    const bx = xs[i];
    const color = COLORS[i];
    svg += `<line class="bone" x1="${bx}" y1="${cy}" x2="${bx}" y2="${boneTop}" stroke="${color}"/>`;
    svg += `<text class="cause" x="${bx - 10}" y="${boneTop + 4}" text-anchor="end" font-weight="bold" fill="${color}">${escapeHtml(cat.nome)}</text>`;
    cat.causas.forEach((c, j) => {
      const lineY = boneTop - 26 - j * lineGap;
      const dir = j % 2 === 0 ? 1 : -1;
      const xEnd = bx + dir * 60;
      svg += `<line class="bone" x1="${bx}" y1="${boneTop}" x2="${xEnd}" y2="${lineY}" stroke="${color}"/>`;
      svg += `<text class="cause" x="${xEnd + dir * 6}" y="${lineY + 4}" text-anchor="${dir > 0 ? "start" : "end"}" fill="${color}">${escapeHtml(c)}</text>`;
    });
  });

  bottom.forEach((cat, i) => {
    const bx = xs[i];
    const color = COLORS[i];
    svg += `<line class="bone" x1="${bx}" y1="${cy}" x2="${bx}" y2="${boneBottom}" stroke="${color}"/>`;
    svg += `<text class="cause" x="${bx - 10}" y="${boneBottom + 4}" text-anchor="end" font-weight="bold" fill="${color}">${escapeHtml(cat.nome)}</text>`;
    cat.causas.forEach((c, j) => {
      const lineY = boneBottom + 26 + j * lineGap;
      const dir = j % 2 === 0 ? 1 : -1;
      const xEnd = bx + dir * 60;
      svg += `<line class="bone" x1="${bx}" y1="${boneBottom}" x2="${xEnd}" y2="${lineY}" stroke="${color}"/>`;
      svg += `<text class="cause" x="${xEnd + dir * 6}" y="${lineY + 4}" text-anchor="${dir > 0 ? "start" : "end"}" fill="${color}">${escapeHtml(c)}</text>`;
    });
  });

  svg += "</svg>";
  document.getElementById("issueIshiOut").innerHTML = svg;
}

const KANBAN_COLS = ["backlog", "iniciada", "em_andamento", "em_revisao", "finalizada"];
const KANBAN_LABELS = {
  backlog: "Backlog",
  iniciada: "Início",
  em_andamento: "Em andamento",
  em_revisao: "Revisão",
  finalizada: "Finalizado",
};

async function loadIssueUsuarios() {
  state.issueUsuarios = await api("/api/usuarios").catch(() => []);
  ["issueOperador", "issueInspetor", "issueAcaoResponsavel", "issueRncContencaoResponsavel", "issueRncLider", "issueRncAuditor"].forEach((selId) => {
    const sel = document.getElementById(selId);
    sel.innerHTML = "";
    sel.appendChild(new Option("—", ""));
    state.issueUsuarios.forEach((u) => sel.appendChild(new Option(u.nome, u.id)));
  });
  const equipe = document.getElementById("issueRncEquipe");
  equipe.innerHTML = "";
  state.issueUsuarios.forEach((u) => equipe.appendChild(new Option(u.nome, u.id)));
}

async function loadIssueSetores() {
  const sel = document.getElementById("issueSetor");
  sel.innerHTML = "";
  sel.appendChild(new Option("—", ""));
  if (!state.empresaId) return;
  const setores = await api(`/api/setores?empresa_id=${state.empresaId}`);
  setores.forEach((s) => sel.appendChild(new Option(s.nome, s.id)));
}

async function loadIssueProcessos() {
  const sel = document.getElementById("issueProcesso");
  sel.innerHTML = "";
  sel.appendChild(new Option("—", ""));
  const setorId = Number(document.getElementById("issueSetor").value) || null;
  if (!setorId) return;
  const processos = await api(`/api/processos?setor_id=${setorId}`);
  processos.forEach((p) => sel.appendChild(new Option(p.nome, p.id)));
}

async function loadIssueList() {
  const list = document.getElementById("issueList");
  const items = await api("/api/issues");
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = '<p class="hint">Nenhuma issue registrada.</p>';
    return;
  }
  items.forEach((d) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.style.cursor = "pointer";
    meta.innerHTML = `<span class="title">${escapeHtml(d.codigo)} · ${escapeHtml(d.descricao || "")}</span><span class="sub">${escapeHtml(d.tipo || "")} · ${escapeHtml(d.severidade || "")} · ${escapeHtml(d.status || "")}</span>`;
    meta.onclick = () => selectIssue(d.id);
    item.appendChild(meta);
    list.appendChild(item);
  });
}

function issueOrigemValor() {
  const el = document.querySelector('input[name="issueOrigem"]:checked');
  return el ? el.value : "";
}

function issueOrigemSetar(valor) {
  document.querySelectorAll('input[name="issueOrigem"]').forEach((r) => {
    r.checked = (r.value === valor);
  });
}

function toggleIssueBlocks() {
  const r = state.issue;
  const usarIshi = !!(r && r.usar_ishikawa);
  const usarPorques = !!(r && r.usar_porques);
  document.getElementById("issueIshiBlock").classList.toggle("hidden", !usarIshi);
  document.getElementById("issuePorquesBlock").classList.toggle("hidden", !usarPorques);
  const tabInv = document.querySelector('[data-issue-tab="investigacao"]');
  const investigar = !!(r && r.investigar_causa);
  tabInv.disabled = !investigar;
  tabInv.title = investigar ? "" : "Marque \"investigar a causa\" na Aba 2 para liberar";
  if (!investigar && tabInv.classList.contains("active")) {
    document.querySelector('[data-issue-tab="captura"]').click();
  }
}

function issueNowLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fillIssueCadastroInicial(r) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value == null ? "" : value;
  };
  set("issueCodigo", r && r.codigo);
  set("issueDetectadoEm", r && r.detectado_em ? String(r.detectado_em).slice(0, 16) : "");
  const autor = r && r.criado_por_nome ? `${r.criado_por_nome}${r.criado_por_cargo ? ` (${r.criado_por_cargo})` : ""}` : "";
  set("issueAutor", autor);
  set("issueComportamentoEsperado", r && r.comportamento_esperado);
  set("issueComportamentoObservado", r && r.comportamento_observado);
  set("issueEvidencias", r && r.evidencias_objetivas);
  set("issueCodigoErro", r && r.codigo_erro);
  set("issueAmbiente", r && r.ambiente);
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
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value == null ? "" : value;
  };
  const emitted = !!(r && (r.rnc_status === "emitida" || r.rnc_codigo));
  set("issueRncIssueCodigo", r && (r.rnc_issue_codigo || r.codigo));
  set("issueRncCodigo", r && r.rnc_codigo);
  set("issueRncCriticidade", r && r.rnc_criticidade);
  set("issueRncEnquadramento", r && r.rnc_enquadramento_normativo);
  set("issueRncOrigem", r && r.rnc_origem_gatilho);
  set("issueRncContencao", r && r.rnc_acao_contencao_definitiva);
  set("issueRncContencaoResponsavel", r && r.rnc_contencao_responsavel_id);
  set("issueRncContencaoEm", r && r.rnc_contencao_em ? String(r.rnc_contencao_em).slice(0, 16) : "");
  set("issueRncDisposicao", r && r.rnc_disposicao_inicial);
  set("issueRncLider", r && r.rnc_lider_investigacao_id);
  set("issueRncAuditor", r && r.rnc_auditor_eficacia_id);
  set("issueRncMetodologia", r && r.rnc_metodologia);
  set("issueRncPrazoAnalise", r && r.rnc_prazo_analise);
  set("issueRncPrazoPlano", r && r.rnc_prazo_plano_acao);
  set("issueRncPrazoEficacia", r && r.rnc_prazo_verificacao_eficacia);
  const equipe = document.getElementById("issueRncEquipe");
  if (equipe) {
    const equipeSelecionada = ((r && r.rnc_equipe_investigacao) || []).map(Number);
    Array.from(equipe.options).forEach((opt) => { opt.selected = equipeSelecionada.includes(Number(opt.value)); });
  }
  const status = document.getElementById("issueRncStatus");
  if (status) status.textContent = emitted ? `RNC ${r.rnc_codigo}` : "RNC nÃ£o emitida";
  const audit = document.getElementById("issueRncAuditoria");
  if (audit) audit.textContent = emitted ? `Emitida em ${r.rnc_emitida_em || "â€”"} por ${r.rnc_emitida_por_nome || "â€”"}. Issue de origem: ${r.rnc_issue_codigo || r.codigo}.` : "Ainda nÃ£o emitida.";
  document.querySelectorAll(".issue-rnc-emissao input, .issue-rnc-emissao textarea, .issue-rnc-emissao select").forEach((el) => { el.disabled = emitted; });
  const formButton = document.getElementById("btnIssueEmitirRncForm");
  if (formButton) formButton.disabled = emitted;
  const headerButton = document.getElementById("btnIssueEmitirRnc");
  if (headerButton) headerButton.disabled = !r || !r.id || emitted;
}

function novaIssue() {
  state.issueId = null;
  state.issue = null;
  state.editingAcaoId = null;
  fillIssueRnc(null);
  document.getElementById("issueDetail").classList.remove("hidden");
  document.querySelector('[data-issue-tab="captura"]').click();
  document.getElementById("issueTitulo").textContent = "Nova issue";
  document.getElementById("issueStatus").textContent = "";
  ["issueCodigo", "issueAutor", "issueComportamentoEsperado", "issueComportamentoObservado",
    "issueEvidencias", "issueCodigoErro", "issueAmbiente", "issueEnvolvidos", "issueImpacto",
    "issueAcaoEmergencial", "issueOnde", "issuePorQueInicial", "issueComoDetectado", "issueDescricao", "issueProduto", "issueNorma", "issueImpacto", "issueEnvolvidos",
    "issueUltimoOk", "issueAlarme", "issueMargem", "issueCodigoMaterial", "issueLote",
    "issueOrdemProducao", "issueSnInicio", "issueSnFim", "issueLinhaPosto",
    "issueStatusEstoque", "issuePosicaoEstoque", "issueMotivoBloqueio",
    "issueIshiNome", "issueIshiEfeito", "issueIshiAtivo", "issueIshiDescricao", "issueCausaRaiz"].forEach((id) => {
      document.getElementById(id).value = "";
    });
  document.getElementById("issueDetectadoEm").value = issueNowLocal();
  document.getElementById("issueTipo").value = "nao_conformidade";
  document.getElementById("issueSeveridade").value = "media";
  document.getElementById("issueEtapa").value = "";
  document.getElementById("issueSetor").value = "";
  document.getElementById("issueProcesso").innerHTML = '<option value="">—</option>';
  document.getElementById("issueOperador").value = "";
  document.getElementById("issueInspetor").value = "";
  issueOrigemSetar("");
  document.getElementById("issueReincidencia").checked = false;
  document.getElementById("issueInvestigar").checked = false;
  document.getElementById("issueUsarIshikawa").checked = false;
  document.getElementById("issueUsarPorques").checked = false;
  ISSUE_ISHI_KEYS.forEach(({ inputId }) => { document.getElementById(inputId).value = ""; });
  fillIssueCategorias({});
  let tbody = document.querySelector("#issueAcoes .rnc-matrix tbody");
  if (tbody) tbody.innerHTML = "";
  document.getElementById("issueResultado").value = "";
  document.getElementById("issueResultadoEsperado").value = "";
  document.getElementById("issueNota").value = "3";
  document.getElementById("issueDocsTree").innerHTML = "";
  document.getElementById("issueIshiOut").innerHTML = "";
  toggleInvestigar();
  toggleIssueBlocks();
  renderPorques();
}

function toggleInvestigar() {
  const inv = document.getElementById("issueInvestigar").checked;
  document.getElementById("issueInvestigarOpts").classList.toggle("hidden", !inv);
}

async function selectIssue(id) {
  state.issue = await api(`/api/issues/${id}`);
  state.issueId = id;
  state.editingAcaoId = null;
  document.getElementById("issueDetail").classList.remove("hidden");
  document.getElementById("issueTitulo").textContent = state.issue.codigo;
  document.getElementById("issueStatus").textContent = state.issue.status || "";
  const r = state.issue;
  fillIssueCadastroInicial(r);
  fillIssueRnc(r);
  document.getElementById("issueDescricao").value = r.descricao || "";
  issueOrigemSetar(r.origem || "");
  document.getElementById("issueProduto").value = r.produto || "";
  document.getElementById("issueNorma").value = r.norma || "";
  document.getElementById("issueTipo").value = r.tipo || "nao_conformidade";
  const impactoParaPicklist = { baixa: "baixo", media: "medio", alta: "alto", critica: "critico" };
  document.getElementById("issueImpacto").value = ["baixo", "medio", "alto", "critico"].includes(r.impacto)
    ? r.impacto
    : (impactoParaPicklist[r.severidade] || "");
  const envolvidosPicklist = ["cliente", "operador", "equipe_interna", "fornecedor", "sistema_processo", "multiplos"];
  if (!envolvidosPicklist.includes(r.envolvidos_afetados)) document.getElementById("issueEnvolvidos").value = r.envolvidos_afetados ? "multiplos" : "";
  document.getElementById("issueEtapa").value = r.etapa_captura || "";
  document.getElementById("issueReincidencia").checked = !!r.reincidencia;
  document.getElementById("issueSetor").value = r.setor_id || "";
  await loadIssueProcessos();
  document.getElementById("issueProcesso").value = r.processo_id || "";
  document.getElementById("issueUltimoOk").value = r.ultimo_ok_em || "";
  document.getElementById("issueAlarme").value = r.alarme_em || "";
  document.getElementById("issueMargem").value = r.margem_seguranca_min || "";
  document.getElementById("issueCodigoMaterial").value = r.codigo_material || "";
  document.getElementById("issueLote").value = r.lote || "";
  document.getElementById("issueOrdemProducao").value = r.ordem_producao || "";
  document.getElementById("issueSnInicio").value = r.sn_inicio || "";
  document.getElementById("issueSnFim").value = r.sn_fim || "";
  document.getElementById("issueLinhaPosto").value = r.linha_posto || "";
  document.getElementById("issueStatusEstoque").value = r.status_estoque || "";
  document.getElementById("issuePosicaoEstoque").value = r.posicao_estoque || "";
  document.getElementById("issueOperador").value = r.operador_id || "";
  document.getElementById("issueInspetor").value = r.inspetor_id || "";
  document.getElementById("issueMotivoBloqueio").value = r.motivo_bloqueio || "";
  document.getElementById("issueInvestigar").checked = !!r.investigar_causa;
  document.getElementById("issueUsarIshikawa").checked = !!r.usar_ishikawa;
  document.getElementById("issueUsarPorques").checked = !!r.usar_porques;
  toggleInvestigar();
  if (r.ishikawa) {
    document.getElementById("issueIshiNome").value = r.codigo;
    document.getElementById("issueIshiEfeito").value = r.ishikawa.efeito || "";
    document.getElementById("issueIshiAtivo").value = r.ishikawa.ativo || "";
    document.getElementById("issueIshiDescricao").value = r.ishikawa.descricao || "";
    ISSUE_ISHI_KEYS.forEach(({ key, inputId }) => {
      document.getElementById(inputId).value = ((r.ishikawa.causas && r.ishikawa.causas[key]) || []).join("\n");
    });
    fillIssueCategorias(r.ishikawa.categorias);
  } else {
    document.getElementById("issueIshiNome").value = r.codigo;
    document.getElementById("issueIshiEfeito").value = "";
    document.getElementById("issueIshiAtivo").value = "";
    document.getElementById("issueIshiDescricao").value = "";
    ISSUE_ISHI_KEYS.forEach(({ inputId }) => { document.getElementById(inputId).value = ""; });
    fillIssueCategorias({});
  }
  renderIssueIshikawa();
  document.getElementById("issueCausaRaiz").value = r.causa_raiz || "";
  renderPorques();
  toggleIssueBlocks();
  renderAcoes(r.acoes || []);
  document.getElementById("issueResultadoEsperado").value = r.resultado_esperado || "";
  document.getElementById("issueResultado").value = r.resultado_alcancado || "";
  document.getElementById("issueNota").value = String(r.nota_atingimento || "3");
  await loadIssueDocsTree();
}

function readCaptura() {
  const detectadoEm = document.getElementById("issueDetectadoEm").value;
  const impacto = document.getElementById("issueImpacto").value;
  const envolvidos = document.getElementById("issueEnvolvidos").value;
  const observado = document.getElementById("issueComportamentoObservado").value;
  const body = {
    descricao: document.getElementById("issueDescricao").value,
    data: detectadoEm ? detectadoEm.slice(0, 10) : "",
    origem: issueOrigemValor(),
    produto: document.getElementById("issueProduto").value,
    norma: document.getElementById("issueNorma").value,
    reincidencia: document.getElementById("issueReincidencia").checked ? 1 : 0,
    tipo: document.getElementById("issueTipo").value,
    severidade: impacto === "baixo" ? "baixa" : impacto === "medio" ? "media" : impacto === "alto" ? "alta" : impacto === "critico" ? "critica" : "",
    etapa_captura: document.getElementById("issueEtapa").value,
    detectado_em: detectadoEm,
    comportamento_esperado: document.getElementById("issueComportamentoEsperado").value,
    comportamento_observado: document.getElementById("issueComportamentoObservado").value,
    evidencias_objetivas: document.getElementById("issueEvidencias").value,
    codigo_erro: document.getElementById("issueCodigoErro").value,
    ambiente: document.getElementById("issueAmbiente").value,
    envolvidos_afetados: envolvidos,
    impacto,
    acao_emergencial: document.getElementById("issueAcaoEmergencial").value,
    o_que: observado,
    onde: document.getElementById("issueOnde").value,
    quando: detectadoEm,
    quem: envolvidos,
    por_que_inicial: document.getElementById("issuePorQueInicial").value,
    como_detectado: document.getElementById("issueComoDetectado").value,
    setor_id: Number(document.getElementById("issueSetor").value) || null,
    processo_id: Number(document.getElementById("issueProcesso").value) || null,
  };
  if (isSuperuser()) body.empresa_id = state.empresaId || null;
  return body;
}

function readContencao() {
  return {
    ultimo_ok_em: document.getElementById("issueUltimoOk").value,
    alarme_em: document.getElementById("issueAlarme").value,
    margem_seguranca_min: document.getElementById("issueMargem").value,
    codigo_material: document.getElementById("issueCodigoMaterial").value,
    lote: document.getElementById("issueLote").value,
    ordem_producao: document.getElementById("issueOrdemProducao").value,
    sn_inicio: document.getElementById("issueSnInicio").value,
    sn_fim: document.getElementById("issueSnFim").value,
    linha_posto: document.getElementById("issueLinhaPosto").value,
    status_estoque: document.getElementById("issueStatusEstoque").value,
    posicao_estoque: document.getElementById("issuePosicaoEstoque").value,
    operador_id: Number(document.getElementById("issueOperador").value) || null,
    inspetor_id: Number(document.getElementById("issueInspetor").value) || null,
    motivo_bloqueio: document.getElementById("issueMotivoBloqueio").value,
    investigar_causa: document.getElementById("issueInvestigar").checked ? 1 : 0,
    usar_ishikawa: document.getElementById("issueUsarIshikawa").checked ? 1 : 0,
    usar_porques: document.getElementById("issueUsarPorques").checked ? 1 : 0,
  };
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
  document.getElementById("issueStatus").textContent = state.issue.status || "";
  fillIssueCadastroInicial(state.issue);
  fillIssueRnc(state.issue);
  document.getElementById("issueIshiNome").value = state.issue.codigo || "";
  await loadIssueList();
  await loadIssueKanban();
  renderIssueIshikawa();
}

async function salvarIssueContencao() {
  if (!state.issueId) {
    alert("Salve o registro (Aba 1) antes.");
    return;
  }
  const body = readContencao();
  if (body.investigar_causa && !(body.usar_ishikawa || body.usar_porques)) {
    alert("Ao investigar a causa, marque ao menos uma ferramenta (Ishikawa ou 5 Porquês).");
    return;
  }
  try {
    state.issue = await api(`/api/issues/${state.issueId}`, { method: "PUT", body });
  } catch (e) {
    alert(e.message || "Erro ao salvar a contenção.");
    return;
  }
  toggleInvestigar();
  toggleIssueBlocks();
  renderIssueIshikawa();
  renderPorques();
}

async function salvarIssueIshikawa() {
  if (!state.issueId) {
    alert("Salve o registro (Aba 1) antes.");
    return;
  }
  const nome = document.getElementById("issueIshiNome").value.trim() || (state.issue && state.issue.codigo) || "";
  if (!nome) {
    alert("Informe o nome do Ishikawa.");
    return;
  }
  const comum = {
    nome,
    efeito: document.getElementById("issueIshiEfeito").value,
    ativo: document.getElementById("issueIshiAtivo").value,
    descricao: document.getElementById("issueIshiDescricao").value,
    causas: readIssueCausas(),
    categorias: readIssueCategorias(),
  };
  try {
    if (state.issue && state.issue.ishikawa && state.issue.ishikawa.id) {
      await api(`/api/issues/${state.issueId}/ishikawa`, { method: "PUT", body: comum });
    } else {
      await api(`/api/issues/${state.issueId}/ishikawa`, {
        method: "POST",
        body: { ...comum, setor_id: Number(document.getElementById("issueSetor").value) || (state.issue && state.issue.setor_id) || null },
      });
    }
  } catch (e) {
    alert(e.message || "Erro ao salvar o Ishikawa.");
    return;
  }
  state.issue = await api(`/api/issues/${state.issueId}`);
  renderIssueIshikawa();
  alert("Ishikawa vinculado.");
}

async function gerarAcoesDoIshikawa() {
  if (!state.issueId) {
    alert("Salve o registro (Aba 1) antes.");
    return;
  }
  const causas = flatIshikawaCausas(state.issue);
  if (!causas.length) {
    alert("Nenhuma causa no Ishikawa vinculado. Salve o Ishikawa (Aba 3) primeiro.");
    return;
  }
  if (!confirm(`Gerar ${causas.length} ações a partir das causas do Ishikawa no plano de ação?`)) return;
  for (const causa of causas) {
    await api(`/api/issues/${state.issueId}/acoes`, {
      method: "POST",
      body: { descricao: causa, responsavel_id: state.user.id },
    });
  }
  await api(`/api/issues/${state.issueId}`, {
    method: "PUT",
    body: { resultado_esperado: document.getElementById("issueResultadoEsperado").value },
  });
  await refreshIssue();
  await loadIssueKanban();
  const tab = document.querySelector('[data-issue-tab="acao"]');
  if (tab) tab.click();
}

function flatIshikawaCausas(issue) {
  const out = [];
  if (issue && issue.ishikawa && issue.ishikawa.causas) {
    Object.entries(issue.ishikawa.causas).forEach(([cat, arr]) => {
      (arr || []).forEach((c) => out.push(c));
    });
  }
  return out;
}

function renderPorques() {
  const container = document.getElementById("issuePorquesList");
  const issue = state.issue;
  const porques = (issue && issue.porques) || [];
  const both = issue && issue.usar_ishikawa && issue.usar_porques;
  const causas = flatIshikawaCausas(issue);
  container.innerHTML = "";
  for (let i = 1; i <= 5; i++) {
    const atual = porques.find((p) => p.numero === i) || { numero: i, item_ishikawa: "", resposta: "" };
    const row = document.createElement("div");
    row.className = "porque-row";
    const label = document.createElement("label");
    label.textContent = `${i}º Porquê`;
    row.appendChild(label);
    if (both) {
      const sel = document.createElement("select");
      sel.dataset.porque = String(i);
      sel.dataset.field = "item_ishikawa";
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "— item do Ishikawa —";
      sel.appendChild(opt);
      causas.forEach((c) => {
        const o = document.createElement("option");
        o.value = c;
        o.textContent = c;
        sel.appendChild(o);
      });
      sel.value = atual.item_ishikawa || "";
      row.appendChild(sel);
    }
    const ta = document.createElement("textarea");
    ta.rows = 2;
    ta.dataset.porque = String(i);
    ta.dataset.field = "resposta";
    ta.value = atual.resposta || "";
    row.appendChild(ta);
    container.appendChild(row);
  }
}

function readPorques() {
  const porques = [];
  const container = document.getElementById("issuePorquesList");
  for (let i = 1; i <= 5; i++) {
    const itemSel = container.querySelector(`select[data-porque="${i}"]`);
    const resp = container.querySelector(`textarea[data-porque="${i}"]`);
    const resposta = resp ? resp.value : "";
    const item_ishikawa = itemSel ? itemSel.value : "";
    if (resposta || item_ishikawa) {
      porques.push({ numero: i, item_ishikawa, resposta });
    }
  }
  return porques;
}

async function salvarIssuePorques() {
  if (!state.issueId) {
    alert("Salve o registro (Aba 1) antes.");
    return;
  }
  const body = {
    porques: readPorques(),
    causa_raiz: document.getElementById("issueCausaRaiz").value,
  };
  try {
    state.issue = await api(`/api/issues/${state.issueId}/porques`, { method: "PUT", body });
  } catch (e) {
    alert(e.message || "Erro ao salvar 5 Porquês.");
    return;
  }
  renderPorques();
}

function renderAcoes(acoes) {
  const tbody = document.querySelector("#issueAcoes .rnc-matrix tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  acoes.forEach((a, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td>${escapeHtml(a.descricao)}</td>
      <td>${escapeHtml(a.por_que || "")}</td>
      <td>${escapeHtml(a.onde || "")}</td>
      <td>${escapeHtml(a.como || "")}</td>
      <td>${escapeHtml(a.quanto || "")}</td>
      <td>${escapeHtml(a.prazo_limite || "")}</td>
      <td>${escapeHtml(a.responsavel_nome || "")}</td>
      <td>${escapeHtml(a.status || "")}</td>
      <td>${escapeHtml(a.observacao || "")}</td>
      <td><button class="btn btn-sm btn-x">×</button></td>
    `;
    tr.querySelector(".btn-x").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Excluir esta ação?")) return;
      await api(`/api/issues/${state.issueId}/acoes/${a.id}`, { method: "DELETE" });
      if (state.editingAcaoId === a.id) cancelarEdicaoAcao();
      await refreshIssue();
    });
    tr.addEventListener("dblclick", () => editarIssueAcao(a));
    tbody.appendChild(tr);
  });
}

function editarIssueAcao(a) {
  state.editingAcaoId = a.id;
  document.getElementById("issueAcaoDescricao").value = a.descricao || "";
  document.getElementById("issueAcaoResponsavel").value = a.responsavel_id || "";
  document.getElementById("issueAcaoPrazo").value = a.prazo_limite || "";
  document.getElementById("issueAcaoPorQue").value = a.por_que || "";
  document.getElementById("issueAcaoOnde").value = a.onde || "";
  document.getElementById("issueAcaoComo").value = a.como || "";
  document.getElementById("issueAcaoQuanto").value = a.quanto || "";
  document.getElementById("issueAcaoObservacao").value = a.observacao || "";
  document.getElementById("issueAcaoFormTitle").textContent = "Editar ação (5W2H)";
  document.getElementById("btnIssueAddAcao").textContent = "Salvar alterações";
  document.getElementById("btnIssueCancelarAcao").classList.remove("hidden");
  document.getElementById("issueAcaoDescricao").focus();
}

function cancelarEdicaoAcao() {
  state.editingAcaoId = null;
  ["issueAcaoDescricao", "issueAcaoPrazo", "issueAcaoPorQue",
    "issueAcaoOnde", "issueAcaoComo", "issueAcaoQuanto", "issueAcaoObservacao"].forEach((id) => {
      document.getElementById(id).value = "";
    });
  document.getElementById("issueAcaoFormTitle").textContent = "Nova ação (5W2H)";
  document.getElementById("btnIssueAddAcao").textContent = "Adicionar ação";
  document.getElementById("btnIssueCancelarAcao").classList.add("hidden");
}

async function salvarIssueAcao() {
  if (!state.issueId) {
    alert("Salve o registro (Aba 1) antes.");
    return;
  }
  const descricao = document.getElementById("issueAcaoDescricao").value.trim();
  if (!descricao) {
    alert("Informe a descrição da ação.");
    return;
  }
  const body = {
    descricao,
    responsavel_id: Number(document.getElementById("issueAcaoResponsavel").value) || null,
    prazo_limite: document.getElementById("issueAcaoPrazo").value,
    por_que: document.getElementById("issueAcaoPorQue").value,
    onde: document.getElementById("issueAcaoOnde").value,
    como: document.getElementById("issueAcaoComo").value,
    quanto: document.getElementById("issueAcaoQuanto").value,
    observacao: document.getElementById("issueAcaoObservacao").value,
  };
  try {
    if (state.editingAcaoId) {
      await api(`/api/issues/${state.issueId}/acoes/${state.editingAcaoId}`, { method: "PUT", body });
    } else {
      await api(`/api/issues/${state.issueId}/acoes`, { method: "POST", body });
    }
    await api(`/api/issues/${state.issueId}`, {
      method: "PUT",
      body: { resultado_esperado: document.getElementById("issueResultadoEsperado").value },
    });
  } catch (e) {
    alert(e.message || "Erro ao salvar a ação.");
    return;
  }
  cancelarEdicaoAcao();
  await refreshIssue();
  await loadIssueKanban();
}

function readRncEmissao() {
  return {
    criticidade: document.getElementById("issueRncCriticidade").value,
    enquadramento_normativo: document.getElementById("issueRncEnquadramento").value,
    origem_gatilho: document.getElementById("issueRncOrigem").value,
    acao_contencao_definitiva: document.getElementById("issueRncContencao").value,
    contencao_responsavel_id: Number(document.getElementById("issueRncContencaoResponsavel").value) || 0,
    contencao_em: document.getElementById("issueRncContencaoEm").value,
    disposicao_inicial: document.getElementById("issueRncDisposicao").value,
    lider_investigacao_id: Number(document.getElementById("issueRncLider").value) || 0,
    auditor_eficacia_id: Number(document.getElementById("issueRncAuditor").value) || 0,
    equipe_investigacao: Array.from(document.getElementById("issueRncEquipe").selectedOptions).map((o) => Number(o.value)).filter(Boolean),
    metodologia: document.getElementById("issueRncMetodologia").value,
    prazo_analise: document.getElementById("issueRncPrazoAnalise").value,
    prazo_plano_acao: document.getElementById("issueRncPrazoPlano").value,
    prazo_verificacao_eficacia: document.getElementById("issueRncPrazoEficacia").value,
  };
}

async function emitirIssueRnc() {
  if (!state.issueId) {
    alert("Salve a Issue antes de emitir a RNC.");
    return;
  }
  try {
    state.issue = await api(`/api/issues/${state.issueId}/emitir-rnc`, { method: "POST", body: readRncEmissao() });
  } catch (e) {
    alert(e.message || "NÃ£o foi possÃ­vel emitir a RNC.");
    return;
  }
  document.getElementById("issueTitulo").textContent = `${state.issue.codigo} â†’ ${state.issue.rnc_codigo}`;
  fillIssueRnc(state.issue);
  await loadIssueList();
}

async function refreshIssue() {
  state.issue = await api(`/api/issues/${state.issueId}`);
  fillIssueCadastroInicial(state.issue);
  fillIssueRnc(state.issue);
  renderAcoes(state.issue.acoes || []);
  document.getElementById("issueStatus").textContent = state.issue.status || "";
}

async function finalizarIssue() {
  if (!state.issueId) return;
  const body = {
    resultado_alcancado: document.getElementById("issueResultado").value,
    nota_atingimento: Number(document.getElementById("issueNota").value),
  };
  if (!body.resultado_alcancado) {
    alert("Informe o resultado alcançado.");
    return;
  }
  try {
    state.issue = await api(`/api/issues/${state.issueId}/finalizar`, { method: "POST", body });
  } catch (e) {
    alert(e.message || "Erro ao finalizar.");
    return;
  }
  document.getElementById("issueStatus").textContent = state.issue.status || "";
  await loadIssueList();
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
  const container = document.getElementById("issueKanban");
  const items = await api("/api/issues/kanban");
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
      loadIssueKanban();
    });
    items.filter((a) => a.status === col).forEach((a) => {
      const card = document.createElement("div");
      card.className = "kanban-card";
      card.draggable = true;
      const descricao = a.descricao || a.issue_descricao || "";
      card.title = `${a.codigo} — ${descricao}\nResponsável: ${a.responsavel_nome || "—"}`;
      card.innerHTML = `<div class="kc-title">${escapeHtml(a.codigo)}</div><div class="kc-sub">${escapeHtml(descricao)}</div>`;
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

async function loadIssueAnalise() {
  const tryGet = async (url) => {
    try { return await api(url); } catch (e) { return null; }
  };
  const [stats, trends] = await Promise.all([tryGet("/api/issues/stats"), tryGet("/api/issues/trends")]);
  const resumo = document.getElementById("issueAnaliseResumo");

  if (stats && stats.total != null) {
    resumo.innerHTML = [
      `Total: ${stats.total}`,
    ].map((t) => `<span class="meta-chip">${t}</span>`).join("");
  }

  renderIssueAnalisePareto(stats);

  if (trends) {
    document.getElementById("issueAnaliseResumo").innerHTML += [
      trends.criadas != null ? `Criadas: ${trends.criadas}` : "",
      trends.finalizadas != null ? `Finalizadas: ${trends.finalizadas}` : "",
      trends.em_aberto != null ? `Em aberto: ${trends.em_aberto}` : "",
    ].filter(Boolean).map((t) => `<span class="meta-chip">${t}</span>`).join("");

    const periodos = trends.por_criacao || [];
    const x = periodos.map((p) => p.periodo);
    const yCriadas = periodos.map((p) => p.total);
    const finalMap = {};
    (trends.por_finalizacao || []).forEach((p) => { finalMap[p.periodo] = p.total; });
    const yFinalizadas = x.map((p) => finalMap[p] || 0);
    plot("issueTrendsOut", { xaxis: { title: "Período (mês)" }, yaxis: { title: "Quantidade" }, title: "Criação vs finalização" }, [
      { type: "scatter", mode: "lines+markers", x, y: yCriadas, name: "Criadas" },
      { type: "scatter", mode: "lines+markers", x, y: yFinalizadas, name: "Finalizadas" },
    ]);
  }
}

function renderIssueAnalisePareto(stats) {
  if (!stats || !stats.dimensoes) return;
  const div = document.getElementById("issueParetoOut");
  div.innerHTML = "";
  const sel = document.getElementById("issueAnaliseDimensao");
  const dim = (stats.dimensoes || []).find((d) => d.chave === sel.value) || (stats.dimensoes || [])[0];
  if (!dim) return;
  const itens = (dim.dados && dim.dados.itens) || [];
  if (!itens.length) {
    div.innerHTML = '<p class="hint">Sem dados para esta dimensão.</p>';
    return;
  }
  const traceBar = { type: "bar", x: itens.map((i) => i.rotulo), y: itens.map((i) => i.frequencia), name: "Frequência" };
  const traceLine = { type: "scatter", x: itens.map((i) => i.rotulo), y: itens.map((i) => i.acumulado), name: "% Acumulado", yaxis: "y2" };
  plot("issueParetoOut", { title: `Pareto — ${dim.rotulo}`, yaxis: { title: "Frequência" }, yaxis2: { title: "%", overlaying: "y", side: "right", range: [0, 100] } }, [traceBar, traceLine]);
}

async function bindIssueTabs() {
  document.querySelectorAll(".rnc-tab[data-issue-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".rnc-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".rnc-pane").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const pane = document.getElementById("issue-tab-" + tab.dataset.issueTab);
      if (pane) pane.classList.add("active");
      if (tab.dataset.issueTab === "analise") loadIssueAnalise();
    });
  });
}

async function initIssues() {
  bindIssueTabs();
  await loadIssueUsuarios();
  await loadIssueSetores();
  await loadIssueList();
  await loadIssueKanban();
  await loadIssueAnalise();
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

document.querySelectorAll(".sidebar a").forEach((a) => {
  a.addEventListener("click", () => navigate(a.dataset.section));
});

document.getElementById("btnLogin").addEventListener("click", login);
document.getElementById("btnLogout").addEventListener("click", logout);
document.getElementById("empresaForm").addEventListener("submit", createEmpresa);
document.getElementById("usuarioForm").addEventListener("submit", createUsuario);
document.getElementById("usuarioEmpresa").addEventListener("change", loadUsuarioSetores);
document.getElementById("empresaSelect").addEventListener("change", async (e) => {
  state.empresaId = Number(e.target.value) || null;
  state.processoId = null;
  document.getElementById("processoDetail").classList.add("hidden");
  await Promise.all([loadCrudSetores(), loadCrudProcessos(), loadIssueSetores(), loadUsuarioSetores()]);
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
document.getElementById("btnIssueSalvarContencao").addEventListener("click", salvarIssueContencao);
document.getElementById("btnIssueSalvarIshi").addEventListener("click", salvarIssueIshikawa);
document.getElementById("btnIssueGerarIshi").addEventListener("click", renderIssueIshikawa);
document.getElementById("btnIssueGerarAcoesIshi").addEventListener("click", gerarAcoesDoIshikawa);
ISSUE_ISHI_KEYS.forEach(({ catInputId }) => {
  const el = document.getElementById(catInputId);
  if (el) el.addEventListener("input", () => { syncIssueCatLabels(); renderIssueIshikawa(); });
});
document.getElementById("btnIssueSalvarPorques").addEventListener("click", salvarIssuePorques);
document.getElementById("btnIssueAddAcao").addEventListener("click", salvarIssueAcao);
document.getElementById("btnIssueCancelarAcao").addEventListener("click", cancelarEdicaoAcao);
document.getElementById("btnIssueFinalizar").addEventListener("click", finalizarIssue);
document.getElementById("btnIssueExcluir").addEventListener("click", excluirIssue);
document.getElementById("btnIssueEmitirRnc").addEventListener("click", () => {
  document.querySelector('[data-issue-tab="analise"]').click();
  emitirIssueRnc();
});
document.getElementById("btnIssueEmitirRncForm").addEventListener("click", emitirIssueRnc);
document.getElementById("btnIssueNovaPasta").addEventListener("click", issueCreatePasta);
document.getElementById("btnIssueCriarDoc").addEventListener("click", issueCreateArquivo);
document.getElementById("btnIssueRefreshDocs").addEventListener("click", loadIssueDocsTree);
document.getElementById("btnIssueAnalise").addEventListener("click", async () => {
  const tryGet = async (url) => {
    try { return await api(url); } catch (e) { return null; }
  };
  renderIssueAnalisePareto(await tryGet("/api/issues/stats"));
});
document.getElementById("issueInvestigar").addEventListener("change", toggleInvestigar);
document.getElementById("issueSetor").addEventListener("change", loadIssueProcessos);
document.getElementById("issueTranscricaoFile").addEventListener("change", (ev) => transcreverArquivo(ev, "issueAcaoObservacao"));
document.getElementById("issueTranscricaoDescricao").addEventListener("change", (ev) => transcreverArquivo(ev, "issueDescricao"));

(async function init() {
  try {
    state.user = await api("/api/auth/me");
    await onAuth();
  } catch (e) {
    showLogin();
  }
})();
