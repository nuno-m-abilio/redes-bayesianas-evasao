"""Construção da rede pgmpy a partir do modelo.json."""
from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import networkx as nx

from .erros import CPTInvalidaError, ModeloInvalidoError
from .loader import validar_modelo

if TYPE_CHECKING:  # evita importar pgmpy no momento do import do módulo
    from pgmpy.models import DiscreteBayesianNetwork


def construir_rede(modelo: dict[str, Any]) -> "DiscreteBayesianNetwork":
    """
    Constrói a rede a partir do dict do modelo.json.

    Valida o modelo, confere o DAG, usa state_names explícitos e monta cada
    TabularCPD por dicionário, nunca por posição. As colunas seguem a ordem do
    campo "pais" da CPT, com o último pai variando mais rápido, que é a
    convenção do pgmpy. Termina com check_model().
    Levanta CPTInvalidaError ou ModeloInvalidoError.
    """
    from pgmpy.factors.discrete import TabularCPD
    from pgmpy.models import DiscreteBayesianNetwork

    # Defesa em profundidade: quem chama pode ter alterado o dict depois de carregá-lo.
    validar_modelo(modelo)

    estados = {v["id"]: [e["id"] for e in v["estados"]] for v in modelo["variaveis"]}
    arcos = [(a["de"], a["para"]) for a in modelo["estrutura"]["arcos"]]

    grafo = nx.DiGraph(arcos)
    grafo.add_nodes_from(estados)
    if not nx.is_directed_acyclic_graph(grafo):
        ciclo = " → ".join(str(a) for a, _ in nx.find_cycle(grafo))
        raise ModeloInvalidoError(f"O grafo possui ciclo envolvendo {ciclo}.")

    rede = DiscreteBayesianNetwork()
    rede.add_nodes_from(estados)
    rede.add_edges_from(arcos)

    cpds = [_montar_cpd(cpt, estados, TabularCPD) for cpt in modelo["probabilidades"]]
    rede.add_cpds(*cpds)

    try:
        rede.check_model()
    except ValueError as erro:
        raise CPTInvalidaError(f"O pgmpy recusou a rede: {erro}") from erro
    return rede


def _montar_cpd(cpt: dict[str, Any], estados: dict[str, list[str]], TabularCPD: Any) -> Any:
    var = cpt["variavel"]
    pais = list(cpt["pais"])
    estados_var = estados[var]

    # Cada linha do JSON é localizada pela combinação de estados dos pais.
    por_config = {
        tuple(linha["configuracao_pais"][pai] for pai in pais): linha["probabilidades"]
        for linha in cpt["linhas"]
    }

    # Produto cartesiano na ordem dos pais, último pai variando mais rápido.
    combinacoes = list(itertools.product(*(estados[pai] for pai in pais)))
    valores = [[por_config[comb][estado] for comb in combinacoes] for estado in estados_var]

    state_names = {var: estados_var, **{pai: estados[pai] for pai in pais}}
    return TabularCPD(
        variable=var,
        variable_card=len(estados_var),
        values=valores,
        evidence=pais or None,
        evidence_card=[len(estados[pai]) for pai in pais] or None,
        state_names=state_names,
    )