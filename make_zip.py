import zipfile, os

base = r'C:\Produttare\Qualidade'
out = os.path.join(base, 'qualidade_completa.zip')

# Files/dirs to explicitly include at root level
root_items = [
    'app', 'data', 'Documentos', 'Vault', 'tests', 'docs', 'qa',
    'regrasnegocio', 'stack', 'AGENTS.md', 'README.md',
    'requirements.txt', 'iniciar.bat', 'PRD.md', 'OPERACAO.md',
    'atividade.md', 'iniciar.bat'
]

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add root items
    for item in root_items:
        full = os.path.join(base, item)
        if os.path.isdir(full):
            for root2, dirs2, files2 in os.walk(full):
                for f in files2:
                    fp = os.path.join(root2, f)
                    arc = os.path.relpath(fp, base)
                    zf.write(fp, arc)
        elif os.path.isfile(full):
            zf.write(full, item)
    
    # Walk the entire base but skip problematic dirs
    skip_dirs = ['.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules', 'tmp']
    for root, dirs, files in os.walk(base):
        # Modify dirs in-place to skip unwanted directories
        dirs[:] = [d for d in dirs if not any(d.startswith(s) or d == s for s in skip_dirs)]
        for f in files:
            if any(f.startswith(s) or f == s + '.py' for s in skip_dirs):
                continue
            full = os.path.join(root, f)
            try:
                arc = os.path.relpath(full, base)
                zf.write(full, arc)
            except:
                pass

print('OK - zip created')