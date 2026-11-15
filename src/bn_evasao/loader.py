"""Leitura e validação do modelo.json.

carregar_modelo faz, nesta ordem, a leitura do arquivo, a rejeição de chaves
duplicadas, a validação contra o schema e as validações semânticas de
validar_modelo. Falhas de estrutura levantam ModeloInvalidoError e falhas de CPT
levantam CPTInvalidaError, sempre com mensagem que aponta onde está o erro.

validar_modelo também pode ser chamada direto com um dict, o que facilita os
testes de casos inválidos sem escrever arquivos.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from typing import Any

from .erros import CPTInvalidaError, ModeloInvalidoError
from .schema import validar_contra_schema

TOLERANCIA_SOMA = 1e-6
_MAX_ITENS_NA_MENSAGEM = 5


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def _sem_duplicatas(pares: list[tuple[str, Any]]) -> dict[str, Any]:
    """object_pairs_hook que recusa chaves repetidas no mesmo objeto."""
    objeto: dict[str, Any] = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ModeloInvalidoError(
                f"Chave duplicada no JSON: '{chave}' (objeto com chaves "
                f"{list(objeto)[:_MAX_ITENS_NA_MENSAGEM]}).")
        objeto[chave] = valor
    return objeto


def _recusar_constante(nome: str) -> Any:
    raise ModeloInvalidoError(
        f"Valor '{nome}' não é permitido no JSON do modelo (use números finitos).")


def carregar_modelo_de_texto(texto: str, origem: str = "<texto>") -> dict[str, Any]:
    """Interpreta e valida o conteúdo de um modelo.json já lido."""
    try:
        modelo = json.loads(texto, object_pairs_hook=_sem_duplicatas,
                            parse_constant=_recusar_constante)
    except json.JSONDecodeError as erro:
        raise ModeloInvalidoError(
            f"JSON malformado em {origem}, linha {erro.lineno}, coluna {erro.colno}: "
            f"{erro.msg}.") from erro
    if not isinstance(modelo, dict):
        raise ModeloInvalidoError(f"A raiz de {origem} deve ser um objeto JSON.")
    validar_modelo(modelo)
    return modelo


def carregar_modelo(caminho: str | Path = "modelo.json") -> dict[str, Any]:
    """Lê o arquivo, valida e devolve o modelo como dict."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ModeloInvalidoError(f"Arquivo do modelo não encontrado: {caminho}")
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as erro:
        raise ModeloInvalidoError(f"Não foi possível ler {caminho}: {erro}") from erro
    return carregar_modelo_de_texto(texto, origem=str(caminho))


# ---------------------------------------------------------------------------
# Validação semântica
# ---------------------------------------------------------------------------
def validar_modelo(modelo: dict[str, Any]) -> None:
    """Valida schema e consistência entre variáveis, arcos, pais, CPTs e cenários."""
    validar_contra_schema(modelo)
    estados_por_var = _validar_variaveis(modelo)
    pais_por_var = _validar_estrutura(modelo, estados_por_var)
    _validar_aciclico(pais_por_var)
    _validar_ids_cenarios(modelo)
    _validar_cpts(modelo, estados_por_var, pais_por_var)


def _duplicados(itens: list[str]) -> list[str]:
    vistos: set[str] = set()
    repetidos: list[str] = []
    for item in itens:
        if item in vistos and item not in repetidos:
            repetidos.append(item)
        vistos.add(item)
    return repetidos


def _fmt_config(config: dict[str, str]) -> str:
    return ", ".join(f"{pai}={estado}" for pai, estado in config.items()) or "(sem pais)"


def _validar_variaveis(modelo: dict[str, Any]) -> dict[str, list[str]]:
    ids = [v["id"] for v in modelo["variaveis"]]
    repetidas = _duplicados(ids)
    if repetidas:
        raise ModeloInvalidoError(f"Variáveis com id duplicado: {repetidas}.")
    estados_por_var: dict[str, list[str]] = {}
    for variavel in modelo["variaveis"]:
        estados = [e["id"] for e in variavel["estados"]]
        repetidos = _duplicados(estados)
        if repetidos:
            raise ModeloInvalidoError(
                f"Variável '{variavel['id']}' tem estados duplicados: {repetidos}.")
        estados_por_var[variavel["id"]] = estados
    return estados_por_var


def _validar_estrutura(modelo: dict[str, Any],
                       estados_por_var: dict[str, list[str]]) -> dict[str, list[str]]:
    ids = set(estados_por_var)
    estrutura = modelo["estrutura"]

    derivado: dict[str, list[str]] = {var: [] for var in estados_por_var}
    vistos: set[tuple[str, str]] = set()
    for arco in estrutura["arcos"]:
        de, para = arco["de"], arco["para"]
        for nome in (de, para):
            if nome not in ids:
                raise ModeloInvalidoError(
                    f"O arco {de} → {para} cita a variável inexistente '{nome}'.")
        if de == para:
            raise ModeloInvalidoError(f"O arco {de} → {para} liga a variável a si mesma.")
        if (de, para) in vistos:
            raise ModeloInvalidoError(f"O arco {de} → {para} aparece mais de uma vez.")
        vistos.add((de, para))
        derivado[para].append(de)

    declarado = estrutura["pais"]
    sem_entrada = sorted(ids - set(declarado))
    if sem_entrada:
        raise ModeloInvalidoError(
            f"estrutura.pais não lista as variáveis {sem_entrada} (use lista vazia "
            "para variáveis sem pais).")
    desconhecidas = sorted(set(declarado) - ids)
    if desconhecidas:
        raise ModeloInvalidoError(
            f"estrutura.pais cita variáveis inexistentes: {desconhecidas}.")

    for var in estados_por_var:
        lista = declarado[var]
        repetidos = _duplicados(lista)
        if repetidos:
            raise ModeloInvalidoError(
                f"estrutura.pais['{var}'] repete os pais {repetidos}.")
        inexistentes = [p for p in lista if p not in ids]
        if inexistentes:
            raise ModeloInvalidoError(
                f"estrutura.pais['{var}'] cita pais inexistentes: {inexistentes}.")
        if set(lista) != set(derivado[var]):
            raise ModeloInvalidoError(
                f"estrutura.pais['{var}'] = {lista} não bate com os arcos, que "
                f"indicam {derivado[var]}.")
    return {var: list(declarado[var]) for var in estados_por_var}


