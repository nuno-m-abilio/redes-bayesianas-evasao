
"""Testes de construir_rede, consultar e comparar_evidencias.
 
A verdade de referência vem de duas fontes independentes do pgmpy: contas escritas
à mão no teste (regra de Bayes) e um enumerador da distribuição conjunta que lê
direto o dict do modelo. Nenhum número foi copiado da saída do código.
"""
import copy
import itertools
import json
import math
from pathlib import Path
 
import pytest
 
from bn_evasao.erros import CPTInvalidaError, EvidenciaInvalidaError, ModeloInvalidoError
from bn_evasao.inference import comparar_evidencias, consultar
from bn_evasao.loader import carregar_modelo
from bn_evasao.network import construir_rede
 
EXEMPLO = Path(__file__).resolve().parents[1] / "docs" / "exemplos" / "modelo_exemplo.json"
ABS = 1e-9
 
 
# ---------------------------------------------------------------------------
# Modelos de apoio
# ---------------------------------------------------------------------------
def _var(id_, estados):
    return {"id": id_, "nome": id_, "descricao": f"variável {id_}", "observavel": True,
            "estados": [{"id": e, "interpretacao": f"estado {e}"} for e in estados]}
 
 
def _cpt(var, pais, estados, linhas):
    return {"variavel": var, "pais": pais, "estados": estados,
            "linhas": [{"configuracao_pais": c, "probabilidades": p} for c, p in linhas]}
 
 
def modelo_abc():
    """A (3 estados) e B (2 estados) são pais de C (2 estados).
 
    A CPT de C declara os pais na ordem ["B", "A"], oposta à dos arcos, e lista as
    linhas fora da ordem do produto cartesiano. Qualquer montagem por posição erra.
    """
    modelo = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    modelo["variaveis"] = [_var("A", ["X1", "X2", "X3"]), _var("B", ["Y1", "Y2"]),
                           _var("C", ["Z1", "Z2"])]
    modelo["estrutura"] = {
        "arcos": [{"de": "A", "para": "C", "justificativa": "teste"},
                  {"de": "B", "para": "C", "justificativa": "teste"}],
        "pais": {"A": [], "B": [], "C": ["A", "B"]},
    }
    p_z1 = {("Y1", "X1"): 0.10, ("Y1", "X2"): 0.25, ("Y1", "X3"): 0.40,
            ("Y2", "X1"): 0.55, ("Y2", "X2"): 0.70, ("Y2", "X3"): 0.90}
    ordem_embaralhada = [("Y2", "X2"), ("Y1", "X3"), ("Y1", "X1"),
                         ("Y2", "X3"), ("Y1", "X2"), ("Y2", "X1")]
    linhas_c = [({"B": y, "A": x}, {"Z1": p_z1[(y, x)], "Z2": 1 - p_z1[(y, x)]})
                for y, x in ordem_embaralhada]
    modelo["probabilidades"] = [
        _cpt("A", [], ["X1", "X2", "X3"],
             [({}, {"X1": 0.2, "X2": 0.5, "X3": 0.3})]),
        _cpt("B", [], ["Y1", "Y2"], [({}, {"Y1": 0.6, "Y2": 0.4})]),
        _cpt("C", ["B", "A"], ["Z1", "Z2"], linhas_c),
    ]
    return modelo
 
 
def probabilidade_exata(modelo, consulta, evidencias):
    """P(consulta | evidencias) por enumeração da conjunta, sem pgmpy."""
    estados = {v["id"]: [e["id"] for e in v["estados"]] for v in modelo["variaveis"]}
    tabelas = {}
    for cpt in modelo["probabilidades"]:
        tabelas[cpt["variavel"]] = (
            cpt["pais"],
            {tuple(l["configuracao_pais"][p] for p in cpt["pais"]): l["probabilidades"]
             for l in cpt["linhas"]})
    variaveis = list(estados)
    pesos = {e: 0.0 for e in estados[consulta]}
    for combinacao in itertools.product(*(estados[v] for v in variaveis)):
        atribuicao = dict(zip(variaveis, combinacao))
        if any(atribuicao[v] != e for v, e in evidencias.items()):
            continue
        conjunta = 1.0
        for var, (pais, tabela) in tabelas.items():
            conjunta *= tabela[tuple(atribuicao[p] for p in pais)][atribuicao[var]]
        pesos[atribuicao[consulta]] += conjunta
    total = sum(pesos.values())
    return {e: p / total for e, p in pesos.items()}
 
 
