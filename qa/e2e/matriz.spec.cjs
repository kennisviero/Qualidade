const {test,expect}=require('@playwright/test');
const path=require('path');
test('Matriz: Uma RNC/Geral, avaliar, salvar e reabrir sem alterar planos',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));const logs=[];page.on('console',m=>logs.push({type:m.type(),text:m.text()}));
 let aiCalls=0;const sent=[];
 await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.hostname==='127.0.0.1'&&u.port==='18765')return route.continue();if(u.hostname==='cdn.plot.ly')return route.fulfill({contentType:'application/javascript',body:'window.Plotly={newPlot:async()=>{},purge:()=>{}};'});return route.abort('blockedbyclient');});
 await page.route('**/api/ferramentas/ia/acessos?*',route=>route.fulfill({json:[{id:999,nome:'IA simulada QA',modelo:'mock'}]}));
 await page.route('**/api/ferramentas/ia/consultar',route=>{aiCalls++;sent.push(route.request().postDataJSON());return route.fulfill({json:{resposta:'Resposta simulada de revisão da matriz',modelo:'mock',completa:true}});});
 await page.goto('/');await page.locator('#loginEmail').fill('admin');await page.locator('#loginSenha').fill('admin');await page.locator('#btnLogin').click();await expect(page.locator('#loginOverlay')).toBeHidden();
 const company=await (await page.request.post('/api/empresas',{data:{razao_social:'QA Matriz '+Date.now()}})).json();const ids=[];
 for(let n=0;n<2;n++){
  const response=await page.request.post('/api/issues',{data:{empresa_id:company.id,detectado_em:'2026-10-16T10:00',comportamento_esperado:'Identificação legível',comportamento_observado:'Etiqueta ilegível '+n,evidencias_objetivas:'Inspeção simulada',impacto:'medio',acao_emergencial:'Retenção',o_que:'Etiqueta',onde:'Posto QA',quando:'2026-10-16T10:00',quem:'Equipe QA',como_detectado:'Inspeção'}});expect(response.status()).toBe(201);
  const issue=await response.json();const emitted=await page.request.post(`/api/issues/${issue.id}/emitir-rnc`,{data:{}});expect(emitted.ok()).toBeTruthy();ids.push((await emitted.json()).rnc_id);
 }
 const plans=await (await page.request.get('/api/issues/kanban?empresa_id='+company.id)).json();
 await page.reload();await page.locator('#empresaSelect').selectOption(String(company.id));await page.locator('[data-section="matriz"]').click();
 await expect(page.locator('#mat-rncs option')).toHaveCount(2);await page.locator('#mat-tab-ajuda').click();await expect(page.locator('#mat-ajuda')).toContainText('Uma célula não avaliada não significa ausência de relação');await page.locator('#mat-tab-quadro').click();
 await page.locator('#mat-rncs').selectOption(String(ids[0]));await page.locator('#mat-gerar').click();await expect(page.locator('#mat-resumo')).toContainText('0/1 cruzamentos avaliados');
 await page.locator('#mat-tabela .mat-cell').click();await page.locator('#mat-intensidade').selectOption('nenhuma');await page.locator('#mat-aplicar').click();await expect(page.locator('#mat-mensagem')).toContainText('Justifique');
 await page.locator('#mat-justificativa').fill('A ação não trata este fator');await page.locator('#mat-aplicar').click();await expect(page.locator('#mat-resumo')).toContainText('1/1 cruzamentos avaliados');
 await page.locator('#mat-titulo').fill('Matriz individual QA');await page.locator('#mat-salvar').click();await expect(page.locator('#mat-mensagem')).toContainText('revisão 1');
 await page.locator('#mat-ia').click();await expect(page.locator('#toolAI-prompt')).toHaveValue(/^Analise esta RNC:/);expect(aiCalls).toBe(0);await page.locator('#toolAI-send').click();await expect(page.locator('#toolAI-answer')).toContainText('Resposta simulada');expect(aiCalls).toBe(1);expect(JSON.parse(sent[0].snapshot).resultados.contexto).toBe('rnc');await page.locator('#toolAI-close').click();
 await page.locator('#mat-form [value="geral"]').check();await expect(page.locator('#mat-rncs')).toHaveAttribute('multiple','');await page.locator('#mat-rncs').selectOption(ids.map(String));await page.locator('#mat-gerar').click();await expect(page.locator('#mat-resumo')).toContainText('0/4 cruzamentos avaliados');
 await page.locator('#mat-tabela .mat-cell').nth(1).click();await page.locator('#mat-intensidade').selectOption('forte');await page.locator('#mat-justificativa').fill('Contribuição entre RNCs a verificar');await page.locator('#mat-aplicar').click();
 await page.locator('#mat-titulo').fill('Matriz geral QA');await page.locator('#mat-salvar').click();await expect(page.locator('#mat-mensagem')).toContainText('revisão 1');
 await page.locator('#mat-ia').click();await expect(page.locator('#toolAI-prompt')).toHaveValue(/^Analise o contexto geral das RNCs selecionadas:/);expect(aiCalls).toBe(1);await page.locator('#toolAI-prompt').fill('Instruções editadas: revise cobertura sem inventar evidências.');await page.locator('#toolAI-send').click();await expect(page.locator('#toolAI-answer')).toContainText('Resposta simulada');expect(aiCalls).toBe(2);expect(sent[1].prompt).toContain('Instruções editadas');expect(JSON.parse(sent[1].snapshot).resultados.contexto).toBe('geral');await page.locator('#toolAI-close').click();
 await page.reload();await page.locator('#empresaSelect').selectOption(String(company.id));await page.locator('[data-section="matriz"]').click();await page.locator('#mat-form [value="geral"]').check();await expect(page.locator('#mat-salvos option')).toHaveCount(2);await page.locator('#mat-salvos').selectOption({label:'Matriz geral QA · revisão 1'});await page.locator('#mat-abrir').click();await expect(page.locator('#mat-tabela .mat-forte')).toHaveCount(1);
 await page.locator('#mat-titulo').fill('Matriz geral QA revista');await page.locator('#mat-salvar').click();await expect(page.locator('#mat-mensagem')).toContainText('revisão 2');
 expect(await (await page.request.get('/api/issues/kanban?empresa_id='+company.id)).json()).toEqual(plans);expect(errors).toEqual([]);
 await page.screenshot({path:path.join(process.env.QA_EVIDENCE_DIR,'matriz-sucesso.png'),fullPage:true});await test.info().attach('matriz-console',{body:Buffer.from(JSON.stringify({errors,logs})),contentType:'application/json'});
});
