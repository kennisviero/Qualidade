let relResult=null,relFactors=[],relEdges=[],relId=null,relRevision=1,relSequence=0,relDirty=false;
const relEl=id=>document.getElementById(`rel-${id}`);
function resetRelacoes(){
  relSequence++;relResult=null;relFactors=[];relEdges=[];relEditingEdge=null;relId=null;relDirty=false;resetToolAI();
  document.getElementById('relacoesWorkspace').replaceChildren();
}
function relChanged(){relSequence++;relDirty=true;resetToolAI();relEl('salvar').disabled=false;relEl('ia').disabled=false;relEl('mensagem').textContent='Alterações no quadro ainda não salvas.';}
function buildRelacoes(){
  const select=(key,label)=>`<div id="rel-${key}-block"><label for="rel-${key}">${label}</label><select name="${key}" id="rel-${key}"></select></div>`;
  document.getElementById('relacoesWorkspace').innerHTML=`
  <div class="pareto-actions" role="tablist" aria-label="Diagrama de Relações"><button class="btn primary" id="rel-tab-quadro" role="tab" aria-selected="true" aria-controls="rel-quadro">Diagrama</button><button class="btn" id="rel-tab-ajuda" role="tab" aria-selected="false" aria-controls="rel-ajuda">Como funciona — Issues e RNCs</button></div>
  <div id="rel-ajuda" class="card hidden" role="tabpanel" aria-labelledby="rel-tab-ajuda">
  <h3>Para que serve?</h3><p>O Diagrama de Relações explora possíveis influências entre fatores de um problema. Cada seta parte do fator que influencia e aponta para o fator influenciado. Afinidades agrupa semelhanças; Relações investiga conexões entre fatores.</p>
  <h3>Usando Issues</h3><p>Carregue Issues abertas sem RNC vinculada para investigar fatores comuns nos relatos. Crie fatores com nomes claros e vincule os registros que os sustentam. Exemplo de hipótese: instrução desatualizada → orientações divergentes → ajustes inconsistentes.</p>
  <h3>Usando RNCs</h3><p>Carregue RNCs para explorar influências entre fatores identificados nos fatos preservados e nas observações da investigação. Uma RNC pode sustentar vários fatores; um fator pode reunir várias RNCs. Os códigos das Issues de origem permanecem disponíveis.</p>
  <h3>Passo a passo</h3><ol><li>Selecione empresa, base e filtros e clique em Carregar registros.</li><li>Defina o título, crie fatores e selecione seus registros de apoio. Um fator sem vínculo deve ser entendido como proposta do analista.</li><li>Selecione origem e destino, justifique a influência e inclua a seta. Use Hipótese enquanto a relação não estiver verificada. Para Sustentada por evidência, descreva a evidência e sua referência.</li><li>Revise a direção das setas, inclusive relações recíprocas e ciclos. Edite ou remova as conexões quando necessário.</li><li>Salve o diagrama para reabrir depois. A gravação é manual e preserva uma fotografia dos relatos e filtros.</li></ol>
  <p>Setas laranja tracejadas indicam hipóteses; azuis contínuas indicam relações declaradas pelo usuário como sustentadas por evidência. A ferramenta não valida a veracidade dessa evidência. Quantidades de entradas e saídas ajudam a explorar o quadro, mas não determinam causa raiz, relevância ou prioridade.</p>
  <p>Consultar IA abre instruções editáveis e a prévia do diagrama atual. Só Enviar à IA chama o provedor. A resposta não cria fatores ou setas automaticamente e não é salva como parte do diagrama.</p>
  <p>Admin/editor podem salvar. Visualizadores podem consultar e explorar temporariamente. Nenhuma alteração é feita nos registros de origem, aprovações ou ações.</p></div>
  <div id="rel-quadro" role="tabpanel" aria-labelledby="rel-tab-quadro"><form id="rel-form" class="card"><fieldset class="pareto-source"><legend>Base da análise</legend><label><input type="radio" name="base" value="issues" checked> Issues</label><label><input type="radio" name="base" value="rncs"> RNCs</label></fieldset><p id="rel-elegibilidade" class="hint"></p>
  <div class="pareto-filters">${select('data_referencia','Data de referência')}<div><label for="rel-inicio">De</label><input id="rel-inicio" name="inicio" type="date"></div><div><label for="rel-fim">Até</label><input id="rel-fim" name="fim" type="date"></div>${select('simulados','Dados simulados')}${Object.entries(paretoDimensions).map(([k,v])=>select(k,v)).join('')}</div><button id="rel-carregar" class="btn primary">Carregar registros</button></form>
  <div class="card"><label for="rel-salvos">Diagramas salvos desta base</label><select id="rel-salvos"></select><button id="rel-abrir" class="btn">Abrir diagrama</button></div><p id="rel-mensagem" role="status" aria-live="polite"></p>
  <div id="rel-editor" class="hidden"><div class="card"><label for="rel-titulo">Título da análise</label><input id="rel-titulo" maxlength="160" value="Análise de relações"><div class="pareto-actions"><button id="rel-salvar" class="btn primary">Salvar diagrama</button><button id="rel-ia" class="btn">Consultar IA</button></div><p id="rel-resumo"></p><p class="hint">Hipóteses: laranja tracejado. Relações sustentadas por evidência declarada: azul contínuo. Setas não comprovam causalidade; entradas e saídas não determinam prioridade.</p><div id="rel-grafico" class="rel-graph"></div></div>
  <div class="rel-editors"><section class="card"><h3>Fatores</h3><form id="rel-fator-form"><label for="rel-novo">Nome do fator</label><input id="rel-novo" maxlength="160" required><label for="rel-fontes">Registros de apoio (opcional; selecione um ou mais)</label><select id="rel-fontes" multiple size="5"></select><button id="rel-adicionar" class="btn" type="submit">Criar fator</button></form><div id="rel-fatores"></div></section>
  <section class="card"><h3>Relações de influência</h3><form id="rel-seta-form"><label for="rel-origem">Origem — influencia</label><select id="rel-origem" required></select><label for="rel-destino">Destino — é influenciado</label><select id="rel-destino" required></select><label for="rel-tipo">Situação da relação</label><select id="rel-tipo"><option value="hipotese">Hipótese</option><option value="evidenciada">Sustentada por evidência declarada</option></select><label for="rel-justificativa">Justificativa da influência</label><textarea id="rel-justificativa" rows="3" maxlength="3000" required></textarea><label for="rel-evidencia">Evidência e referência (obrigatória para relação sustentada)</label><textarea id="rel-evidencia" rows="3" maxlength="3000"></textarea><div class="pareto-actions"><button id="rel-incluir-seta" class="btn" type="submit">Incluir relação</button><button id="rel-cancelar-seta" class="btn" type="button">Limpar edição</button></div></form><div id="rel-setas"></div></section></div>
  <details class="card"><summary>Registros carregados e relatos originais</summary><div id="rel-registros"></div></details></div></div>`;
  for(const tab of ['quadro','ajuda'])relEl(`tab-${tab}`).onclick=()=>{for(const other of ['quadro','ajuda']){const active=tab===other;relEl(other).classList.toggle('hidden',!active);relEl(`tab-${other}`).setAttribute('aria-selected',String(active));relEl(`tab-${other}`).classList.toggle('primary',active);}};
  relEl('form').onsubmit=e=>{e.preventDefault();relLoadCards();};
  relEl('form').onchange=e=>{if(e.target.name==='base'){if(relDirty&&!confirm('Descartar as alterações não salvas?')){document.querySelectorAll('#rel-form [name="base"]').forEach(r=>r.checked=r.value===relResult?.base);return;}loadRelacoes(true);}else{relSequence++;resetToolAI();for(const k of ['carregar','salvar','ia'])relEl(k).disabled=false;relEl('mensagem').textContent='Filtros alterados. Carregue os registros para iniciar outro diagrama. O quadro atual conserva os filtros anteriores.';}};
  relEl('titulo').oninput=relChanged;
  relEl('fator-form').onsubmit=e=>{e.preventDefault();relAddFactor();};
  relEl('seta-form').onsubmit=e=>{e.preventDefault();relAddEdge();};
  relEl('cancelar-seta').onclick=relClearEdge;
  relEl('abrir').onclick=relOpen;relEl('salvar').onclick=()=>relSubmit(false);relEl('ia').onclick=()=>relSubmit(true);
}

