"""Interface de linha de comando.

    python -m bn_evasao.cli validar   [--modelo modelo.json]
    python -m bn_evasao.cli consultar --consulta Desfecho --evidencia Turno=Noturno [--json]
    python -m bn_evasao.cli cenarios  [--id S2_alerta_precoce] [--json]
    python -m bn_evasao.cli desenhar  [--saida outputs/figuras/rede.png] [--motor auto]

Códigos de saída: 0 para sucesso, 1 para erro do projeto (modelo inválido, evidência
inválida, falha ao desenhar), 2 para uso incorreto da linha de comando (argparse) e
3 quando algum cenário executa mas tem expectativa reprovada.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import scenarios
from .erros import ErroBN, EvidenciaInvalidaError
from .inference import consultar
from .loader import carregar_modelo
from .network import construir_rede
from .visualize import CAMINHO_PADRAO, FORMATOS, MOTORES, desenhar_rede

SAIDA_OK = 0
SAIDA_ERRO = 1
SAIDA_CENARIO_REPROVADO = 3

# Metas do enunciado e decisões do grupo, usadas só para avisos em "validar".
MIN_VARIAVEIS = 10
MIN_CENARIOS = 4
MAX_PAIS = 3


# ---------------------------------------------------------------------------
# Saída em texto
# ---------------------------------------------------------------------------
def _configurar_saida() -> None:
    """Força UTF-8, porque o terminal do Windows costuma usar uma codificação que não tem as barras."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _tabela(distribuicao: dict[str, float], recuo: str = "  ") -> str:
    largura = max(len(estado) for estado in distribuicao)
    linhas = [f"{recuo}{estado:<{largura}}  {p:.4f}  {'█' * round(p * 30)}"
              for estado, p in distribuicao.items()]
    return "\n".join(linhas)


def _condicao(evidencias: dict[str, str]) -> str:
    return ", ".join(f"{v}={e}" for v, e in evidencias.items()) or "sem evidências"


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def _cmd_validar(args: argparse.Namespace) -> int:
    modelo = carregar_modelo(args.modelo)
    construir_rede(modelo)  # confirma que o pgmpy aceita a rede e todas as CPTs

    variaveis = modelo["variaveis"]
    pais_max = max((len(p) for p in modelo["estrutura"]["pais"].values()), default=0)
    latentes = [v["id"] for v in variaveis if v.get("observavel", True) is False]
    n_linhas = sum(len(c["linhas"]) for c in modelo["probabilidades"])

    print(f"Modelo válido ({args.modelo})")
    print(f"  {len(variaveis)} variáveis, {len(modelo['estrutura']['arcos'])} arcos, "
          f"{len(modelo['probabilidades'])} CPTs ({n_linhas} linhas), "
          f"{len(modelo['cenarios'])} cenário(s)")
    if latentes:
        print(f"  variáveis latentes {latentes}")

    avisos = []
    if len(variaveis) < MIN_VARIAVEIS:
        avisos.append(f"o enunciado pede pelo menos {MIN_VARIAVEIS} variáveis, o modelo tem "
                      f"{len(variaveis)}")
    if len(modelo["cenarios"]) < MIN_CENARIOS:
        avisos.append(f"o enunciado pede pelo menos {MIN_CENARIOS} cenários, o modelo tem "
                      f"{len(modelo['cenarios'])}")
    if pais_max > MAX_PAIS:
        avisos.append(f"há variável com {pais_max} pais, e o grupo decidiu no máximo {MAX_PAIS}")
    if modelo["projeto"].get("cpts_preliminares"):
        avisos.append("as CPTs estão marcadas como preliminares (cpts_preliminares no projeto)")
    for aviso in avisos:
        print(f"Aviso: {aviso}.")
    return SAIDA_OK


def _juntar_evidencias(pares: list[tuple[str, str]]) -> dict[str, str]:
    evidencias: dict[str, str] = {}
    for var, estado in pares:
        if var in evidencias and evidencias[var] != estado:
            raise EvidenciaInvalidaError(
                f"A variável '{var}' recebeu duas evidências diferentes "
                f"('{evidencias[var]}' e '{estado}').")
        evidencias[var] = estado
    return evidencias


def _cmd_consultar(args: argparse.Namespace) -> int:
    modelo = carregar_modelo(args.modelo)
    rede = construir_rede(modelo)
    evidencias = _juntar_evidencias(args.evidencia)
    resultado = consultar(rede, args.consulta, evidencias)

    if args.json:
        print(json.dumps({"evidencias": evidencias, "resultado": resultado},
                         ensure_ascii=False, indent=2))
        return SAIDA_OK
    for var, distribuicao in resultado.items():
        print(f"P({var} | {_condicao(evidencias)})")
        print(_tabela(distribuicao))
    return SAIDA_OK


