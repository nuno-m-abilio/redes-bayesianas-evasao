"""Desenho da estrutura da rede em PNG e SVG.

Plano A usa o executável dot do Graphviz, chamado por subprocess com um texto DOT
gerado aqui (nenhum pacote Python extra). Plano B usa só networkx e matplotlib e
entra sozinho quando o dot não existe ou falha, então a visualização e os testes
nunca dependem do Graphviz instalado.

As variáveis são coloridas por papel (raiz, intermediária, latente e alvo), com
layout em camadas da esquerda para a direita e legenda. A figura precisa apenas
das chaves "variaveis" e "estrutura" do modelo, então serve também para um modelo
ainda sem todas as CPTs. Uma rede pgmpy também é aceita, mas sem a informação de
variável latente, que só existe no modelo.json.
"""
from __future__ import annotations

import shutil
import subprocess
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

import networkx as nx

from .erros import ModeloInvalidoError

CAMINHO_PADRAO = Path("outputs/figuras/rede.png")
FORMATOS = ("png", "svg")
MOTORES = ("auto", "graphviz", "matplotlib")

ESTILOS: dict[str, dict[str, Any]] = {
    "raiz": {"legenda": "Raiz (sem pais)", "fundo": "#cfe8ff", "borda": "#2f6ea5",
             "largura": 1.2, "tracejado": False},
    "intermediaria": {"legenda": "Intermediária", "fundo": "#ececec", "borda": "#555555",
                      "largura": 1.2, "tracejado": False},
    "latente": {"legenda": "Latente (tracejado)", "fundo": "#e6dbf5", "borda": "#6a3fa0",
                "largura": 1.6, "tracejado": True},
    "alvo": {"legenda": "Variável alvo", "fundo": "#ffd9a8", "borda": "#c75b00",
             "largura": 2.6, "tracejado": False},
}
_COR_ARCO = "#555555"


# ---------------------------------------------------------------------------
# Estrutura a desenhar
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Estrutura:
    nos: list[str]
    arcos: list[tuple[str, str]]
    latentes: frozenset[str]
    alvo: str | None

    def grafo(self) -> nx.DiGraph:
        g = nx.DiGraph()
        g.add_nodes_from(self.nos)
        g.add_edges_from(self.arcos)
        return g

    def tipo(self, no: str, grau_entrada: int) -> str:
        if no == self.alvo:
            return "alvo"
        if no in self.latentes:
            return "latente"
        return "raiz" if grau_entrada == 0 else "intermediaria"


def _extrair(modelo_ou_rede: Any, alvo: str | None) -> _Estrutura:
    if isinstance(modelo_ou_rede, dict):
        try:
            nos = [v["id"] for v in modelo_ou_rede["variaveis"]]
            arcos = [(a["de"], a["para"]) for a in modelo_ou_rede["estrutura"]["arcos"]]
            latentes = frozenset(v["id"] for v in modelo_ou_rede["variaveis"]
                                 if v.get("observavel", True) is False)
        except (KeyError, TypeError) as erro:
            raise ModeloInvalidoError(
                "Para desenhar, o modelo precisa ter 'variaveis' e 'estrutura.arcos'.") from erro
    else:
        nos = list(modelo_ou_rede.nodes())
        arcos = list(modelo_ou_rede.edges())
        latentes = frozenset()

    desconhecidos = sorted({n for arco in arcos for n in arco} - set(nos))
    if desconhecidos:
        raise ModeloInvalidoError(f"Há arcos que citam variáveis inexistentes: {desconhecidos}.")
    return _Estrutura(nos, arcos, latentes, alvo if alvo in nos else None)


def _camadas(grafo: nx.DiGraph) -> dict[str, int]:
    """Camada de cada nó, pelo caminho mais longo a partir das raízes."""
    try:
        ordem = list(nx.topological_sort(grafo))
    except nx.NetworkXUnfeasible as erro:
        raise ModeloInvalidoError("Não é possível desenhar, o grafo possui ciclo.") from erro
    camada: dict[str, int] = {}
    for no in ordem:
        camada[no] = 1 + max((camada[p] for p in grafo.predecessors(no)), default=-1)
    return camada


