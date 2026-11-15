"""Garante por varredura de código a regra central do enunciado.

A seção 6 proíbe aprender estrutura ou probabilidades a partir dos dados. Este teste
recusa qualquer uso, em src/ e scripts/, de estimadores e buscas de estrutura do pgmpy,
de métodos fit e de bibliotecas de aprendizagem de máquina. As CPTs devem vir só das
regras escritas pelo grupo.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PASTAS = [RAIZ / "src", RAIZ / "scripts"]

PROIBIDOS = {
    "estimador de parâmetros": r"\b(MaximumLikelihoodEstimator|BayesianEstimator|"
                               r"ExpectationMaximization)\b",
    "busca de estrutura": r"\b(HillClimbSearch|ExhaustiveSearch|TreeSearch|MmhcEstimator|"
                          r"StructureEstimator|PCAlg)\b",
    "módulo de estimadores do pgmpy": r"pgmpy\.estimators",
    "método fit": r"\.fit\s*\(",
    "biblioteca de aprendizagem de máquina": r"\b(import|from)\s+(sklearn|torch|tensorflow|"
                                             r"xgboost|lightgbm|pomegranate)\b",
}


def arquivos_python():
    for pasta in PASTAS:
        if pasta.exists():
            yield from sorted(p for p in pasta.rglob("*.py") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("descricao, padrao", PROIBIDOS.items(), ids=list(PROIBIDOS))
def test_nenhum_codigo_aprende_dos_dados(descricao, padrao):
    achados = []
    for arquivo in arquivos_python():
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(padrao, linha):
                achados.append(f"{arquivo.relative_to(RAIZ)}, linha {numero}")
    assert not achados, f"Uso de {descricao} encontrado em {achados}"


def test_a_varredura_enxerga_os_arquivos():
    assert any(p.name == "network.py" for p in arquivos_python())