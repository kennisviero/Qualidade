const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('app/static/js/app.js','utf8');
const context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function apiErrorMessage('),source.indexOf('function isSuperuser(')),context);
assert.equal(context.apiErrorMessage('Mensagem existente','Falha'),'Mensagem existente');
const detail=[{loc:['query','inicio'],msg:'Input should be a valid date',input:''},{loc:['query','fim'],msg:'Input should be a valid date',input:''}];
assert.equal(context.apiErrorMessage(detail,'Falha'),'Data inicial: Input should be a valid date\nData final: Input should be a valid date');
assert.equal(context.apiErrorMessage({unexpected:true},'Falha'),'Falha');
context.fetch=async()=>({ok:false,status:422,statusText:'Unprocessable Entity',json:async()=>({detail})});
(async()=>{
  await assert.rejects(context.api('/teste'),error=>error.status===422&&error.message.includes('Data inicial')&&!error.message.includes('[object Object]'));
  console.log('OK: erros textuais preservados e validações estruturadas exibidas com campo e mensagem.');
})().catch(e=>{console.error(e);process.exitCode=1;});
