"""Motor de inferência probabilística e avaliação de cenários."""
from __future__ import annotations

import math
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork


class ErroInferencia(ValueError):
    """Erro levantado para consultas ou evidências incompatíveis com a rede."""


def _estados_da_rede(rede: DiscreteBayesianNetwork) -> dict[str, list[str]]:
    """Extrai o mapeamento {variavel: [estados]} a partir das CPDs da rede."""
    estados: dict[str, list[str]] = {}
    for cpd in rede.get_cpds():
        var = cpd.variable
        estados[var] = list(cpd.state_names[var])
    return estados


def validar_evidencias(
    rede: DiscreteBayesianNetwork,
    evidencias: dict[str, str] | None,
) -> dict[str, str]:
    """Valida se todas as variáveis e estados informados nas evidências existem na rede."""
    if not evidencias:
        return {}

    estados_rede = _estados_da_rede(rede)
    for var, estado in evidencias.items():
        if var not in estados_rede:
            raise ErroInferencia(
                f"Variável de evidência inexistente na rede: '{var}'. "
                f"Variáveis válidas: {sorted(estados_rede.keys())}"
            )
        if estado not in estados_rede[var]:
            raise ErroInferencia(
                f"Estado inválido '{estado}' para a variável '{var}'. "
                f"Estados válidos: {estados_rede[var]}"
            )
    return dict(evidencias)


def consultar_variavel(
    rede: DiscreteBayesianNetwork,
    variavel: str,
    evidencias: dict[str, str] | None = None,
) -> dict[str, float]:
    """
    Calcula a distribuição posterior marginal P(variavel | evidencias).
    Retorna um dicionário {estado: probabilidade} normalizado (soma = 1.0).
    """
    estados_rede = _estados_da_rede(rede)
    if variavel not in estados_rede:
        raise ErroInferencia(
            f"Variável de consulta inexistente na rede: '{variavel}'. "
            f"Variáveis válidas: {sorted(estados_rede.keys())}"
        )

    evid_validas = validar_evidencias(rede, evidencias)
    if variavel in evid_validas:
        raise ErroInferencia(
            f"A variável consultada '{variavel}' não pode constar simultaneamente nas evidências."
        )

    inferencia = VariableElimination(rede)
    resultado = inferencia.query(
        variables=[variavel],
        evidence=evid_validas if evid_validas else None,
        show_progress=False,
    )

    nomes_estados = list(resultado.state_names[variavel])
    valores = [float(v) for v in resultado.values]

    if any(math.isnan(v) or v < 0.0 for v in valores):
        raise ErroInferencia(
            f"Inferência produziu valores inválidos para '{variavel}' com evidências {evid_validas}."
        )

    soma = sum(valores)
    if soma <= 0.0:
        raise ErroInferencia(
            f"Distribuição degenerada (soma <= 0) para '{variavel}' com evidências {evid_validas}."
        )

    return {
        estado: valor / soma
        for estado, valor in zip(nomes_estados, valores)
    }


def consultar_marginais(
    rede: DiscreteBayesianNetwork,
    variaveis: list[str],
    evidencias: dict[str, str] | None = None,
) -> dict[str, dict[str, float]]:
    """Consulta a distribuição marginal posterior de múltiplas variáveis dado um conjunto de evidências."""
    if not variaveis:
        raise ErroInferencia("A lista de variáveis para consulta não pode ser vazia.")

    return {
        var: consultar_variavel(rede, var, evidencias)
        for var in variaveis
    }


def calcular_utilidade_esperada(
    distribuicao: dict[str, float],
    utilidades: dict[str, float],
    custo: float = 0.0,
) -> float:
    """
    Calcula a utilidade esperada líquida de uma alternativa de decisão:
        EU = sum(P(estado) * U(estado)) - custo
    """
    faltando = set(distribuicao.keys()) - set(utilidades.keys())
    if faltando:
        raise ErroInferencia(
            f"Utilidades não definidas para os estados: {sorted(faltando)}."
        )

    utilidade_bruta = sum(
        prob * utilidades[estado] for estado, prob in distribuicao.items()
    )
    return utilidade_bruta - float(custo)


def executar_cenario(
    rede: DiscreteBayesianNetwork,
    cenario: dict,
) -> dict:
    """
    Executa todas as variantes de um cenário definido no modelo.json, verifica
    suas expectativas qualitativas e calcula utilidades esperadas (se aplicável).
    """
    evid_base = dict(cenario.get("evidencias_base", {}))
    consultas = list(cenario["consultas"])

    resultados_variantes: dict[str, dict] = {}
    for variante in cenario["variantes"]:
        vid = variante["id"]
        evid_total = {**evid_base, **variante.get("evidencias_adicionais", {})}
        distribuicoes = consultar_marginais(rede, consultas, evid_total)
        resultados_variantes[vid] = {
            "descricao": variante.get("descricao", ""),
            "evidencias": evid_total,
            "distribuicoes": distribuicoes,
        }

    verificacoes: list[dict] = []
    for exp in cenario.get("expectativas", []):
        var_c = exp["consulta"]
        estado = exp["estado"]
        id_maior = exp["maior"]
        id_menor = exp["menor"]

        p_maior = resultados_variantes[id_maior]["distribuicoes"][var_c][estado]
        p_menor = resultados_variantes[id_menor]["distribuicoes"][var_c][estado]

        verificacoes.append({
            "consulta": var_c,
            "estado": estado,
            "maior_esperado": id_maior,
            "prob_maior": p_maior,
            "menor_esperado": id_menor,
            "prob_menor": p_menor,
            "satisfeita": p_maior > p_menor,
            "fundamentacao": exp.get("fundamentacao", ""),
        })

    resultado_decisao = None
    if "decisao" in cenario:
        dec = cenario["decisao"]
        var_alvo = dec["consulta"]
        utilidades = dec["utilidades"]
        avaliacoes_alt: dict[str, dict] = {}

        for nome_alt, cfg_alt in dec["alternativas"].items():
            vid = cfg_alt["variante"]
            custo = cfg_alt["custo"]
            dist = resultados_variantes[vid]["distribuicoes"][var_alvo]
            eu = calcular_utilidade_esperada(dist, utilidades, custo)
            avaliacoes_alt[nome_alt] = {
                "variante": vid,
                "custo": custo,
                "utilidade_esperada": eu,
            }

        melhor_alt = max(
            avaliacoes_alt,
            key=lambda k: avaliacoes_alt[k]["utilidade_esperada"],
        )
        resultado_decisao = {
            "consulta": var_alvo,
            "alternativas": avaliacoes_alt,
            "melhor_alternativa": melhor_alt,
        }

    return {
        "id": cenario["id"],
        "tipo_analise": cenario["tipo_analise"],
        "pergunta": cenario["pergunta"],
        "variantes": resultados_variantes,
        "verificacoes": verificacoes,
        "decisao": resultado_decisao,
    }