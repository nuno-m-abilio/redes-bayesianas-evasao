"""Casos inválidos: cada teste confere o TIPO da exceção e parte da mensagem."""
import pytest

from bn_evasao.loader import ErroValidacaoModelo, carregar_modelo, validar_modelo_dict
from bn_evasao.network import construir_rede_do_dicionario


def _cpt(m, var):
    return next(c for c in m["probabilidades"] if c["variavel"] == var)


# ---------------- arquivo e sintaxe ----------------
def test_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        carregar_modelo(tmp_path / "nao_existe.json")


def test_json_malformado(escrever_json):
    with pytest.raises(ErroValidacaoModelo, match="JSON malformado"):
        carregar_modelo(escrever_json('{"projeto": '))


def test_chave_duplicada(escrever_json):
    with pytest.raises(ErroValidacaoModelo, match="Chave duplicada"):
        carregar_modelo(escrever_json('{"projeto": {}, "projeto": {}}'))


# ---------------- schema ----------------
@pytest.mark.parametrize("chave", ["projeto", "variaveis", "estrutura", "probabilidades", "cenarios",
                                   "metadados_execucao"])
def test_chave_obrigatoria_ausente(modelo_copia, chave):
    del modelo_copia[chave]
    with pytest.raises(ErroValidacaoModelo, match="JSON Schema"):
        validar_modelo_dict(modelo_copia)


def test_chave_de_topo_desconhecida(modelo_copia):
    modelo_copia["typo"] = 1
    with pytest.raises(ErroValidacaoModelo, match="JSON Schema"):
        validar_modelo_dict(modelo_copia)


@pytest.mark.parametrize("valor", [1.2, -0.1])
def test_probabilidade_fora_do_intervalo(modelo_copia, valor):
    _cpt(modelo_copia, "Bolsista")["linhas"][0]["probabilidades"]["Sim"] = valor
    with pytest.raises(ErroValidacaoModelo):
        validar_modelo_dict(modelo_copia)


def test_menos_de_dez_variaveis(modelo_copia):
    modelo_copia["variaveis"] = modelo_copia["variaveis"][:9]
    with pytest.raises(ErroValidacaoModelo):
        validar_modelo_dict(modelo_copia)


# ---------------- CPTs ----------------
def test_soma_diferente_de_um(modelo_copia):
    _cpt(modelo_copia, "Desfecho")["linhas"][0]["probabilidades"]["Dropout"] += 0.05
    with pytest.raises(ErroValidacaoModelo, match="somam"):
        validar_modelo_dict(modelo_copia)


def test_cpt_incompleta_falta_configuracao(modelo_copia):
    _cpt(modelo_copia, "Desfecho")["linhas"].pop()
    with pytest.raises(ErroValidacaoModelo, match="incompleta"):
        validar_modelo_dict(modelo_copia)


def test_configuracao_de_pais_duplicada(modelo_copia):
    linhas = _cpt(modelo_copia, "Desfecho")["linhas"]
    linhas[1] = {"configuracao_pais": dict(linhas[0]["configuracao_pais"]),
                 "probabilidades": dict(linhas[0]["probabilidades"])}
    with pytest.raises(ErroValidacaoModelo, match="duplicada"):
        validar_modelo_dict(modelo_copia)


def test_estado_invalido_na_configuracao_de_pais(modelo_copia):
    _cpt(modelo_copia, "Desfecho")["linhas"][0]["configuracao_pais"]["Desemprego"] = "Medio"
    with pytest.raises(ErroValidacaoModelo, match="estado inválido"):
        validar_modelo_dict(modelo_copia)


def test_estado_inexistente_nas_probabilidades(modelo_copia):
    probs = _cpt(modelo_copia, "Bolsista")["linhas"][0]["probabilidades"]
    probs["Talvez"] = probs.pop("Sim")
    with pytest.raises(ErroValidacaoModelo, match="diferem"):
        validar_modelo_dict(modelo_copia)


def test_estados_da_cpt_diferem_da_variavel(modelo_copia):
    _cpt(modelo_copia, "Bolsista")["estados"] = ["Nao", "Sim"]
    with pytest.raises(ErroValidacaoModelo, match="diferem da definição"):
        validar_modelo_dict(modelo_copia)


def test_variavel_sem_cpt(modelo_copia):
    modelo_copia["probabilidades"] = [c for c in modelo_copia["probabilidades"] if c["variavel"] != "Devedor"]
    with pytest.raises(ErroValidacaoModelo, match="sem CPT"):
        validar_modelo_dict(modelo_copia)