@pytest.fixture(scope="module")
def modelo_exemplo():
    return carregar_modelo(EXEMPLO)
 
 
@pytest.fixture(scope="module")
def rede_exemplo(modelo_exemplo):
    return construir_rede(modelo_exemplo)
 
 
@pytest.fixture(scope="module")
def rede_abc():
    return construir_rede(modelo_abc())
 
 
# ---------------------------------------------------------------------------
# construir_rede
# ---------------------------------------------------------------------------
def test_rede_do_exemplo_bate_com_o_json(modelo_exemplo, rede_exemplo):
    assert set(rede_exemplo.nodes()) == {v["id"] for v in modelo_exemplo["variaveis"]}
    assert set(rede_exemplo.edges()) == {(a["de"], a["para"])
                                         for a in modelo_exemplo["estrutura"]["arcos"]}
    assert rede_exemplo.check_model()
 
 
def test_state_names_seguem_a_ordem_das_variaveis(rede_abc):
    assert list(rede_abc.get_cpds("A").state_names["A"]) == ["X1", "X2", "X3"]
    assert list(rede_abc.get_cpds("C").state_names["C"]) == ["Z1", "Z2"]
 
 
def test_cpt_celula_por_celula_com_pais_em_ordem_trocada(rede_abc):
    """Compara cada linha do JSON com a CPT do pgmpy, indexando por nome de estado."""
    modelo = modelo_abc()
    cpd = rede_abc.get_cpds("C")
    # values tem formato (estados de C, *estados dos pais na ordem de cpd.variables[1:])
    pais_do_cpd = cpd.variables[1:]
    cpt_c = next(c for c in modelo["probabilidades"] if c["variavel"] == "C")
    for linha in cpt_c["linhas"]:
        indices = [list(cpd.state_names[p]).index(linha["configuracao_pais"][p])
                   for p in pais_do_cpd]
        for estado, esperado in linha["probabilidades"].items():
            i = list(cpd.state_names["C"]).index(estado)
            assert cpd.values[(i, *indices)] == pytest.approx(esperado, abs=ABS)
 
 
def test_construir_rede_recusa_ciclo():
    modelo = modelo_abc()
    modelo["estrutura"]["arcos"].append({"de": "C", "para": "A", "justificativa": "teste"})
    modelo["estrutura"]["pais"]["A"] = ["C"]
    with pytest.raises(ModeloInvalidoError, match="ciclo"):
        construir_rede(modelo)
 
 
def test_construir_rede_recusa_cpt_com_soma_errada():
    modelo = modelo_abc()
    modelo["probabilidades"][1]["linhas"][0]["probabilidades"]["Y1"] = 0.9
    with pytest.raises(CPTInvalidaError, match="somam"):
        construir_rede(modelo)
 
 
# ---------------------------------------------------------------------------
# consultar, contra contas feitas à mão
# ---------------------------------------------------------------------------
def test_bayes_a_mao_no_exemplo(rede_exemplo):
    # P(Chuva=Sim | Grama=Sim) = 0,3*0,9 / (0,3*0,9 + 0,7*0,2)
    esperado = (0.3 * 0.9) / (0.3 * 0.9 + 0.7 * 0.2)
    resultado = consultar(rede_exemplo, ["Chuva"], {"Grama_Molhada": "Sim"})
    assert resultado["Chuva"]["Sim"] == pytest.approx(esperado, abs=ABS)
    assert resultado["Chuva"]["Nao"] == pytest.approx(1 - esperado, abs=ABS)
 
 
def test_marginal_sem_evidencia_a_mao(rede_exemplo):
    # P(Grama=Sim) = 0,3*0,9 + 0,7*0,2
    resultado = consultar(rede_exemplo, ["Grama_Molhada"], {})
    assert resultado["Grama_Molhada"]["Sim"] == pytest.approx(0.3 * 0.9 + 0.7 * 0.2, abs=ABS)
 
 
