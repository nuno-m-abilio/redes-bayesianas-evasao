#!/usr/bin/env python3
"""
Gera modelo.json a partir de:
  - src/bn_evasao/definicao.py   (variáveis, estados, arcos)
  - src/bn_evasao/cpt_rules.py   (CPTs definidas manualmente)
  - scenarios/cenarios.json      (cenários de utilização)

Uso:
    python scripts/gerar_modelo_json.py              # escreve modelo.json
    python scripts/gerar_modelo_json.py --verificar  # falha (exit 1) se modelo.json estiver desatualizado

NUNCA edite modelo.json à mão: altere a regra/definição e regenere.
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from bn_evasao import cpt_rules, definicao as d  # noqa: E402

CAMINHO_CENARIOS = RAIZ / "scenarios" / "cenarios.json"
CAMINHO_MODELO = RAIZ / "modelo.json"
BIBLIOTECAS = ["pgmpy", "networkx", "pandas", "numpy", "matplotlib", "pydot", "pytest", "jsonschema"]


def _versao(pacote: str) -> str:
    try:
        return metadata.version(pacote)
    except metadata.PackageNotFoundError:
        return "nao-instalado"


def montar_modelo() -> dict:
    variaveis = [
        {
            "id": v,
            "nome": info["nome"],
            "descricao": info["descricao"],
            "tipo": info["tipo"],
            "observavel": info["observavel"],
            "estados": [{"id": e, "interpretacao": i} for e, i in info["estados"].items()],
        }
        for v, info in d.VARIAVEIS.items()
    ]
    cenarios = json.loads(CAMINHO_CENARIOS.read_text(encoding="utf-8"))["cenarios"]
    cpts = cpt_rules.gerar_todas_cpts()

    return {
        "projeto": {
            "tema": "Risco de evasão e sucesso acadêmico no ensino superior",
            "pergunta_principal": "Dado o perfil de ingresso e o desempenho inicial, qual a probabilidade de Dropout, Enrolled ou Graduate?",
            "dataset": {
                "nome": "Predict Students' Dropout and Academic Success",
                "fonte": "UCI Machine Learning Repository (id 697)",
                "url": "https://archive.ics.uci.edu/dataset/697",
                "uso": "Contextualização e justificativa das escolhas. Nenhum parâmetro foi estimado automaticamente.",
            },
            "nota_causalidade": "Arcos representam hipóteses de dependência probabilística; o dataset não comprova causalidade.",
            "cpts_preliminares": bool(getattr(cpt_rules, "PRELIMINAR", False)),
        },
        "variaveis": variaveis,
        "estrutura": {
            "arcos": [{"de": a, "para": b, "justificativa": j} for a, b, j in d.ARCOS],
            "pais": {v: list(p) for v, p in d.PAIS.items()},
        },
        "probabilidades": [cpts[v] for v in d.ordem_topologica()],
        "cenarios": cenarios,
        "metadados_execucao": {
            "python_minimo": "3.11",
            "bibliotecas": {p: _versao(p) for p in BIBLIOTECAS},
            "observacao": "Versões lidas do ambiente em que o modelo.json foi gerado.",
        },
    }


def serializar(modelo: dict) -> str:
    return json.dumps(modelo, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=CAMINHO_MODELO)
    ap.add_argument("--verificar", action="store_true")
    args = ap.parse_args()

    texto = serializar(montar_modelo())
    if args.verificar:
        atual = args.saida.read_text(encoding="utf-8") if args.saida.exists() else None
        if atual != texto:
            raise SystemExit(f"{args.saida} está desatualizado. Rode: python scripts/gerar_modelo_json.py")
        print("modelo.json está atualizado.")
        return
    args.saida.write_text(texto, encoding="utf-8")
    print(f"Gerado: {args.saida}")


if __name__ == "__main__":
    main()