def _validar_aciclico(pais_por_var: dict[str, list[str]]) -> None:
    filhos: dict[str, list[str]] = {var: [] for var in pais_por_var}
    for filho, pais in pais_por_var.items():
        for pai in pais:
            filhos[pai].append(filho)

    branco, cinza, preto = 0, 1, 2
    cor = {var: branco for var in pais_por_var}
    caminho: list[str] = []

    def visitar(var: str) -> None:
        cor[var] = cinza
        caminho.append(var)
        for filho in filhos[var]:
            if cor[filho] == cinza:
                ciclo = caminho[caminho.index(filho):] + [filho]
                raise ModeloInvalidoError("O grafo possui ciclo: " + " → ".join(ciclo))
            if cor[filho] == branco:
                visitar(filho)
        caminho.pop()
        cor[var] = preto

    for var in sorted(cor):
        if cor[var] == branco:
            visitar(var)


def _validar_ids_cenarios(modelo: dict[str, Any]) -> None:
    repetidos = _duplicados([c["id"] for c in modelo["cenarios"]])
    if repetidos:
        raise ModeloInvalidoError(f"Cenários com id duplicado: {repetidos}.")


def _validar_cpts(modelo: dict[str, Any], estados_por_var: dict[str, list[str]],
                  pais_por_var: dict[str, list[str]]) -> None:
    por_variavel: dict[str, dict[str, Any]] = {}
    for cpt in modelo["probabilidades"]:
        var = cpt["variavel"]
        if var not in estados_por_var:
            raise CPTInvalidaError(f"Existe CPT para a variável inexistente '{var}'.")
        if var in por_variavel:
            raise CPTInvalidaError(f"A variável '{var}' tem mais de uma CPT.")
        por_variavel[var] = cpt

    sem_cpt = [var for var in estados_por_var if var not in por_variavel]
    if sem_cpt:
        raise CPTInvalidaError(f"Variáveis sem CPT: {sem_cpt}.")

    for var in estados_por_var:
        _validar_cpt(var, por_variavel[var], estados_por_var, pais_por_var[var])


def _validar_cpt(var: str, cpt: dict[str, Any], estados_por_var: dict[str, list[str]],
                 pais_esperados: list[str]) -> None:
    pais_cpt = cpt["pais"]
    if _duplicados(pais_cpt) or set(pais_cpt) != set(pais_esperados):
        raise CPTInvalidaError(
            f"A CPT de '{var}' declara pais {pais_cpt}, mas a estrutura define "
            f"{pais_esperados}.")

    estados_var = estados_por_var[var]
    if _duplicados(cpt["estados"]) or set(cpt["estados"]) != set(estados_var):
        raise CPTInvalidaError(
            f"A CPT de '{var}' lista os estados {cpt['estados']}, mas a variável "
            f"define {estados_var}.")

    vistas: set[tuple[str, ...]] = set()
    for i, linha in enumerate(cpt["linhas"]):
        onde = f"CPT de '{var}', linha {i}"
        config = linha["configuracao_pais"]
        if set(config) != set(pais_cpt):
            raise CPTInvalidaError(
                f"{onde}, a configuração cita {sorted(config)} mas os pais são "
                f"{sorted(pais_cpt)}.")
        for pai, estado in config.items():
            if estado not in estados_por_var[pai]:
                raise CPTInvalidaError(
                    f"{onde}, o estado '{estado}' não existe na variável '{pai}'.")
        chave = tuple(config[pai] for pai in pais_cpt)
        if chave in vistas:
            raise CPTInvalidaError(
                f"{onde}, configuração repetida ({_fmt_config(config)}).")
        vistas.add(chave)

        probs = linha["probabilidades"]
        if set(probs) != set(estados_var):
            raise CPTInvalidaError(
                f"{onde} ({_fmt_config(config)}), estados {sorted(probs)} diferem "
                f"dos estados da variável {sorted(estados_var)}.")
        for estado, valor in probs.items():
            # A comparação em forma positiva também recusa NaN.
            if not (0.0 <= valor <= 1.0):
                raise CPTInvalidaError(
                    f"{onde} ({_fmt_config(config)}), P({estado}) = {valor} fora de [0, 1].")
        soma = math.fsum(probs.values())
        if abs(soma - 1.0) > TOLERANCIA_SOMA:
            raise CPTInvalidaError(
                f"{onde} ({_fmt_config(config)}), as probabilidades somam {soma:.8f}, "
                "esperado 1.")

    esperado = math.prod(len(estados_por_var[pai]) for pai in pais_cpt)
    if len(vistas) < esperado:
        faltantes: list[str] = []
        for combinacao in itertools.product(*(estados_por_var[p] for p in pais_cpt)):
            if combinacao not in vistas:
                faltantes.append(_fmt_config(dict(zip(pais_cpt, combinacao))))
                if len(faltantes) >= _MAX_ITENS_NA_MENSAGEM:
                    break
        raise CPTInvalidaError(
            f"A CPT de '{var}' está incompleta, tem {len(vistas)} de {esperado} "
            f"configurações de pais. Faltam, por exemplo, {'; '.join(faltantes)}.")