"""Testes de visualize.py.

Nenhum teste depende do Graphviz, exceto o marcado com skipif. O texto DOT, o layout
e o plano B em matplotlib são verificados sem o executável dot.
"""
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

from bn_evasao import visualize
from bn_evasao.erros import ModeloInvalidoError
from bn_evasao.loader import carregar_modelo
from bn_evasao.network import construir_rede
from bn_evasao.visualize import _camadas, _layout, _rotulo, desenhar_rede, gerar_dot

EXEMPLO = Path(__file__).resolve().parents[1] / "docs" / "exemplos" / "modelo_exemplo.json"
ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

IDS_14 = ["Area_Curso", "Faixa_Etaria", "Escolaridade_Pais", "Bolsista", "Deslocado",
          "Nota_Admissao", "Desemprego", "Turno", "Pressao_Financeira", "Devedor",
          "Mensalidade_Em_Dia", "Desempenho_Sem1", "Desempenho_Sem2", "Desfecho"]
ARCOS_14 = [
    ("Area_Curso", "Turno"), ("Faixa_Etaria", "Turno"),
    ("Escolaridade_Pais", "Pressao_Financeira"), ("Bolsista", "Pressao_Financeira"),
    ("Deslocado", "Pressao_Financeira"),
    ("Pressao_Financeira", "Devedor"), ("Pressao_Financeira", "Mensalidade_Em_Dia"),
    ("Nota_Admissao", "Desempenho_Sem1"), ("Faixa_Etaria", "Desempenho_Sem1"),
    ("Area_Curso", "Desempenho_Sem1"),
    ("Desempenho_Sem1", "Desempenho_Sem2"), ("Pressao_Financeira", "Desempenho_Sem2"),
    ("Turno", "Desempenho_Sem2"),
    ("Desempenho_Sem2", "Desfecho"), ("Pressao_Financeira", "Desfecho"),
    ("Desemprego", "Desfecho"),
]


def estrutura(ids, arcos, latentes=()):
    """Modelo só com variáveis e estrutura, o suficiente para desenhar."""
    return {"variaveis": [{"id": i, "observavel": i not in latentes} for i in ids],
            "estrutura": {"arcos": [{"de": a, "para": b} for a, b in arcos]}}


@pytest.fixture
def modelo14():
    return estrutura(IDS_14, ARCOS_14, latentes={"Pressao_Financeira"})


# ---------------------------------------------------------------------------
# Texto DOT, sem Graphviz
# ---------------------------------------------------------------------------
def test_dot_tem_todos_os_nos_e_arcos(modelo14):
    dot = gerar_dot(modelo14)
    for no in IDS_14:
        assert f'"{no}" [label=' in dot
    for de, para in ARCOS_14:
        assert f'"{de}" -> "{para}";' in dot
    assert dot.count("->") == len(ARCOS_14)


def test_dot_marca_latente_e_alvo(modelo14):
    linhas = {l.strip().split(" ")[0]: l for l in gerar_dot(modelo14).splitlines()
              if "[label=" in l}
    assert "dashed" in linhas['"Pressao_Financeira"']
    assert "dashed" not in linhas['"Bolsista"']
    assert "penwidth=2.6" in linhas['"Desfecho"']


def test_dot_legenda_so_com_papeis_presentes():
    dot = gerar_dot(estrutura(["A", "B"], [("A", "B")]), alvo=None)
    assert "Raiz (sem pais)" in dot and "Intermediária" in dot
    assert "Latente" not in dot and "Variável alvo" not in dot


def test_alvo_inexistente_e_ignorado():
    assert "Variável alvo" not in gerar_dot(estrutura(["A", "B"], [("A", "B")]), alvo="Nada")


def test_rotulo_quebra_sem_cortar_palavras():
    assert _rotulo("Mensalidade_Em_Dia") == ["Mensalidade", "Em Dia"]
    assert _rotulo("Escolaridade_Pais") == ["Escolaridade", "Pais"]
    assert _rotulo("Turno") == ["Turno"]


# ---------------------------------------------------------------------------
# Camadas e layout
# ---------------------------------------------------------------------------
def test_camadas_em_cadeia():
    g = visualize._Estrutura(["A", "B", "C"], [("A", "B"), ("B", "C")], frozenset(), None).grafo()
    assert _camadas(g) == {"A": 0, "B": 1, "C": 2}


def test_camadas_recusa_ciclo():
    g = visualize._Estrutura(["A", "B"], [("A", "B"), ("B", "A")], frozenset(), None).grafo()
    with pytest.raises(ModeloInvalidoError, match="ciclo"):
        _camadas(g)


def test_layout_respeita_a_direcao_dos_arcos_e_nao_sobrepoe(modelo14):
    est = visualize._extrair(modelo14, "Desfecho")
    lay = _layout(est.grafo())
    for de, para in ARCOS_14:
        assert lay.camada[de] < lay.camada[para]

    posicoes = defaultdict(list)
    for no, c in lay.camada.items():
        posicoes[c].append(lay.y[no])
    for pontos in lay.rotas.values():
        for c, y in pontos:
            posicoes[c].append(y)
    for ys in posicoes.values():
        ordenados = sorted(ys)
        assert all(b - a >= visualize._DY - 1e-9 for a, b in zip(ordenados, ordenados[1:]))


