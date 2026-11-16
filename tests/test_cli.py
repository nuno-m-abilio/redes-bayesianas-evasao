"""Fumaça da CLI e da visualização (não dependem do executável Graphviz)."""
from bn_evasao.cli import main


def test_validar(capsys):
    assert main(["validar"]) == 0
    saida = capsys.readouterr().out
    assert "Modelo válido" in saida and "Variáveis: 14" in saida and "Arcos: 16" in saida


def test_info(capsys):
    assert main(["info"]) == 0
    assert "Pressao_Financeira" in capsys.readouterr().out


def test_consultar_com_evidencias(capsys):
    assert main(["consultar", "-c", "Desfecho", "-e", "Turno=Noturno", "Bolsista=Nao"]) == 0
    saida = capsys.readouterr().out
    assert "Dropout" in saida and "Graduate" in saida


def test_consultar_evidencia_malformada(capsys):
    assert main(["consultar", "-c", "Desfecho", "-e", "TurnoNoturno"]) == 1
    assert "[ERRO]" in capsys.readouterr().err


def test_consultar_estado_invalido(capsys):
    assert main(["consultar", "-c", "Desfecho", "-e", "Turno=Madrugada"]) == 1
    assert "Estado inválido" in capsys.readouterr().err


def test_cenarios_todos_e_um(capsys):
    assert main(["cenarios"]) == 0
    assert "S4_prescritivo" in capsys.readouterr().out
    assert main(["cenarios", "--id", "S2_alerta_precoce"]) == 0


def test_cenario_inexistente(capsys):
    assert main(["cenarios", "--id", "S9"]) == 1


def test_modelo_inexistente(capsys, tmp_path):
    assert main(["--modelo", str(tmp_path / "x.json"), "validar"]) == 1


def test_desenhar_gera_png_e_dot(tmp_path):
    png, dot = tmp_path / "rede.png", tmp_path / "rede.dot"
    assert main(["desenhar", "--saida-png", str(png), "--saida-dot", str(dot)]) == 0
    assert png.stat().st_size > 10_000
    texto = dot.read_text(encoding="utf-8")
    assert "Desfecho" in texto and "->" in texto