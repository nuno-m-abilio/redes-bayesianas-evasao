"""Inferência probabilística com validação de evidências."""
from __future__ import annotations

import difflib
import math

import numpy as np
from typing import TYPE_CHECKING

from .erros import EvidenciaInvalidaError

if TYPE_CHECKING:
    from pgmpy.models import DiscreteBayesianNetwork

TOLERANCIA_SOMA = 1e-6


def consultar(
    rede: "DiscreteBayesianNetwork",
    consultas: list[str],
    evidencias: dict[str, str],
) -> dict[str, dict[str, float]]:
    """
    P(consultas | evidencias) por VariableElimination.

    Retorna {variavel: {estado: probabilidade}} (nomes, não índices), normalizado
    (soma 1, tolerância 1e-6). Cada variável consultada recebe a sua distribuição
    marginal, calculada separadamente, e não a conjunta. `evidencias` pode ser vazio.
    Levanta EvidenciaInvalidaError se: consulta vazia; variável/estado inexistente;
    variável consultada também presente nas evidências; evidência de probabilidade zero.
    """
    from pgmpy.inference import VariableElimination

    estados = _estados_da_rede(rede)
    consultas = _validar_pedido(estados, consultas, evidencias)

    inferencia = VariableElimination(rede)
    resultado: dict[str, dict[str, float]] = {}
    for var in consultas:
        try:
            # Evidência de probabilidade zero gera 0/0 dentro do pgmpy. O resultado NaN
            # é tratado em _distribuicao, então o aviso do numpy não ajuda ninguém.
            with np.errstate(invalid="ignore", divide="ignore"):
                fator = inferencia.query(
                    variables=[var], evidence=dict(evidencias) or None, show_progress=False)
        except (ValueError, ZeroDivisionError) as erro:
            raise EvidenciaInvalidaError(
                f"Não foi possível inferir P({var} | {_fmt(evidencias)}): {erro}") from erro
        resultado[var] = _distribuicao(var, fator, estados[var], evidencias)
    return resultado


def comparar_evidencias(
    rede: "DiscreteBayesianNetwork",
    consulta: str,
    estado: str,
    conjuntos_de_evidencias: dict[str, dict[str, str]],
) -> dict[str, float]:
    """Devolve {rotulo: P(consulta=estado | evidencias do rótulo)} para cada conjunto."""
    estados = _estados_da_rede(rede)
    if consulta not in estados:
        raise EvidenciaInvalidaError(_msg_variavel_inexistente(consulta, estados))
    if estado not in estados[consulta]:
        raise EvidenciaInvalidaError(_msg_estado_inexistente(consulta, estado, estados))
    if not conjuntos_de_evidencias:
        raise EvidenciaInvalidaError("Nenhum conjunto de evidências foi informado para comparar.")

    return {
        rotulo: consultar(rede, [consulta], evidencias)[consulta][estado]
        for rotulo, evidencias in conjuntos_de_evidencias.items()
    }


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _estados_da_rede(rede: "DiscreteBayesianNetwork") -> dict[str, list[str]]:
    return {cpd.variable: list(cpd.state_names[cpd.variable]) for cpd in rede.get_cpds()}


def _fmt(evidencias: dict[str, str]) -> str:
    return ", ".join(f"{v}={e}" for v, e in evidencias.items()) or "sem evidências"


def _msg_variavel_inexistente(var: str, estados: dict[str, list[str]]) -> str:
    msg = f"A variável '{var}' não existe na rede."
    parecidas = difflib.get_close_matches(str(var), list(estados), n=1)
    if parecidas:
        msg += f" Você quis dizer '{parecidas[0]}'?"
    return msg + f" Variáveis disponíveis: {', '.join(sorted(estados))}."


def _msg_estado_inexistente(var: str, estado: str, estados: dict[str, list[str]]) -> str:
    msg = f"O estado '{estado}' não existe na variável '{var}'."
    parecidos = difflib.get_close_matches(str(estado), estados[var], n=1)
    if parecidos:
        msg += f" Você quis dizer '{parecidos[0]}'?"
    return msg + f" Estados válidos: {', '.join(estados[var])}."


def _validar_pedido(estados: dict[str, list[str]], consultas: list[str],
                    evidencias: dict[str, str]) -> list[str]:
    if not consultas:
        raise EvidenciaInvalidaError("Nenhuma variável foi consultada.")
    if isinstance(consultas, str):
        raise EvidenciaInvalidaError(
            "As consultas devem ser uma lista de nomes de variáveis, não uma string.")
    # Consultas repetidas não mudam o resultado, então são unificadas preservando a ordem.
    consultas = list(dict.fromkeys(consultas))

    for var in consultas:
        if var not in estados:
            raise EvidenciaInvalidaError(_msg_variavel_inexistente(var, estados))
    for var, estado in evidencias.items():
        if var not in estados:
            raise EvidenciaInvalidaError(_msg_variavel_inexistente(var, estados))
        if estado not in estados[var]:
            raise EvidenciaInvalidaError(_msg_estado_inexistente(var, estado, estados))
    repetidas = [var for var in consultas if var in evidencias]
    if repetidas:
        raise EvidenciaInvalidaError(
            f"As variáveis {repetidas} aparecem como consulta e como evidência.")
    return consultas


def _distribuicao(var: str, fator, estados_var: list[str],
                  evidencias: dict[str, str]) -> dict[str, float]:
    nomes = list(fator.state_names[var])
    valores = [float(v) for v in fator.values.ravel()]
    soma = math.fsum(valores)
    if not math.isfinite(soma) or soma <= 0.0:
        raise EvidenciaInvalidaError(
            f"A evidência ({_fmt(evidencias)}) tem probabilidade zero no modelo, "
            f"então P({var} | evidência) não está definida.")
    distribuicao = {nome: valor / soma for nome, valor in zip(nomes, valores)}
    # Devolve na ordem de estados da variável, não na ordem interna do pgmpy.
    return {estado: distribuicao[estado] for estado in estados_var}