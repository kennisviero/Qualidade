import re
from typing import ClassVar

from pydantic import BaseModel, field_validator

_SCRIPT_RE = re.compile(r"<\s*/?\s*script[^>]*>", re.IGNORECASE)
_EVENT_RE = re.compile(r"\son\w+\s*=", re.IGNORECASE)
_JS_URL_RE = re.compile(r"javascript\s*:", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_text(value):
    """Remove padrões perigosos (XSS) de conteúdo textual, recursivamente.

    Preserva o texto interno; só remove tags/scripts/handlers/javascript:.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = _SCRIPT_RE.sub("", value)
        value = _EVENT_RE.sub(" ", value)
        value = _JS_URL_RE.sub("", value)
        value = _TAG_RE.sub("", value)
        return value
    if isinstance(value, list):
        return [sanitize_text(v) for v in value]
    if isinstance(value, dict):
        return {k: sanitize_text(v) for k, v in value.items()}
    return value


def sanitize_fields(data: dict, skip: set = None):
    skip = skip or set()
    return {k: (v if k in skip else sanitize_text(v)) for k, v in data.items()}


class SafeModel(BaseModel):
    """Base para modelos de entrada: sanitiza todos os campos de texto (recursivo).

    Subclasses podem declarar `_sanitize_skip` (frozenset de nomes) para pular
    campos como `sintaxe` (Mermaid) e `senha`.
    """

    _sanitize_skip: ClassVar[frozenset] = frozenset()

    @field_validator("*", mode="before")
    @classmethod
    def _sanitize_field(cls, v, info):
        if info.field_name in cls._sanitize_skip:
            return v
        return sanitize_text(v)