def test_arco_longo_reserva_uma_posicao_por_camada_atravessada(modelo14):
    est = visualize._extrair(modelo14, "Desfecho")
    lay = _layout(est.grafo())
    for (de, para), pontos in lay.rotas.items():
        assert len(pontos) == lay.camada[para] - lay.camada[de] - 1
    assert len(lay.rotas[("Pressao_Financeira", "Desfecho")]) == 1


def test_variavel_sem_pais_fica_perto_do_primeiro_filho(modelo14):
    est = visualize._extrair(modelo14, "Desfecho")
    lay = _layout(est.grafo())
    assert lay.camada["Desemprego"] == lay.camada["Desfecho"] - 1


# ---------------------------------------------------------------------------
# Plano B, matplotlib
# ---------------------------------------------------------------------------
def test_matplotlib_gera_png_e_svg(tmp_path, modelo14):
    saidas = desenhar_rede(modelo14, tmp_path / "rede.png", motor="matplotlib")
    assert [s.name for s in saidas] == ["rede.png", "rede.svg"]
    assert saidas[0].read_bytes().startswith(ASSINATURA_PNG)
    assert "<svg" in saidas[1].read_text(encoding="utf-8")


def test_cria_a_pasta_de_saida(tmp_path, modelo14):
    destino = tmp_path / "a" / "b" / "rede.png"
    desenhar_rede(modelo14, destino, motor="matplotlib", formatos=("png",))
    assert destino.is_file() and not destino.with_suffix(".svg").exists()


def test_aceita_rede_pgmpy(tmp_path):
    rede = construir_rede(carregar_modelo(EXEMPLO))
    saidas = desenhar_rede(rede, tmp_path / "rede.png", motor="matplotlib", alvo="Chuva")
    assert saidas[0].read_bytes().startswith(ASSINATURA_PNG)


def test_aceita_modelo_completo_do_exemplo(tmp_path):
    saidas = desenhar_rede(carregar_modelo(EXEMPLO), tmp_path / "rede.png", motor="matplotlib")
    assert all(s.stat().st_size > 0 for s in saidas)


# ---------------------------------------------------------------------------
# Escolha do motor
# ---------------------------------------------------------------------------
def test_auto_cai_para_matplotlib_quando_nao_ha_dot(tmp_path, modelo14, monkeypatch):
    monkeypatch.setattr(visualize.shutil, "which", lambda nome: None)

    def nao_deveria_ser_chamado(*args, **kwargs):
        raise AssertionError("o Graphviz não deveria ser usado sem o dot")

    monkeypatch.setattr(visualize, "_desenhar_graphviz", nao_deveria_ser_chamado)
    saidas = desenhar_rede(modelo14, tmp_path / "rede.png")
    assert saidas[0].read_bytes().startswith(ASSINATURA_PNG)


def test_auto_cai_para_matplotlib_se_o_graphviz_falhar(tmp_path, modelo14, monkeypatch):
    monkeypatch.setattr(visualize.shutil, "which", lambda nome: "/caminho/dot")

    def falha(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "dot")

    monkeypatch.setattr(visualize, "_desenhar_graphviz", falha)
    with pytest.warns(UserWarning, match="matplotlib"):
        saidas = desenhar_rede(modelo14, tmp_path / "rede.png")
    assert saidas[0].read_bytes().startswith(ASSINATURA_PNG)


def test_graphviz_forcado_sem_dot_levanta_erro(tmp_path, modelo14, monkeypatch):
    monkeypatch.setattr(visualize.shutil, "which", lambda nome: None)
    with pytest.raises(RuntimeError, match="Graphviz não encontrado"):
        desenhar_rede(modelo14, tmp_path / "rede.png", motor="graphviz")


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz não instalado")
def test_graphviz_gera_png_e_svg(tmp_path, modelo14):
    saidas = desenhar_rede(modelo14, tmp_path / "rede.png", motor="graphviz")
    assert saidas[0].read_bytes().startswith(ASSINATURA_PNG)
    assert "<svg" in saidas[1].read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Entradas inválidas
# ---------------------------------------------------------------------------
def test_motor_invalido(tmp_path, modelo14):
    with pytest.raises(ValueError, match="motor"):
        desenhar_rede(modelo14, tmp_path / "r.png", motor="inexistente")


@pytest.mark.parametrize("formatos", [(), ("pdf",), ("png", "gif")])
def test_formatos_invalidos(tmp_path, modelo14, formatos):
    with pytest.raises(ValueError, match="formatos"):
        desenhar_rede(modelo14, tmp_path / "r.png", formatos=formatos)


def test_ciclo_nao_e_desenhado(tmp_path):
    modelo = estrutura(["A", "B"], [("A", "B"), ("B", "A")])
    with pytest.raises(ModeloInvalidoError, match="ciclo"):
        desenhar_rede(modelo, tmp_path / "r.png")
    with pytest.raises(ModeloInvalidoError, match="ciclo"):
        gerar_dot(modelo)


def test_modelo_sem_estrutura(tmp_path):
    with pytest.raises(ModeloInvalidoError, match="estrutura"):
        desenhar_rede({"variaveis": []}, tmp_path / "r.png")


def test_arco_com_variavel_inexistente(tmp_path):
    with pytest.raises(ModeloInvalidoError, match="inexistentes"):
        desenhar_rede(estrutura(["A"], [("A", "B")]), tmp_path / "r.png")