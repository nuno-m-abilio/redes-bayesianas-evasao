"""Carregamento e validação semântica do modelo.json."""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import jsonschema
import networkx as nx

from .schema import validar_schema

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_MODELO_PADRAO = RAIZ_PROJETO / "modelo.json"
TOLERANCIA_SOMA_CPT = 1e-5


class ErroValidacaoModelo(ValueError):
    """Erro levantado quando o modelo.json viola regras estruturais ou probabilísticas."""

def _rejeitar_chaves_duplicadas(pares: list[tuple[str, object]]) -> dict:
    """object_pairs_hook: o enunciado exige JSON sem chaves duplicadas."""
    resultado: dict = {}
    for chave, valor in pares:
        if chave in resultado:
            raise ErroValidacaoModelo(f"Chave duplicada no JSON: '{chave}'.")
        resultado[chave] = valor
    return resultado

def carregar_modelo(caminho: str | Path = CAMINHO_MODELO_PADRAO) -> dict:
    """Lê um arquivo modelo.json do disco, valida e retorna o dicionário."""
    path = Path(caminho)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de modelo não encontrado: {path}")

    try:
        texto = path.read_text(encoding="utf-8")
        dados = json.loads(texto, object_pairs_hook=_rejeitar_chaves_duplicadas)
    except json.JSONDecodeError as exc:
        raise ErroValidacaoModelo(f"JSON malformado em {path}: {exc}") from exc

    validar_modelo_dict(dados)
    return dados


def validar_modelo_dict(
    dados: dict, tolerancia: float = TOLERANCIA_SOMA_CPT
) -> None:
    """Valida esquema, estrutura DAG, completude das CPTs e cenários."""
    try:
        validar_schema(dados)
    except jsonschema.ValidationError as exc:
        raise ErroValidacaoModelo(
            f"Falha na validação do JSON Schema: {exc.message}"
        ) from exc

    estados_por_var = _validar_variaveis(dados["variaveis"])
    _validar_estrutura(dados["estrutura"], estados_por_var)
    _validar_cpts(
        dados["probabilidades"],
        dados["estrutura"]["pais"],
        estados_por_var,
        tolerancia,
    )
    _validar_cenarios(dados["cenarios"], estados_por_var)


def _validar_variaveis(variaveis: list[dict]) -> dict[str, list[str]]:
    estados_por_var: dict[str, list[str]] = {}
    for var in variaveis:
        vid = var["id"]
        if vid in estados_por_var:
            raise ErroValidacaoModelo(f"Variável duplicada no JSON: '{vid}'.")
        estados = [e["id"] for e in var["estados"]]
        if len(set(estados)) != len(estados):
            raise ErroValidacaoModelo(
                f"Estados duplicados definidos para a variável '{vid}'."
            )
        estados_por_var[vid] = estados

    if len(estados_por_var) < 10:
        raise ErroValidacaoModelo(
            f"A rede precisa ter no mínimo 10 variáveis (encontradas: {len(estados_por_var)})."
        )
    return estados_por_var


def _validar_estrutura(
    estrutura: dict, estados_por_var: dict[str, list[str]]
) -> None:
    arcos = estrutura["arcos"]
    pais_dict = estrutura["pais"]

    if set(pais_dict.keys()) != set(estados_por_var.keys()):
        faltando = set(estados_por_var) - set(pais_dict)
        extras = set(pais_dict) - set(estados_por_var)
        raise ErroValidacaoModelo(
            f"Chaves de 'estrutura.pais' diferem das variáveis declaradas. "
            f"Faltando: {sorted(faltando)}; Extras: {sorted(extras)}"
        )

    grafo = nx.DiGraph()
    grafo.add_nodes_from(estados_por_var.keys())

    pais_derivados: dict[str, list[str]] = {v: [] for v in estados_por_var}
    arcos_vistos: set[tuple[str, str]] = set()

    for arco in arcos:
        de, para = arco["de"], arco["para"]
        if de not in estados_por_var or para not in estados_por_var:
            raise ErroValidacaoModelo(
                f"Arco referencia variável inexistente: '{de}' -> '{para}'."
            )
        if de == para:
            raise ErroValidacaoModelo(f"Auto-loop detectado na variável '{de}'.")
        if (de, para) in arcos_vistos:
            raise ErroValidacaoModelo(f"Arco duplicado: '{de}' -> '{para}'.")

        arcos_vistos.add((de, para))
        pais_derivados[para].append(de)
        grafo.add_edge(de, para)

    for var, pais_declarados in pais_dict.items():
        for p in pais_declarados:
            if p not in estados_por_var:
                raise ErroValidacaoModelo(
                    f"Pai inexistente '{p}' declarado para '{var}'."
                )
        if pais_declarados != pais_derivados[var]:
            raise ErroValidacaoModelo(
                f"Inconsistência entre 'arcos' e 'pais' para '{var}': "
                f"pais={pais_declarados} vs arcos={pais_derivados[var]}."
            )

    if not nx.is_directed_acyclic_graph(grafo):
        ciclo = nx.find_cycle(grafo)
        raise ErroValidacaoModelo(f"O grafo não é acíclico (ciclo: {ciclo}).")


