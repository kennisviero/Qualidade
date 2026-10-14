let toolAISequence=0,toolAIBusy=false,toolAIContext=null;
const toolAIElement=id=>document.getElementById(`toolAI-${id}`);
function buildToolAI(){
  if(toolAIElement('overlay'))return;
  const overlay=document.createElement('div');overlay.id='toolAI-overlay';overlay.className='overlay hidden';
  overlay.innerHTML=`<div class="card tool-ai-dialog" role="dialog" aria-modal="true" aria-labelledby="toolAI-title">
  <div class="rnc-header"><h2 id="toolAI-title">Consultar IA</h2><button id="toolAI-close" class="btn" type="button">Fechar</button></div>
  <form id="toolAI-form" novalidate><label for="toolAI-access">Acesso LLM da empresa</label><select id="toolAI-access"></select>
  <label for="toolAI-prompt">Instruções para a IA</label><textarea id="toolAI-prompt" rows="7" maxlength="12000" placeholder="Descreva o que deseja investigar, comparar ou interpretar."></textarea>
  <details><summary>Consultar os dados que serão enviados junto com o prompt</summary><pre id="toolAI-data" class="tool-ai-data"></pre></details>
  <p class="hint">O envio usa os dados da análise gerada e o provedor selecionado. A resposta é uma consulta; decisões e alterações nos registros continuam sob sua avaliação.</p>
  <button id="toolAI-send" class="btn primary" type="submit">Enviar à IA</button></form><p id="toolAI-status" role="status" aria-live="polite"></p><pre id="toolAI-answer" class="tool-ai-answer"></pre></div>`;
  document.body.append(overlay);
  toolAIElement('close').onclick=()=>overlay.classList.add('hidden');
  toolAIElement('form').addEventListener('submit',event=>{event.preventDefault();sendToolAI();});
  overlay.addEventListener('keydown',event=>{
    if(event.key==='Escape')overlay.classList.add('hidden');
    if(event.key==='Tab'){
      const controls=Array.from(overlay.querySelectorAll('button:not([disabled]),select:not([disabled]),textarea,summary'));
      const first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
}
function resetToolAI(){
  toolAISequence++;toolAIContext=null;if(!toolAIElement('overlay'))return;
  toolAIElement('overlay').classList.add('hidden');
  for(const id of ['answer','data','status'])toolAIElement(id).textContent='';
  toolAIElement('prompt').value='';toolAIElement('access').replaceChildren();
}
async function openToolAI(tool,result){
  buildToolAI();
  if(toolAIBusy){toolAIElement('status').textContent='Aguarde a consulta em andamento terminar.';toolAIElement('overlay').classList.remove('hidden');return;}
  resetToolAI();toolAIElement('overlay').classList.remove('hidden');toolAIElement('send').disabled=true;
  if(!result?.consulta_ia){toolAIElement('status').textContent='Gere a análise antes de consultar a IA.';return;}
  if(!state.empresaId){toolAIElement('status').textContent='Selecione uma empresa e gere a análise novamente.';return;}
  const sequence=++toolAISequence;toolAIContext={...result.consulta_ia,empresa_id:state.empresaId};
  toolAIElement('title').textContent=`Consultar IA — ${{pareto:'Pareto',histograma:'Histograma',dispersao:'Diagrama de Dispersão'}[tool]||tool}`;
  toolAIElement('prompt').value='Analise os resultados apresentados, destaque os principais achados e limitações e sugira próximos passos de investigação. Diferencie hipóteses de conclusões sustentadas pelos dados.';
  toolAIElement('data').textContent=JSON.stringify(JSON.parse(toolAIContext.snapshot),null,2);
  toolAIElement('status').textContent='Carregando os acessos LLM…';
  try{
    const accesses=await api(`/api/ferramentas/ia/acessos?empresa_id=${state.empresaId}`);if(sequence!==toolAISequence)return;
    const select=toolAIElement('access');select.replaceChildren(new Option('Selecione um acesso',''));
    accesses.forEach(access=>select.add(new Option(`${access.nome} · ${access.modelo}`,access.id)));
    if(accesses.length===1)select.value=String(accesses[0].id);
    toolAIElement('send').disabled=!accesses.length;
    toolAIElement('status').textContent=accesses.length?'Edite as instruções e clique em Enviar à IA.':'Nenhum acesso LLM ativo. Solicite o cadastro em Configuração.';
    toolAIElement('prompt').focus();
  }catch(error){if(sequence===toolAISequence)toolAIElement('status').textContent=error.message;}
}
async function sendToolAI(){
  if(toolAIBusy||!toolAIContext)return;
  const prompt=toolAIElement('prompt').value,access=Number(toolAIElement('access').value);
  if(!prompt.trim()||!access){toolAIElement('status').textContent='Informe as instruções e selecione um acesso LLM.';return;}
  if(prompt.length>12000||toolAIContext.snapshot.length>1000000){toolAIElement('status').textContent='Reduza as instruções ou filtre uma quantidade menor de registros.';return;}
  const sequence=++toolAISequence;toolAIBusy=true;toolAIElement('send').disabled=true;
  toolAIElement('answer').textContent='';toolAIElement('status').textContent='Enviando as instruções e os dados. Aguardando a IA…';
  try{
    const result=await api('/api/ferramentas/ia/consultar',{method:'POST',body:{acesso_id:access,prompt,snapshot:toolAIContext.snapshot,assinatura:toolAIContext.assinatura}});
    if(sequence!==toolAISequence)return;
    toolAIElement('answer').textContent=result.resposta;
    toolAIElement('status').textContent=result.completa===false
      ?`${result.aviso||'Resposta parcial: a análise não foi concluída.'} · ${result.modelo}`
      :`Resposta recebida · ${result.modelo}`;
  }catch(error){if(sequence===toolAISequence)toolAIElement('status').textContent=error.message;}
  finally{toolAIBusy=false;if(sequence===toolAISequence)toolAIElement('send').disabled=false;}
}
