"""Leitura e validação do modelo.json."""
from __future__ import annotations

from pathlib import Path


def carregar_modelo(caminho: str | Path = "modelo.json") -> dict:
    """
    Lê o modelo.json e devolve o dicionário validado.

    Deve: (1) falhar se o arquivo não existir; (2) detectar CHAVES DUPLICADAS
    (object_pairs_hook); (3) validar contra o schema; (4) validar coerência
    semântica (ids únicos, pais existentes, arcos x pais, uma CPT por variável,
    estados das CPTs = estados da variável).
    Levanta ModeloInvalidoError informando ONDE está o erro.
    """
    raise NotImplementedError