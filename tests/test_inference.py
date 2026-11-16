"""Validação das consultas. A verdade vem de cálculos independentes (à mão e força bruta),
nunca da própria saída do pgmpy."""
import itertools

import numpy as np
import pytest

from bn_evasao import definicao as d
from bn_evasao.inference import (ErroInferencia, calcular_utilidade_esperada, consultar_marginais,
                                 consultar_variavel, validar_evidencias)

TOL = 1e-6


# ---------------- oráculo independente: distribuição conjunta por força bruta ----------------
def _conjunta(modelo):
    """Tensor da conjunta P(X1..X14) montado só a partir do JSON (sem pgmpy)."""
    ordem = [v["id"] for v in modelo["variaveis"]]
    estados = {v["id"]: [e["id"] for e in v["estados"]] for v in modelo["variaveis"]}
    idx = {v: i for i, v in enumerate(ordem)}
    conjunta = np.ones([1] * len(ordem))
    for cpt in modelo["probabilidades"]:
        var, pais = cpt["variavel"], cpt["pais"]
        eixos = [idx[p] for p in pais] + [idx[var]]
        arr = np.zeros([len(estados[p]) for p in pais] + [len(estados[var])])
        for linha in cpt["linhas"]:
            pos = tuple(estados[p].index(linha["configuracao_pais"][p]) for p in pais)
            for e, prob in linha["probabilidades"].items():
                arr[pos + (estados[var].index(e),)] = prob
        arr = arr.transpose(np.argsort(eixos))
        forma = [len(estados[v]) if idx[v] in eixos else 1 for v in ordem]
        conjunta = conjunta * arr.reshape(forma)
    return conjunta, ordem, estados, idx


def _posterior_bruta(modelo, variavel, evidencias):
    conjunta, ordem, estados, idx = _conjunta(modelo)
    fatia = [slice(None)] * len(ordem)
    for v, e in evidencias.items():
        fatia[idx[v]] = estados[v].index(e)
    sub = conjunta[tuple(fatia)]
    restantes = [v for v in ordem if v not in evidencias]
    soma_outros = tuple(i for i, v in enumerate(restantes) if v != variavel)
    marginal = sub.sum(axis=soma_outros).ravel()
    return dict(zip(estados[variavel], marginal / marginal.sum()))


def test_conjunta_soma_um(modelo):
    conjunta, *_ = _conjunta(modelo)
    assert conjunta.sum() == pytest.approx(1.0, abs=1e-9)


EVIDENCIAS = [
    {},
    {"Desfecho": "Dropout"},
    {"Turno": "Noturno", "Faixa_Etaria": "Maduro", "Bolsista": "Nao"},
    {"Desempenho_Sem1": "Baixo", "Devedor": "Sim"},
    {"Mensalidade_Em_Dia": "Nao", "Desemprego": "Alto", "Area_Curso": "Saude"},
]


@pytest.mark.parametrize("evidencias", EVIDENCIAS)
@pytest.mark.parametrize("consulta", ["Desfecho", "Pressao_Financeira", "Desempenho_Sem2"])
def test_inferencia_bate_com_forca_bruta(modelo, rede, consulta, evidencias):
    if consulta in evidencias:
        pytest.skip("consulta presente nas evidências")
    obtido = consultar_variavel(rede, consulta, evidencias)
    esperado = _posterior_bruta(modelo, consulta, evidencias)
    for estado, p in esperado.items():
        assert obtido[estado] == pytest.approx(p, abs=1e-6)


# ---------------- propriedades gerais ----------------
@pytest.mark.parametrize("evidencias", EVIDENCIAS)
def test_resultados_normalizados_para_todas_as_variaveis(rede, evidencias):
    for var in d.VARIAVEIS:
        if var in evidencias:
            continue
        dist = consultar_variavel(rede, var, evidencias)
        assert set(dist) == set(d.ESTADOS[var])
        assert sum(dist.values()) == pytest.approx(1.0, abs=TOL)
        assert all(0.0 <= p <= 1.0 for p in dist.values())


def test_ordem_das_evidencias_nao_altera_o_resultado(rede):
    base = {"Turno": "Noturno", "Faixa_Etaria": "Maduro", "Bolsista": "Nao", "Desemprego": "Alto"}
    ref = consultar_variavel(rede, "Desfecho", base)
    for perm in itertools.permutations(base.items()):
        dist = consultar_variavel(rede, "Desfecho", dict(perm))
        for e in ref:
            assert dist[e] == pytest.approx(ref[e], abs=1e-9)


def test_multiplas_consultas_equivalem_a_consultas_individuais(rede):
    ev = {"Bolsista": "Nao"}
    juntas = consultar_marginais(rede, ["Desfecho", "Devedor"], ev)
    assert juntas["Desfecho"] == consultar_variavel(rede, "Desfecho", ev)
    assert juntas["Devedor"] == consultar_variavel(rede, "Devedor", ev)


def test_evidencia_vazia_ou_none_equivale_a_priori(rede):
    assert consultar_variavel(rede, "Desfecho", None) == consultar_variavel(rede, "Desfecho", {})
    assert validar_evidencias(rede, None) == {}


# ---------------- independências condicionais (d-separação) ----------------
def test_devedor_e_independente_de_bolsista_dado_pressao(rede):
    """Bolsista -> Pressao -> Devedor: observar Pressao bloqueia o caminho."""
    a = consultar_variavel(rede, "Bolsista", {"Pressao_Financeira": "Alta"})
    b = consultar_variavel(rede, "Bolsista", {"Pressao_Financeira": "Alta", "Devedor": "Sim"})
    for e in a:
        assert b[e] == pytest.approx(a[e], abs=1e-9)


