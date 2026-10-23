const {test,expect}=require('@playwright/test');
const path=require('path');

test.beforeEach(async({page})=>{
  const pageErrors=[],consoleMessages=[];page.on('pageerror',e=>pageErrors.push(String(e)));
  page.on('console',msg=>consoleMessages.push({type:msg.type(),text:msg.text()}));
  // Rede externa bloqueada. Apenas Plotly CDN recebe biblioteca mínima para não
  // impedir navegação; estes cenários não validam os gráficos Plotly.
  await page.route('**/*',route=>{
    const url=new URL(route.request().url());
    if(url.hostname==='127.0.0.1'&&url.port==='18765')return route.continue();
    if(url.hostname==='cdn.plot.ly')return route.fulfill({contentType:'application/javascript',body:'window.Plotly={newPlot:async function(){},purge:function(){}};'});
    return route.abort('blockedbyclient');
  });
  page.__qaErrors=pageErrors;page.__qaConsole=consoleMessages;
});
test.afterEach(async({page},testInfo)=>{
  await testInfo.attach('browser-console',{body:Buffer.from(JSON.stringify({pageErrors:page.__qaErrors,messages:page.__qaConsole})),contentType:'application/json'});
});
async function loginUI(page,email='admin',senha='admin'){
  await page.goto('/');await page.locator('#loginEmail').fill(email);await page.locator('#loginSenha').fill(senha);
  await page.locator('#btnLogin').click();await expect(page.locator('#loginOverlay')).toBeHidden();
}
async function company(page){
  const name='QA E2E '+Date.now();
  const response=await page.request.post('/api/empresas',{data:{razao_social:name}});expect(response.ok()).toBeTruthy();
  await page.reload();await expect(page.locator('#loginOverlay')).toBeHidden();
  const id=String((await response.json()).id);
  const loaded=page.waitForResponse(r=>r.url().includes('/api/issues/kanban?empresa_id='+id)&&r.request().method()==='GET');
  await page.locator('#empresaSelect').selectOption(id);await loaded;
  return name;
}
async function capture(page){
  await page.locator('[data-issue-view="capturar"]').click();await page.locator('#btnIssueNova').click();
  for(const [id,value] of Object.entries({issueDetectadoEm:'2026-10-16T10:00',issueComportamentoEsperado:'Etiqueta deve identificar o lote',issueComportamentoObservado:'Etiqueta ilegível QA',issueEvidencias:'Inspeção simulada QA: 3 etiquetas ilegíveis',issueAcaoEmergencial:'Lote retido para inspeção',issueOnde:'Posto QA',issueComoDetectado:'Inspeção de legibilidade'}))await page.locator('#'+id).fill(value);
  await page.locator('#issueImpacto').selectOption('medio');await page.locator('#issueEnvolvidos').selectOption('equipe_interna');
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/issues')&&r.request().method()==='POST');
  await page.locator('#btnIssueSalvar').click();const response=await saved;expect(response.status()).toBe(201);
  await expect(page.locator('#issueCodigo')).toHaveValue(/ISSUE-\d+/);return response.json();
}
test('RG-AUT-001 login inválido e login válido',async({page})=>{
  await page.goto('/');await page.locator('#loginSenha').fill('incorreta');await page.locator('#btnLogin').click();
  await expect(page.locator('#loginError')).toContainText('Credenciais');
  await loginUI(page);await expect(page.locator('#userInfo')).toContainText('admin');
});
test('RG-ISS-003 captura real pela SPA e RG-EST-005 fechamento',async({page})=>{
  await loginUI(page);await company(page);await capture(page);
  page.once('dialog',d=>d.accept());await page.locator('#btnIssueFechar').click();
  await expect(page.locator('#issueDetail')).toBeHidden();
  await expect(page.locator('#issueList option')).toHaveCount(1);
  expect(page.__qaErrors).toEqual([]);
});
test('RG-AFI-007 e RG-REL-010 persistem após recarregar a página',async({page})=>{
  await loginUI(page);await company(page);await capture(page);
  await page.locator('[data-section="afinidades"]').click();
  await expect(page.locator('#afin-carregar')).toBeEnabled();await page.locator('#afin-carregar').click();
  await expect(page.locator('#afin-resumo')).toContainText('1 cartões');
  await page.locator('#afin-titulo').fill('Afinidades QA');await page.locator('#afin-novo').fill('Identificação');await page.locator('#afin-adicionar').click();
  await page.locator('#afin-board .afin-card select').selectOption('0');await page.locator('#afin-salvar').click();
  await expect(page.locator('#afin-mensagem')).toContainText('Diagrama salvo');
  await page.reload();await page.locator('[data-section="afinidades"]').click();
  // A empresa selecionada volta ao padrão no login/recarga; escolha a empresa QA.
  await page.locator('#empresaSelect').selectOption({label:await companyNameFromDiagram(page)});
  await expect(page.locator('#afin-salvos option')).toHaveCount(2);await page.locator('#afin-salvos').selectOption({label:'Afinidades QA · revisão 1'});await page.locator('#afin-abrir').click();
  await expect(page.locator('#afin-board')).toContainText('Identificação');
  await page.locator('[data-section="relacoes"]').click();await expect(page.locator('#rel-carregar')).toBeEnabled();await page.locator('#rel-carregar').click();
  await expect(page.locator('#rel-editor')).toBeVisible();await page.locator('#rel-titulo').fill('Relações QA');
  for(const name of ['Instrução','Ajustes']){await page.locator('#rel-novo').fill(name);await page.locator('#rel-adicionar').click();}
  await page.locator('#rel-origem').selectOption('1');await page.locator('#rel-destino').selectOption('2');await page.locator('#rel-justificativa').fill('Verificar influência da instrução no ajuste');await page.locator('#rel-incluir-seta').click();
  await expect(page.locator('#rel-grafico svg')).toBeVisible();await page.locator('#rel-salvar').click();await expect(page.locator('#rel-mensagem')).toContainText('Diagrama salvo');
  const companyId=await page.locator('#empresaSelect').inputValue();await page.reload();await page.locator('#empresaSelect').selectOption(companyId);await page.locator('[data-section="relacoes"]').click();
  await expect(page.locator('#rel-salvos option')).toHaveCount(2);await page.locator('#rel-salvos').selectOption({label:'Relações QA · revisão 1'});await page.locator('#rel-abrir').click();await expect(page.locator('#rel-setas')).toContainText('Verificar influência');
  await page.screenshot({path:path.join(process.env.QA_EVIDENCE_DIR,'relacoes-sucesso.png'),fullPage:true});expect(page.__qaErrors).toEqual([]);
});
async function companyNameFromDiagram(page){
  const response=await page.request.get('/api/empresas');const companies=await response.json();return companies.filter(c=>c.razao_social.startsWith('QA E2E ')).at(-1).razao_social;
}
