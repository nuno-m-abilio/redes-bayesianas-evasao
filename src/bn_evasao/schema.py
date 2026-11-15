"""JSON Schema (Draft 2020-12) do modelo.json.

O schema cobre a forma do documento: chaves obrigatórias, tipos, padrão dos
identificadores e faixa dos valores. As regras que envolvem referências cruzadas
(pai existe, CPT completa, soma 1, grafo acíclico) ficam em loader.py.

Os campos opcionais "tipo" (papel da variável) e "cpts_preliminares" (CPTs ainda
provisórias) existem para o gerador do modelo. O loader confere se o tipo é coerente
com os arcos.

Identificadores de variáveis e estados usam apenas letras, dígitos e sublinhado,
começando por letra, sem acentos. O campo tipo_analise dos cenários aceita
descritiva, diagnostica, preditiva ou prescritiva (sem acento).
"""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from .erros import ModeloInvalidoError

_ID = {"type": "string", "pattern": r"^[A-Za-z][A-Za-z0-9_]*$"}
_TEXTO = {"type": "string", "minLength": 1}
_LISTA_IDS = {"type": "array", "items": _ID, "uniqueItems": True}

SCHEMA_MODELO: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "modelo.json da rede bayesiana",
    "type": "object",
    "required": ["projeto", "variaveis", "estrutura", "probabilidades",
                 "cenarios", "metadados_execucao"],
    "additionalProperties": False,
    "properties": {
        "projeto": {
            "type": "object",
            "required": ["tema", "pergunta_principal", "dataset"],
            "additionalProperties": False,
            "properties": {
                "tema": _TEXTO,
                "pergunta_principal": _TEXTO,
                "nota_causalidade": _TEXTO,
                "cpts_preliminares": {"type": "boolean"},
                "dataset": {
                    "type": "object",
                    "required": ["nome", "fonte"],
                    "additionalProperties": False,
                    "properties": {
                        "nome": _TEXTO,
                        "fonte": _TEXTO,
                        "url": {"type": "string"},
                        "uso": {"type": "string"},
                    },
                },
            },
        },
        "variaveis": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "nome", "descricao", "estados"],
                "additionalProperties": False,
                "properties": {
                    "id": _ID,
                    "nome": _TEXTO,
                    "descricao": _TEXTO,
                    "observavel": {"type": "boolean"},
                    "tipo": {"enum": ["raiz", "intermediaria", "latente", "alvo"]},
                    "estados": {
                        "type": "array",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "required": ["id", "interpretacao"],
                            "additionalProperties": False,
                            "properties": {"id": _ID, "interpretacao": _TEXTO},
                        },
                    },
                },
            },
        },
        "estrutura": {
            "type": "object",
            "required": ["arcos", "pais"],
            "additionalProperties": False,
            "properties": {
                "arcos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["de", "para", "justificativa"],
                        "additionalProperties": False,
                        "properties": {"de": _ID, "para": _ID, "justificativa": _TEXTO},
                    },
                },
                "pais": {"type": "object", "additionalProperties": _LISTA_IDS},
            },
        },
        "probabilidades": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["variavel", "pais", "estados", "linhas"],
                "additionalProperties": False,
                "properties": {
                    "variavel": _ID,
                    "pais": _LISTA_IDS,
                    "estados": {"type": "array", "items": _ID, "minItems": 2,
                                "uniqueItems": True},
                    "regra_geracao": {"type": "string"},
                    "linhas": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["configuracao_pais", "probabilidades"],
                            "additionalProperties": False,
                            "properties": {
                                "configuracao_pais": {"type": "object",
                                                      "additionalProperties": _ID},
                                "probabilidades": {
                                    "type": "object",
                                    "minProperties": 2,
                                    "additionalProperties": {
                                        "type": "number", "minimum": 0, "maximum": 1},
                                },
                            },
                        },
                    },
                },
            },
        },
        "cenarios": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "tipo_analise", "pergunta"],
                "properties": {
                    "id": _ID,
                    "tipo_analise": {"enum": ["descritiva", "diagnostica",
                                              "preditiva", "prescritiva"]},
                    "pergunta": _TEXTO,
                },
            },
        },
        "metadados_execucao": {
            "type": "object",
            "required": ["bibliotecas"],
            "properties": {
                "python": {"type": "string"},
                "bibliotecas": {"type": "object",
                                "additionalProperties": {"type": "string"}},
                "observacao": {"type": "string"},
            },
        },
    },
}

_VALIDADOR = Draft202012Validator(SCHEMA_MODELO)
_MAX_ERROS_NA_MENSAGEM = 5


def validar_contra_schema(modelo: Any) -> None:
    """Levanta ModeloInvalidoError listando onde o documento viola o schema."""
    erros = sorted(_VALIDADOR.iter_errors(modelo),
                   key=lambda e: [str(p) for p in e.absolute_path])
    if not erros:
        return
    linhas = []
    for erro in erros[:_MAX_ERROS_NA_MENSAGEM]:
        caminho = "/".join(str(p) for p in erro.absolute_path) or "(raiz)"
        linhas.append(f"  em {caminho} {erro.message[:200]}")
    extra = len(erros) - _MAX_ERROS_NA_MENSAGEM
    if extra > 0:
        linhas.append(f"  e mais {extra} erro(s)")
    raise ModeloInvalidoError("modelo.json não respeita o schema:\n" + "\n".join(linhas))