def test_resultado_usa_nomes_e_e_normalizado(rede_exemplo):
    resultado = consultar(rede_exemplo, ["Chuva", "Guarda_Chuva"], {"Grama_Molhada": "Sim"})
    assert list(resultado) == ["Chuva", "Guarda_Chuva"]
    for distribuicao in resultado.values():
        assert set(distribuicao) == {"Sim", "Nao"}
        assert math.fsum(distribuicao.values()) == pytest.approx(1.0, abs=1e-6)
 
 
# ---------------------------------------------------------------------------
# consultar, contra enumeração da conjunta (CPT de 2 pais com ordem trocada)
# ---------------------------------------------------------------------------
CASOS_EVIDENCIA = [
    pytest.param("C", {}, id="marginal_de_C"),
    pytest.param("A", {}, id="marginal_de_A"),
    pytest.param("C", {"A": "X3"}, id="C_dado_A"),
    pytest.param("C", {"B": "Y2"}, id="C_dado_B"),
    pytest.param("C", {"A": "X1", "B": "Y2"}, id="C_dado_A_e_B"),
    pytest.param("A", {"C": "Z1"}, id="A_dado_C"),
    pytest.param("B", {"C": "Z2", "A": "X2"}, id="B_dado_C_e_A"),
    pytest.param("A", {"C": "Z1", "B": "Y1"}, id="A_dado_C_e_B"),
]
 
 
@pytest.mark.parametrize("consulta, evidencias", CASOS_EVIDENCIA)
def test_consulta_bate_com_enumeracao_da_conjunta(rede_abc, consulta, evidencias):
    esperado = probabilidade_exata(modelo_abc(), consulta, evidencias)
    obtido = consultar(rede_abc, [consulta], evidencias)[consulta]
    assert set(obtido) == set(esperado)
    for estado, p in esperado.items():
        assert obtido[estado] == pytest.approx(p, abs=ABS)
 
 
def test_ordem_das_evidencias_nao_altera_o_resultado(rede_abc):
    a = consultar(rede_abc, ["A"], {"C": "Z1", "B": "Y1"})
    b = consultar(rede_abc, ["A"], {"B": "Y1", "C": "Z1"})
    for estado in a["A"]:
        assert a["A"][estado] == pytest.approx(b["A"][estado], abs=ABS)
 
 
def test_varias_consultas_sao_marginais_separadas(rede_abc):
    juntas = consultar(rede_abc, ["A", "B"], {"C": "Z1"})
    for var in ("A", "B"):
        sozinha = consultar(rede_abc, [var], {"C": "Z1"})[var]
        assert math.fsum(juntas[var].values()) == pytest.approx(1.0, abs=1e-6)
        for estado, p in sozinha.items():
            assert juntas[var][estado] == pytest.approx(p, abs=ABS)
 
 
def test_consultas_repetidas_sao_unificadas(rede_exemplo):
    assert list(consultar(rede_exemplo, ["Chuva", "Chuva"], {})) == ["Chuva"]
 
 
# ---------------------------------------------------------------------------
# Propriedades probabilísticas
# ---------------------------------------------------------------------------
def test_d_separacao_irmaos_dado_o_pai(rede_exemplo):
    """Grama_Molhada e Guarda_Chuva são independentes dado Chuva."""
    base = consultar(rede_exemplo, ["Guarda_Chuva"], {"Chuva": "Sim"})["Guarda_Chuva"]
    com_irmao = consultar(rede_exemplo, ["Guarda_Chuva"],
                          {"Chuva": "Sim", "Grama_Molhada": "Sim"})["Guarda_Chuva"]
    for estado, p in base.items():
        assert com_irmao[estado] == pytest.approx(p, abs=ABS)
 
 
def test_irmaos_sao_dependentes_sem_observar_o_pai(rede_exemplo):
    sem = consultar(rede_exemplo, ["Guarda_Chuva"], {})["Guarda_Chuva"]["Sim"]
    com = consultar(rede_exemplo, ["Guarda_Chuva"], {"Grama_Molhada": "Sim"})["Guarda_Chuva"]["Sim"]
    assert com > sem
 
 
