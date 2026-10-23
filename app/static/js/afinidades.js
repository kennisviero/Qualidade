let afinResult=null,afinGroups=[],afinId=null,afinRevision=1,afinSequence=0,afinDirty=false;
const afinEl=id=>document.getElementById(`afin-${id}`);
function resetAfinidades(){
  afinSequence++;afinResult=null;afinGroups=[];afinId=null;afinDirty=false;resetToolAI();
  document.getElementById('afinidadesWorkspace').replaceChildren();
}
function afinChanged(){afinSequence++;afinDirty=true;resetToolAI();afinEl('salvar').disabled=false;afinEl('ia').disabled=false;afinEl('mensagem').textContent='Alterações no quadro ainda não salvas.';}
function buildAfinidades(){
  const select=(key,label)=>`<div id="afin-${key}-block"><label for="afin-${key}">${label}</label><select name="${key}" id="afin-${key}"></select></div>`;
  document.getElementById('afinidadesWorkspace').innerHTML=`
  <div class="pareto-actions" role="tablist" aria-label="Diagrama de Afinidades">
    <button class="btn primary" id="afin-tab-quadro" role="tab" aria-selected="true" aria-controls="afin-quadro">Diagrama</button>
    <button class="btn" id="afin-tab-ajuda" role="tab" aria-selected="false" aria-controls="afin-ajuda">Como funciona — Issues e RNCs</button>
  </div>
  <div id="afin-ajuda" role="tabpanel" aria-labelledby="afin-tab-ajuda" class="card hidden">
    <h3>Para que serve?</h3><p>O Diagrama de Afinidades organiza relatos por semelhança de significado. Leia os cartões, aproxime os que tratam do mesmo tema e só então dê um nome ao grupo. Um grupo representa um tema de análise; não comprova causa raiz.</p>
    <h3>Usando Issues</h3><p>Selecione Issues para explorar temas recorrentes nos relatos de ocorrências abertas, cadastradas ou em tratamento, sem RNC vinculada. Cada cartão conserva o código e o comportamento observado.</p>
    <p>Exemplo: “Instrução desatualizada”, “Orientações diferentes” e “Procedimento indisponível no posto” podem formar o grupo “Clareza e disponibilidade das instruções”. A semelhança precisa ser avaliada pelo usuário.</p>
    <h3>Usando RNCs</h3><p>Selecione RNCs para comparar não conformidades emitidas. Os cartões apresentam os fatos preservados na emissão e as observações da investigação. O código da Issue de origem permanece visível.</p>
    <p>Para analisar uma única RNC, filtre o contexto e trabalhe com seu relato. Nesta versão, cada cartão corresponde a uma RNC inteira: observações e hipóteses não são divididas em cartões independentes.</p>
    <h3>Passo a passo</h3><ol><li>Selecione a empresa, a base e os filtros. Clique em Carregar cartões.</li><li>Defina o título da análise e crie grupos com nomes claros.</li><li>Use o seletor de cada cartão para movê-lo. Mantenha casos duvidosos em Sem grupo. Abra Detalhes para conferir o contexto.</li><li>Revise os temas e salve o diagrama. Ao remover um grupo, seus cartões voltam a Sem grupo.</li><li>Reabra análises pelo seletor de diagramas salvos. O quadro guarda uma fotografia dos relatos carregados; alterações posteriores na origem não atualizam essa fotografia.</li></ol>
    <p>Consultar IA abre instruções editáveis e uma prévia do quadro. O provedor recebe os dados somente após Enviar à IA. Peça sugestões de temas e limitações; avalie a resposta e mova os cartões manualmente.</p>
    <p>Salvar exige papel admin ou editor. Visualizadores podem explorar o quadro e consultar análises salvas. A organização não modifica Issues, RNCs, aprovações ou ações.</p>
  </div>
  <div id="afin-quadro" role="tabpanel" aria-labelledby="afin-tab-quadro">
  <form id="afin-form" class="card"><fieldset class="pareto-source"><legend>Base da análise</legend><label><input type="radio" name="base" value="issues" checked> Issues</label><label><input type="radio" name="base" value="rncs"> RNCs</label></fieldset>
  <p id="afin-elegibilidade" class="hint"></p><div class="pareto-filters">${select('data_referencia','Data de referência')}<div><label for="afin-inicio">De</label><input type="date" name="inicio" id="afin-inicio"></div><div><label for="afin-fim">Até</label><input type="date" name="fim" id="afin-fim"></div>${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([k,v])=>select(k,v)).join('')}</div>
  <button class="btn primary" id="afin-carregar" type="submit">Carregar cartões</button></form>
  <div class="card"><label for="afin-salvos">Diagramas salvos desta base</label><select id="afin-salvos"></select><button id="afin-abrir" class="btn">Abrir diagrama</button></div>
  <p id="afin-mensagem" role="status" aria-live="polite"></p>
  <div id="afin-editor" class="hidden"><div class="card"><label for="afin-titulo">Título da análise</label><input id="afin-titulo" maxlength="160" value="Análise de afinidades">
  <div class="pareto-actions"><input id="afin-novo" maxlength="120" aria-label="Nome do novo grupo" placeholder="Nome do novo grupo"><button id="afin-adicionar" class="btn">Criar grupo</button><button id="afin-salvar" class="btn primary">Salvar diagrama</button><button id="afin-ia" class="btn">Consultar IA</button></div><p id="afin-resumo"></p><p class="hint">Agrupamento manual por significado. Semelhança não comprova causa. Os registros originais são preservados.</p></div><div id="afin-board" class="afin-board"></div></div></div>`;
  for(const tab of ['quadro','ajuda'])afinEl(`tab-${tab}`).onclick=()=>{
    for(const other of ['quadro','ajuda']){const active=tab===other;afinEl(other).classList.toggle('hidden',!active);afinEl(`tab-${other}`).setAttribute('aria-selected',String(active));afinEl(`tab-${other}`).classList.toggle('primary',active);}
  };
  afinEl('form').onsubmit=e=>{e.preventDefault();afinLoadCards();};
  afinEl('form').onchange=e=>{if(e.target.name==='base'){if(afinDirty&&!confirm('Descartar as alterações não salvas do quadro?')){document.querySelectorAll('#afin-form [name="base"]').forEach(r=>r.checked=r.value===afinResult?.base);return;}loadAfinidades(true);}else{afinSequence++;afinEl('carregar').disabled=false;afinEl('salvar').disabled=false;afinEl('ia').disabled=false;resetToolAI();afinEl('mensagem').textContent='Filtros alterados. Carregue os cartões para iniciar outro quadro. O quadro atual conserva os filtros anteriores.';}};
  afinEl('titulo').oninput=afinChanged;
  afinEl('adicionar').onclick=()=>{
    const name=afinEl('novo').value.trim();if(!name){afinEl('mensagem').textContent='Informe o nome do grupo.';return;}
    if(afinGroups.some(g=>g.nome.toLocaleLowerCase()===name.toLocaleLowerCase())){afinEl('mensagem').textContent='Já existe um grupo com esse nome.';return;}
    afinGroups.push({nome:name,registros:[]});afinEl('novo').value='';afinChanged();afinRender();
  };
  afinEl('abrir').onclick=afinOpen;
  afinEl('salvar').onclick=()=>afinSubmit(false);
  afinEl('ia').onclick=()=>afinSubmit(true);
}
function afinSelect(key,options,empty='Todos'){
  const el=afinEl(key);el.replaceChildren();if(empty!==null)el.add(new Option(empty,''));options.forEach(o=>el.add(new Option(o.rotulo,o.valor)));
}
async function afinList(){
  const base=document.querySelector('#afin-form [name="base"]:checked').value;
  const seq=afinSequence;
  const list=await api(`/api/ferramentas/afinidades/diagramas?empresa_id=${state.empresaId}&base=${base}`);
  if(seq!==afinSequence)return;
  afinEl('salvos').replaceChildren(new Option('Selecione um diagrama',''));
  list.forEach(r=>afinEl('salvos').add(new Option(`${r.titulo} · revisão ${r.revisao}`,r.id)));
}
async function loadAfinidades(clear=false){
  if(afinEl('form')&&!clear)return;
  if(!afinEl('form'))buildAfinidades();
  if(!state.empresaId){afinEl('mensagem').textContent='Selecione uma empresa.';return;}
  const sequence=++afinSequence;resetToolAI();afinResult=null;afinGroups=[];afinId=null;afinDirty=false;afinEl('editor').classList.add('hidden');
  const base=document.querySelector('#afin-form [name="base"]:checked').value;
  if(clear)for(const key of ['inicio','fim'])afinEl(key).value='';
  afinSelect('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:base==='issues'?'criado_em':'emitida_em',rotulo:base==='issues'?'Cadastro da Issue':'Emissão da RNC'}],null);
  afinSelect('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados'}],null);
  afinEl('classificacao-block').classList.toggle('hidden',base==='issues');afinEl('classificacao').disabled=base==='issues';
  afinEl('elegibilidade').textContent=base==='issues'?'Issues abertas, sem RNC vinculada.':'RNCs emitidas: fatos da emissão e observações da investigação.';
  afinEl('mensagem').textContent='Carregando filtros…';afinEl('carregar').disabled=true;
  try{
    const result=await api(`/api/ferramentas/afinidades?empresa_id=${state.empresaId}&base=${base}`);if(sequence!==afinSequence)return;
    for(const key of Object.keys(paretoDimensions))afinSelect(key,result.opcoes[key]);
    await afinList();if(sequence!==afinSequence)return;afinEl('mensagem').textContent='Selecione os filtros e carregue os cartões, ou abra um diagrama salvo.';
  }catch(e){if(sequence===afinSequence)afinEl('mensagem').textContent=e.message;}
  finally{if(sequence===afinSequence)afinEl('carregar').disabled=false;}
}
async function afinLoadCards(){
  if(afinDirty&&!confirm('Descartar as alterações não salvas e carregar outro quadro?'))return;
  const params=new URLSearchParams();
  for(const [key,value] of new FormData(afinEl('form')))if(value)params.set(key,value);
  params.set('empresa_id',state.empresaId);
  const seq=++afinSequence;resetToolAI();afinEl('carregar').disabled=true;
  try{
    const result=await api(`/api/ferramentas/afinidades?${params}`);if(seq!==afinSequence)return;
    afinResult=result;afinGroups=[];afinId=null;afinRevision=1;afinDirty=false;afinEl('titulo').value='Análise de afinidades';afinRender();
    afinEl('mensagem').textContent=`${result.registros.length} cartões carregados. ${result.sem_data} registros sem data para o período.`;
  }catch(e){if(seq===afinSequence)afinEl('mensagem').textContent=e.message;}
  finally{if(seq===afinSequence)afinEl('carregar').disabled=false;}
}
function afinRender(){
  afinEl('editor').classList.remove('hidden');afinEl('salvar').classList.toggle('hidden',!isEditor());
  const board=afinEl('board');board.replaceChildren();
  const assigned=new Set(afinGroups.flatMap(g=>g.registros));
  const filters=afinResult.parametros||JSON.parse(afinResult.consulta_ia.snapshot).parametros;
  afinEl('resumo').textContent=`${afinResult.base==='rncs'?'RNCs':'Issues'} · ${afinResult.registros.length} cartões · ${afinGroups.length} grupos · ${afinResult.registros.length-assigned.size} sem grupo · período: ${filters.inicio||'sem início'} a ${filters.fim||'sem fim'}`;
  for(let index=-1;index<afinGroups.length;index++){
    const group=afinGroups[index],column=document.createElement('section');column.className='card afin-column';
    const rows=afinResult.registros.filter(r=>index===-1?!assigned.has(r.id):group.registros.includes(r.id));
    const heading=document.createElement('h3');heading.textContent=`${group?group.nome:'Sem grupo'} (${rows.length})`;column.append(heading);
    if(group){
      const rename=document.createElement('button');rename.className='btn';rename.textContent='Renomear';rename.onclick=()=>{const value=prompt('Nome do grupo',group.nome)?.trim();if(!value)return;if(afinGroups.some((g,i)=>i!==index&&g.nome.toLocaleLowerCase()===value.toLocaleLowerCase())){afinEl('mensagem').textContent='Já existe um grupo com esse nome.';return;}group.nome=value;afinChanged();afinRender();};column.append(rename);
      const remove=document.createElement('button');remove.className='btn';remove.textContent='Remover grupo';remove.onclick=()=>{if(confirm('Remover o grupo e devolver seus cartões a Sem grupo?')){afinGroups.splice(index,1);afinChanged();afinRender();}};column.append(remove);
    }
    for(const row of rows){
      const card=document.createElement('article');card.className='afin-card';
      const title=document.createElement('strong');title.textContent=row.codigo+(afinResult.base==='rncs'?` · origem ${row.issue_codigo}`:'');
      const description=document.createElement('p');description.textContent=row.descricao||'Sem relato informado';
      const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Detalhes do registro';details.append(summary);
      const context=document.createElement('div');context.className='afin-details';
      const observation=row.observacoes||{};
      for(const [name,value] of [['Categoria',row.categoria],['Local',row.local],['Status',row.status],['Dados simulados',row.simulado?'Sim':'Não identificados'],['Comportamento esperado',row.esperado],['Evidências objetivas',row.evidencias],['Sintomas e condições',observation.sintomas_condicoes],['Condições sem falha',observation.condicoes_sem_falha],['Equipes envolvidas',observation.equipes_envolvidas]]){if(value){const p=document.createElement('p');p.textContent=`${name}: ${value}`;context.append(p);}}details.append(context);
      const label=document.createElement('label');label.textContent='Mover para grupo';const select=document.createElement('select');label.append(select);select.add(new Option('Sem grupo','-1'));afinGroups.forEach((g,i)=>select.add(new Option(g.nome,String(i))));select.value=String(index);
      select.onchange=()=>{const target=Number(select.value);afinGroups.forEach(g=>g.registros=g.registros.filter(id=>id!==row.id));if(target>=0)afinGroups[target].registros.push(row.id);afinChanged();afinRender();};
      card.append(title,description,details,label);column.append(card);
    }
    board.append(column);
  }
}
async function afinOpen(){
  const id=afinEl('salvos').value;if(!id)return;
  if(afinDirty&&!confirm('Descartar as alterações não salvas e abrir outro diagrama?'))return;
  const seq=++afinSequence;resetToolAI();
  try{const result=await api(`/api/ferramentas/afinidades/diagramas/${id}`);if(seq!==afinSequence)return;
    afinResult=result;afinGroups=result.grupos;afinId=result.id;afinRevision=result.revisao;afinDirty=false;afinEl('titulo').value=result.titulo;afinRender();afinEl('mensagem').textContent='Diagrama salvo aberto. Os cartões preservam os relatos da data em que foram carregados.';
  }catch(e){if(seq===afinSequence)afinEl('mensagem').textContent=e.message;}
}
async function afinSubmit(ai){
  if(!afinResult)return;
  const seq=afinSequence;
  const body={titulo:afinEl('titulo').value,...afinResult.consulta_ia,grupos:afinGroups,revisao:afinRevision};
  afinEl('salvar').disabled=true;afinEl('ia').disabled=true;
  try{
    const result=await api(ai?'/api/ferramentas/afinidades/preparar':`/api/ferramentas/afinidades/diagramas${afinId?'/'+afinId:''}`,{method:ai||!afinId?'POST':'PUT',body});
    if(seq!==afinSequence)return;
    if(ai){await openToolAI('afinidades',result);}
    else{afinResult=result;afinGroups=result.grupos;afinId=result.id;afinRevision=result.revisao;afinDirty=false;afinEl('mensagem').textContent=`Diagrama salvo · revisão ${afinRevision}`;await afinList();}
  }catch(e){if(seq===afinSequence)afinEl('mensagem').textContent=e.message;}
  finally{if(seq===afinSequence){afinEl('salvar').disabled=false;afinEl('ia').disabled=false;}}
}
