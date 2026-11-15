"""Testes do CLI, chamando main() com argumentos e lendo saída e código de retorno.

A execução de cenários é simulada com monkeypatch, porque o formato do resultado e
a implementação pertencem a scenarios.py. Assim estes testes continuam valendo
quando a pessoa C entregar o módulo.
"""
import json
from pathlib import Path

import pytest

from bn_evasao import cli, scenarios
from bn_evasao.cli import main

EXEMPLO = Path(__file__).resolve().parents[1] / "docs" / "exemplos" / "modelo_exemplo.json"
ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


def rodar(capsys, *argv):
    codigo = main([str(a) for a in argv])
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


@pytest.fixture
def modelo_com_dois_cenarios(tmp_path):
    modelo = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    segundo = dict(modelo["cenarios"][0], id="E2_outro")
    modelo["cenarios"].append(segundo)
    caminho = tmp_path / "modelo.json"
    caminho.write_text(json.dumps(modelo), encoding="utf-8")
    return caminho


def cenario_simulado(aprovado=True):
    def executar(rede, cenario):
        return {
            "id": cenario["id"], "pergunta": cenario["pergunta"], "aprovado": aprovado,
            "variantes": {"base": {"evidencias": {"Grama_Molhada": "Sim"},
                                   "resultados": {"Chuva": {"Sim": 0.7, "Nao": 0.3}}}},
            "expectativas": [{"descricao": "chuva mais provável", "aprovado": aprovado}],
            "interpretacao": "texto de interpretação",
        }
    return executar


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------
def test_validar_exemplo(capsys):
    codigo, saida, _ = rodar(capsys, "validar", "--modelo", EXEMPLO)
    assert codigo == 0
    assert "Modelo válido" in saida
    assert "3 variáveis, 2 arcos, 3 CPTs" in saida


def test_validar_avisa_quando_faltam_variaveis_e_cenarios(capsys):
    _, saida, _ = rodar(capsys, "validar", "--modelo", EXEMPLO)
    assert "pelo menos 10 variáveis" in saida
    assert "pelo menos 4 cenários" in saida


def test_validar_arquivo_inexistente(capsys, tmp_path):
    codigo, _, erro = rodar(capsys, "validar", "--modelo", tmp_path / "nao_existe.json")
    assert codigo == 1
    assert "não encontrado" in erro


def test_validar_modelo_com_cpt_invalida(capsys, tmp_path):
    modelo = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    modelo["probabilidades"][1]["linhas"][0]["probabilidades"]["Sim"] = 0.5
    caminho = tmp_path / "ruim.json"
    caminho.write_text(json.dumps(modelo), encoding="utf-8")
    codigo, _, erro = rodar(capsys, "validar", "--modelo", caminho)
    assert codigo == 1
    assert "somam" in erro


# ---------------------------------------------------------------------------
# consultar
# ---------------------------------------------------------------------------
def test_consultar_json_bate_com_bayes_a_mao(capsys):
    codigo, saida, _ = rodar(capsys, "consultar", "--modelo", EXEMPLO, "--consulta", "Chuva",
                             "--evidencia", "Grama_Molhada=Sim", "--json")
    assert codigo == 0
    dados = json.loads(saida)
    esperado = (0.3 * 0.9) / (0.3 * 0.9 + 0.7 * 0.2)
    assert dados["evidencias"] == {"Grama_Molhada": "Sim"}
    assert dados["resultado"]["Chuva"]["Sim"] == pytest.approx(esperado, abs=1e-9)


def test_consultar_texto_mostra_cabecalho_e_estados(capsys):
    codigo, saida, _ = rodar(capsys, "consultar", "--modelo", EXEMPLO, "-c", "Chuva",
                             "-e", "Grama_Molhada=Sim")
    assert codigo == 0
    assert "P(Chuva | Grama_Molhada=Sim)" in saida
    assert "Sim" in saida and "Nao" in saida


def test_consultar_sem_evidencia_e_varias_consultas(capsys):
    codigo, saida, _ = rodar(capsys, "consultar", "--modelo", EXEMPLO,
                             "-c", "Chuva", "-c", "Grama_Molhada", "--json")
    assert codigo == 0
    assert set(json.loads(saida)["resultado"]) == {"Chuva", "Grama_Molhada"}


def test_consultar_mesma_evidencia_repetida_e_aceita(capsys):
    codigo, _, _ = rodar(capsys, "consultar", "--modelo", EXEMPLO, "-c", "Chuva",
                         "-e", "Grama_Molhada=Sim", "-e", "Grama_Molhada=Sim")
    assert codigo == 0


@pytest.mark.parametrize("argumentos, trecho", [
    (["-c", "Chuva", "-e", "Grama_Molhada=Talvez"], "Estados válidos"),
    (["-c", "Chuva", "-e", "Fantasma=Sim"], "não existe na rede"),
    (["-c", "Chuvaa"], "Você quis dizer 'Chuva'"),
    (["-c", "Chuva", "-e", "Chuva=Sim"], "consulta e como evidência"),
    (["-c", "Chuva", "-e", "Grama_Molhada=Sim", "-e", "Grama_Molhada=Nao"], "duas evidências"),
])
def test_consultar_erros_viram_codigo_1(capsys, argumentos, trecho):
    codigo, _, erro = rodar(capsys, "consultar", "--modelo", EXEMPLO, *argumentos)
    assert codigo == 1
    assert trecho in erro


