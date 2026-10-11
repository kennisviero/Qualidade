import os
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import get_current_user

router = APIRouter(prefix="/api/transcricao", tags=["transcricao"])


def _transcreve_txt(data: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _transcreve_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(status_code=500, detail="pypdf não instalado")
    try:
        reader = PdfReader(BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        raise HTTPException(status_code=400, detail="PDF inválido ou corrompido")


def _transcreve_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx não instalado")
    try:
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception:
        raise HTTPException(status_code=400, detail="DOCX inválido ou corrompido")


@router.post("")
def transcrever(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext == ".pdf":
        texto = _transcreve_pdf(data)
    elif ext == ".docx":
        texto = _transcreve_docx(data)
    elif ext == ".txt":
        texto = _transcreve_txt(data)
    else:
        raise HTTPException(
            status_code=400, detail="Formato não suportado (use TXT, PDF ou DOCX)"
        )
    return {"texto": texto}
