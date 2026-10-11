from app.calculations import controle, dispersao, pareto


def test_pareto_ordena_e_calcula_acumulado():
    result = pareto([{"rotulo": "A", "frequencia": 10}, {"rotulo": "B", "frequencia": 5}])
    assert result["total"] == 15
    assert [i["rotulo"] for i in result["itens"]] == ["A", "B"]
    assert result["itens"][0]["percentual"] == 66.67
    assert result["itens"][1]["acumulado"] == 100.0


def test_pareto_vazio():
    assert pareto([]) == {"itens": [], "total": 0}


def test_dispersao_correlacao_perfeita():
    pares = [{"x": i, "y": i} for i in range(1, 11)]
    result = dispersao(pares)
    assert result["correlacao"] == 1.0


def test_dispersao_sem_pares():
    assert dispersao([])["correlacao"] is None


def test_controle_limites():
    result = controle([10, 12, 11, 9, 13, 10, 12, 11])
    assert result["lsc"] > result["media"]
    assert result["lic"] < result["media"]
    assert len(result["pontos"]) == 8
