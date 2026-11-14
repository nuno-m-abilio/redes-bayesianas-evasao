"""Inferência probabilística com validação de evidências."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgmpy.models import DiscreteBayesianNetwork


def consultar(
    rede: "DiscreteBayesianNetwork",
    consultas: list[str],
    evidencias: dict[str, str],
) -> dict[str, dict[str, float]]:
    """
    P(consultas | evidencias) por VariableElimination.

    Retorna {variavel: {estado: probabilidade}} (nomes, não índices), normalizado
    (soma 1, tolerância 1e-6). `evidencias` pode ser vazio.
    Levanta EvidenciaInvalidaError se: consulta vazia; variável/estado inexistente;
    variável consultada também presente nas evidências.
    """
    raise NotImplementedError


def comparar_evidencias(
    rede: "DiscreteBayesianNetwork",
    consulta: str,
    estado: str,
    conjuntos_de_evidencias: dict[str, dict[str, str]],
) -> dict[str, float]:
    """Devolve {rotulo: P(consulta=estado | evidencias do rótulo)} para cada conjunto."""
    raise NotImplementedError