"""Execução dos 4 cenários. As expectativas são QUALITATIVAS, definidas no modelo.json antes
de rodar; a decisão do S4 é conferida por conta manual no próprio teste."""
import pytest

from bn_evasao import scenarios
from bn_evasao.inference import ErroInferencia, consultar_marginais

IDS = ["S1_preditivo_ingresso", "S2_alerta_precoce", "S3_diagnostico", "S4_prescritivo"]


@pytest.fixture(scope="module")
def resultados(rede, modelo):
    return {r["id"]: r for r in scenarios.executar_todos(rede, modelo["cenarios"])}


def test_existem_quatro_cenarios_distintos(modelo):
    assert [c["id"] for c in modelo["cenarios"]] == IDS
    assert {c["tipo_analise"] for c in modelo["cenarios"]} == {"preditiva", "diagnostica", "prescritiva"}


@pytest.mark.parametrize("cid", IDS)
def test_cenario_executa_e_satisfaz_todas_as_expectativas(resultados, cid):
    r = resultados[cid]
    assert r["verificacoes"], "cenário sem expectativas verificáveis"
    for v in r["verificacoes"]:
        assert v["satisfeita"], f"{cid}: {v['consulta']}={v['estado']} {v['maior_esperado']} !> {v['menor_esperado']}"
        assert v["prob_maior"] > v["prob_menor"]


@pytest.mark.parametrize("cid", IDS)
def test_distribuicoes_dos_cenarios_normalizadas(resultados, cid):
    for info in resultados[cid]["variantes"].values():
        for dist in info["distribuicoes"].values():
            assert sum(dist.values()) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("cid", IDS)
def test_cenario_consulta_realmente_a_rede(rede, modelo, resultados, cid):
    """O resultado do cenário deve ser reproduzível por uma consulta direta (não é valor colado)."""
    cen = next(c for c in modelo["cenarios"] if c["id"] == cid)
    for var in cen["variantes"]:
        ev = {**cen["evidencias_base"], **var["evidencias_adicionais"]}
        direto = consultar_marginais(rede, cen["consultas"], ev)
        assert direto == resultados[cid]["variantes"][var["id"]]["distribuicoes"]


def test_s2_efeito_monotono_do_desempenho_no_1o_semestre(rede):
    base = {"Faixa_Etaria": "Maduro", "Turno": "Noturno", "Bolsista": "Nao"}
    p = {s: consultar_marginais(rede, ["Desfecho"], {**base, "Desempenho_Sem1": s})["Desfecho"]["Dropout"]
         for s in ("Alto", "Medio", "Baixo")}
    assert p["Alto"] < p["Medio"] < p["Baixo"]


def test_s3_posterior_coerente_com_bayes(rede):
    """Regra de Bayes: P(Pressao=Alta|Dropout) = P(Dropout|Alta)P(Alta)/P(Dropout)."""
    p_alta = consultar_marginais(rede, ["Pressao_Financeira"])["Pressao_Financeira"]["Alta"]
    p_drop = consultar_marginais(rede, ["Desfecho"])["Desfecho"]["Dropout"]
    p_drop_dado_alta = consultar_marginais(rede, ["Desfecho"], {"Pressao_Financeira": "Alta"})["Desfecho"]["Dropout"]
    posterior = consultar_marginais(rede, ["Pressao_Financeira"], {"Desfecho": "Dropout"})["Pressao_Financeira"]["Alta"]
    assert posterior == pytest.approx(p_drop_dado_alta * p_alta / p_drop, abs=1e-6)


def test_s3_efeito_em_devedor_e_indireto(rede):
    """Dropout informa Devedor só via Pressao: dado Pressao, Dropout não altera Devedor."""
    a = consultar_marginais(rede, ["Devedor"], {"Pressao_Financeira": "Alta"})["Devedor"]
    b = consultar_marginais(rede, ["Devedor"], {"Pressao_Financeira": "Alta", "Desfecho": "Dropout"})["Devedor"]
    assert b["Sim"] == pytest.approx(a["Sim"], abs=1e-9)


def test_s4_recomendacao_confere_com_conta_manual(resultados, modelo):
    dec_json = next(c for c in modelo["cenarios"] if c["id"] == "S4_prescritivo")["decisao"]
    r = resultados["S4_prescritivo"]
    eu = {}
    for nome, alt in dec_json["alternativas"].items():
        dist = r["variantes"][alt["variante"]]["distribuicoes"][dec_json["consulta"]]
        eu[nome] = sum(p * dec_json["utilidades"][e] for e, p in dist.items()) - alt["custo"]
    for nome, valor in eu.items():
        assert r["decisao"]["alternativas"][nome]["utilidade_esperada"] == pytest.approx(valor, abs=1e-9)
    assert r["decisao"]["melhor_alternativa"] == max(eu, key=eu.get)


def test_s4_custo_de_equilibrio_inverte_a_recomendacao(resultados):
    dec = resultados["S4_prescritivo"]["decisao"]
    ce = scenarios.custo_equilibrio(dec, "bolsa_sim", "bolsa_nao")
    bruta = {n: a["utilidade_esperada"] + a["custo"] for n, a in dec["alternativas"].items()}
    # com custo ligeiramente abaixo do equilíbrio, bolsa_sim vence; acima, bolsa_nao vence
    assert bruta["bolsa_sim"] - (ce - 0.01) > bruta["bolsa_nao"]
    assert bruta["bolsa_sim"] - (ce + 0.01) < bruta["bolsa_nao"]


def test_custo_equilibrio_alternativa_inexistente(resultados):
    with pytest.raises(ErroInferencia):
        scenarios.custo_equilibrio(resultados["S4_prescritivo"]["decisao"], "x", "bolsa_nao")


def test_relatorio_markdown_e_codigo_de_saida(rede, modelo, tmp_path):
    res = scenarios.executar_todos(rede, modelo["cenarios"])
    assert scenarios.todas_expectativas_satisfeitas(res)
    texto = scenarios.relatorio_markdown(res)
    for cid in IDS:
        assert cid in texto
    assert "Custo de equilíbrio" in texto
    assert scenarios.main(["--saida", str(tmp_path / "r.md")]) == 0
    assert (tmp_path / "r.md").read_text(encoding="utf-8").startswith("# Resultados")