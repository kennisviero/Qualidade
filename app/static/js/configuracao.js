function resetLlmForm() {
  document.getElementById('llmForm').reset();
  document.getElementById('llmId').value = '';
  document.getElementById('llmChave').required = true;
  document.getElementById('llmMensagem').textContent = '';
}

async function loadLlmAcessos() {
  const list = document.getElementById('llmLista');
  list.innerHTML = '';
  if (!isAdmin()) return;
  if (!state.empresaId) { list.textContent = 'Selecione uma empresa para configurar os acessos.'; return; }
  const empresaId = state.empresaId;
  const items = await api(`/api/configuracao/llm?empresa_id=${empresaId}`);
  if (empresaId !== state.empresaId) return;
  list.textContent = items.length ? '' : 'Nenhum acesso cadastrado.';
  items.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'list-item';
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = `<span class="title">${escapeHtml(item.nome)} · ${item.ativo ? 'Ativo' : 'Inativo'}</span><span class="sub">${escapeHtml(item.provedor)} · ${escapeHtml(item.modelo)} · ${escapeHtml(item.url_base)} · Chave ${item.chave_configurada ? 'configurada' : 'não informada'}</span>`;
    const edit = document.createElement('button');
    edit.className = 'btn'; edit.textContent = 'Editar';
    edit.onclick = () => {
      resetLlmForm();
      for (const [field, value] of Object.entries({llmId:item.id,llmNome:item.nome,llmProvedor:item.provedor,llmModelo:item.modelo,llmUrl:item.url_base})) document.getElementById(field).value = value;
      document.getElementById('llmAtivo').checked = item.ativo;
      document.getElementById('llmChave').required = false;
      document.getElementById('llmNome').focus();
    };
    const remove = document.createElement('button');
    remove.className = 'btn'; remove.textContent = 'Excluir';
    remove.onclick = async () => {
      if (!confirm(`Excluir o acesso "${item.nome}"?`)) return;
      try {
        await api(`/api/configuracao/llm/${item.id}`, {method:'DELETE'});
        if (Number(document.getElementById('llmId').value) === item.id) resetLlmForm();
        await loadLlmAcessos();
      } catch (e) { document.getElementById('llmMensagem').textContent = e.message; }
    };
    row.append(meta, edit, remove); list.appendChild(row);
  });
}

document.getElementById('llmNovo').addEventListener('click', resetLlmForm);
document.getElementById('llmForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = document.getElementById('llmMensagem');
  if (!isAdmin() || !state.empresaId) { message.textContent = 'Selecione uma empresa.'; return; }
  const id = document.getElementById('llmId').value;
  const company = state.empresaId;
  const body = {empresa_id:company, nome:document.getElementById('llmNome').value.trim(),
    provedor:document.getElementById('llmProvedor').value.trim(), modelo:document.getElementById('llmModelo').value.trim(),
    url_base:document.getElementById('llmUrl').value.trim(), api_key:document.getElementById('llmChave').value,
    ativo:document.getElementById('llmAtivo').checked};
  const save = document.getElementById('llmSalvar'); save.disabled = true;
  try {
    await api(`/api/configuracao/llm${id ? '/' + id : ''}`, {method:id ? 'PUT' : 'POST', body});
    if (company !== state.empresaId) return;
    resetLlmForm(); await loadLlmAcessos(); message.textContent = 'Acesso salvo.';
  } catch (e) { message.textContent = e.message; }
  finally { save.disabled = false; }
});
resetLlmForm();
