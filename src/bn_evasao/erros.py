"""Exceções compartilhadas do projeto. Qualquer erro de validação usa estas classes."""


class ErroBN(Exception):
    """Base de todos os erros do projeto."""


class ModeloInvalidoError(ErroBN):
    """modelo.json malformado, com chaves duplicadas, fora do schema ou semanticamente inconsistente."""


class CPTInvalidaError(ErroBN):
    """CPT com probabilidade fora de [0,1], soma diferente de 1, incompleta ou duplicada."""


class EvidenciaInvalidaError(ErroBN):
    """Evidência ou consulta com variável/estado inexistente, ou consulta repetida nas evidências."""


class CenarioInvalidoError(ErroBN):
    """Cenário mal definido (variante, expectativa ou decisão referenciando algo inexistente)."""