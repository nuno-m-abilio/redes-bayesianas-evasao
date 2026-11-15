"""
Definição canônica da rede (CONGELADA no Dia 1).

Fonte única de: variáveis, estados, arcos e pais.
Alterações exigem PR revisado pelos três integrantes.

Importante: os arcos representam HIPÓTESES de dependência probabilística,
não causalidade comprovada pelo dataset.
"""
from __future__ import annotations

from graphlib import TopologicalSorter
from itertools import product

RAIZ_TIPO = "raiz"
INTERMEDIARIA = "intermediaria"
LATENTE = "latente"
ALVO = "alvo"

# Ordem dos estados = ordem das colunas das CPTs. Estados em ordem do "pior" para o
# "melhor" onde faz sentido, exceto onde indicado.
VARIAVEIS: dict[str, dict] = {
    "Area_Curso": {
        "nome": "Área do curso",
        "descricao": "Área de conhecimento do curso, agrupando os códigos de curso do dataset.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {
            "Saude": "Enfermagem e higiene oral",
            "Ciencias_Sociais": "Serviço social e educação básica",
            "Gestao_Turismo": "Gestão e turismo",
            "Comunicacao_Design": "Design de comunicação, animação/multimídia, publicidade/gestão de propaganda e jornalismo",
            "Ciencias_Agricolas": "Agronomia, enfermagem veterinária e equinocultura",
            "Engenharias_Tecnologia": "Tecnologias de produção de biocombustíveis e engenharia informática",
        },
    },
    "Faixa_Etaria": {
        "nome": "Faixa etária no ingresso",
        "descricao": "Idade do estudante no momento da matrícula.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {
            "Jovem": "idade <= 20 anos",
            "Adulto": "21 a 25 anos",
            "Maduro": "idade > 25 anos",
        },
    },
    "Escolaridade_Pais": {
        "nome": "Escolaridade dos pais",
        "descricao": "Maior nível de escolaridade entre mãe e pai.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {
            "Baixa": "ensino básico, sem escolaridade ou desconhecida",
            "Media": "ensino secundário e equivalentes",
            "Alta": "ensino superior",
        },
    },
    "Bolsista": {
        "nome": "Bolsista",
        "descricao": "O estudante recebe bolsa de estudos.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {"Sim": "possui bolsa", "Nao": "não possui bolsa"},
    },
    "Deslocado": {
        "nome": "Deslocado",
        "descricao": "O estudante vive fora de sua cidade de origem para estudar.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {"Sim": "estudante deslocado", "Nao": "não deslocado"},
    },
    "Nota_Admissao": {
        "nome": "Nota de admissão",
        "descricao": "Nota de admissão (escala 0-200) discretizada.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {
            "Baixa": "nota < 115",
            "Media": "115 <= nota < 135",
            "Alta": "nota >= 135",
        },
    },
    "Desemprego": {
        "nome": "Taxa de desemprego no contexto",
        "descricao": "Taxa de desemprego (contexto macroeconômico) no período do estudante.",
        "tipo": RAIZ_TIPO,
        "observavel": True,
        "estados": {"Baixo": "taxa <= 11%", "Alto": "taxa > 11%"},
    },
    "Turno": {
        "nome": "Turno de frequência",
        "descricao": "Regime de frequência às aulas.",
        "tipo": INTERMEDIARIA,
        "observavel": True,
        "estados": {"Diurno": "aulas diurnas", "Noturno": "aulas noturnas"},
    },
    "Pressao_Financeira": {
        "nome": "Pressão financeira (latente)",
        "descricao": "Variável latente: grau de pressão financeira sobre o estudante. Não existe no dataset.",
        "tipo": LATENTE,
        "observavel": False,
        "estados": {
            "Baixa": "baixa pressão financeira",
            "Alta": "alta pressão financeira",
        },
    },
    "Devedor": {
        "nome": "Devedor",
        "descricao": "O estudante possui dívida com a instituição.",
        "tipo": INTERMEDIARIA,
        "observavel": True,
        "estados": {"Sim": "possui dívida", "Nao": "sem dívida"},
    },
    "Mensalidade_Em_Dia": {
        "nome": "Mensalidade em dia",
        "descricao": "As taxas acadêmicas estão em dia.",
        "tipo": INTERMEDIARIA,
        "observavel": True,
        "estados": {"Sim": "pagamentos em dia", "Nao": "pagamentos atrasados"},
    },
    "Desempenho_Sem1": {
        "nome": "Desempenho no 1º semestre",
        "descricao": "Taxa de aprovação (aprovadas/inscritas) no 1º semestre.",
        "tipo": INTERMEDIARIA,
        "observavel": True,
        "estados": {
            "Baixo": "taxa < 0,50",
            "Medio": "0,50 <= taxa < 0,85",
            "Alto": "taxa >= 0,85",
        },
    },
    "Desempenho_Sem2": {
        "nome": "Desempenho no 2º semestre",
        "descricao": "Taxa de aprovação (aprovadas/inscritas) no 2º semestre.",
        "tipo": INTERMEDIARIA,
        "observavel": True,
        "estados": {
            "Baixo": "taxa < 0,50",
            "Medio": "0,50 <= taxa < 0,85",
            "Alto": "taxa >= 0,85",
        },
    },
    "Desfecho": {
        "nome": "Desfecho acadêmico",
        "descricao": "Situação do estudante ao final da duração normal do curso.",
        "tipo": ALVO,
        "observavel": True,
        "estados": {
            "Dropout": "evadiu",
            "Enrolled": "ainda matriculado",
            "Graduate": "concluiu o curso",
        },
    },
}

