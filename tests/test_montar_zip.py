"""Testes de scripts/montar_zip.py, rodado como processo sobre repositórios de mentira."""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "montar_zip.py"

OBRIGATORIOS = [
    "README.md", "requirements.txt", "pytest.ini", "pyproject.toml", "modelo.json",
    "docs/modelo_json_guia.md", "docs/uso_de_ia.md", "docs/exemplos/modelo_exemplo.json",
    "src/bn_evasao/__init__.py", "tests/test_ok.py", "slides/apresentacao.pdf",
]


def escrever(raiz: Path, rel: str, conteudo: str = "x") -> None:
    caminho = raiz / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    """Repositório mínimo e completo, com lixo que não pode entrar no ZIP."""
    raiz = tmp_path / "repo"
    for rel in OBRIGATORIOS:
        escrever(raiz, rel)
    escrever(raiz, "pytest.ini", "[pytest]\npythonpath = src\ntestpaths = tests\n")
    escrever(raiz, "pyproject.toml", '[project]\nname = "falso"\nversion = "0"\n')
    escrever(raiz, "tests/test_ok.py", "def test_ok():\n    assert True\n")
    escrever(raiz, "data/README.md")
    escrever(raiz, "data/processed/dados_discretizados.csv")
    for lixo in [".git/config", ".venv/lib/x.py", "src/bn_evasao/__pycache__/a.pyc",
                 "data/raw/data.csv", "dist/antigo.zip", ".pytest_cache/v", ".coverage",
                 "outputs/.DS_Store", "src/bn_evasao.egg-info/PKG-INFO", "build/lib/x.py"]:
        escrever(raiz, lixo)
    return raiz


def rodar(raiz, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(raiz), *args],
                          capture_output=True, text=True)


def test_gera_zip_com_nome_conteudo_e_sem_lixo(repo):
    resultado = rodar(repo, "JoaoDS", "PauloC")
    assert resultado.returncode == 0, resultado.stderr
    destino = repo / "dist" / "2026.AMMCI.JoaoDS.PauloC.zip"
    with zipfile.ZipFile(destino) as zf:
        nomes = set(zf.namelist())
    assert set(OBRIGATORIOS) <= nomes
    assert {"data/README.md", "data/processed/dados_discretizados.csv"} <= nomes
    for lixo in [".git/config", ".venv/lib/x.py", "src/bn_evasao/__pycache__/a.pyc",
                 "data/raw/data.csv", "dist/antigo.zip", ".coverage", "outputs/.DS_Store",
                 "src/bn_evasao.egg-info/PKG-INFO", "build/lib/x.py"]:
        assert lixo not in nomes
    assert "ZIP íntegro" in resultado.stdout


def test_arquivos_ficam_na_raiz_do_zip(repo):
    rodar(repo, "JoaoDS")
    with zipfile.ZipFile(repo / "dist" / "2026.AMMCI.JoaoDS.zip") as zf:
        assert "modelo.json" in zf.namelist()


def test_tres_integrantes(repo):
    assert rodar(repo, "AnaB", "BrunoC", "CarlaD").returncode == 0
    assert (repo / "dist" / "2026.AMMCI.AnaB.BrunoC.CarlaD.zip").is_file()


@pytest.mark.parametrize("integrantes", [
    ["João"], ["Joao Silva"], ["Joao_DS"], ["Joao.DS"], ["Joao1"],
    ["A", "B", "C", "D"],
])
def test_integrantes_fora_do_padrao(repo, integrantes):
    resultado = rodar(repo, *integrantes)
    assert resultado.returncode == 1
    assert "Erro" in resultado.stderr
    assert not (repo / "dist").exists() or not list((repo / "dist").glob("2026.*"))


def test_sem_integrantes_e_erro_de_uso(repo):
    assert rodar(repo).returncode == 2


@pytest.mark.parametrize("faltando", ["modelo.json", "docs/uso_de_ia.md", "README.md", "pyproject.toml"])
def test_arquivo_obrigatorio_ausente(repo, faltando):
    (repo / faltando).unlink()
    resultado = rodar(repo, "JoaoDS")
    assert resultado.returncode == 1
    assert faltando in resultado.stderr
    assert not (repo / "dist" / "2026.AMMCI.JoaoDS.zip").exists()


def test_slides_so_com_placeholder_conta_como_ausente(repo):
    (repo / "slides" / "apresentacao.pdf").unlink()
    escrever(repo, "slides/.gitkeep", "")
    resultado = rodar(repo, "JoaoDS")
    assert resultado.returncode == 1
    assert "slides/" in resultado.stderr


def test_permitir_incompleto_so_avisa(repo):
    (repo / "modelo.json").unlink()
    resultado = rodar(repo, "JoaoDS", "--permitir-incompleto")
    assert resultado.returncode == 0
    assert "modelo.json" in resultado.stderr
    assert (repo / "dist" / "2026.AMMCI.JoaoDS.zip").is_file()


def test_gerar_de_novo_substitui_o_zip_anterior(repo):
    rodar(repo, "JoaoDS")
    escrever(repo, "README.md", "versão nova do readme")
    rodar(repo, "JoaoDS")
    with zipfile.ZipFile(repo / "dist" / "2026.AMMCI.JoaoDS.zip") as zf:
        assert zf.read("README.md").decode("utf-8") == "versão nova do readme"


def test_saida_dir_personalizada(repo, tmp_path):
    saida = tmp_path / "entrega"
    assert rodar(repo, "JoaoDS", "--saida-dir", str(saida)).returncode == 0
    assert (saida / "2026.AMMCI.JoaoDS.zip").is_file()


def test_verificar_testes_passa(repo):
    resultado = rodar(repo, "JoaoDS", "--verificar-testes")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "1 passed" in resultado.stdout


def test_verificar_testes_falha_quando_um_teste_falha(repo):
    escrever(repo, "tests/test_quebra.py", "def test_quebra():\n    assert False\n")
    resultado = rodar(repo, "JoaoDS", "--verificar-testes")
    assert resultado.returncode == 1
    assert "falharam no ZIP" in resultado.stderr