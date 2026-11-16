"""Fixtures compartilhadas pelos testes."""
import copy
import json
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore", category=FutureWarning)

from pgmpy.factors.discrete import TabularCPD  # noqa: E402
from pgmpy.models import DiscreteBayesianNetwork  # noqa: E402

from bn_evasao.loader import carregar_modelo  # noqa: E402
from bn_evasao.network import construir_rede_do_dicionario  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_MODELO = RAIZ / "modelo.json"


@pytest.fixture(scope="session")
def modelo() -> dict:
    """modelo.json validado (NÃO modificar: use `modelo_copia` nos testes inválidos)."""
    return carregar_modelo(CAMINHO_MODELO)


@pytest.fixture(scope="session")
def rede(modelo):
    return construir_rede_do_dicionario(modelo)


@pytest.fixture()
def modelo_copia(modelo) -> dict:
    """Cópia profunda, livre para ser corrompida em casos inválidos."""
    return copy.deepcopy(modelo)


@pytest.fixture()
def escrever_json(tmp_path):
    def _escrever(conteudo, nome="modelo_teste.json") -> Path:
        caminho = tmp_path / nome
        texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False)
        caminho.write_text(texto, encoding="utf-8")
        return caminho
    return _escrever


@pytest.fixture(scope="session")
def rede_mini():
    """
    Rede miniatura A -> B, A -> C com valores escolhidos à mão, para conferir a
    inferência contra cálculos manuais (regra da cadeia e Bayes).
        P(A)=[0.3, 0.7]
        P(B|A): a0 -> [0.9, 0.1] ; a1 -> [0.2, 0.8]
        P(C|A): a0 -> [0.5, 0.5] ; a1 -> [0.1, 0.9]
    """
    rede = DiscreteBayesianNetwork([("A", "B"), ("A", "C")])
    sn = {"A": ["a0", "a1"], "B": ["b0", "b1"], "C": ["c0", "c1"]}
    rede.add_cpds(
        TabularCPD("A", 2, [[0.3], [0.7]], state_names={"A": sn["A"]}),
        TabularCPD("B", 2, [[0.9, 0.2], [0.1, 0.8]], evidence=["A"], evidence_card=[2],
                   state_names={"B": sn["B"], "A": sn["A"]}),
        TabularCPD("C", 2, [[0.5, 0.1], [0.5, 0.9]], evidence=["A"], evidence_card=[2],
                   state_names={"C": sn["C"], "A": sn["A"]}),
    )
    rede.check_model()
    return rede