def _validar_cpts(
    probabilidades: list[dict],
    pais_estrutura: dict[str, list[str]],
    estados_por_var: dict[str, list[str]],
    tolerancia: float,
) -> None:
    cpts_vistas: set[str] = set()

    for cpt in probabilidades:
        var = cpt["variavel"]
        if var not in estados_por_var:
            raise ErroValidacaoModelo(f"CPT definida para variável inexistente: '{var}'.")
        if var in cpts_vistas:
            raise ErroValidacaoModelo(f"CPT duplicada para a variável '{var}'.")
        cpts_vistas.add(var)

        pais = cpt["pais"]
        if pais != pais_estrutura[var]:
            raise ErroValidacaoModelo(
                f"Pais na CPT de '{var}' ({pais}) diferem da estrutura ({pais_estrutura[var]})."
            )

        estados_var = estados_por_var[var]
        if cpt["estados"] != estados_var:
            raise ErroValidacaoModelo(
                f"Estados na CPT de '{var}' ({cpt['estados']}) diferem da definição ({estados_var})."
            )

        combinacoes_esperadas = (
            [()]
            if not pais
            else list(product(*(estados_por_var[p] for p in pais)))
        )
        esperadas_set = set(combinacoes_esperadas)
        vistas_set: set[tuple[str, ...]] = set()

        for idx, linha in enumerate(cpt["linhas"]):
            cfg = linha["configuracao_pais"]
            if set(cfg.keys()) != set(pais):
                raise ErroValidacaoModelo(
                    f"CPT de '{var}' (linha {idx}): chaves de configuracao_pais "
                    f"({list(cfg.keys())}) não batem com os pais ({pais})."
                )

            tupla_cfg = tuple(cfg[p] for p in pais)
            if tupla_cfg not in esperadas_set:
                raise ErroValidacaoModelo(
                    f"CPT de '{var}' (linha {idx}): estado inválido em configuracao_pais: {cfg}."
                )
            if tupla_cfg in vistas_set:
                raise ErroValidacaoModelo(
                    f"CPT de '{var}' (linha {idx}): configuração de pais duplicada: {cfg}."
                )
            vistas_set.add(tupla_cfg)

            probs = linha["probabilidades"]
            if set(probs.keys()) != set(estados_var):
                raise ErroValidacaoModelo(
                    f"CPT de '{var}' (linha {idx}): estados de probabilidade "
                    f"({list(probs.keys())}) diferem de {estados_var}."
                )

            for est, val in probs.items():
                if not (0.0 <= val <= 1.0):
                    raise ErroValidacaoModelo(
                        f"CPT de '{var}' (linha {idx}, estado '{est}'): "
                        f"probabilidade fora de [0, 1]: {val}."
                    )

            soma = sum(probs.values())
            if abs(soma - 1.0) > tolerancia:
                raise ErroValidacaoModelo(
                    f"CPT de '{var}' (linha {idx}, pais={cfg}): "
                    f"probabilidades somam {soma:.6f} (esperado: 1.0)."
                )

        if vistas_set != esperadas_set:
            faltando = esperadas_set - vistas_set
            raise ErroValidacaoModelo(
                f"CPT de '{var}' incompleta. Faltam {len(faltando)} configurações de pais."
            )

    if cpts_vistas != set(estados_por_var.keys()):
        faltando = set(estados_por_var) - cpts_vistas
        raise ErroValidacaoModelo(f"Variáveis sem CPT definida: {sorted(faltando)}.")


def _validar_cenarios(
    cenarios: list[dict], estados_por_var: dict[str, list[str]]
) -> None:
    ids_cenarios: set[str] = set()
    for cen in cenarios:
        cid = cen["id"]
        if cid in ids_cenarios:
            raise ErroValidacaoModelo(f"Cenário duplicado: '{cid}'.")
        ids_cenarios.add(cid)

        _validar_mapa_evidencias(cen["evidencias_base"], estados_por_var, f"{cid}.evidencias_base")

        ids_variantes: set[str] = set()
        for var_item in cen["variantes"]:
            vid = var_item["id"]
            if vid in ids_variantes:
                raise ErroValidacaoModelo(f"Variante '{vid}' duplicada no cenário '{cid}'.")
            ids_variantes.add(vid)
            _validar_mapa_evidencias(
                var_item["evidencias_adicionais"],
                estados_por_var,
                f"{cid}.variantes[{vid}]",
            )

        for cons in cen["consultas"]:
            if cons not in estados_por_var:
                raise ErroValidacaoModelo(
                    f"Cenário '{cid}': variável de consulta inexistente '{cons}'."
                )

        for exp in cen.get("expectativas", []):
            if exp["consulta"] not in cen["consultas"]:
                raise ErroValidacaoModelo(
                    f"Cenário '{cid}': expectativa referencia consulta '{exp['consulta']}' "
                    f"fora da lista de consultas do cenário."
                )
            if exp["estado"] not in estados_por_var[exp["consulta"]]:
                raise ErroValidacaoModelo(
                    f"Cenário '{cid}': estado inválido '{exp['estado']}' para '{exp['consulta']}'."
                )
            if exp["maior"] not in ids_variantes or exp["menor"] not in ids_variantes:
                raise ErroValidacaoModelo(
                    f"Cenário '{cid}': expectativa referencia variante inexistente."
                )


def _validar_mapa_evidencias(
    evidencias: dict[str, str],
    estados_por_var: dict[str, list[str]],
    contexto: str,
) -> None:
    for var, estado in evidencias.items():
        if var not in estados_por_var:
            raise ErroValidacaoModelo(
                f"{contexto}: variável de evidência inexistente '{var}'."
            )
        if estado not in estados_por_var[var]:
            raise ErroValidacaoModelo(
                f"{contexto}: estado inválido '{estado}' para variável '{var}' "
                f"(válidos: {estados_por_var[var]})."
            )