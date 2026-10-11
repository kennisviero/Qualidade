import math
import statistics


def pareto(categorias):
    if not categorias:
        return {"itens": [], "total": 0}
    itens = sorted(categorias, key=lambda c: c["frequencia"], reverse=True)
    total = sum(c["frequencia"] for c in itens)
    acumulado = 0.0
    resultado = []
    for c in itens:
        acumulado += c["frequencia"]
        resultado.append(
            {
                "rotulo": c["rotulo"],
                "frequencia": c["frequencia"],
                "percentual": round(c["frequencia"] / total * 100, 2) if total else 0,
                "acumulado": round(acumulado / total * 100, 2) if total else 0,
            }
        )
    return {"itens": resultado, "total": total}


def dispersao(pares):
    n = len(pares)
    if n == 0:
        return {"pontos": [], "n": 0, "correlacao": None}
    xs = [p["x"] for p in pares]
    ys = [p["y"] for p in pares]
    correlacao = None
    if n >= 2 and statistics.pstdev(xs) != 0 and statistics.pstdev(ys) != 0:
        media_x = statistics.mean(xs)
        media_y = statistics.mean(ys)
        num = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
        den = math.sqrt(
            sum((x - media_x) ** 2 for x in xs)
            * sum((y - media_y) ** 2 for y in ys)
        )
        correlacao = round(num / den, 4) if den else None
    return {"pontos": pares, "n": n, "correlacao": correlacao}


def controle(valores):
    n = len(valores)
    if n == 0:
        return {"media": 0, "desvio": 0, "lsc": 0, "lic": 0, "pontos": []}
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if n > 1 else 0.0
    lsc = media + 3 * desvio
    lic = media - 3 * desvio
    pontos = [{"amostra": i + 1, "valor": v} for i, v in enumerate(valores)]
    return {
        "media": round(media, 4),
        "desvio": round(desvio, 4),
        "lsc": round(lsc, 4),
        "lic": round(lic, 4),
        "pontos": pontos,
    }
