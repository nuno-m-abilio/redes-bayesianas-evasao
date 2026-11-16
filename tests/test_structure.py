"""Validação estrutural: variáveis, estados, arcos, pais e ausência de ciclos."""
import networkx as nx
import pytest

from bn_evasao import definicao as d


def test_minimo_de_variaveis(modelo):
    assert len(modelo["variaveis"]) >= 10
    assert len(modelo["variaveis"]) == len(d.VARIAVEIS) == 14


def test_todas_as_variaveis_e_estados_do_modelo_existem_na_rede(modelo, rede):
    for var in modelo["variaveis"]:
        assert var["id"] in rede.nodes()
        estados_json = [e["id"] for e in var["estados"]]
        assert estados_json == d.ESTADOS[var["id"]]
        assert list(rede.get_cpds(var["id"]).state_names[var["id"]]) == estados_json


def test_cada_arco_do_json_existe_na_rede(modelo, rede):
    arcos_json = {(a["de"], a["para"]) for a in modelo["estrutura"]["arcos"]}
    assert arcos_json == set(rede.edges())
    assert len(arcos_json) == 16


def test_pais_do_json_batem_com_a_rede(modelo, rede):
    for var, pais in modelo["estrutura"]["pais"].items():
        assert set(rede.get_parents(var)) == set(pais)


def test_rede_e_dag(rede):
    g = nx.DiGraph(rede.edges())
    g.add_nodes_from(rede.nodes())
    assert nx.is_directed_acyclic_graph(g)


def test_desfecho_tem_exatamente_tres_pais(rede):
    assert set(rede.get_parents("Desfecho")) == {"Desempenho_Sem2", "Pressao_Financeira", "Desemprego"}


def test_nenhum_no_com_mais_de_tres_pais(rede):
    assert max(len(rede.get_parents(v)) for v in rede.nodes()) <= 3


def test_desfecho_e_folha_e_tem_tres_estados(rede):
    folhas = [v for v in rede.nodes() if not list(rede.get_children(v))]
    assert "Desfecho" in folhas
    assert set(rede.get_cpds("Desfecho").state_names["Desfecho"]) == {"Dropout", "Enrolled", "Graduate"}


def test_raizes_esperadas(rede):
    raizes = {v for v in rede.nodes() if not rede.get_parents(v)}
    assert raizes == {"Area_Curso", "Faixa_Etaria", "Escolaridade_Pais", "Bolsista",
                      "Deslocado", "Nota_Admissao", "Desemprego"}


def test_pressao_financeira_e_latente(modelo):
    por_id = {v["id"]: v for v in modelo["variaveis"]}
    assert por_id["Pressao_Financeira"]["observavel"] is False
    assert por_id["Pressao_Financeira"]["tipo"] == "latente"
    assert all(v["observavel"] for k, v in por_id.items() if k != "Pressao_Financeira")


def test_pressao_financeira_nao_esta_no_dataset_discretizado():
    from pathlib import Path
    import csv
    caminho = Path(__file__).resolve().parents[1] / "data" / "processed" / "dados_discretizados.csv"
    if not caminho.exists():
        pytest.skip("dados_discretizados.csv ausente (rode scripts/discretizar_dataset.py)")
    with caminho.open(encoding="utf-8") as f:
        cabecalho = next(csv.reader(f))
    assert "Pressao_Financeira" not in cabecalho
    assert set(cabecalho) == set(d.VARIAVEIS_OBSERVAVEIS)