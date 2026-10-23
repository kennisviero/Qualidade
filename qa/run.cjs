const fs=require('fs'),path=require('path'),os=require('os'),cp=require('child_process');
const root=path.resolve(__dirname,'..');
const suite=process.argv[2];
if(!['unit','backend','ui','e2e','inventory','all'].includes(suite))throw Error('Suíte não permitida.');
const focus=process.argv[3];
if(process.argv.length>4||(focus!==undefined&&(suite!=='backend'||!['--focus=qa','--focus=matriz','--focus=live-readonly'].includes(focus))))throw Error('Filtro não permitido.');
const stamp=new Date().toISOString().replace(/[:.]/g,'-')+'-'+process.pid;
const folder=path.join(__dirname,'evidencias',stamp+'-'+suite);fs.mkdirSync(folder,{recursive:true});
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=fs.existsSync(localPython)?localPython:(process.platform==='win32'?'python':'python3');
const env={...process.env,PYTHONIOENCODING:'utf-8',PYTHONUTF8:'1',QA_EVIDENCE_DIR:folder,
  QUALIDADE_DB:path.join(os.tmpdir(),'qualidade_qa_'+stamp+'.db'),QUALIDADE_DOCS:path.join(os.tmpdir(),'qualidade_qa_docs_'+stamp)};
if(focus==='--focus=live-readonly')env.QA_ACTIVE_DB=process.env.QUALIDADE_DB||path.join(root,'data','qualidade.db');
const results=[];
function run(name,command,args){
  const started=new Date().toISOString(),log=path.join(folder,name+'.txt');
  const header=JSON.stringify({name,started,command:path.basename(command),args},null,2)+'\n';fs.writeFileSync(log,header);
  process.stdout.write(`\n[QA] ${name} — ${log}\n`);
  const fd=fs.openSync(log,'a');
  let child;
  try{child=cp.spawnSync(command,args,{cwd:root,env,stdio:['ignore',fd,fd],timeout:900000,windowsHide:true});}
  finally{fs.closeSync(fd);}
  const code=typeof child.status==='number'?child.status:1;
  if(child.error)fs.appendFileSync(log,'\n'+String(child.error)+'\n');
  const result={name,started,finished:new Date().toISOString(),exit_code:code,signal:child.signal,log:path.relative(root,log)};
  results.push(result);fs.appendFileSync(log,`\n[QA] exit_code=${code}\n`);
  process.stdout.write(fs.readFileSync(log,'utf8').slice(-4500)+'\n');
  return code;
}
function execute(kind){
  if(kind==='backend'&&focus==='--focus=live-readonly')return run('live-readonly',python,['qa/live_readonly.py']);
  if(kind==='unit')return run('unit',python,['-m','pytest','-q','-p','qa.pytest_guard','tests/qa/test_unit_rules.py',`--junitxml=${path.join(folder,'unit.xml')}`]);
  if(kind==='backend')return run('backend',python,['-m','pytest','-q','-p','qa.pytest_guard',focus==='--focus=matriz'?'tests/test_matriz.py':focus?'tests/qa/test_integration_rules.py':'tests','--ignore=tests/qa/test_unit_rules.py',`--junitxml=${path.join(folder,'backend.xml')}`]);
  if(kind==='ui'){
    let code=0;
    for(const file of fs.readdirSync(path.join(root,'tests')).filter(f=>/^check_.*\.cjs$/.test(f)).sort())code=run(file.slice(0,-4),process.execPath,['tests/'+file])||code;
    return code;
  }
  if(kind==='e2e'){
    const cli=path.join(root,'node_modules','@playwright','test','cli.js');
    return run('e2e',process.execPath,[cli,'test','--config=qa/playwright.config.cjs']);
  }
  return run('inventory',python,['qa/inventory.py']);
}
let code=0;
try{for(const kind of suite==='all'?['unit','backend','ui','e2e','inventory']:[suite])code=execute(kind)||code;}
catch(error){code=1;fs.writeFileSync(path.join(folder,'runner-error.txt'),String(error.stack));process.stderr.write(String(error)+'\n');}
finally{
  const summary={suite,scope:focus==='--focus=live-readonly'?'live-readonly':focus==='--focus=matriz'?'matriz':focus?'qa-integration':'complete',finished:new Date().toISOString(),exit_code:code,results};
  fs.writeFileSync(path.join(folder,'summary.json'),JSON.stringify(summary,null,2));
  fs.writeFileSync(path.join(__dirname,'ULTIMA_EXECUCAO.json'),JSON.stringify({folder:path.relative(root,folder),...summary},null,2));
  process.stdout.write(`[QA] Resultado: ${code===0?'PASSOU':'FALHOU'}; evidências: ${folder}\n`);
}
process.exitCode=code;
