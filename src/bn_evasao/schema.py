"""Esquema JSON (jsonschema) para validação estrutural do modelo.json."""
from __future__ import annotations

import jsonschema

MODELO_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "projeto",
        "variaveis",
        "estrutura",
        "probabilidades",
        "cenarios",
        "metadados_execucao",
    ],
    "additionalProperties": False,
    "properties": {
        "projeto": {
            "type": "object",
            "required": [
                "tema",
                "pergunta_principal",
                "dataset",
                "nota_causalidade",
            ],
            "properties": {
                "tema": {"type": "string", "minLength": 1},
                "pergunta_principal": {"type": "string", "minLength": 1},
                "dataset": {
                    "type": "object",
                    "required": ["nome", "fonte", "url", "uso"],
                    "properties": {
                        "nome": {"type": "string", "minLength": 1},
                        "fonte": {"type": "string", "minLength": 1},
                        "url": {"type": "string", "minLength": 1},
                        "uso": {"type": "string", "minLength": 1},
                    },
                },
                "nota_causalidade": {"type": "string", "minLength": 1},
                "cpts_preliminares": {"type": "boolean"},
            },
        },
        "variaveis": {
            "type": "array",
            "minItems": 10,
            "items": {
                "type": "object",
                "required": ["id", "nome", "descricao", "estados"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "nome": {"type": "string", "minLength": 1},
                    "descricao": {"type": "string", "minLength": 1},
                    "tipo": {
                        "type": "string",
                        "enum": ["raiz", "intermediaria", "latente", "alvo"],
                    },
                    "observavel": {"type": "boolean"},
                    "estados": {
                        "type": "array",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "required": ["id", "interpretacao"],
                            "properties": {
                                "id": {"type": "string", "minLength": 1},
                                "interpretacao": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                },
            },
        },
        "estrutura": {
            "type": "object",
            "required": ["arcos", "pais"],
            "properties": {
                "arcos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["de", "para"],
                        "properties": {
                            "de": {"type": "string", "minLength": 1},
                            "para": {"type": "string", "minLength": 1},
                            "justificativa": {"type": "string"},
                        },
                    },
                },
                "pais": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "probabilidades": {
            "type": "array",
            "minItems": 10,
            "items": {
                "type": "object",
                "required": ["variavel", "pais", "estados", "linhas"],
                "properties": {
                    "variavel": {"type": "string", "minLength": 1},
                    "pais": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "estados": {
                        "type": "array",
                        "minItems": 2,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "linhas": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["configuracao_pais", "probabilidades"],
                            "properties": {
                                "configuracao_pais": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                },
                                "probabilidades": {
                                    "type": "object",
                                    "additionalProperties": {
                                        "type": "number",
                                        "minimum": 0.0,
                                        "maximum": 1.0,
                                    },
                                },
                            },
                        },
                    },
                    "regra_geracao": {"type": "string"},
                },
            },
        },
        "cenarios": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "tipo_analise",
                    "pergunta",
                    "evidencias_base",
                    "variantes",
                    "consultas",
                    "relevancia",
                    "limitacoes",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "tipo_analise": {"type": "string", "minLength": 1},
                    "pergunta": {"type": "string", "minLength": 1},
                    "evidencias_base": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "variantes": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["id", "evidencias_adicionais"],
                            "properties": {
                                "id": {"type": "string", "minLength": 1},
                                "descricao": {"type": "string"},
                                "evidencias_adicionais": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                },
                            },
                        },
                    },
                    "consultas": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "expectativas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "tipo",
                                "consulta",
                                "estado",
                                "maior",
                                "menor",
                            ],
                            "properties": {
                                "tipo": {"type": "string"},
                                "consulta": {"type": "string"},
                                "estado": {"type": "string"},
                                "maior": {"type": "string"},
                                "menor": {"type": "string"},
                                "fundamentacao": {"type": "string"},
                            },
                        },
                    },
                    "decisao": {
                        "type": "object",
                        "required": ["consulta", "utilidades", "alternativas"],
                        "properties": {
                            "consulta": {"type": "string"},
                            "utilidades": {
                                "type": "object",
                                "additionalProperties": {"type": "number"},
                            },
                            "alternativas": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "required": ["variante", "custo"],
                                    "properties": {
                                        "variante": {"type": "string"},
                                        "custo": {"type": "number"},
                                    },
                                },
                            },
                            "nota": {"type": "string"},
                        },
                    },
                    "relevancia": {"type": "string", "minLength": 1},
                    "limitacoes": {"type": "string", "minLength": 1},
                },
            },
        },
        "metadados_execucao": {
            "type": "object",
            "required": ["bibliotecas"],
            "properties": {
                "python_minimo": {"type": "string"},
                "bibliotecas": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "observacao": {"type": "string"},
            },
        },
    },
}


def validar_schema(dados: dict) -> None:
    """Valida o dicionário carregado do JSON contra o esquema oficial."""
    jsonschema.validate(instance=dados, schema=MODELO_SCHEMA)