def test_pais_independentes_sem_observar_o_filho(rede_abc):
    base = consultar(rede_abc, ["A"], {})["A"]
    com_b = consultar(rede_abc, ["A"], {"B": "Y1"})["A"]
    for estado, p in base.items():
        assert com_b[estado] == pytest.approx(p, abs=ABS)
 
 
def test_explaining_away(rede_abc):
    """Observado o filho, saber B muda a crença sobre A (pais ficam dependentes)."""
    sem_b = consultar(rede_abc, ["A"], {"C": "Z1"})["A"]
    com_b = consultar(rede_abc, ["A"], {"C": "Z1", "B": "Y2"})["A"]
    assert any(abs(sem_b[e] - com_b[e]) > 1e-3 for e in sem_b)
 
 
# ---------------------------------------------------------------------------
# Evidências e consultas inválidas
# ---------------------------------------------------------------------------
def test_consulta_vazia(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="Nenhuma variável"):
        consultar(rede_exemplo, [], {})
 
 
def test_consulta_como_string(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="lista"):
        consultar(rede_exemplo, "Chuva", {})
 
 
def test_variavel_consultada_inexistente_com_sugestao(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="Você quis dizer 'Chuva'"):
        consultar(rede_exemplo, ["Chuvaa"], {})
 
 
def test_variavel_de_evidencia_inexistente(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="não existe na rede"):
        consultar(rede_exemplo, ["Chuva"], {"Fantasma": "Sim"})
 
 
def test_estado_de_evidencia_inexistente(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="Estados válidos"):
        consultar(rede_exemplo, ["Chuva"], {"Grama_Molhada": "Talvez"})
 
 
def test_variavel_consultada_tambem_em_evidencia(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="consulta e como evidência"):
        consultar(rede_exemplo, ["Chuva"], {"Chuva": "Sim"})
 
 
def test_evidencia_de_probabilidade_zero(modelo_exemplo):
    modelo = copy.deepcopy(modelo_exemplo)
    modelo["probabilidades"][0]["linhas"][0]["probabilidades"] = {"Sim": 1.0, "Nao": 0.0}
    modelo["probabilidades"][1]["linhas"][0]["probabilidades"] = {"Sim": 1.0, "Nao": 0.0}
    rede = construir_rede(modelo)
    # Chuva=Sim com certeza e Grama molhada com certeza, então Grama=Nao é impossível.
    with pytest.raises(EvidenciaInvalidaError, match="probabilidade zero"):
        consultar(rede, ["Chuva"], {"Grama_Molhada": "Nao"})
 
 
# ---------------------------------------------------------------------------
# comparar_evidencias
# ---------------------------------------------------------------------------
def test_comparar_evidencias_a_mao(rede_exemplo):
    resultado = comparar_evidencias(rede_exemplo, "Chuva", "Sim", {
        "molhada": {"Grama_Molhada": "Sim"},
        "seca": {"Grama_Molhada": "Nao"},
        "nada": {},
    })
    assert list(resultado) == ["molhada", "seca", "nada"]
    assert resultado["molhada"] == pytest.approx(0.3 * 0.9 / (0.3 * 0.9 + 0.7 * 0.2), abs=ABS)
    assert resultado["seca"] == pytest.approx(0.3 * 0.1 / (0.3 * 0.1 + 0.7 * 0.8), abs=ABS)
    assert resultado["nada"] == pytest.approx(0.3, abs=ABS)
    assert resultado["molhada"] > resultado["nada"] > resultado["seca"]
 
 
def test_comparar_evidencias_estado_inexistente(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="não existe na variável"):
        comparar_evidencias(rede_exemplo, "Chuva", "Talvez", {"x": {}})
 
 
def test_comparar_evidencias_sem_conjuntos(rede_exemplo):
    with pytest.raises(EvidenciaInvalidaError, match="Nenhum conjunto"):
        comparar_evidencias(rede_exemplo, "Chuva", "Sim", {})
 