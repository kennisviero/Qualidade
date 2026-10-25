import mimetypes
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.db import DOCS_DIR

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(name):
    name = (name or "").strip().strip(".")
    name = _INVALID.sub("_", name).strip()
    if not name:
        name = "_"
    return name[:80]


def build_pasta(empresa, setor, processo):
    parts = [sanitize(empresa)]
    if setor:
        parts.append(sanitize(setor))
    parts.append(sanitize(processo))
    return "/".join(parts)


def folder_for(pasta):
    return DOCS_DIR / Path(pasta)


def ensure_pasta(pasta):
    d = folder_for(pasta)
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_rel(folder: Path, rel: str) -> Path:
    base = folder.resolve()
    rel = (rel or "").strip().replace("\\", "/").strip("/")
    target = (base / rel).resolve() if rel else base
    if target != base and not target.is_relative_to(base):
        raise ValueError("Caminho fora da pasta do processo")
    return target


def save_file(folder: Path, filename: str, data: bytes) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    stem, ext = os.path.splitext(filename)
    stem = sanitize(stem)
    ext = ("." + sanitize(ext[1:])) if ext else ""
    candidate = f"{stem}{ext}"
    path = folder / candidate
    i = 1
    while path.exists():
        candidate = f"{stem} ({i}){ext}"
        path = folder / candidate
        i += 1
    path.write_bytes(data)
    return candidate


def delete_path(folder: Path, rel: str) -> None:
    target = safe_rel(folder, rel)
    if target == folder.resolve():
        raise ValueError("Não é possível excluir a raiz")
    if target.is_dir():
        shutil.rmtree(target)
    elif target.is_file():
        target.unlink()
    else:
        raise FileNotFoundError(rel)


def guess_mime(name):
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def file_node(path):
    st = path.stat()
    return {
        "nome": path.name,
        "tipo": "arquivo",
        "tamanho": st.st_size,
        "mime": guess_mime(path.name),
        "modificado_em": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def node(path):
    if path.is_dir():
        children = sorted(
            (node(c) for c in path.iterdir()),
            key=lambda n: (n["tipo"] != "dir", n["nome"].lower()),
        )
        return {"nome": path.name, "tipo": "dir", "filhos": children}
    return file_node(path)


def build_ishikawa_pasta(empresa, setor, nome):
    base = "/".join([sanitize(empresa), sanitize(setor), sanitize(nome)])
    candidate = base
    i = 2
    while (DOCS_DIR / candidate).exists():
        candidate = f"{base} ({i})"
        i += 1
    return candidate


def build_issue_pasta(empresa, codigo):
    base = "/".join([sanitize(empresa), sanitize(codigo)])
    candidate = base
    i = 2
    while (DOCS_DIR / candidate).exists():
        candidate = f"{base} ({i})"
        i += 1
    return candidate


def build_documento_pasta(empresa, codigo):
    """Pasta no Vault do documento controlado (PDM): Vault/{empresa}/_pdm/{codigo}/.

    O subnível `_pdm` isola os documentos controlados dos códigos de Issue/RNC
    na mesma empresa. Cada revisão grava em `R{numero}/` (ver router do PDM).
    """
    base = "/".join([sanitize(empresa), "_pdm", sanitize(codigo)])
    candidate = base
    i = 2
    while (DOCS_DIR / candidate).exists():
        candidate = f"{base} ({i})"
        i += 1
    return candidate


def arvore_tree(pasta):
    parts = [p for p in (pasta or "").split("/") if p]
    root = {"nome": DOCS_DIR.name, "tipo": "dir", "filhos": []}
    cur = root
    folder = DOCS_DIR
    for part in parts:
        folder = folder / part
        child = {"nome": part, "tipo": "dir", "filhos": []}
        cur["filhos"].append(child)
        cur = child
    if folder.exists():
        cur["filhos"] = sorted(
            (node(c) for c in folder.iterdir()),
            key=lambda n: (n["tipo"] != "dir", n["nome"].lower()),
        )
    return root
