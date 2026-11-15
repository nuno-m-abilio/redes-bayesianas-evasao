#!/usr/bin/env python3
"""
Monta o ZIP de entrega no padrão 2026.AMMCI.<Integrante1>.<Integrante2>.<Integrante3>.zip.

Cada integrante é o primeiro nome seguido das iniciais dos sobrenomes, sem espaços,
acentos ou caracteres especiais (exemplo, JoaoDS). O script é em Python, e não em shell,
porque o Git Bash do Windows não traz o comando zip.

O ZIP leva o código, o modelo.json, os testes, a documentação, os slides e os dados
mínimos. Ficam de fora o ambiente virtual, caches, a pasta .git e data/raw, porque o
dataset original deve ser baixado pela fonte (ver data/README.md). Os arquivos ficam na
raiz do ZIP, sem pasta intermediária.

Uso:
    python scripts/montar_zip.py JoaoDS PauloC
    python scripts/montar_zip.py JoaoDS PauloC MariaS --verificar-testes
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

RAIZ_PADRAO = Path(__file__).resolve().parents[1]
PADRAO_INTEGRANTE = re.compile(r"^[A-Za-z]+$")

PASTAS_EXCLUIDAS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
                    ".ipynb_checkpoints", ".mypy_cache", "htmlcov", "dist", "node_modules"}
PREFIXOS_EXCLUIDOS = ("data/raw/",)
NOMES_EXCLUIDOS = {".DS_Store", ".coverage", "Thumbs.db"}
SUFIXOS_EXCLUIDOS = {".pyc", ".pyo", ".zip"}

ARQUIVOS_OBRIGATORIOS = [
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "modelo.json",
    "docs/modelo_json_guia.md",
    "docs/uso_de_ia.md",
    "docs/exemplos/modelo_exemplo.json",
    "src/bn_evasao/__init__.py",
]
PASTAS_COM_CONTEUDO = ["tests", "slides"]
PLACEHOLDERS = {".gitkeep", ".keep"}


def nome_do_zip(integrantes: list[str]) -> str:
    return "2026.AMMCI." + ".".join(integrantes) + ".zip"


def validar_integrantes(integrantes: list[str]) -> None:
    if not 1 <= len(integrantes) <= 3:
        raise ValueError("Informe de 1 a 3 integrantes.")
    for nome in integrantes:
        if not PADRAO_INTEGRANTE.match(nome):
            raise ValueError(
                f"Integrante '{nome}' fora do padrão. Use o primeiro nome seguido das "
                "iniciais dos sobrenomes, só com letras sem acento (exemplo, JoaoDS).")


def listar_arquivos(raiz: Path) -> list[str]:
    """Caminhos relativos, com barra normal, dos arquivos que entram no ZIP."""
    arquivos: list[str] = []
    for pasta, subpastas, nomes in os.walk(raiz):
        rel_pasta = Path(pasta).relative_to(raiz).as_posix()
        subpastas[:] = sorted(
            s for s in subpastas
            if s not in PASTAS_EXCLUIDAS
            and not f"{'' if rel_pasta == '.' else rel_pasta + '/'}{s}/".startswith(PREFIXOS_EXCLUIDOS))
        for nome in sorted(nomes):
            if nome in NOMES_EXCLUIDOS or Path(nome).suffix in SUFIXOS_EXCLUIDOS:
                continue
            rel = nome if rel_pasta == "." else f"{rel_pasta}/{nome}"
            if not rel.startswith(PREFIXOS_EXCLUIDOS):
                arquivos.append(rel)
    return arquivos


def itens_faltando(arquivos: list[str]) -> list[str]:
    presentes = set(arquivos)
    faltando = [f for f in ARQUIVOS_OBRIGATORIOS if f not in presentes]
    for pasta in PASTAS_COM_CONTEUDO:
        if not any(a.startswith(pasta + "/") and Path(a).name not in PLACEHOLDERS
                   for a in arquivos):
            faltando.append(f"{pasta}/ (sem arquivos)")
    return faltando


def montar(raiz: Path, destino: Path, arquivos: list[str]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in arquivos:
            zf.write(raiz / rel, rel)


def verificar_integridade(destino: Path, arquivos: list[str]) -> None:
    with zipfile.ZipFile(destino) as zf:
        corrompido = zf.testzip()
        if corrompido is not None:
            raise RuntimeError(f"ZIP corrompido, primeiro arquivo com erro {corrompido}.")
        if sorted(zf.namelist()) != sorted(arquivos):
            raise RuntimeError("O conteúdo do ZIP difere da lista de arquivos esperada.")


def rodar_testes_no_zip(destino: Path) -> int:
    """Extrai o ZIP numa pasta temporária e roda o pytest ali, sem usar o repositório."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(destino) as zf:
            zf.extractall(tmp)
        ambiente = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=tmp, env=ambiente).returncode


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monta o ZIP de entrega do trabalho de AMMCI.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("integrantes", nargs="+", metavar="INTEGRANTE",
                        help="de 1 a 3 nomes no padrão primeiro nome mais iniciais (JoaoDS)")
    parser.add_argument("--raiz", type=Path, default=RAIZ_PADRAO,
                        help="raiz do repositório (padrão, a pasta pai de scripts/)")
    parser.add_argument("--saida-dir", type=Path, default=None,
                        help="pasta do ZIP (padrão, dist/ dentro da raiz)")
    parser.add_argument("--permitir-incompleto", action="store_true",
                        help="só avisa, em vez de falhar, quando faltar arquivo obrigatório")
    parser.add_argument("--verificar-testes", action="store_true",
                        help="extrai o ZIP numa pasta temporária e roda o pytest nela")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _criar_parser().parse_args(argv)
    try:
        validar_integrantes(args.integrantes)
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    raiz = args.raiz.resolve()
    destino = (args.saida_dir or raiz / "dist").resolve() / nome_do_zip(args.integrantes)
    arquivos = listar_arquivos(raiz)

    faltando = itens_faltando(arquivos)
    if faltando:
        mensagem = "Itens obrigatórios ausentes:\n" + "\n".join(f"  {f}" for f in faltando)
        if not args.permitir_incompleto:
            print(f"Erro: {mensagem}", file=sys.stderr)
            return 1
        print(f"Aviso: {mensagem}", file=sys.stderr)

    montar(raiz, destino, arquivos)
    try:
        verificar_integridade(destino, arquivos)
    except RuntimeError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    tamanho_kb = destino.stat().st_size / 1024
    print(f"ZIP íntegro, {len(arquivos)} arquivos, {tamanho_kb:.0f} KB")
    print(f"  {destino}")
    for entrada in sorted({a.split("/")[0] for a in arquivos}):
        print(f"  {entrada}{'/' if any(a.startswith(entrada + '/') for a in arquivos) else ''}")

    if args.verificar_testes:
        print("\nRodando os testes a partir do ZIP extraído")
        if rodar_testes_no_zip(destino) != 0:
            print("Erro: os testes falharam no ZIP extraído.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())