"""Testes do contrato do Dia 1: definição da rede, formato das CPTs e cenários."""
import importlib.util
import json
import math
from pathlib import Path

import networkx as nx
import pytest

from bn_evasao import cpt_rules
from bn_evasao import definicao as d

RAIZ = Path(__file__).resolve().parents[1]
TOL = 1e-6


def _carregar_script_discretizacao():
    spec = importlib.util.spec_from_file_location(
        "discretizar_dataset", RAIZ / "scripts" / "discretizar_dataset.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_numero_de_variaveis_e_arcos():
    assert len(d.VARIAVEIS) >= 10
    assert len(d.VARIAVEIS) == 14
    assert len(d.ARCOS) == 16


def test_grafo_e_dag():
    g = nx.DiGraph([(a, b) for a, b, _ in d.ARCOS])
    g.add_nodes_from(d.VARIAVEIS)
    assert nx.is_directed_acyclic_graph(g)


def test_no_maximo_3_pais():
    assert all(len(p) <= 3 for p in d.PAIS.values())


def test_desfecho_tem_exatamente_os_tres_pais():
    assert set(d.PAIS["Desfecho"]) == {"Desempenho_Sem2", "Pressao_Financeira", "Desemprego"}


def test_estados_unicos_e_minimo_dois():
    for v, estados in d.ESTADOS.items():
        assert len(estados) >= 2, v
        assert len(set(estados)) == len(estados), v


def test_pressao_financeira_e_a_unica_latente():
    latentes = [v for v, i in d.VARIAVEIS.items() if not i["observavel"]]
    assert latentes == ["Pressao_Financeira"]


def test_estados_batem_com_script_de_discretizacao():
    disc = _carregar_script_discretizacao()
    assert set(disc.ESTADOS) == set(d.VARIAVEIS_OBSERVAVEIS)
    for v, estados in disc.ESTADOS.items():
        assert estados == d.ESTADOS[v], f"{v}: estados divergem do script de discretização"


@pytest.mark.parametrize("variavel", list(d.VARIAVEIS))
def test_numero_de_configuracoes_de_pais(variavel):
    esperado = math.prod(len(d.ESTADOS[p]) for p in d.PAIS[variavel])
    assert len(d.configuracoes_pais(variavel)) == esperado


def test_configuracoes_ordem_ultimo_pai_varia_mais_rapido():
    cfgs = d.configuracoes_pais("Turno")  # pais: Area_Curso, Faixa_Etaria
    assert cfgs[0] == {"Area_Curso": "Saude", "Faixa_Etaria": "Jovem"}
    assert cfgs[1] == {"Area_Curso": "Saude", "Faixa_Etaria": "Adulto"}
    assert cfgs[3] == {"Area_Curso": "Ciencias_Sociais", "Faixa_Etaria": "Jovem"}


@pytest.mark.parametrize("variavel", list(d.VARIAVEIS))
def test_cpts_seguem_o_contrato_de_formato(variavel):
    cpt = cpt_rules.gerar_todas_cpts()[variavel]
    assert cpt["variavel"] == variavel
    assert cpt["pais"] == d.PAIS[variavel]
    assert cpt["estados"] == d.ESTADOS[variavel]
    assert [l["configuracao_pais"] for l in cpt["linhas"]] == d.configuracoes_pais(variavel)
    for linha in cpt["linhas"]:
        probs = linha["probabilidades"]
        assert set(probs) == set(d.ESTADOS[variavel])
        assert all(0.0 <= p <= 1.0 for p in probs.values())
        assert abs(sum(probs.values()) - 1.0) <= TOL


def test_cenarios_referenciam_apenas_elementos_validos():
    cenarios = json.loads((RAIZ / "scenarios" / "cenarios.json").read_text(encoding="utf-8"))["cenarios"]
    assert len(cenarios) == 4
    ids = [c["id"] for c in cenarios]
    assert len(set(ids)) == 4

    def checar_evidencias(ev, contexto):
        for var, est in ev.items():
            assert var in d.VARIAVEIS, f"{contexto}: variável inexistente {var}"
            assert est in d.ESTADOS[var], f"{contexto}: estado inexistente {var}={est}"

    for c in cenarios:
        checar_evidencias(c["evidencias_base"], c["id"])
        variantes = {v["id"]: {**c["evidencias_base"], **v["evidencias_adicionais"]} for v in c["variantes"]}
        for vid, ev in variantes.items():
            checar_evidencias(ev, f"{c['id']}/{vid}")
            for q in c["consultas"]:
                assert q in d.VARIAVEIS
                assert q not in ev, f"{c['id']}/{vid}: consulta {q} também está nas evidências"
        for e in c["expectativas"]:
            assert e["consulta"] in c["consultas"]
            assert e["estado"] in d.ESTADOS[e["consulta"]]
            for chave in ("maior", "menor", "variante"):
                if chave in e:
                    assert e[chave] in variantes
            for vid in e.get("variantes", []):
                assert vid in variantes
        if "decisao" in c:
            for alt in c["decisao"]["alternativas"].values():
                assert alt["variante"] in variantes