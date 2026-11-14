"""
Geração das CPTs (definidas MANUALMENTE pela equipe por regras de pontuação).

ESTADO ATUAL: PRELIMINAR. Todas as CPTs são uniformes, apenas para permitir o
desenvolvimento em paralelo. Pessoa A deve substituir por regras de domínio
documentadas em docs/justificativas.md.

CONTRATO DE SAÍDA (não alterar sem avisar B e C):
    gerar_todas_cpts() -> {
        "<Variavel>": {
            "variavel": str,
            "pais": [str, ...],                  # ordem = definicao.PAIS[variavel]
            "estados": [str, ...],               # ordem = definicao.ESTADOS[variavel]
            "linhas": [
                {"configuracao_pais": {pai: estado, ...},     # {} para raízes
                 "probabilidades": {estado: float, ...}},     # soma = 1 (tol. 1e-6)
                ... uma linha por configuração, em definicao.configuracoes_pais()
            ],
            "regra_geracao": str,                # descrição curta ou referência a docs/
        },
        ...
    }
Nenhuma probabilidade pode ser exatamente 0 ou 1 (piso planejado: 0,02).
"""
from __future__ import annotations

from . import definicao as d

PRELIMINAR = True


def _cpt_uniforme(variavel: str) -> dict:
    estados = d.ESTADOS[variavel]
    p = 1.0 / len(estados)
    return {
        "variavel": variavel,
        "pais": list(d.PAIS[variavel]),
        "estados": list(estados),
        "linhas": [
            {"configuracao_pais": cfg, "probabilidades": {e: p for e in estados}}
            for cfg in d.configuracoes_pais(variavel)
        ],
        "regra_geracao": "PRELIMINAR: distribuição uniforme (substituir pelas regras de A).",
    }


def gerar_todas_cpts() -> dict[str, dict]:
    return {v: _cpt_uniforme(v) for v in d.ordem_topologica()}