function relSelect(key,options,empty='Todos'){
  const el=relEl(key);el.replaceChildren();if(empty!==null)el.add(new Option(empty,''));options.forEach(o=>el.add(new Option(o.rotulo,o.valor)));
}
async function relList(){
  const base=document.querySelector('#rel-form [name="base"]:checked').value;
  const seq=relSequence;
  const list=await api(`/api/ferramentas/relacoes/diagramas?empresa_id=${state.empresaId}&base=${base}`);
  if(seq!==relSequence)return;
  relEl('salvos').replaceChildren(new Option('Selecione um diagrama',''));
  list.forEach(r=>relEl('salvos').add(new Option(`${r.titulo} · revisão ${r.revisao}`,r.id)));
}
async function loadRelacoes(clear=false){
  if(relEl('form')&&!clear)return;
  if(!relEl('form'))buildRelacoes();
  if(!state.empresaId){relEl('mensagem').textContent='Selecione uma empresa.';return;}
  const sequence=++relSequence;resetToolAI();relResult=null;relFactors=[],relEdges=[];relId=null;relDirty=false;relEl('editor').classList.add('hidden');
  const base=document.querySelector('#rel-form [name="base"]:checked').value;
  if(clear)for(const key of ['inicio','fim'])relEl(key).value='';
  relSelect('data_referencia',[{valor:'detectado_em',rotulo:'Detecção'},{valor:base==='issues'?'criado_em':'emitida_em',rotulo:base==='issues'?'Cadastro da Issue':'Emissão da RNC'}],null);
  relSelect('simulados',[{valor:'todos',rotulo:'Todos'},{valor:'somente',rotulo:'Somente simulados'},{valor:'excluir',rotulo:'Excluir simulados'}],null);
  relEl('classificacao-block').classList.toggle('hidden',base==='issues');relEl('classificacao').disabled=base==='issues';
  relEl('elegibilidade').textContent=base==='issues'?'Issues abertas, sem RNC vinculada.':'RNCs emitidas: fatos da emissão e observações da investigação.';
  relEl('mensagem').textContent='Carregando filtros…';relEl('carregar').disabled=true;
  try{
    const result=await api(`/api/ferramentas/relacoes?empresa_id=${state.empresaId}&base=${base}`);if(sequence!==relSequence)return;
    for(const key of Object.keys(paretoDimensions))relSelect(key,result.opcoes[key]);
    await relList();if(sequence!==relSequence)return;relEl('mensagem').textContent='Selecione os filtros e carregue os cartões, ou abra um diagrama salvo.';
  }catch(e){if(sequence===relSequence)relEl('mensagem').textContent=e.message;}
  finally{if(sequence===relSequence)relEl('carregar').disabled=false;}
}
async function relLoadCards(){
  if(relDirty&&!confirm('Descartar as alterações não salvas e carregar outro quadro?'))return;
  const params=new URLSearchParams();
  for(const [key,value] of new FormData(relEl('form')))if(value)params.set(key,value);
  params.set('empresa_id',state.empresaId);
  const seq=++relSequence;resetToolAI();relEl('carregar').disabled=true;
  try{
    const result=await api(`/api/ferramentas/relacoes?${params}`);if(seq!==relSequence)return;
    relResult=result;relFactors=[];relEdges=[];relClearEdge();relId=null;relRevision=1;relDirty=false;relEl('titulo').value='Análise de relações';relRender();
    relEl('mensagem').textContent=`${result.registros.length} cartões carregados. ${result.sem_data} registros sem data para o período.`;
  }catch(e){if(seq===relSequence)relEl('mensagem').textContent=e.message;}
  finally{if(seq===relSequence)relEl('carregar').disabled=false;}
}
let relEditingEdge=null;
function relClearEdge(){
  relEditingEdge=null;relEl('justificativa').value='';relEl('evidencia').value='';relEl('tipo').value='hipotese';relEl('incluir-seta').textContent='Incluir relação';
}
function relAddFactor(){
  const nome=relEl('novo').value.trim();
  if(!nome||nome.length>160){relEl('mensagem').textContent='Informe o nome do fator (até 160 caracteres).';return;}
  if(relFactors.length>=40){relEl('mensagem').textContent='Limite de 40 fatores por diagrama.';return;}
  if(relFactors.some(f=>f.nome.toLocaleLowerCase()===nome.toLocaleLowerCase())){relEl('mensagem').textContent='Já existe um fator com esse nome.';return;}
  const registros=Array.from(relEl('fontes').selectedOptions,o=>Number(o.value));
  relFactors.push({id:Math.max(0,...relFactors.map(f=>f.id))+1,nome,registros});relEl('novo').value='';relChanged();relRender();
}
function relAddEdge(){
  const edge={origem:Number(relEl('origem').value),destino:Number(relEl('destino').value),tipo:relEl('tipo').value,justificativa:relEl('justificativa').value.trim(),evidencia:relEl('evidencia').value.trim()};
  if(!relFactors.some(f=>f.id===edge.origem)||!relFactors.some(f=>f.id===edge.destino)||edge.origem===edge.destino){relEl('mensagem').textContent='Selecione dois fatores diferentes.';return;}
  if(!edge.justificativa||edge.tipo==='evidenciada'&&!edge.evidencia){relEl('mensagem').textContent='Preencha a justificativa e a evidência quando a relação for sustentada.';return;}
  if(relEdges.some((e,i)=>i!==relEditingEdge&&e.origem===edge.origem&&e.destino===edge.destino)){relEl('mensagem').textContent='Já existe uma relação nessa direção.';return;}
  if(relEditingEdge===null&&relEdges.length>=200){relEl('mensagem').textContent='Limite de 200 relações por diagrama.';return;}
  if(relEditingEdge===null)relEdges.push(edge);else relEdges[relEditingEdge]=edge;
  relClearEdge();relChanged();relRender();
}
function relButton(label,handler){const button=document.createElement('button');button.type='button';button.className='btn';button.textContent=label;button.onclick=handler;return button;}
function relRender(){
  relEl('editor').classList.remove('hidden');relEl('salvar').classList.toggle('hidden',!isEditor());
  const filters=relResult.parametros||JSON.parse(relResult.consulta_ia.snapshot).parametros;
  relEl('resumo').textContent=`${relResult.base==='rncs'?'RNCs':'Issues'} · ${relResult.registros.length} registros · ${relFactors.length} fatores · ${relEdges.length} relações · período: ${filters.inicio||'sem início'} a ${filters.fim||'sem fim'}`;
  const sources=relEl('fontes');sources.replaceChildren();relResult.registros.forEach(r=>sources.add(new Option(`${r.codigo} · ${r.descricao||'Sem relato'}`,String(r.id))));
  for(const key of ['origem','destino']){const old=relEl(key).value;relEl(key).replaceChildren(new Option('Selecione',''));relFactors.forEach(f=>relEl(key).add(new Option(f.nome,String(f.id))));if(relFactors.some(f=>String(f.id)===old))relEl(key).value=old;}
  relEl('fatores').replaceChildren();
  for(const factor of relFactors){
    const card=document.createElement('article');card.className='rel-card';const title=document.createElement('h4');title.textContent=factor.nome;
    const counts=document.createElement('p');counts.textContent=`Entradas: ${relEdges.filter(e=>e.destino===factor.id).length} · Saídas: ${relEdges.filter(e=>e.origem===factor.id).length}`;
    const label=document.createElement('label');label.textContent='Registros de apoio';const select=document.createElement('select');select.multiple=true;select.size=3;
    relResult.registros.forEach(r=>{const option=new Option(`${r.codigo} · ${r.descricao||'Sem relato'}`,String(r.id));option.selected=factor.registros.includes(r.id);select.add(option);});label.append(select);
    select.onchange=()=>{factor.registros=Array.from(select.selectedOptions,o=>Number(o.value));relChanged();};
    const rename=relButton('Renomear',()=>{const name=prompt('Nome do fator',factor.nome)?.trim();if(!name)return;if(name.length>160||relFactors.some(f=>f.id!==factor.id&&f.nome.toLocaleLowerCase()===name.toLocaleLowerCase())){relEl('mensagem').textContent='Use um nome único com até 160 caracteres.';return;}factor.nome=name;relChanged();relRender();});
    const remove=relButton('Remover fator',()=>{if(!confirm('Remover este fator e todas as setas ligadas a ele?'))return;relFactors=relFactors.filter(f=>f.id!==factor.id);relEdges=relEdges.filter(e=>e.origem!==factor.id&&e.destino!==factor.id);relClearEdge();relChanged();relRender();});
    card.append(title,counts,label,rename,remove);relEl('fatores').append(card);
  }
  const names=new Map(relFactors.map(f=>[f.id,f.nome]));relEl('setas').replaceChildren();
  relEdges.forEach((edge,index)=>{
    const card=document.createElement('article');card.className='rel-card';const title=document.createElement('h4');title.textContent=`${names.get(edge.origem)} → ${names.get(edge.destino)}`;
    const text=document.createElement('p');text.textContent=`${edge.tipo==='hipotese'?'Hipótese':'Sustentada por evidência declarada'}: ${edge.justificativa}`;
    const evidence=document.createElement('p');evidence.textContent=edge.evidencia?`Evidência: ${edge.evidencia}`:'Sem evidência declarada.';
    const edit=relButton('Editar relação',()=>{relEditingEdge=index;for(const key of ['origem','destino','tipo','justificativa','evidencia'])relEl(key).value=String(edge[key]);relEl('incluir-seta').textContent='Atualizar relação';relEl('justificativa').focus();});
    const remove=relButton('Remover relação',()=>{relEdges.splice(index,1);relClearEdge();relChanged();relRender();});
    card.append(title,text,evidence,edit,remove);relEl('setas').append(card);
  });
  relEl('registros').replaceChildren();
  for(const row of relResult.registros){
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=`${row.codigo}${relResult.base==='rncs'?' · origem '+row.issue_codigo:''} · ${row.descricao||'Sem relato'}`;details.append(summary);
    for(const [name,value] of [['Relato',row.descricao],['Esperado',row.esperado],['Evidências',row.evidencias],['Categoria',row.categoria],['Local',row.local],['Sintomas e condições',row.observacoes?.sintomas_condicoes]]){if(value){const p=document.createElement('p');p.textContent=`${name}: ${value}`;details.append(p);}}relEl('registros').append(details);
  }
  relDraw();
}
function relDraw(){
  const host=relEl('grafico');host.replaceChildren();
  if(!relFactors.length){host.textContent='Crie fatores e inclua relações para montar o diagrama.';return;}
  const ns='http://www.w3.org/2000/svg';
  const svgElement=(tag,attrs={})=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));return el;};
  const width=Math.max(1100,relFactors.length*120),height=Math.max(700,relFactors.length*95);
  const svg=svgElement('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'Diagrama de influências. As relações também estão listadas no formulário abaixo.'});
  svg.style.minWidth=`${width}px`;
  const defs=svgElement('defs');
  for(const [type,color] of [['hipotese','#b45309'],['evidenciada','#1d4ed8']]){const marker=svgElement('marker',{id:`rel-arrow-${type}`,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:9,markerHeight:9,orient:'auto-start-reverse'});marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:color}));defs.append(marker);}svg.append(defs);
  const positions=new Map(relFactors.map((f,i)=>{const angle=2*Math.PI*i/relFactors.length-Math.PI/2;return [f.id,{x:width/2+width*.35*Math.cos(angle),y:height/2+height*.35*Math.sin(angle)}];}));
  relEdges.forEach(edge=>{
    const a=positions.get(edge.origem),b=positions.get(edge.destino);if(!a||!b)return;
    const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy),ux=dx/d,uy=dy/d;
    const offset=relEdges.some(e=>e.origem===edge.destino&&e.destino===edge.origem)?18:0;
    const trim=Math.min(110,d*.3),x1=a.x+ux*trim,y1=a.y+uy*trim,x2=b.x-ux*trim,y2=b.y-uy*trim;
    const path=svgElement('path',{d:`M ${x1} ${y1} Q ${(x1+x2)/2-uy*offset} ${(y1+y2)/2+ux*offset} ${x2} ${y2}`,fill:'none',stroke:edge.tipo==='hipotese'?'#b45309':'#1d4ed8','stroke-width':2,'stroke-dasharray':edge.tipo==='hipotese'?'7 5':'none','marker-end':`url(#rel-arrow-${edge.tipo})`});
    const title=svgElement('title');title.textContent=`${edge.justificativa}${edge.evidencia?' · '+edge.evidencia:''}`;path.append(title);svg.append(path);
  });
  for(const factor of relFactors){const pos=positions.get(factor.id),group=svgElement('g');group.append(svgElement('rect',{x:pos.x-108,y:pos.y-42,width:216,height:84,rx:10,fill:'#eff6ff',stroke:'#2563eb'}));
    const text=svgElement('text',{x:pos.x,y:pos.y-15,'text-anchor':'middle',fill:'#172554','font-size':14});
    const words=factor.nome.match(/.{1,26}(?:\s|$)|.{1,26}/g)||[factor.nome];words.slice(0,3).forEach((line,i)=>{const span=svgElement('tspan',{x:pos.x,dy:i?17:0});span.textContent=line.trim()+(i===2&&words.length>3?'…':'');text.append(span);});
    const title=svgElement('title');title.textContent=factor.nome;group.append(text,title);svg.append(group);
  }
  host.append(svg);
}

