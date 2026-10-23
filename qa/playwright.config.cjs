const {defineConfig}=require('@playwright/test');
const path=require('path');
const evidence=process.env.QA_EVIDENCE_DIR;
if(!evidence)throw Error('Execute pelo script npm run qa:e2e para registrar isolamento/evidências.');
module.exports=defineConfig({
  testDir:path.join(__dirname,'e2e'),fullyParallel:false,workers:1,retries:0,timeout:60000,
  globalTeardown:require.resolve('./teardown.cjs'),
  outputDir:path.join(evidence,'browser-artifacts'),
  reporter:[['list'],['junit',{outputFile:path.join(evidence,'e2e.xml')}],['html',{outputFolder:path.join(evidence,'html'),open:'never'}]],
  use:{baseURL:'http://127.0.0.1:18765',headless:true,channel:'msedge',trace:'retain-on-failure',screenshot:'only-on-failure',video:'off'},
  webServer:{command:'npm run qa:serve',cwd:path.resolve(__dirname,'..'),url:'http://127.0.0.1:18765/',reuseExistingServer:false,timeout:45000,stdout:'pipe',stderr:'pipe'}
});
