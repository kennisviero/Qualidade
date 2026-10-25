"""Sugestão de requisitos a partir do texto de uma norma (parsing por IA).

Reusa o adapter `llm_client.analisar_issues` (JSON mode). Não persiste nada: devolve
candidatos para aprovação humana. Regra de ouro: não inventar — espelha
`app/services/issue_triagem.py`. Validação estrita do JSON de retorno.
"""
import json

from app.services.llm_client import LlmError, analisar_issues

CATEGORIAS = ("normativo", "interno", "cliente", "legal")
OBRIGATORIEDADE = ("obrigatorio", "recomendado", "informativo")

INSTRUCOES = (
    "Você extrai requisitos/cláusulas de uma norma ou regulamento a partir do texto fornecido. "
    "Trabalhe apenas com o que está no texto: não invente cláusulas, números, obrigações ou conteúdo ausente. "
    "Retorne um objeto JSON com a chave \"requisitos\", uma lista de objetos com os campos: "
    "codigo_clausula (string, o número/identificador da cláusula se houver, senão vazio), "
    "titulo (string, resumo curto do requisito), texto (string, o enunciado do requisito como no documento), "
    "categoria (um de: normativo, interno, cliente, legal), "
    "obrigatoriedade (um de: obrigatorio, recomendado, informativo). "
    "Se o texto não permitir identificar requisitos, retorne lista vazia. Responda só com o JSON."
)

MAX_TEXTO = 100000


def sugerir(acesso: dict, texto: str) -> list:
    content = analisar_issues(acesso, INSTRUCOES, {"texto": (texto or "")[:MAX_TEXTO]},
                              data_key="documento", json_mode=True)
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        raise LlmError("resposta_invalida", "A IA não retornou JSON válido.")
    itens = data.get("requisitos") if isinstance(data, dict) else data
    if not isinstance(itens, list):
        raise LlmError("resposta_invalida", "Formato inesperado: esperado uma lista de requisitos.")
    out = []
    for it in itens:
        if not isinstance(it, dict):
            continue
        titulo = str(it.get("titulo") or "").strip()
        if not titulo:
            continue
        cat = it.get("categoria") if it.get("categoria") in CATEGORIAS else "normativo"
        obr = it.get("obrigatoriedade") if it.get("obrigatoriedade") in OBRIGATORIEDADE else "obrigatorio"
        out.append(dict(
            codigo_clausula=str(it.get("codigo_clausula") or "")[:60],
            titulo=titulo[:300],
            texto=str(it.get("texto") or "")[:8000],
            categoria=cat,
            obrigatoriedade=obr,
        ))
    return out