# (pai, filho, justificativa curta). A ORDEM dos pais de um filho segue a ordem desta lista
# e define a ordem de configurações das CPTs.
ARCOS: list[tuple[str, str, str]] = [
    ("Area_Curso", "Turno", "Alguns cursos são oferecidos predominantemente no período noturno."),
    ("Faixa_Etaria", "Turno", "Estudantes mais velhos tendem a conciliar estudo e trabalho, preferindo o noturno."),
    ("Escolaridade_Pais", "Pressao_Financeira", "Menor escolaridade familiar associa-se a menor renda e menor suporte."),
    ("Bolsista", "Pressao_Financeira", "A bolsa alivia o custo do estudo."),
    ("Deslocado", "Pressao_Financeira", "Morar fora de casa acrescenta custos de moradia e transporte."),
    ("Pressao_Financeira", "Devedor", "Pressão financeira alta leva a dívidas com a instituição (sintoma observável)."),
    ("Pressao_Financeira", "Mensalidade_Em_Dia", "Pressão financeira alta leva a atrasos de pagamento (sintoma observável)."),
    ("Nota_Admissao", "Desempenho_Sem1", "Melhor preparo prévio favorece o rendimento inicial."),
    ("Faixa_Etaria", "Desempenho_Sem1", "Idade influencia a adaptação e a disponibilidade para estudar."),
    ("Area_Curso", "Desempenho_Sem1", "Cursos têm exigências e taxas de aprovação distintas."),
    ("Desempenho_Sem1", "Desempenho_Sem2", "O rendimento no 1º semestre persiste no semestre seguinte."),
    ("Pressao_Financeira", "Desempenho_Sem2", "Pressão financeira reduz o tempo e a energia dedicados aos estudos."),
    ("Turno", "Desempenho_Sem2", "O turno noturno tende a reduzir o tempo disponível para estudo."),
    ("Desempenho_Sem2", "Desfecho", "O rendimento recente é o principal indicador do desfecho."),
    ("Pressao_Financeira", "Desfecho", "Pressão financeira influencia a decisão de abandonar, além do desempenho."),
    ("Desemprego", "Desfecho", "Contexto econômico afeta a permanência e a conclusão."),
]

ESTADOS: dict[str, list[str]] = {v: list(d["estados"]) for v, d in VARIAVEIS.items()}

PAIS: dict[str, list[str]] = {v: [] for v in VARIAVEIS}
for _de, _para, _ in ARCOS:
    PAIS[_para].append(_de)

FILHOS: dict[str, list[str]] = {v: [] for v in VARIAVEIS}
for _de, _para, _ in ARCOS:
    FILHOS[_de].append(_para)

VARIAVEIS_OBSERVAVEIS = [v for v, d in VARIAVEIS.items() if d["observavel"]]


def ordem_topologica() -> list[str]:
    """Pais antes dos filhos (determinística). Levanta CycleError se houver ciclo."""
    return list(TopologicalSorter({v: set(p) for v, p in PAIS.items()}).static_order())


def configuracoes_pais(variavel: str) -> list[dict[str, str]]:
    """
    Todas as configurações dos pais de `variavel`, na ordem usada pelo pgmpy:
    produto cartesiano na ordem de PAIS[variavel], com o ÚLTIMO pai variando mais rápido.
    Para raízes devolve [{}] (uma única configuração vazia).
    """
    pais = PAIS[variavel]
    if not pais:
        return [{}]
    return [dict(zip(pais, combinacao)) for combinacao in product(*(ESTADOS[p] for p in pais))]


def validar_definicao() -> None:
    """Sanidade da própria definição (usada pelos testes e pelo gerador)."""
    for de, para, _ in ARCOS:
        if de not in VARIAVEIS or para not in VARIAVEIS:
            raise ValueError(f"Arco com variável inexistente: {de} -> {para}")
    ordem_topologica()
    for v, d in VARIAVEIS.items():
        if len(ESTADOS[v]) < 2:
            raise ValueError(f"{v}: precisa de pelo menos 2 estados")
        if len(PAIS[v]) > 3:
            raise ValueError(f"{v}: mais de 3 pais")


validar_definicao()