async function relOpen(){
  const id=relEl('salvos').value;if(!id)return;
  if(relDirty&&!confirm('Descartar as alterações não salvas e abrir outro diagrama?'))return;
  const seq=++relSequence;resetToolAI();
  try{const result=await api(`/api/ferramentas/relacoes/diagramas/${id}`);if(seq!==relSequence)return;
    relResult=result;relFactors=result.fatores;relEdges=result.relacoes;relClearEdge();relId=result.id;relRevision=result.revisao;relDirty=false;relEl('titulo').value=result.titulo;relRender();relEl('mensagem').textContent='Diagrama salvo aberto. Os registros preservam os relatos da data em que foram carregados.';
  }catch(e){if(seq===relSequence)relEl('mensagem').textContent=e.message;}
}
async function relSubmit(ai){
  if(!relResult)return;
  const seq=relSequence;
  const body={titulo:relEl('titulo').value,...relResult.consulta_ia,fatores:relFactors.map(({id,nome,registros})=>({id,nome,registros})),relacoes:relEdges,revisao:relRevision};
  relEl('salvar').disabled=true;relEl('ia').disabled=true;
  try{
    const result=await api(ai?'/api/ferramentas/relacoes/preparar':`/api/ferramentas/relacoes/diagramas${relId?'/'+relId:''}`,{method:ai||!relId?'POST':'PUT',body});
    if(seq!==relSequence)return;
    if(ai){await openToolAI('relacoes',result);}
    else{relResult=result;relFactors=result.fatores;relEdges=result.relacoes;relId=result.id;relRevision=result.revisao;relDirty=false;relEl('mensagem').textContent=`Diagrama salvo · revisão ${relRevision}`;await relList();}
  }catch(e){if(seq===relSequence)relEl('mensagem').textContent=e.message;}
  finally{if(seq===relSequence){relEl('salvar').disabled=false;relEl('ia').disabled=false;}}
}
