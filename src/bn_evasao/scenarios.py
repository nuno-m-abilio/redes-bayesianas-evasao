"""Execução, análise de sensibilidade e relatório dos cenários de utilização.

A avaliação de cada cenário (inferência, expectativas e utilidade esperada) é feita por
`inference.executar_cenario`. Este módulo orquestra os 4 cenários, calcula o custo de
equilíbrio da decisão (S4) e gera um relatório em Markdown a partir de resultados
EFETIVAMENTE calculados pela rede (nada é pré-calculado).

Uso:
    python -m bn_evasao.scenarios [--modelo modelo.json] [--saida outputs/cenarios/resultados.md]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .inference import ErroInferencia, executar_cenario
from .loader import CAMINHO_MODELO_PADRAO
from .network import construir_rede_do_arquivo


def executar_todos(rede, cenarios: list[dict]) -> list[dict]:
    """Executa todos os cenários e devolve a lista de resultados (mesma ordem)."""
    return [executar_cenario(rede, c) for c in cenarios]


def todas_expectativas_satisfeitas(resultados: list[dict]) -> bool:
    return all(v["satisfeita"] for r in resultados for v in r["verificacoes"])


def custo_equilibrio(decisao: dict, alternativa: str, referencia: str) -> float:
    """
    Custo máximo de `alternativa` para que ela continue sendo preferida a `referencia`
    (mantido o custo de `referencia`): EU_bruta(alt) - EU_bruta(ref) + custo(ref).
    Se o custo real exceder este valor, a recomendação se inverte.
    """
    alts = decisao["alternativas"]
    for nome in (alternativa, referencia):
        if nome not in alts:
            raise ErroInferencia(f"Alternativa inexistente na decisão: '{nome}'.")
    bruta = {n: a["utilidade_esperada"] + a["custo"] for n, a in alts.items()}
    return bruta[alternativa] - bruta[referencia] + alts[referencia]["custo"]


def relatorio_markdown(resultados: list[dict]) -> str:
    """Relatório legível (valores calculados pela rede) para apoiar a interpretação."""
    linhas = ["# Resultados dos cenários (gerados pela execução da rede)", ""]
    for r in resultados:
        linhas += [f"## {r['id']} ({r['tipo_analise']})", f"**Pergunta:** {r['pergunta']}", ""]
        for vid, info in r["variantes"].items():
            linhas.append(f"- **{vid}** — {info['descricao']}  ")
            linhas.append(f"  Evidências: `{info['evidencias'] or 'nenhuma (a priori)'}`")
            for var, dist in info["distribuicoes"].items():
                resumo = ", ".join(f"{e}={p:.3f}" for e, p in dist.items())
                linhas.append(f"  - P({var}): {resumo}")
        if r["verificacoes"]:
            linhas += ["", "Expectativas qualitativas:"]
            for v in r["verificacoes"]:
                status = "OK" if v["satisfeita"] else "FALHOU"
                linhas.append(
                    f"- [{status}] P({v['consulta']}={v['estado']}): {v['maior_esperado']} "
                    f"({v['prob_maior']:.3f}) > {v['menor_esperado']} ({v['prob_menor']:.3f})")
        if r["decisao"]:
            dec = r["decisao"]
            linhas += ["", "Decisão (utilidade esperada líquida):"]
            for nome, a in dec["alternativas"].items():
                linhas.append(f"- {nome}: EU = {a['utilidade_esperada']:.2f} (custo {a['custo']})")
            linhas.append(f"- **Melhor alternativa:** {dec['melhor_alternativa']}")
            nomes = list(dec["alternativas"])
            if len(nomes) == 2:
                alt, ref = nomes[0], nomes[1]
                linhas.append(
                    f"- Custo de equilíbrio de `{alt}` frente a `{ref}`: "
                    f"{custo_equilibrio(dec, alt, ref):.2f} (acima disso a recomendação se inverte)")
        linhas.append("")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", type=Path, default=CAMINHO_MODELO_PADRAO)
    ap.add_argument("--saida", type=Path, default=None)
    args = ap.parse_args(argv)
    rede, dados = construir_rede_do_arquivo(args.modelo)
    resultados = executar_todos(rede, dados["cenarios"])
    texto = relatorio_markdown(resultados)
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(texto, encoding="utf-8")
        print(f"Relatório salvo em: {args.saida}")
    else:
        print(texto)
    return 0 if todas_expectativas_satisfeitas(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())