def _rotulo(identificador: str, largura: int = 13) -> list[str]:
    """Quebra 'Mensalidade_Em_Dia' em linhas curtas, sem cortar palavras."""
    linhas: list[str] = []
    for palavra in identificador.split("_"):
        if linhas and len(linhas[-1]) + 1 + len(palavra) <= largura:
            linhas[-1] += " " + palavra
        else:
            linhas.append(palavra)
    return linhas


# ---------------------------------------------------------------------------
# Plano A, Graphviz
# ---------------------------------------------------------------------------
def _q(texto: str) -> str:
    return '"' + texto.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gerar_dot(modelo_ou_rede: Any, alvo: str | None = "Desfecho") -> str:
    """Texto DOT da rede, com cores por papel e legenda. Não precisa do Graphviz."""
    est = _extrair(modelo_ou_rede, alvo)
    grafo = est.grafo()
    _camadas(grafo)  # recusa ciclos antes de gerar qualquer coisa

    tipos = {no: est.tipo(no, grafo.in_degree(no)) for no in est.nos}
    linhas = [
        "digraph rede {",
        '  rankdir=LR; nodesep=0.35; ranksep=0.9; labelloc=b; labeljust=l; pad=0.3;',
        '  node [shape=box, fontname="Helvetica", fontsize=12, margin="0.16,0.09"];',
        f'  edge [color="{_COR_ARCO}", arrowsize=0.8];',
    ]
    for no in est.nos:
        estilo = ESTILOS[tipos[no]]
        rotulo = "\\n".join(l.replace("\\", "\\\\").replace('"', '\\"') for l in _rotulo(no))
        forma = "rounded,filled" + (",dashed" if estilo["tracejado"] else "")
        linhas.append(
            f'  {_q(no)} [label="{rotulo}", style="{forma}", fillcolor="{estilo["fundo"]}", '
            f'color="{estilo["borda"]}", penwidth={estilo["largura"]}];')
    for de, para in est.arcos:
        linhas.append(f"  {_q(de)} -> {_q(para)};")

    celulas = "".join(
        f'<TD BGCOLOR="{ESTILOS[t]["fundo"]}" COLOR="{ESTILOS[t]["borda"]}">'
        f'<FONT FACE="Helvetica" POINT-SIZE="12">{ESTILOS[t]["legenda"]}</FONT></TD>'
        for t in ESTILOS if t in set(tipos.values()))
    linhas.append(
        '  label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="6" CELLPADDING="6">'
        f"<TR>{celulas}</TR></TABLE>>;")
    linhas.append("}")
    return "\n".join(linhas)


def _desenhar_graphviz(dot_texto: str, saidas: list[Path], executavel: str) -> None:
    for saida in saidas:
        formato = saida.suffix.lstrip(".")
        comando = [executavel, f"-T{formato}", "-o", str(saida)]
        if formato == "png":
            comando.insert(2, "-Gdpi=150")
        subprocess.run(comando, input=dot_texto.encode("utf-8"), check=True,
                       capture_output=True, timeout=60)


# ---------------------------------------------------------------------------
# Plano B, networkx e matplotlib
# ---------------------------------------------------------------------------
_LARGURA_CAIXA, _ALTURA_CAIXA, _DX, _DY = 2.0, 0.78, 3.0, 1.05


@dataclass(frozen=True)
class _Layout:
    camada: dict[str, int]                         # camada de cada variável
    y: dict[str, float]                            # altura do centro de cada variável
    rotas: dict[tuple[str, str], list[tuple[int, float]]]  # pontos de passagem dos arcos longos
    n_camadas: int
    max_posicoes: int                              # maior número de posições numa camada


