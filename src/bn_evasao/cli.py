"""Interface de Linha de Comando (CLI) para consultas e execução da Rede Bayesiana."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .inference import ErroInferencia, consultar_marginais, executar_cenario
from .loader import CAMINHO_MODELO_PADRAO, ErroValidacaoModelo
from .network import construir_rede_do_arquivo
from .visualize import SAIDA_DOT_PADRAO, SAIDA_PNG_PADRAO, gerar_imagem_rede


def _parsear_evidencias(pares: list[str]) -> dict[str, str]:
    evidencias: dict[str, str] = {}
    for item in pares:
        if "=" not in item:
            raise ErroInferencia(
                f"Formato inválido de evidência: '{item}'. Use VARIAVEL=ESTADO."
            )
        var, estado = item.split("=", 1)
        var, estado = var.strip(), estado.strip()
        if not var or not estado:
            raise ErroInferencia(
                f"Evidência incompleta: '{item}'. Use VARIAVEL=ESTADO."
            )
        evidencias[var] = estado
    return evidencias


def _cmd_validar(args: argparse.Namespace) -> int:
    rede, dados = construir_rede_do_arquivo(args.modelo)
    print(f"Modelo válido: {args.modelo}")
    print(f"- Variáveis: {len(rede.nodes())}")
    print(f"- Arcos: {len(rede.edges())}")
    print(f"- Cenários: {len(dados['cenarios'])}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    _, dados = construir_rede_do_arquivo(args.modelo)
    print(f"Tema: {dados['projeto']['tema']}\n")
    for var in dados["variaveis"]:
        estados = ", ".join(e["id"] for e in var["estados"])
        obs = "observável" if var.get("observavel", True) else "LATENTE"
        print(f"- {var['id']} [{var.get('tipo', '-')}, {obs}]: {estados}")
    return 0


def _cmd_consultar(args: argparse.Namespace) -> int:
    rede, _ = construir_rede_do_arquivo(args.modelo)
    evidencias = _parsear_evidencias(args.evidencia or [])
    resultados = consultar_marginais(rede, args.consulta, evidencias)

    print("Evidências informadas:", evidencias if evidencias else "(nenhuma / a priori)")
    for var, dist in resultados.items():
        print(f"\nDistribuição posterior de '{var}':")
        for estado, prob in dist.items():
            print(f"  {estado:<15} {prob:.4f} ({prob * 100:5.1f}%)")
    return 0


def _cmd_cenarios(args: argparse.Namespace) -> int:
    rede, dados = construir_rede_do_arquivo(args.modelo)
    cenarios = dados["cenarios"]
    if args.id:
        cenarios = [c for c in cenarios if c["id"] == args.id]
        if not cenarios:
            raise ErroInferencia(f"Cenário não encontrado: '{args.id}'.")

    for cen in cenarios:
        res = executar_cenario(rede, cen)
        print("=" * 72)
        print(f"[{res['id']}] ({res['tipo_analise'].upper()})")
        print(f"Pergunta: {res['pergunta']}")

        for vid, info_var in res["variantes"].items():
            print(f"\n  Variante '{vid}' ({info_var['descricao']}):")
            print(f"  Evidências: {info_var['evidencias'] or '(a priori)'}")
            for var_c, dist in info_var["distribuicoes"].items():
                resumo = " | ".join(f"{e}: {p:.4f}" for e, p in dist.items())
                print(f"    -> {var_c}: {resumo}")

        if res["verificacoes"]:
            print("\n  Verificação das expectativas qualitativas:")
            for v in res["verificacoes"]:
                status = "OK" if v["satisfeita"] else "FALHOU"
                print(
                    f"    [{status}] P({v['consulta']}={v['estado']}): "
                    f"{v['maior_esperado']} ({v['prob_maior']:.4f}) > "
                    f"{v['menor_esperado']} ({v['prob_menor']:.4f})"
                )

        if res["decisao"]:
            dec = res["decisao"]
            print(f"\n  Análise de Decisão (Utilidade Esperada em '{dec['consulta']}'):")
            for alt, info_alt in dec["alternativas"].items():
                print(
                    f"    - {alt}: EU = {info_alt['utilidade_esperada']:.2f} "
                    f"(custo = {info_alt['custo']})"
                )
            print(f"    => Melhor alternativa: {dec['melhor_alternativa']}")

    print("=" * 72)
    return 0


def _cmd_desenhar(args: argparse.Namespace) -> int:
    rede, dados = construir_rede_do_arquivo(args.modelo)
    png = gerar_imagem_rede(
        rede,
        dados_modelo=dados,
        caminho_png=args.saida_png,
        caminho_dot=args.saida_dot,
    )
    print(f"Diagrama PNG salvo em: {png}")
    if args.saida_dot:
        print(f"Arquivo DOT salvo em: {args.saida_dot}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bn-evasao",
        description="CLI da Rede Bayesiana para Risco de Evasão no Ensino Superior.",
    )
    parser.add_argument(
        "--modelo",
        type=Path,
        default=CAMINHO_MODELO_PADRAO,
        help="Caminho para o arquivo modelo.json (padrão: ./modelo.json).",
    )

    sub = parser.add_subparsers(dest="comando", required=True)

    p_val = sub.add_parser("validar", help="Valida esquema, DAG e CPTs do modelo.json.")
    p_val.set_defaults(func=_cmd_validar)

    p_info = sub.add_parser("info", help="Lista variáveis e estados válidos da rede.")
    p_info.set_defaults(func=_cmd_info)

    p_cons = sub.add_parser("consultar", help="Executa consulta probabilística com evidências.")
    p_cons.add_argument(
        "-c",
        "--consulta",
        nargs="+",
        required=True,
        help="Uma ou mais variáveis a consultar (ex.: Desfecho Pressao_Financeira).",
    )
    p_cons.add_argument(
        "-e",
        "--evidencia",
        nargs="*",
        default=[],
        help="Pares VARIAVEL=ESTADO (ex.: Faixa_Etaria=Maduro Turno=Noturno).",
    )
    p_cons.set_defaults(func=_cmd_consultar)

    p_cen = sub.add_parser("cenarios", help="Executa os cenários definidos no modelo.json.")
    p_cen.add_argument("--id", type=str, default=None, help="Executa apenas o cenário especificado.")
    p_cen.set_defaults(func=_cmd_cenarios)

    p_des = sub.add_parser("desenhar", help="Gera a representação gráfica da estrutura da rede.")
    p_des.add_argument("--saida-png", type=Path, default=SAIDA_PNG_PADRAO)
    p_des.add_argument("--saida-dot", type=Path, default=SAIDA_DOT_PADRAO)
    p_des.set_defaults(func=_cmd_desenhar)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ErroValidacaoModelo, ErroInferencia, FileNotFoundError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())