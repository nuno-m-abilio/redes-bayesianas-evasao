"""Execução dos cenários de utilização definidos em scenarios/cenarios.json."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgmpy.models import DiscreteBayesianNetwork


def executar_cenario(rede: "DiscreteBayesianNetwork", cenario: dict) -> dict:
    """
    Executa todas as variantes do cenário (evidencias_base + evidencias_adicionais)
    e avalia as expectativas (tipos: comparacao, faixa, igual, decisao).

    Retorna:
        {"id": str,
         "resultados": {variante_id: {variavel: {estado: prob}}},
         "expectativas": [{"expectativa": dict, "aprovada": bool, "detalhe": str}],
         "decisao": {...} ou None}
    Levanta CenarioInvalidoError se algo referenciado não existir.
    """
    raise NotImplementedError


def executar_todos(rede: "DiscreteBayesianNetwork", cenarios: list[dict]) -> list[dict]:
    raise NotImplementedError


def utilidade_esperada(
    distribuicao_desfecho: dict[str, float],
    utilidades: dict[str, float],
    custo: float = 0.0,
) -> float:
    """sum_e P(e) * U(e) - custo."""
    raise NotImplementedError