def test_devedor_e_independente_do_desfecho_dado_pressao(rede):
    a = consultar_variavel(rede, "Desfecho", {"Pressao_Financeira": "Baixa"})
    b = consultar_variavel(rede, "Desfecho", {"Pressao_Financeira": "Baixa", "Devedor": "Sim"})
    for e in a:
        assert b[e] == pytest.approx(a[e], abs=1e-9)


def test_devedor_informa_sobre_desfecho_quando_pressao_nao_e_observada(rede):
    """Sem observar Pressao o caminho está aberto: a evidência TEM de mudar a posterior."""
    a = consultar_variavel(rede, "Desfecho")
    b = consultar_variavel(rede, "Desfecho", {"Devedor": "Sim"})
    assert b["Dropout"] > a["Dropout"]


def test_raizes_marginalmente_independentes(rede):
    a = consultar_variavel(rede, "Bolsista")
    b = consultar_variavel(rede, "Bolsista", {"Faixa_Etaria": "Maduro", "Area_Curso": "Saude"})
    for e in a:
        assert b[e] == pytest.approx(a[e], abs=1e-9)


def test_explaining_away_bolsista_e_escolaridade(rede):
    """Bolsista e Escolaridade_Pais são pais de Pressao_Financeira. Dado Pressao=Alta, ter bolsa
    deixa de ser uma explicação possível da pressão, então a escolaridade baixa se torna
    MAIS provável (explaining away)."""
    com_bolsa = consultar_variavel(rede, "Escolaridade_Pais", {"Pressao_Financeira": "Alta", "Bolsista": "Sim"})
    sem_bolsa = consultar_variavel(rede, "Escolaridade_Pais", {"Pressao_Financeira": "Alta", "Bolsista": "Nao"})
    assert com_bolsa["Baixa"] > sem_bolsa["Baixa"]


# ---------------- rede miniatura contra cálculo manual ----------------
def test_mini_marginal_de_b(rede_mini):
    # P(b1) = 0.3*0.1 + 0.7*0.8 = 0.59
    dist = consultar_variavel(rede_mini, "B")
    assert dist["b1"] == pytest.approx(0.59, abs=1e-9)
    assert dist["b0"] == pytest.approx(0.41, abs=1e-9)


def test_mini_bayes_posterior_de_a_dado_b(rede_mini):
    # P(a1|b1) = 0.7*0.8 / 0.59
    dist = consultar_variavel(rede_mini, "A", {"B": "b1"})
    assert dist["a1"] == pytest.approx(0.56 / 0.59, abs=1e-9)


def test_mini_filho_irmao_dado_evidencia(rede_mini):
    # P(c1|b1) = [0.3*0.1*0.5 + 0.7*0.8*0.9] / 0.59
    dist = consultar_variavel(rede_mini, "C", {"B": "b1"})
    assert dist["c1"] == pytest.approx((0.015 + 0.504) / 0.59, abs=1e-9)


def test_mini_independencia_condicional(rede_mini):
    # B ⟂ C | A
    a = consultar_variavel(rede_mini, "C", {"A": "a1"})
    b = consultar_variavel(rede_mini, "C", {"A": "a1", "B": "b0"})
    assert a["c1"] == pytest.approx(b["c1"], abs=1e-9) == pytest.approx(0.9, abs=1e-9)


# ---------------- casos inválidos ----------------
def test_estado_inexistente(rede):
    with pytest.raises(ErroInferencia, match="Estado inválido"):
        consultar_variavel(rede, "Desfecho", {"Turno": "Madrugada"})


def test_variavel_de_evidencia_inexistente(rede):
    with pytest.raises(ErroInferencia, match="Variável de evidência inexistente"):
        consultar_variavel(rede, "Desfecho", {"Cor_Do_Cabelo": "Preto"})


def test_variavel_de_consulta_inexistente(rede):
    with pytest.raises(ErroInferencia, match="consulta inexistente"):
        consultar_variavel(rede, "Inexistente")


def test_consulta_nas_evidencias(rede):
    with pytest.raises(ErroInferencia, match="não pode constar"):
        consultar_variavel(rede, "Desfecho", {"Desfecho": "Dropout"})


def test_lista_de_consultas_vazia(rede):
    with pytest.raises(ErroInferencia, match="não pode ser vazia"):
        consultar_marginais(rede, [], {})


def test_estado_case_sensitive(rede):
    with pytest.raises(ErroInferencia):
        consultar_variavel(rede, "Desfecho", {"Turno": "noturno"})


# ---------------- utilidade esperada ----------------
def test_utilidade_esperada_calculo_manual():
    dist = {"Graduate": 0.5, "Enrolled": 0.2, "Dropout": 0.3}
    util = {"Graduate": 100, "Enrolled": 20, "Dropout": -100}
    # 50 + 4 - 30 = 24 ; menos custo 10
    assert calcular_utilidade_esperada(dist, util) == pytest.approx(24.0)
    assert calcular_utilidade_esperada(dist, util, custo=10) == pytest.approx(14.0)


def test_utilidade_com_estado_sem_utilidade():
    with pytest.raises(ErroInferencia, match="Utilidades não definidas"):
        calcular_utilidade_esperada({"A": 0.5, "B": 0.5}, {"A": 1})