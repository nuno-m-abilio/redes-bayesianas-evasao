"""Construção da rede pgmpy a partir do modelo.json."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # evita importar pgmpy no momento do import do módulo
    from pgmpy.models import DiscreteBayesianNetwork


def construir_rede(modelo: dict) -> "DiscreteBayesianNetwork":
    """
    Constrói a rede a partir do dict do modelo.json.

    Deve: verificar DAG; usar state_names explícitos; montar cada TabularCPD por
    DICIONÁRIO (nunca por posição), na ordem de definicao.configuracoes_pais
    (último pai varia mais rápido); chamar check_model().
    Levanta CPTInvalidaError / ModeloInvalidoError.
    """
    raise NotImplementedError