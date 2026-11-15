"""Testes do schema e do loader, usando docs/exemplos/modelo_exemplo.json.

Cada caso inválido parte de uma cópia do modelo válido e altera um único ponto,
então a falha esperada é sempre a que o teste descreve.
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from bn_evasao.erros import CPTInvalidaError, ModeloInvalidoError
from bn_evasao.loader import carregar_modelo, carregar_modelo_de_texto, validar_modelo
from bn_evasao.schema import SCHEMA_MODELO

EXEMPLO = Path(__file__).resolve().parents[1] / "docs" / "exemplos" / "modelo_exemplo.json"


@pytest.fixture
def modelo():
    """Cópia nova do modelo válido a cada teste."""
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


def cpt(modelo, var):
    return next(c for c in modelo["probabilidades"] if c["variavel"] == var)


def test_schema_e_um_schema_valido():
    Draft202012Validator.check_schema(SCHEMA_MODELO)


def test_exemplo_valido_carrega():
    modelo = carregar_modelo(EXEMPLO)
    assert [v["id"] for v in modelo["variaveis"]] == ["Chuva", "Grama_Molhada", "Guarda_Chuva"]


# ---------------------------------------------------------------------------
# Problemas de leitura
# ---------------------------------------------------------------------------
def test_arquivo_inexistente(tmp_path):
    with pytest.raises(ModeloInvalidoError, match="não encontrado"):
        carregar_modelo(tmp_path / "nao_existe.json")


def test_json_malformado(tmp_path):
    arq = tmp_path / "m.json"
    arq.write_text('{"projeto": ', encoding="utf-8")
    with pytest.raises(ModeloInvalidoError, match="malformado"):
        carregar_modelo(arq)


def test_chave_duplicada_no_mesmo_objeto():
    with pytest.raises(ModeloInvalidoError, match="duplicada"):
        carregar_modelo_de_texto('{"a": 1, "a": 2}')


def test_chave_duplicada_aninhada(modelo):
    texto = json.dumps(modelo).replace('"tema":', '"tema": "x", "tema":', 1)
    with pytest.raises(ModeloInvalidoError, match="duplicada"):
        carregar_modelo_de_texto(texto)


def test_nan_e_recusado(modelo):
    cpt(modelo, "Chuva")["linhas"][0]["probabilidades"]["Sim"] = float("nan")
    with pytest.raises(ModeloInvalidoError, match="NaN"):
        carregar_modelo_de_texto(json.dumps(modelo))


def test_raiz_que_nao_e_objeto():
    with pytest.raises(ModeloInvalidoError, match="objeto"):
        carregar_modelo_de_texto("[1, 2]")


# ---------------------------------------------------------------------------
# Problemas de schema e de estrutura (ModeloInvalidoError)
# ---------------------------------------------------------------------------
def _sem_cenarios(m):
    del m["cenarios"]


def _chave_com_typo(m):
    m["projeto"]["tema_typo"] = "x"


def _prob_acima_de_1(m):
    cpt(m, "Chuva")["linhas"][0]["probabilidades"] = {"Sim": 1.2, "Nao": -0.2}


def _prob_negativa(m):
    cpt(m, "Chuva")["linhas"][0]["probabilidades"] = {"Sim": 1.1, "Nao": -0.1}


def _arco_com_variavel_inexistente(m):
    m["estrutura"]["arcos"].append(
        {"de": "Fantasma", "para": "Chuva", "justificativa": "teste"})


def _pais_diferem_dos_arcos(m):
    m["estrutura"]["pais"]["Grama_Molhada"] = []


def _ciclo(m):
    m["estrutura"]["arcos"].append(
        {"de": "Grama_Molhada", "para": "Chuva", "justificativa": "teste"})
    m["estrutura"]["pais"]["Chuva"] = ["Grama_Molhada"]


def _variavel_duplicada(m):
    m["variaveis"].append(dict(m["variaveis"][0]))


def _estado_duplicado(m):
    m["variaveis"][0]["estados"].append(dict(m["variaveis"][0]["estados"][0]))


def _cenario_duplicado(m):
    m["cenarios"].append(dict(m["cenarios"][0]))


CASOS_MODELO_INVALIDO = [
    pytest.param(_sem_cenarios, "cenarios", id="chave_obrigatoria_ausente"),
    pytest.param(_chave_com_typo, "tema_typo", id="chave_desconhecida"),
    pytest.param(_prob_acima_de_1, "1.2", id="probabilidade_acima_de_1"),
    pytest.param(_prob_negativa, "-0.1", id="probabilidade_negativa"),
    pytest.param(_arco_com_variavel_inexistente, "inexistente", id="arco_com_pai_inexistente"),
    pytest.param(_pais_diferem_dos_arcos, "não bate", id="pais_diferem_dos_arcos"),
    pytest.param(_ciclo, "ciclo", id="ciclo_injetado"),
    pytest.param(_variavel_duplicada, "duplicado", id="variavel_duplicada"),
    pytest.param(_estado_duplicado, "duplicados", id="estado_duplicado"),
    pytest.param(_cenario_duplicado, "duplicado", id="cenario_duplicado"),
]


@pytest.mark.parametrize("alterar, trecho", CASOS_MODELO_INVALIDO)
def test_modelo_invalido(modelo, alterar, trecho):
    alterar(modelo)
    with pytest.raises(ModeloInvalidoError, match=trecho):
        validar_modelo(modelo)


def test_mensagem_do_ciclo_mostra_o_caminho(modelo):
    _ciclo(modelo)
    with pytest.raises(ModeloInvalidoError) as info:
        validar_modelo(modelo)
    assert "Chuva → Grama_Molhada → Chuva" in str(info.value)


# ---------------------------------------------------------------------------
# Problemas de CPT (CPTInvalidaError)
# ---------------------------------------------------------------------------
def _soma_diferente_de_1(m):
    cpt(m, "Grama_Molhada")["linhas"][0]["probabilidades"]["Sim"] = 0.5


def _linha_faltando(m):
    cpt(m, "Grama_Molhada")["linhas"].pop()


def _linha_repetida(m):
    linhas = cpt(m, "Grama_Molhada")["linhas"]
    linhas[1]["configuracao_pais"] = dict(linhas[0]["configuracao_pais"])


def _estado_inexistente_no_pai(m):
    cpt(m, "Grama_Molhada")["linhas"][0]["configuracao_pais"]["Chuva"] = "Talvez"


def _estado_inexistente_na_probabilidade(m):
    cpt(m, "Grama_Molhada")["linhas"][0]["probabilidades"] = {"Sim": 0.9, "Talvez": 0.1}


def _cpt_ausente(m):
    m["probabilidades"].pop()


def _cpt_repetida(m):
    m["probabilidades"].append(json.loads(json.dumps(m["probabilidades"][0])))


def _pais_da_cpt_diferem_da_estrutura(m):
    cpt(m, "Grama_Molhada")["pais"] = []


def _soma_quase_1_dentro_da_tolerancia(m):
    cpt(m, "Chuva")["linhas"][0]["probabilidades"] = {"Sim": 0.3, "Nao": 0.7 + 1e-9}


CASOS_CPT_INVALIDA = [
    pytest.param(_soma_diferente_de_1, "somam", id="soma_diferente_de_1"),
    pytest.param(_linha_faltando, "incompleta", id="cpt_incompleta"),
    pytest.param(_linha_repetida, "repetida", id="configuracao_repetida"),
    pytest.param(_estado_inexistente_no_pai, "Talvez", id="estado_inexistente_no_pai"),
    pytest.param(_estado_inexistente_na_probabilidade, "diferem", id="estado_inexistente_na_prob"),
    pytest.param(_cpt_ausente, "sem CPT", id="variavel_sem_cpt"),
    pytest.param(_cpt_repetida, "mais de uma CPT", id="cpt_repetida"),
    pytest.param(_pais_da_cpt_diferem_da_estrutura, "declara pais", id="pais_da_cpt_errados"),
]


@pytest.mark.parametrize("alterar, trecho", CASOS_CPT_INVALIDA)
def test_cpt_invalida(modelo, alterar, trecho):
    alterar(modelo)
    with pytest.raises(CPTInvalidaError, match=trecho):
        validar_modelo(modelo)


def test_soma_dentro_da_tolerancia_e_aceita(modelo):
    _soma_quase_1_dentro_da_tolerancia(modelo)
    validar_modelo(modelo)


# ---------------------------------------------------------------------------
# Campos opcionais escritos pelo gerador, tipo e cpts_preliminares
# ---------------------------------------------------------------------------
def _com_tipos_coerentes(m):
    m["variaveis"][0]["tipo"] = "raiz"
    m["variaveis"][1]["tipo"] = "intermediaria"
    m["variaveis"][2]["tipo"] = "alvo"
    m["projeto"]["cpts_preliminares"] = False


def test_tipo_e_cpts_preliminares_coerentes_sao_aceitos(modelo):
    _com_tipos_coerentes(modelo)
    validar_modelo(modelo)


def _raiz_com_pais(m):
    m["variaveis"][1]["tipo"] = "raiz"


def _intermediaria_sem_pais(m):
    m["variaveis"][0]["tipo"] = "intermediaria"


def _latente_observavel(m):
    m["variaveis"][1]["tipo"] = "latente"


def _tipo_desconhecido(m):
    m["variaveis"][0]["tipo"] = "chefe"


def _preliminar_nao_booleano(m):
    m["projeto"]["cpts_preliminares"] = "sim"


CASOS_TIPO_INVALIDO = [
    pytest.param(_raiz_com_pais, "tipo 'raiz'", id="raiz_com_pais"),
    pytest.param(_intermediaria_sem_pais, "tipo 'intermediaria'", id="intermediaria_sem_pais"),
    pytest.param(_latente_observavel, "tipo 'latente'", id="latente_marcada_como_observavel"),
    pytest.param(_tipo_desconhecido, "chefe", id="tipo_desconhecido"),
    pytest.param(_preliminar_nao_booleano, "sim", id="cpts_preliminares_nao_booleano"),
]


@pytest.mark.parametrize("alterar, trecho", CASOS_TIPO_INVALIDO)
def test_tipo_ou_flag_invalidos(modelo, alterar, trecho):
    alterar(modelo)
    with pytest.raises(ModeloInvalidoError, match=trecho):
        validar_modelo(modelo)


def test_latente_nao_observavel_e_aceita(modelo):
    modelo["variaveis"][1]["tipo"] = "latente"
    modelo["variaveis"][1]["observavel"] = False
    validar_modelo(modelo)