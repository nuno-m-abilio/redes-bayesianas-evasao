"""Geração da representação gráfica legível da estrutura da Rede Bayesiana."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Backend sem interface gráfica para execução segura em terminal/CI

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import pydot
from pgmpy.models import DiscreteBayesianNetwork

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
SAIDA_PNG_PADRAO = RAIZ_PROJETO / "outputs" / "figuras" / "estrutura_rede.png"
SAIDA_DOT_PADRAO = RAIZ_PROJETO / "outputs" / "figuras" / "estrutura_rede.dot"

ESTILOS_TIPO: dict[str, dict] = {
    "raiz": {"cor": "#DCEBFA", "borda": "#2B6CB0", "estilo_linha": "solid", "rotulo": "Variável Raiz"},
    "intermediaria": {"cor": "#E6F4EA", "borda": "#2F855A", "estilo_linha": "solid", "rotulo": "Intermediária"},
    "latente": {"cor": "#FEF3C7", "borda": "#B7791F", "estilo_linha": "dashed", "rotulo": "Latente (não observável)"},
    "alvo": {"cor": "#FEE2E2", "borda": "#C53030", "estilo_linha": "solid", "rotulo": "Variável Alvo"},
}


def exportar_dot(
    rede: DiscreteBayesianNetwork,
    caminho_dot: str | Path = SAIDA_DOT_PADRAO,
    tipos_nos: dict[str, str] | None = None,
) -> Path:
    """Exporta a estrutura do grafo no formato Graphviz DOT via pydot."""
    destino = Path(caminho_dot)
    destino.parent.mkdir(parents=True, exist_ok=True)

    grafo_dot = pydot.Dot("RedeBayesianaEvasao", graph_type="digraph", rankdir="TB")
    tipos = tipos_nos or {}

    for no in rede.nodes():
        tipo = tipos.get(no, "intermediaria")
        estilo = ESTILOS_TIPO.get(tipo, ESTILOS_TIPO["intermediaria"])
        node_dot = pydot.Node(
            no,
            label=no.replace("_", "\n"),
            shape="box",
            style="rounded,filled,dashed" if tipo == "latente" else "rounded,filled",
            fillcolor=estilo["cor"],
            color=estilo["borda"],
        )
        grafo_dot.add_node(node_dot)

    for origem, destino_no in rede.edges():
        grafo_dot.add_edge(pydot.Edge(origem, destino_no))

    destino.write_text(grafo_dot.to_string(), encoding="utf-8")
    return destino


def gerar_imagem_rede(
    rede: DiscreteBayesianNetwork,
    dados_modelo: dict | None = None,
    caminho_png: str | Path = SAIDA_PNG_PADRAO,
    caminho_dot: str | Path | None = SAIDA_DOT_PADRAO,
) -> Path:
    """
    Desenha o DAG da rede bayesiana organizado em camadas topológicas e salva em PNG.
    Opcionalmente exporta também o arquivo .dot correspondente.
    """
    destino = Path(caminho_png)
    destino.parent.mkdir(parents=True, exist_ok=True)

    tipos_nos: dict[str, str] = {}
    if dados_modelo:
        for var in dados_modelo.get("variaveis", []):
            tipos_nos[var["id"]] = var.get("tipo", "intermediaria")

    if caminho_dot is not None:
        exportar_dot(rede, caminho_dot=caminho_dot, tipos_nos=tipos_nos)

    grafo = nx.DiGraph()
    grafo.add_nodes_from(rede.nodes())
    grafo.add_edges_from(rede.edges())

    camadas = list(nx.topological_generations(grafo))
    posicoes: dict[str, tuple[float, float]] = {}
    num_camadas = len(camadas)

    for idx_camada, nos_camada in enumerate(camadas):
        nos_ordenados = sorted(nos_camada)
        largura = len(nos_ordenados)
        y = float(num_camadas - 1 - idx_camada)
        for idx_no, no in enumerate(nos_ordenados):
            x = (idx_no - (largura - 1) / 2.0) * 2.2
            posicoes[no] = (x, y * 1.8)

    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=180)
    ax.set_axis_off()

    # Desenha arestas direcionadas com leve curvatura para evitar sobreposição
    nx.draw_networkx_edges(
        grafo,
        pos=posicoes,
        ax=ax,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=16,
        edge_color="#4A5568",
        width=1.4,
        connectionstyle="arc3,rad=0.06",
        node_size=3400,
    )

    # Desenha caixas dos nós com estilo por papel na rede
    for no, (x, y) in posicoes.items():
        tipo = tipos_nos.get(no, "intermediaria")
        estilo = ESTILOS_TIPO.get(tipo, ESTILOS_TIPO["intermediaria"])
        rotulo = no.replace("_", "\n")

        ax.text(
            x,
            y,
            rotulo,
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color="#1A202C",
            bbox={
                "boxstyle": "round,pad=0.55",
                "facecolor": estilo["cor"],
                "edgecolor": estilo["borda"],
                "linewidth": 1.8,
                "linestyle": estilo["estilo_linha"],
            },
            zorder=4,
        )

    # Ajusta margens dos eixos para nenhuma caixa ser cortada
    xs = [p[0] for p in posicoes.values()]
    ys = [p[1] for p in posicoes.values()]
    ax.set_xlim(min(xs) - 1.6, max(xs) + 1.6)
    ax.set_ylim(min(ys) - 1.1, max(ys) + 1.1)

    titulo = "Estrutura da Rede Bayesiana — Evasão e Sucesso Acadêmico"
    if dados_modelo and "projeto" in dados_modelo:
        titulo = f"Rede Bayesiana: {dados_modelo['projeto']['tema']}"
    ax.set_title(titulo, fontsize=12, fontweight="bold", pad=14, color="#1A202C")

    if tipos_nos:
        handles = [
            mpatches.Patch(
                facecolor=cfg["cor"],
                edgecolor=cfg["borda"],
                linestyle=cfg["estilo_linha"],
                linewidth=1.5,
                label=cfg["rotulo"],
            )
            for tipo_chave, cfg in ESTILOS_TIPO.items()
            if tipo_chave in set(tipos_nos.values())
        ]
        ax.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.03),
            ncol=len(handles),
            frameon=False,
            fontsize=8.5,
        )

    plt.tight_layout()
    fig.savefig(destino, bbox_inches="tight")
    plt.close(fig)
    return destino