def _layout(grafo: nx.DiGraph, dy: float = _DY) -> _Layout:
    """
    Layout em camadas. Variáveis sem pais ficam na camada anterior ao primeiro filho,
    e cada arco que atravessa camadas reserva uma posição (nó virtual) em cada camada
    intermediária, então nenhuma aresta passa por cima de uma caixa. A ordem dentro das
    camadas segue o centro de gravidade dos vizinhos para reduzir cruzamentos.
    """
    camada = _camadas(grafo)
    for no in grafo.nodes:
        filhos = list(grafo.successors(no))
        if grafo.in_degree(no) == 0 and filhos:
            camada[no] = min(camada[f] for f in filhos) - 1
    n_camadas = max(camada.values(), default=0) + 1

    colunas: dict[int, list[str]] = defaultdict(list)
    for no in grafo.nodes:
        colunas[camada[no]].append(no)
    pais: dict[str, list[str]] = defaultdict(list)
    filhos_de: dict[str, list[str]] = defaultdict(list)
    cadeias: dict[tuple[str, str], list[str]] = {}
    for de, para in grafo.edges:
        cadeia = [de]
        for c in range(camada[de] + 1, camada[para]):
            virtual = f"\0{de}>{para}@{c}"
            colunas[c].append(virtual)
            cadeia.append(virtual)
        cadeia.append(para)
        cadeias[(de, para)] = cadeia
        for a, b in zip(cadeia, cadeia[1:]):
            pais[b].append(a)
            filhos_de[a].append(b)

    y: dict[str, float] = {}

    def atribuir(c: int) -> None:
        k = len(colunas[c])
        for i, no in enumerate(colunas[c]):
            y[no] = ((k - 1) / 2 - i) * dy

    def ordenar(c: int, vizinhos: dict[str, list[str]]) -> None:
        atual = {n: i for i, n in enumerate(colunas[c])}
        colunas[c].sort(key=lambda n: (
            -(fmean(y[v] for v in vizinhos[n]) if vizinhos[n] else y[n]), atual[n]))
        atribuir(c)

    for c in range(n_camadas):
        atribuir(c)
    for _ in range(2):
        for c in range(1, n_camadas):
            ordenar(c, pais)
        for c in range(n_camadas - 2, -1, -1):
            ordenar(c, filhos_de)
    for c in range(1, n_camadas):
        ordenar(c, pais)

    rotas = {arco: [(camada[v] if v in camada else _camada_virtual(v), y[v])
                    for v in cadeia[1:-1]]
             for arco, cadeia in cadeias.items()}
    return _Layout({n: camada[n] for n in grafo.nodes}, {n: y[n] for n in grafo.nodes},
                   rotas, n_camadas, max((len(v) for v in colunas.values()), default=1))


def _camada_virtual(nome_virtual: str) -> int:
    return int(nome_virtual.rsplit("@", 1)[1])