def test_cpt_duplicada(modelo_copia):
    modelo_copia["probabilidades"].append(_cpt(modelo_copia, "Bolsista"))
    with pytest.raises(ErroValidacaoModelo, match="duplicada"):
        validar_modelo_dict(modelo_copia)


def test_cpt_para_variavel_inexistente(modelo_copia):
    extra = dict(_cpt(modelo_copia, "Bolsista"))
    extra["variavel"] = "Fantasma"
    modelo_copia["probabilidades"].append(extra)
    with pytest.raises(ErroValidacaoModelo, match="inexistente"):
        validar_modelo_dict(modelo_copia)


# ---------------- estrutura ----------------
def test_ciclo_injetado(modelo_copia):
    modelo_copia["estrutura"]["arcos"].append({"de": "Desfecho", "para": "Area_Curso", "justificativa": "x"})
    modelo_copia["estrutura"]["pais"]["Area_Curso"] = ["Desfecho"]
    with pytest.raises(ErroValidacaoModelo, match="acíclico"):
        validar_modelo_dict(modelo_copia)


def test_auto_loop(modelo_copia):
    modelo_copia["estrutura"]["arcos"].append({"de": "Bolsista", "para": "Bolsista", "justificativa": "x"})
    with pytest.raises(ErroValidacaoModelo, match="Auto-loop"):
        validar_modelo_dict(modelo_copia)


def test_pai_inexistente_no_arco(modelo_copia):
    modelo_copia["estrutura"]["arcos"][0]["de"] = "Inexistente"
    with pytest.raises(ErroValidacaoModelo, match="inexistente"):
        validar_modelo_dict(modelo_copia)


def test_arco_duplicado(modelo_copia):
    modelo_copia["estrutura"]["arcos"].append(dict(modelo_copia["estrutura"]["arcos"][0]))
    with pytest.raises(ErroValidacaoModelo, match="duplicado"):
        validar_modelo_dict(modelo_copia)


def test_pais_inconsistentes_com_arcos(modelo_copia):
    modelo_copia["estrutura"]["pais"]["Desfecho"] = ["Desemprego"]
    with pytest.raises(ErroValidacaoModelo, match="Inconsistência"):
        validar_modelo_dict(modelo_copia)


def test_variavel_duplicada(modelo_copia):
    modelo_copia["variaveis"].append(dict(modelo_copia["variaveis"][0]))
    with pytest.raises(ErroValidacaoModelo, match="duplicada"):
        validar_modelo_dict(modelo_copia)


def test_estados_duplicados_na_variavel(modelo_copia):
    var = next(v for v in modelo_copia["variaveis"] if v["id"] == "Bolsista")
    var["estados"].append(dict(var["estados"][0]))
    with pytest.raises(ErroValidacaoModelo, match="Estados duplicados"):
        validar_modelo_dict(modelo_copia)


# ---------------- cenários ----------------
def test_cenario_com_estado_inexistente_na_evidencia(modelo_copia):
    modelo_copia["cenarios"][0]["evidencias_base"] = {"Turno": "Madrugada"}
    with pytest.raises(ErroValidacaoModelo, match="estado inválido"):
        validar_modelo_dict(modelo_copia)


def test_cenario_com_variavel_inexistente_na_consulta(modelo_copia):
    modelo_copia["cenarios"][0]["consultas"] = ["Fantasma"]
    with pytest.raises(ErroValidacaoModelo, match="consulta inexistente"):
        validar_modelo_dict(modelo_copia)


def test_expectativa_com_variante_inexistente(modelo_copia):
    modelo_copia["cenarios"][0]["expectativas"][0]["maior"] = "variante_fantasma"
    with pytest.raises(ErroValidacaoModelo, match="variante inexistente"):
        validar_modelo_dict(modelo_copia)


def test_cenario_duplicado(modelo_copia):
    modelo_copia["cenarios"].append(dict(modelo_copia["cenarios"][0]))
    with pytest.raises(ErroValidacaoModelo, match="duplicado"):
        validar_modelo_dict(modelo_copia)


# ---------------- construção da rede ----------------
def test_construir_rede_recusa_modelo_invalido(modelo_copia):
    _cpt(modelo_copia, "Desfecho")["linhas"].pop()
    with pytest.raises(ErroValidacaoModelo):
        construir_rede_do_dicionario(modelo_copia)