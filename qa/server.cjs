const cp=require('child_process'),path=require('path'),fs=require('fs');
const root=path.resolve(__dirname,'..'),python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
if(!process.env.QA_EVIDENCE_DIR||!fs.existsSync(python))throw Error('Use npm run qa:e2e com a venv do projeto.');
const child=cp.spawn(python,['-m','qa.server'],{cwd:root,env:process.env,stdio:'inherit',windowsHide:true});
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>child.kill());
child.on('exit',code=>process.exitCode=code||0);
