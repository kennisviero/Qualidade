"""Captura/leitura de documentos do PDM.

Camadas, nesta ordem:
1. Extração digital **local** (sem API): texto nativo de TXT/PDF/DOCX.
2. Leitura por **IA via OpenRouter** (modelo com visão): só quando não há texto
   nativo e um acesso LLM foi informado. Renderiza as páginas com PyMuPDF e envia
   as imagens ao modelo, que transcreve o conteúdo e sinaliza assinaturas/carimbos.

Tudo degrada graciosamente: sem `pymupdf`, sem acesso LLM, ou PDF já com texto, a
leitura por IA é simplesmente pulada. Nenhuma chamada externa acontece na via digital.
"""
import base64
import os
from io import BytesIO

INSTRUCOES_VISAO = (
    "Transcreva fielmente, em português, todo o texto legível das páginas do documento enviado. "
    "Não invente conteúdo nem complete lacunas. Preserve títulos, itens e numeração. "
    "Se houver assinatura, carimbo ou rubrica, registre ao final uma linha '[ASSINATURA/CARIMBO]: <descrição breve>'. "
    "Responda apenas com o texto transcrito."
)

MAX_PAGINAS = 10


def extrair_texto_local(nome: str, data: bytes) -> str:
    """Texto nativo de TXT/PDF/DOCX. Retorna '' se não houver camada de texto."""
    ext = os.path.splitext(nome or "")[1].lower()
    if ext == ".txt":
        for enc in ("utf-8", "latin-1"):
            try:
                return data.decode(enc).strip()
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace").strip()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        try:
            reader = PdfReader(BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
        except Exception:
            return ""
    if ext == ".docx":
        try:
            from docx import Document
        except ImportError:
            return ""
        try:
            doc = Document(BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception:
            return ""
    return ""


def render_paginas(nome: str, data: bytes, max_paginas: int = MAX_PAGINAS):
    """Renderiza páginas como data URIs PNG para leitura por visão.

    PDF via PyMuPDF; imagem (PNG/JPG/TIFF) é usada diretamente. Sem PyMuPDF (PDF)
    retorna [] — a leitura por IA é então pulada.
    """
    ext = os.path.splitext(nome or "")[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"):
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        return [f"data:{mime};base64," + base64.b64encode(data).decode("ascii")]
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return []
        imagens = []
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                for page in doc[:max_paginas]:
                    pix = page.get_pixmap(dpi=150)
                    png = pix.tobytes("png")
                    imagens.append("data:image/png;base64," + base64.b64encode(png).decode("ascii"))
        except Exception:
            return []
        return imagens
    return []


def ler_documento(nome: str, data: bytes, acesso: dict | None = None) -> dict:
    """Retorna {'texto', 'origem'} com origem em 'digital' | 'ia' | 'vazio'."""
    texto = extrair_texto_local(nome, data)
    if texto:
        return {"texto": texto, "origem": "digital"}
    if acesso is not None:
        imagens = render_paginas(nome, data)
        if imagens:
            from app.services.llm_client import ler_documento_visao
            texto = (ler_documento_visao(acesso, INSTRUCOES_VISAO, imagens) or "").strip()
            if texto:
                return {"texto": texto, "origem": "ia"}
    return {"texto": "", "origem": "vazio"}
