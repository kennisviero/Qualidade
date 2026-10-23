"""Inventário estático e rastreabilidade explícita; não mede cobertura de linhas."""
import ast
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
QA=ROOT/'qa'
routes=[];functions=[]
for file in sorted((ROOT/'app').rglob('*.py')):
    tree=ast.parse(file.read_text(encoding='utf-8-sig'))
    prefix=''
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and getattr(node.value.func,'id',None)=='APIRouter':
            prefix=next((k.value.value for k in node.value.keywords if k.arg=='prefix' and isinstance(k.value,ast.Constant)),'')
    for node in tree.body:
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        symbol={'file':file.relative_to(ROOT).as_posix(),'line':node.lineno,'function':node.name}
        functions.append(symbol)
        for decorator in node.decorator_list:
            if isinstance(decorator,ast.Call) and isinstance(decorator.func,ast.Attribute) and getattr(decorator.func.value,'id',None)=='router' and decorator.func.attr in ('get','post','put','delete','patch'):
                route=decorator.args[0].value if decorator.args and isinstance(decorator.args[0],ast.Constant) else ''
                routes.append({**symbol,'method':decorator.func.attr.upper(),'path':prefix+route})

rules=[]
for line in (ROOT/'regrasnegocio/RG.md').read_text(encoding='utf-8').splitlines():
    match=re.match(r'\| (RG-[A-Z]+-\d{3}) \| (.*?) \|',line)
    if match:rules.append({'id':match[1],'rule':match[2]})

scenarios=[]
for file in sorted((ROOT/'tests').rglob('test_*.py')):
    tree=ast.parse(file.read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
            ids=['RG-'+m[0].upper()+'-'+m[1] for m in re.findall(r'rg_([a-z]+)_(\d{3})',node.name)]
            scenarios.append({'file':file.relative_to(ROOT).as_posix(),'line':node.lineno,'name':node.name,'rules':ids})
for file in sorted((QA/'e2e').glob('*.cjs')):
    for match in re.finditer(r"test\('([^']+)'",file.read_text(encoding='utf-8')):
        scenarios.append({'file':file.relative_to(ROOT).as_posix(),'line':1,'name':match[1],'rules':re.findall(r'RG-[A-Z]+-\d{3}',match[1])})

# Preserva rodada completa e focada; o foco só substitui casos realmente executados.
latest={}
for summary in sorted((QA/'evidencias').glob('*/summary.json')):
    data=json.loads(summary.read_text(encoding='utf-8'))
    for result in data['results']:
        if result['name'] in ('unit','backend','e2e'):
            xml=summary.parent/(result['name']+'.xml')
            key=(result['name'],data.get('scope','complete'))
            latest[key]={'xml':xml if xml.exists() else None,'result':result,'scope':data.get('scope','complete')}
by_case={};infrastructure=[]
for entry in sorted(latest.values(),key=lambda e:e['result']['started']):
    suite=entry['result']['name']
    xml=entry['xml']
    if xml is None:
        infrastructure.append({'suite':suite,'scope':entry['scope'],'name':'__suite__','status':'erro_infraestrutura',
                         'evidence':Path(entry['result']['log']).as_posix()})
        continue
    for case in ET.parse(xml).getroot().iter('testcase'):
        status='falhou' if case.find('failure') is not None or case.find('error') is not None else 'ignorado' if case.find('skipped') is not None else 'passou'
        by_case[(suite,case.get('classname',''),case.get('name',''))]={'suite':suite,'scope':entry['scope'],'name':case.get('name',''),'status':status,'evidence':xml.relative_to(ROOT).as_posix()}
outcomes=[*by_case.values(),*infrastructure]

lines=['# Cobertura e rastreabilidade QA','',
       'Inventário gerado do código atual. Cenário nomeado é rastreabilidade parcial da regra, não garantia de cobertura integral. Testes legados sem ID continuam no inventário, aguardando ligação de assertivas. Não é percentual de linhas/branches.','',
       f'{len(rules)} regras; {len(routes)} endpoints; {len(functions)} funções de módulo; {len(scenarios)} cenários estáticos (parametrizações são expandidas somente na execução).','',
       '| Regra | Cenários explicitamente ligados | Estado/evidência |','|---|---|---|']
linked=0
for rule in rules:
    cases=[s for s in scenarios if rule['id'] in s['rules']]
    matches=[o for o in outcomes if any(o['name']==s['name'] or o['name'].startswith(s['name']+'[') for s in cases)]
    suites={('unit' if s['file']=='tests/qa/test_unit_rules.py' else 'e2e' if s['file'].startswith('qa/e2e/') else 'backend') for s in cases}
    matches.extend(o for o in outcomes if o['name']=='__suite__' and o['suite'] in suites)
    state='Pendente de vínculo/revisão de assertivas'
    if cases:
        linked+=1
        state='Cenário criado; execução pendente'
        if matches:state='Bloqueado por erro de infraestrutura' if any(o['status']=='erro_infraestrutura' for o in matches) else 'Falha reproduzida' if any(o['status']=='falhou' for o in matches) else 'Cenário passou; cobertura parcial' if all(o['status']=='passou' for o in matches) else 'Execução parcial/ignorada'
    references='<br>'.join(f"[{s['name']}](../{s['file']}:{s['line']})" for s in cases) or 'Consultar testes legados; ainda sem vínculo explícito'
    evidence='<br>'.join(f"[JUnit](../{p})" for p in sorted({o['evidence'] for o in matches}))
    lines.append(f"| {rule['id']} | {references} | {state}{'<br>'+evidence if evidence else ''} |")
lines+=['',f'Regras com cenário explicitamente nomeado: {linked}/{len(rules)}. As demais não são declaradas descobertas nem cobertas somente pelo nome do módulo.','',
        '## Endpoints','', '| Método | Rota | Função |','|---|---|---|']
lines.extend(f"| {r['method']} | `{r['path']}` | [{r['function']}](../{r['file']}:{r['line']}) |" for r in routes)
(QA/'COBERTURA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(QA/'inventario.json').write_text(json.dumps({'rules':rules,'routes':routes,'functions':functions,'scenarios':scenarios,'latest_outcomes':outcomes},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'rules':len(rules),'endpoints':len(routes),'functions':len(functions),'scenarios':len(scenarios),'rules_with_explicit_scenarios':linked},ensure_ascii=False))
