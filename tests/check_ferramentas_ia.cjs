const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
class Element{
  constructor(){this.children=[];this.value='';this.disabled=false;this.listeners={};this.classes=new Set();this.classList={add:c=>this.classes.add(c),remove:c=>this.classes.delete(c),contains:c=>this.classes.has(c)};}
  append(...values){this.children.push(...values);}replaceChildren(...values){this.children=values;}add(value){this.children.push(value);}focus(){}addEventListener(name,fn){this.listeners[name]=fn;}
  set innerHTML(value){for(const match of value.matchAll(/id="([^"]+)"/g))elements[match[1]]=new Element();}
  set id(value){this._id=value;elements[value]=this;}
}
const body=new Element(),requests=[],snapshot={ferramenta:'pareto',empresa_id:4,usuario_id:1,resultados:{registros:[{descricao:'<script>dados</script>'}]}};
const data={consulta_ia:{snapshot:JSON.stringify(snapshot),assinatura:'a'.repeat(64)}};
let resolve,handler=async(path,options)=>options?{resposta:'<script>resposta</script>',modelo:'Teste'}:[{id:7,nome:'Acesso',modelo:'Modelo'}];
const context=vm.createContext({console,state:{empresaId:4},document:{body,getElementById:id=>elements[id],createElement:()=>new Element()},Option:function(text,value){this.textContent=text;this.value=String(value);},api:async(path,options)=>{requests.push({path,options});return handler(path,options);}});
vm.runInContext(fs.readFileSync('app/static/js/ferramentas_ia.js','utf8'),context);
(async()=>{
  await context.openToolAI('pareto',data);
  assert.equal(requests.length,1);assert.equal(requests[0].options,undefined);
  assert.equal(elements['toolAI-access'].value,'7');assert.equal(elements['toolAI-send'].disabled,false);
  assert.match(elements['toolAI-data'].textContent,/<script>dados/);
  elements['toolAI-prompt'].value='Instrução exata\nCom <10 e >2.';
  await context.sendToolAI();assert.equal(requests[1].options.body.prompt,'Instrução exata\nCom <10 e >2.');assert.equal(requests[1].options.body.snapshot,data.consulta_ia.snapshot);
  assert.equal(elements['toolAI-answer'].textContent,'<script>resposta</script>');
  handler=async()=>({resposta:'Texto parcial',modelo:'Teste',completa:false,aviso:'Resposta parcial: limite de saída.'});
  await context.sendToolAI();assert.equal(elements['toolAI-answer'].textContent,'Texto parcial');assert.match(elements['toolAI-status'].textContent,/Resposta parcial/);
  elements['toolAI-prompt'].value=' ';let before=requests.length;await context.sendToolAI();assert.equal(requests.length,before);
  elements['toolAI-prompt'].value='Analise';handler=()=>new Promise(r=>resolve=r);
  const pending=context.sendToolAI();before=requests.length;await context.sendToolAI();assert.equal(requests.length,before,'Não duplicar envio durante processamento');
  context.resetToolAI();resolve({resposta:'antiga',modelo:'Teste'});await pending;
  assert.equal(elements['toolAI-answer'].textContent,'');assert.ok(elements['toolAI-overlay'].classes.has('hidden'));
  handler=async()=>[];await context.openToolAI('histograma',data);assert.equal(elements['toolAI-send'].disabled,true);assert.match(elements['toolAI-status'].textContent,/Nenhum acesso/);
  console.log('OK: prompt editável, envio explícito com dados exatos, sem duplicação, texto seguro e reset de empresa/análise.');
})().catch(error=>{console.error(error);process.exitCode=1;});