def _imprimir_cenario(resultado: dict[str, Any]) -> None:
    """Imprime as partes do resultado que reconhece e mostra o JSON se não reconhecer nenhuma."""
    print(f"=== {resultado.get('id', '(sem id)')} ===")
    if resultado.get("pergunta"):
        print(resultado["pergunta"])
    reconheceu = False

    variantes = resultado.get("variantes")
    if isinstance(variantes, dict):
        for rotulo, variante in variantes.items():
            if not isinstance(variante, dict) or "resultados" not in variante:
                continue
            reconheceu = True
            print(f"\nVariante {rotulo} ({_condicao(variante.get('evidencias', {}))})")
            for var, distribuicao in variante["resultados"].items():
                print(f"  P({var})")
                print(_tabela(distribuicao, recuo="    "))

    expectativas = resultado.get("expectativas")
    if isinstance(expectativas, list):
        reconheceu = True
        print("\nExpectativas")
        for exp in expectativas:
            marca = {True: "[ok]", False: "[FALHOU]"}.get(exp.get("aprovado"), "[?]")
            print(f"  {marca} {exp.get('descricao') or exp.get('tipo', '')}")

    if resultado.get("interpretacao"):
        reconheceu = True
        print(f"\nInterpretação\n  {resultado['interpretacao']}")
    if not reconheceu:
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


def _cmd_cenarios(args: argparse.Namespace) -> int:
    modelo = carregar_modelo(args.modelo)
    rede = construir_rede(modelo)

    cenarios = modelo["cenarios"]
    if args.id:
        cenarios = [c for c in cenarios if c["id"] == args.id]
        if not cenarios:
            existentes = ", ".join(c["id"] for c in modelo["cenarios"])
            raise ErroBN(f"Cenário '{args.id}' não existe. Cenários disponíveis: {existentes}.")

    try:
        resultados = {c["id"]: scenarios.executar_cenario(rede, c) for c in cenarios}
    except NotImplementedError as erro:
        raise ErroBN("A execução de cenários ainda não foi implementada (scenarios.py).") from erro

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2, default=str))
    else:
        for i, resultado in enumerate(resultados.values()):
            if i:
                print()
            _imprimir_cenario(resultado)

    reprovou = any(isinstance(r, dict) and r.get("aprovado") is False
                   for r in resultados.values())
    return SAIDA_CENARIO_REPROVADO if reprovou else SAIDA_OK


def _cmd_desenhar(args: argparse.Namespace) -> int:
    modelo = carregar_modelo(args.modelo)
    try:
        saidas = desenhar_rede(modelo, args.saida, alvo=args.alvo, motor=args.motor,
                               formatos=tuple(args.formatos))
    except RuntimeError as erro:
        raise ErroBN(str(erro)) from erro
    print("Figuras geradas")
    for saida in saidas:
        print(f"  {saida}")
    return SAIDA_OK


# ---------------------------------------------------------------------------
# Argumentos
# ---------------------------------------------------------------------------
def _par_evidencia(texto: str) -> tuple[str, str]:
    variavel, separador, estado = texto.partition("=")
    variavel, estado = variavel.strip(), estado.strip()
    if not separador or not variavel or not estado:
        raise argparse.ArgumentTypeError(
            f"evidência '{texto}' deve ter o formato VARIAVEL=ESTADO")
    return variavel, estado


def _criar_parser() -> argparse.ArgumentParser:
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument("--modelo", type=Path, default=Path("modelo.json"),
                       help="caminho do modelo.json (padrão modelo.json)")

    parser = argparse.ArgumentParser(
        prog="python -m bn_evasao.cli",
        description="Rede bayesiana para risco de evasão no ensino superior.")
    sub = parser.add_subparsers(dest="comando", required=True, metavar="comando")

    p = sub.add_parser("validar", parents=[comum],
                       help="valida o modelo.json e a construção da rede")
    p.set_defaults(func=_cmd_validar)

    p = sub.add_parser("consultar", parents=[comum],
                       help="calcula P(consulta | evidências)")
    p.add_argument("--consulta", "-c", action="append", required=True, metavar="VARIAVEL",
                   help="variável consultada (pode repetir)")
    p.add_argument("--evidencia", "-e", action="append", default=[], type=_par_evidencia,
                   metavar="VARIAVEL=ESTADO", help="evidência observada (pode repetir)")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.set_defaults(func=_cmd_consultar)

    p = sub.add_parser("cenarios", parents=[comum], help="executa os cenários do modelo")
    p.add_argument("--id", help="executa só o cenário com este id")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.set_defaults(func=_cmd_cenarios)

    p = sub.add_parser("desenhar", parents=[comum], help="desenha a estrutura da rede")
    p.add_argument("--saida", type=Path, default=CAMINHO_PADRAO,
                   help=f"base do nome dos arquivos (padrão {CAMINHO_PADRAO})")
    p.add_argument("--motor", choices=MOTORES, default="auto")
    p.add_argument("--alvo", default="Desfecho", help="variável destacada (padrão Desfecho)")
    p.add_argument("--formatos", nargs="+", choices=FORMATOS, default=list(FORMATOS))
    p.set_defaults(func=_cmd_desenhar)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configurar_saida()
    args = _criar_parser().parse_args(argv)
    try:
        return args.func(args)
    except ErroBN as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return SAIDA_ERRO


if __name__ == "__main__":
    sys.exit(main())