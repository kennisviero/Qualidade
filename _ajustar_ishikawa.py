from pathlib import Path

p=Path('app/static/js/rncs.js')
s=p.read_text(encoding='utf-8')
start=s.index('  const treeGrid=')
end=s.index("  grid=block(plan,'Aprovação e prazo do plano'",start)
s=s[:start]+s[end:]
s=s.replace("'Problema / efeito analisado','etapa_ishikawa_efeito'", "'Objetivo RNC','etapa_ishikawa_efeito'")
start=s.index("  for(const [key,label] of [['metodo','Método']")
end=s.index("  grid=block(investigationStages.ishikawa,'Conclusão",start)
s=s[:start]+'''  for(const [key,label] of [['metodo','Método'],['maquina','Máquina / equipamento / sistema'],['material','Material / insumos'],['mao_obra','Mão de obra / pessoas'],['medicao','Medição / controles'],['meio_ambiente','Meio ambiente / condições']]){
    const category=document.createElement('div');grid.appendChild(category);
    const title=field(category,'Título da categoria','etapa_ishikawa_'+key+'_titulo','text',ishikawaData[key+'_titulo']??label);
    title.maxLength=200;ishikawaControls[key+'_titulo']=title;
    ishikawaControls[key]=field(category,'Conteúdo','etapa_ishikawa_'+key,'textarea',ishikawaData[key]||'');
  }
'''+s[end:]
p.write_text(s,encoding='utf-8')
p=Path('app/static/css/style.css');s=p.read_text(encoding='utf-8');s='\n'.join(line for line in s.split('\n') if not line.startswith('.rnc-objective-tree'));p.write_text(s,encoding='utf-8')
p=Path('tests/check_rnc_tabs.cjs');s=p.read_text(encoding='utf-8');start=s.index("  await ctx.renderRncTabs(target,item,'plano');\n  let treeAll");end=s.index("  console.log('OK: abas RNC",start)
s=s[:start]+'''  await ctx.renderRncTabs(target,item,'investigacao','ishikawa');
  const ishFields=flatten(target);
  assert.ok(!ishFields.some(e=>e.textContent==='Criar Diagrama de Árvore'));
  for(const key of ['metodo','maquina','material','mao_obra','medicao','meio_ambiente']){
    ishFields.find(e=>e.dataset.field==='etapa_ishikawa_'+key+'_titulo').value='Título personalizado '+key;
    ishFields.find(e=>e.dataset.field==='etapa_ishikawa_'+key).value='Conteúdo '+key;
  }
  ishFields.find(e=>e.dataset.field==='etapa_ishikawa_efeito').value='Reduzir erros a 1%';
  let ishPayload;
  ctx.api=async(path,options)=>{
    if(path==='/api/usuarios')return [{id:1,nome:'A',empresa_id:4}];
    ishPayload=options.body;return {...item,rnc_investigacao_json:ishPayload.investigacao_json};
  };
  await ishFields.find(e=>e.textContent==='Salvar registro').onclick();
  assert.equal(ishPayload.investigacao_json.etapa_ishikawa.efeito,'Reduzir erros a 1%');
  const reloaded=flatten(target);
  for(const key of ['metodo','maquina','material','mao_obra','medicao','meio_ambiente']){
    assert.equal(reloaded.find(e=>e.dataset.field==='etapa_ishikawa_'+key+'_titulo').value,'Título personalizado '+key);
    assert.equal(reloaded.find(e=>e.dataset.field==='etapa_ishikawa_'+key).value,'Conteúdo '+key);
  }
'''+s[end:];s=s.replace('abas RNC, árvore,','abas RNC, títulos Ishikawa,');p.write_text(s,encoding='utf-8')