def _caminho_suave(pontos: list[tuple[float, float]]):
    """Curva que passa por todos os pontos (Catmull-Rom convertida em Bézier)."""
    from matplotlib.path import Path

    if len(pontos) == 2:
        return Path(pontos, [Path.MOVETO, Path.LINETO])
    verts = [pontos[0]]
    codigos = [Path.MOVETO]
    ext = [pontos[0], *pontos, pontos[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        verts += [(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6),
                  (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6),
                  p2]
        codigos += [Path.CURVE4] * 3
    return Path(verts, codigos)


def _desenhar_matplotlib(est: _Estrutura, saidas: list[Path]) -> None:
    # Figure direto, sem pyplot, para não mexer no backend global nem exigir tela.
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

    grafo = est.grafo()
    lay = _layout(grafo)
    w, h = _LARGURA_CAIXA, _ALTURA_CAIXA
    x = {no: lay.camada[no] * _DX for no in est.nos}
    y = lay.y

    escala = 0.62
    largura_fig = ((lay.n_camadas - 1) * _DX + w + 1.0) * escala
    altura_fig = (lay.max_posicoes * _DY + 2.2) * escala
    fig = Figure(figsize=(largura_fig, altura_fig), facecolor="white")
    ax = fig.add_axes([0.0, 0.1, 1.0, 0.9])
    meia_altura = lay.max_posicoes * _DY / 2 + 0.3
    ax.set_xlim(-w / 2 - 0.5, (lay.n_camadas - 1) * _DX + w / 2 + 0.5)
    ax.set_ylim(-meia_altura, meia_altura)
    ax.set_aspect("equal")
    ax.axis("off")

    for de, para in est.arcos:
        pontos = [(x[de] + w / 2, y[de]),
                  *[(c * _DX, yv) for c, yv in lay.rotas[(de, para)]],
                  (x[para] - w / 2, y[para])]
        ax.add_patch(FancyArrowPatch(
            path=_caminho_suave(pontos), arrowstyle="-|>", mutation_scale=12,
            color=_COR_ARCO, linewidth=1.0, zorder=1))

    tipos = {no: est.tipo(no, grafo.in_degree(no)) for no in est.nos}
    for no in est.nos:
        estilo = ESTILOS[tipos[no]]
        ax.add_patch(FancyBboxPatch(
            (x[no] - w / 2, y[no] - h / 2), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.15", facecolor=estilo["fundo"],
            edgecolor=estilo["borda"], linewidth=estilo["largura"],
            linestyle="--" if estilo["tracejado"] else "-", zorder=2))
        ax.text(x[no], y[no], "\n".join(_rotulo(no)), ha="center", va="center",
                fontsize=8.5, zorder=3)

    presentes = [t for t in ESTILOS if t in set(tipos.values())]
    fig.legend(
        handles=[Patch(facecolor=ESTILOS[t]["fundo"], edgecolor=ESTILOS[t]["borda"],
                       linestyle="--" if ESTILOS[t]["tracejado"] else "-",
                       linewidth=ESTILOS[t]["largura"], label=ESTILOS[t]["legenda"])
                 for t in presentes],
        loc="lower center", ncol=len(presentes), frameon=False, fontsize=9)

    for saida in saidas:
        fig.savefig(saida, dpi=150)


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------
def desenhar_rede(
    modelo_ou_rede: Any,
    caminho_saida: str | Path = CAMINHO_PADRAO,
    *,
    alvo: str | None = "Desfecho",
    motor: str = "auto",
    formatos: tuple[str, ...] = FORMATOS,
) -> list[Path]:
    """
    Desenha a rede e devolve os caminhos dos arquivos gerados.

    caminho_saida é a base do nome, e a extensão é trocada por cada formato pedido
    (rede.png gera rede.png e rede.svg). motor "auto" usa o Graphviz se o dot existir
    e cai para o matplotlib se ele faltar ou falhar. "graphviz" e "matplotlib" forçam
    um dos dois, e "graphviz" levanta RuntimeError se o dot não estiver disponível.
    alvo é a variável destacada, ignorada se não existir na rede.
    """
    if motor not in MOTORES:
        raise ValueError(f"motor deve ser um de {MOTORES}, recebi '{motor}'.")
    formatos_invalidos = [f for f in formatos if f not in FORMATOS]
    if not formatos or formatos_invalidos:
        raise ValueError(f"formatos deve ser um subconjunto não vazio de {FORMATOS}.")

    est = _extrair(modelo_ou_rede, alvo)
    _camadas(est.grafo())

    base = Path(caminho_saida)
    saidas = [base.with_suffix(f".{f}") for f in formatos]
    base.parent.mkdir(parents=True, exist_ok=True)

    dot = shutil.which("dot")
    if motor == "graphviz" and dot is None:
        raise RuntimeError(
            "Graphviz não encontrado (executável 'dot'). Instale o Graphviz ou use "
            "motor='matplotlib'.")

    usar_graphviz = motor == "graphviz" or (motor == "auto" and dot is not None)
    if usar_graphviz:
        try:
            _desenhar_graphviz(gerar_dot(modelo_ou_rede, alvo), saidas, dot)
        except (subprocess.SubprocessError, OSError) as erro:
            if motor == "graphviz":
                raise RuntimeError(f"O Graphviz falhou ao desenhar a rede: {erro}") from erro
            warnings.warn(f"O Graphviz falhou ({erro}); usando matplotlib no lugar.",
                          stacklevel=2)
            usar_graphviz = False
    if not usar_graphviz:
        _desenhar_matplotlib(est, saidas)
    return saidas