def test_evidencia_malformada_e_erro_de_uso(capsys):
    with pytest.raises(SystemExit) as info:
        main(["consultar", "--modelo", str(EXEMPLO), "-c", "Chuva", "-e", "Grama_Molhada"])
    assert info.value.code == 2
    assert "VARIAVEL=ESTADO" in capsys.readouterr().err


def test_consultar_sem_consulta_e_erro_de_uso(capsys):
    with pytest.raises(SystemExit) as info:
        main(["consultar", "--modelo", str(EXEMPLO)])
    assert info.value.code == 2


def test_comando_ausente_e_erro_de_uso(capsys):
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2


# ---------------------------------------------------------------------------
# cenarios
# ---------------------------------------------------------------------------
def test_cenarios_aprovados(capsys, monkeypatch):
    monkeypatch.setattr(scenarios, "executar_cenario", cenario_simulado(True))
    codigo, saida, _ = rodar(capsys, "cenarios", "--modelo", EXEMPLO)
    assert codigo == 0
    assert "=== E1_diagnostico ===" in saida
    assert "[ok] chuva mais provável" in saida
    assert "texto de interpretação" in saida
    assert "P(Chuva)" in saida


def test_cenario_reprovado_retorna_3(capsys, monkeypatch):
    monkeypatch.setattr(scenarios, "executar_cenario", cenario_simulado(False))
    codigo, saida, _ = rodar(capsys, "cenarios", "--modelo", EXEMPLO)
    assert codigo == 3
    assert "[FALHOU]" in saida


def test_cenarios_filtra_por_id(capsys, monkeypatch, modelo_com_dois_cenarios):
    monkeypatch.setattr(scenarios, "executar_cenario", cenario_simulado(True))
    codigo, saida, _ = rodar(capsys, "cenarios", "--modelo", modelo_com_dois_cenarios,
                             "--id", "E2_outro", "--json")
    assert codigo == 0
    assert list(json.loads(saida)) == ["E2_outro"]


def test_cenarios_executa_todos_sem_filtro(capsys, monkeypatch, modelo_com_dois_cenarios):
    monkeypatch.setattr(scenarios, "executar_cenario", cenario_simulado(True))
    _, saida, _ = rodar(capsys, "cenarios", "--modelo", modelo_com_dois_cenarios, "--json")
    assert list(json.loads(saida)) == ["E1_diagnostico", "E2_outro"]


def test_cenario_inexistente_lista_os_disponiveis(capsys, monkeypatch):
    monkeypatch.setattr(scenarios, "executar_cenario", cenario_simulado(True))
    codigo, _, erro = rodar(capsys, "cenarios", "--modelo", EXEMPLO, "--id", "XYZ")
    assert codigo == 1
    assert "E1_diagnostico" in erro


def test_cenarios_nao_implementados_dao_mensagem_clara(capsys, monkeypatch):
    def nao_implementado(rede, cenario):
        raise NotImplementedError

    monkeypatch.setattr(scenarios, "executar_cenario", nao_implementado)
    codigo, _, erro = rodar(capsys, "cenarios", "--modelo", EXEMPLO)
    assert codigo == 1
    assert "ainda não foi implementada" in erro


def test_resultado_de_formato_desconhecido_cai_para_json(capsys, monkeypatch):
    monkeypatch.setattr(scenarios, "executar_cenario",
                        lambda rede, cenario: {"id": cenario["id"], "algo_novo": 42})
    codigo, saida, _ = rodar(capsys, "cenarios", "--modelo", EXEMPLO)
    assert codigo == 0
    assert '"algo_novo": 42' in saida


# ---------------------------------------------------------------------------
# desenhar
# ---------------------------------------------------------------------------
def test_desenhar_gera_figuras(capsys, tmp_path):
    destino = tmp_path / "figuras" / "rede.png"
    codigo, saida, _ = rodar(capsys, "desenhar", "--modelo", EXEMPLO, "--saida", destino,
                             "--motor", "matplotlib", "--alvo", "Chuva")
    assert codigo == 0
    assert destino.read_bytes().startswith(ASSINATURA_PNG)
    assert destino.with_suffix(".svg").is_file()
    assert "Figuras geradas" in saida


def test_desenhar_so_png(capsys, tmp_path):
    destino = tmp_path / "rede.png"
    rodar(capsys, "desenhar", "--modelo", EXEMPLO, "--saida", destino, "--motor", "matplotlib",
          "--formatos", "png")
    assert destino.is_file() and not destino.with_suffix(".svg").exists()


def test_desenhar_graphviz_forcado_sem_dot_vira_erro(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("bn_evasao.visualize.shutil.which", lambda nome: None)
    codigo, _, erro = rodar(capsys, "desenhar", "--modelo", EXEMPLO,
                            "--saida", tmp_path / "r.png", "--motor", "graphviz")
    assert codigo == 1
    assert "Graphviz não encontrado" in erro


def test_motor_desconhecido_e_erro_de_uso(capsys):
    with pytest.raises(SystemExit) as info:
        main(["desenhar", "--modelo", str(EXEMPLO), "--motor", "outro"])
    assert info.value.code == 2


def test_modelo_padrao_e_modelo_json_na_pasta_atual(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "modelo.json").write_text(EXEMPLO.read_text(encoding="utf-8"), encoding="utf-8")
    codigo, saida, _ = rodar(capsys, "validar")
    assert codigo == 0 and "Modelo válido" in saida