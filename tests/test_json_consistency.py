"""Consistência modelo.json <-> rede implementada <-> código-fonte <-> dados."""
import importlib.util
import json
from pathlib import Path

import pytest

from bn_evasao import definicao as d

RAIZ = Path(__file__).resolve().parents[1]


def test_cada_cpt_do_json_bate_celula_a_celula_com_a_rede(modelo, rede):
    for cpt in modelo["probabilidades"]:
        var = cpt["variavel"]
        cpd = rede.get_cpds(var)
        for linha in cpt["linhas"]:
            for estado, prob in linha["probabilidades"].items():
                atribuicao = {var: estado, **linha["configuracao_pais"]}
                assert cpd.get_value(**atribuicao) == pytest.approx(prob, abs=1e-12), atribuicao


def test_pais_e_estados_das_cpds_batem_com_definicao(rede):
    for var in d.VARIAVEIS:
        cpd = rede.get_cpds(var)
        assert list(cpd.state_names[var]) == d.ESTADOS[var]
        assert set(rede.get_parents(var)) == set(d.PAIS[var])


def test_modelo_json_nao_esta_desatualizado(modelo):
    """Regenera o modelo a partir de definicao.py + cpt_rules.py + cenarios.json e compara
    (ignorando metadados_execucao, que dependem das versões instaladas)."""
    script = RAIZ / "scripts" / "gerar_modelo_json.py"
    if not script.exists():
        pytest.skip("scripts/gerar_modelo_json.py ausente")
    spec = importlib.util.spec_from_file_location("gerar_modelo_json", script)
    gerador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gerador)
    novo = gerador.montar_modelo()
    for chave in modelo:
        if chave == "metadados_execucao":
            continue
        assert modelo[chave] == novo[chave], f"'{chave}' do modelo.json difere do código; rode scripts/gerar_modelo_json.py"


def test_cenarios_do_modelo_sao_os_de_scenarios_json(modelo):
    arquivo = RAIZ / "scenarios" / "cenarios.json"
    if not arquivo.exists():
        pytest.skip("scenarios/cenarios.json ausente")
    assert json.loads(arquivo.read_text(encoding="utf-8"))["cenarios"] == modelo["cenarios"]


def test_modelo_json_sem_chaves_duplicadas():
    def hook(pares):
        chaves = [k for k, _ in pares]
        assert len(chaves) == len(set(chaves)), f"chaves duplicadas: {chaves}"
        return dict(pares)
    json.loads((RAIZ / "modelo.json").read_text(encoding="utf-8"), object_pairs_hook=hook)


def test_metadados_de_execucao_listam_as_bibliotecas_principais(modelo):
    libs = modelo["metadados_execucao"]["bibliotecas"]
    for nome in ("pgmpy", "networkx", "jsonschema"):
        assert nome in libs and libs[nome] != "nao-instalado"


def test_estados_do_dataset_discretizado_estao_no_modelo():
    import csv
    caminho = RAIZ / "data" / "processed" / "dados_discretizados.csv"
    if not caminho.exists():
        pytest.skip("dados_discretizados.csv ausente (rode scripts/discretizar_dataset.py)")
    vistos: dict[str, set[str]] = {}
    with caminho.open(encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            for var, valor in linha.items():
                vistos.setdefault(var, set()).add(valor)
    for var, valores in vistos.items():
        assert valores <= set(d.ESTADOS[var]), f"{var}: estados fora do modelo: {valores - set(d.ESTADOS[var])}"


def test_calibracao_ordem_de_grandeza_contra_marginais_do_eda(rede):
    """Sanidade (NÃO é estimação): a marginal da rede deve estar na mesma ordem de grandeza da
    frequência observada no dataset (fator <= 2 para estados com frequência >= 5%)."""
    import csv
    caminho = RAIZ / "outputs" / "eda" / "marginais.csv"
    if not caminho.exists():
        pytest.skip("outputs/eda/marginais.csv ausente")
    from bn_evasao.inference import consultar_variavel
    observavel = {"Turno", "Devedor", "Mensalidade_Em_Dia", "Desempenho_Sem1", "Desempenho_Sem2", "Desfecho"}
    with caminho.open(encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            var, estado, freq = linha["variavel"], linha["estado"], float(linha["proporcao"])
            if var not in observavel or freq < 0.05:
                continue
            modelo_p = consultar_variavel(rede, var)[estado]
            razao = modelo_p / freq
            assert 0.5 <= razao <= 2.0, f"P({var}={estado}) rede={modelo_p:.3f} vs dataset={freq:.3f}"