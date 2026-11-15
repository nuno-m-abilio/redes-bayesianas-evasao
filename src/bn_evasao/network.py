"""Construção dinâmica da Rede Bayesiana (pgmpy) a partir do modelo.json."""
from __future__ import annotations

from itertools import product
from pathlib import Path

from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork

from .loader import CAMINHO_MODELO_PADRAO, carregar_modelo, validar_modelo_dict


def construir_rede_do_dicionario(dados: dict) -> DiscreteBayesianNetwork:
    """
    Constrói e valida uma DiscreteBayesianNetwork do pgmpy a partir do dicionário
    já estruturado no formato do modelo.json.
    """
    validar_modelo_dict(dados)

    estados_por_var: dict[str, list[str]] = {
        v["id"]: [e["id"] for e in v["estados"]] for v in dados["variaveis"]
    }

    rede = DiscreteBayesianNetwork()
    rede.add_nodes_from(estados_por_var.keys())
    rede.add_edges_from((arco["de"], arco["para"]) for arco in dados["estrutura"]["arcos"])

    cpds: list[TabularCPD] = []
    for cpt_info in dados["probabilidades"]:
        var = cpt_info["variavel"]
        pais = cpt_info["pais"]
        estados_var = estados_por_var[var]

        # Indexa cada linha pela tupla ordenada dos estados dos pais
        mapa_linhas: dict[tuple[str, ...], dict[str, float]] = {}
        for linha in cpt_info["linhas"]:
            chave = tuple(linha["configuracao_pais"][p] for p in pais)
            mapa_linhas[chave] = linha["probabilidades"]

        combinacoes_pais = (
            [()]
            if not pais
            else list(product(*(estados_por_var[p] for p in pais)))
        )

        # Matriz (num_estados_var x num_combinacoes_pais) exigida pelo TabularCPD
        matriz_valores = [
            [mapa_linhas[comb][estado] for comb in combinacoes_pais]
            for estado in estados_var
        ]

        state_names = {var: estados_var}
        for p in pais:
            state_names[p] = estados_por_var[p]

        cpd = TabularCPD(
            variable=var,
            variable_card=len(estados_var),
            values=matriz_valores,
            evidence=pais if pais else None,
            evidence_card=[len(estados_por_var[p]) for p in pais] if pais else None,
            state_names=state_names,
        )
        cpds.append(cpd)

    rede.add_cpds(*cpds)
    rede.check_model()
    return rede


def construir_rede_do_arquivo(
    caminho: str | Path = CAMINHO_MODELO_PADRAO,
) -> tuple[DiscreteBayesianNetwork, dict]:
    """Carrega o modelo.json do disco, constrói a rede pgmpy e retorna (rede, dados)."""
    dados = carregar_modelo(caminho)
    rede = construir_rede_do_dicionario(dados)
    return rede, dados