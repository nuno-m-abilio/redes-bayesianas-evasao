"""Validação das probabilidades (CPTs) do modelo.json."""
import math

import pytest

from bn_evasao import definicao as d

TOL = 1e-6
PISO = 0.02
VARIAVEIS = list(d.VARIAVEIS)


def _cpts(modelo):
    return {c["variavel"]: c for c in modelo["probabilidades"]}


def test_uma_cpt_por_variavel(modelo):
    ids = [c["variavel"] for c in modelo["probabilidades"]]
    assert sorted(ids) == sorted(VARIAVEIS) and len(ids) == len(set(ids))


@pytest.mark.parametrize("variavel", VARIAVEIS)
def test_valores_no_intervalo_e_soma_um(modelo, variavel):
    for linha in _cpts(modelo)[variavel]["linhas"]:
        probs = linha["probabilidades"]
        assert all(0.0 <= p <= 1.0 for p in probs.values())
        assert abs(sum(probs.values()) - 1.0) <= TOL, linha["configuracao_pais"]


@pytest.mark.parametrize("variavel", VARIAVEIS)
def test_cpt_completa_sem_duplicatas(modelo, variavel):
    cpt = _cpts(modelo)[variavel]
    esperado = math.prod(len(d.ESTADOS[p]) for p in d.PAIS[variavel])
    configs = [tuple(l["configuracao_pais"][p] for p in cpt["pais"]) for l in cpt["linhas"]]
    assert len(configs) == esperado == len(set(configs))
    assert [l["configuracao_pais"] for l in cpt["linhas"]] == d.configuracoes_pais(variavel)


@pytest.mark.parametrize("variavel", VARIAVEIS)
def test_nenhuma_probabilidade_zero_ou_um(modelo, variavel):
    for linha in _cpts(modelo)[variavel]["linhas"]:
        assert all(PISO - 1e-9 <= p < 1.0 for p in linha["probabilidades"].values())


def test_numero_de_configuracoes_por_variavel(modelo):
    esperado = {"Turno": 18, "Pressao_Financeira": 12, "Desempenho_Sem1": 54,
                "Desempenho_Sem2": 12, "Desfecho": 12, "Devedor": 2, "Mensalidade_Em_Dia": 2}
    cpts = _cpts(modelo)
    for var, n in esperado.items():
        assert len(cpts[var]["linhas"]) == n, var


# (variável, pai, estados do pai do MELHOR para o PIOR, estado "ruim" do filho)
# Propriedade de domínio declarada em docs/justificativas.md: piorar um pai, mantendo os
# demais fixos, aumenta a probabilidade do estado ruim do filho.
MONOTONICIDADE = [
    ("Desfecho", "Desempenho_Sem2", ["Alto", "Medio", "Baixo"], "Dropout"),
    ("Desfecho", "Pressao_Financeira", ["Baixa", "Alta"], "Dropout"),
    ("Desfecho", "Desemprego", ["Baixo", "Alto"], "Dropout"),
    ("Desempenho_Sem2", "Desempenho_Sem1", ["Alto", "Medio", "Baixo"], "Baixo"),
    ("Desempenho_Sem2", "Pressao_Financeira", ["Baixa", "Alta"], "Baixo"),
    ("Desempenho_Sem2", "Turno", ["Diurno", "Noturno"], "Baixo"),
    ("Desempenho_Sem1", "Nota_Admissao", ["Alta", "Media", "Baixa"], "Baixo"),
    ("Desempenho_Sem1", "Faixa_Etaria", ["Jovem", "Adulto", "Maduro"], "Baixo"),
    ("Pressao_Financeira", "Bolsista", ["Sim", "Nao"], "Alta"),
    ("Pressao_Financeira", "Deslocado", ["Nao", "Sim"], "Alta"),
    ("Pressao_Financeira", "Escolaridade_Pais", ["Alta", "Media", "Baixa"], "Alta"),
    ("Devedor", "Pressao_Financeira", ["Baixa", "Alta"], "Sim"),
    ("Mensalidade_Em_Dia", "Pressao_Financeira", ["Baixa", "Alta"], "Nao"),
    ("Turno", "Faixa_Etaria", ["Jovem", "Adulto", "Maduro"], "Noturno"),
]


@pytest.mark.parametrize("filho,pai,ordem,ruim", MONOTONICIDADE)
def test_monotonicidade(modelo, filho, pai, ordem, ruim):
    cpt = _cpts(modelo)[filho]
    grupos = {}  # demais pais fixos -> {estado_do_pai: P(ruim)}
    for linha in cpt["linhas"]:
        cfg = linha["configuracao_pais"]
        chave = tuple(sorted((k, v) for k, v in cfg.items() if k != pai))
        grupos.setdefault(chave, {})[cfg[pai]] = linha["probabilidades"][ruim]
    for chave, por_estado in grupos.items():
        seq = [por_estado[e] for e in ordem]
        assert all(a < b for a, b in zip(seq, seq[1:])), f"{filho}/{pai} {dict(chave)}: {seq}"


def test_prob_graduate_decresce_com_desempenho_pior(modelo):
    cpt = _cpts(modelo)["Desfecho"]
    por_sem2 = {}
    for l in cpt["linhas"]:
        cfg = l["configuracao_pais"]
        if cfg["Pressao_Financeira"] == "Baixa" and cfg["Desemprego"] == "Baixo":
            por_sem2[cfg["Desempenho_Sem2"]] = l["probabilidades"]["Graduate"]
    assert por_sem2["Alto"] > por_sem2["Medio"] > por_sem2["Baixo"]