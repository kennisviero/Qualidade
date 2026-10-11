from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import get_current_user, require_papel
from app.db import DOCS_DIR, get_connection
from app.docs import delete_path, file_node, folder_for, guess_mime, node, safe_rel, sanitize, save_file
from app.routers.processos import fetch_processo
from app.security import SafeModel

router = APIRouter(tags=["documentos"])

editor_dep = require_papel("admin", "editor")


class PastaIn(SafeModel):
    nome: str
    subpasta: str = ""


class ArquivoIn(SafeModel):
    nome: str
    subpasta: str = ""


def processo_folder(conn, processo):
    return folder_for(processo["pasta"] or "")


@router.get("/api/processos/{processo_id}/arvore")
def arvore(processo_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        pasta = processo["pasta"] or ""
    parts = [p for p in pasta.split("/") if p]
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
    return {"pasta": pasta, "arvore": root}


@router.post("/api/processos/{processo_id}/arquivos", status_code=201)
def upload_arquivo(
    processo_id: int,
    subpasta: str = Form(""),
    file: UploadFile = File(...),
    user: dict = Depends(editor_dep),
):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        folder = folder_for(processo["pasta"] or "")
    try:
        target_dir = safe_rel(folder, subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if target_dir.exists() and not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target_dir.mkdir(parents=True, exist_ok=True)
    nome = save_file(target_dir, file.filename or "arquivo", data)
    return {"nome": nome}


@router.post("/api/processos/{processo_id}/arquivos/criar", status_code=201)
def criar_arquivo(processo_id: int, body: ArquivoIn, user: dict = Depends(editor_dep)):
    nome = sanitize(body.nome)
    if nome == "_":
        raise HTTPException(status_code=400, detail="Nome inválido")
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        folder = folder_for(processo["pasta"] or "")
    try:
        target_dir = safe_rel(folder, body.subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if target_dir.exists() and not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target_dir.mkdir(parents=True, exist_ok=True)
    nome_disco = save_file(target_dir, nome, b"")
    return {"nome": nome_disco}


@router.post("/api/processos/{processo_id}/pastas", status_code=201)
def criar_pasta(processo_id: int, body: PastaIn, user: dict = Depends(editor_dep)):
    nome = sanitize(body.nome)
    if nome == "_":
        raise HTTPException(status_code=400, detail="Nome inválido")
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        folder = folder_for(processo["pasta"] or "")
    try:
        base = safe_rel(folder, body.subpasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Subpasta inválida")
    target = base / nome
    target.mkdir(parents=True, exist_ok=True)
    return {"nome": target.name}


@router.delete("/api/processos/{processo_id}/objetos", status_code=204)
def delete_objeto(processo_id: int, caminho: str, user: dict = Depends(editor_dep)):
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        folder = folder_for(processo["pasta"] or "")
    try:
        delete_path(folder, caminho)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Objeto não encontrado")


@router.get("/api/processos/{processo_id}/arquivo")
def abrir_arquivo(processo_id: int, caminho: str, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        processo = fetch_processo(conn, processo_id, user)
        folder = folder_for(processo["pasta"] or "")
    try:
        target = safe_rel(folder, caminho)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    mime = guess_mime(target.name)
    inline = (
        mime.startswith("image/")
        or mime == "application/pdf"
        or mime.startswith("text/")
    )
    return FileResponse(
        target,
        media_type=mime,
        filename=target.name,
        content_disposition_type="inline" if inline else "attachment",
    )
