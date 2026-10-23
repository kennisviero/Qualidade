// Endpoint exists only in qa.server, which enforces temporary database/Vault.
module.exports=async()=>{
  const response=await fetch('http://127.0.0.1:18765/__qa__/shutdown',{method:'POST'});
  if(!response.ok)throw Error('Servidor QA não confirmou encerramento: '+response.status);
  for(let attempt=0;attempt<50;attempt++){
    await new Promise(resolve=>setTimeout(resolve,100));
    try{await fetch('http://127.0.0.1:18765/');}catch{return;}
  }
  throw Error('Servidor QA não encerrou após solicitação cooperativa.');
};
