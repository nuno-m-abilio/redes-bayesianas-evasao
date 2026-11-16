"""
Geração manual das CPTs (Tabelas de Probabilidade Condicional) por regras de domínio.

Como funciona este arquivo:
1. Para as 7 variáveis RAIZ (que não têm pais), definimos diretamente as probabilidades
   a priori arredondadas, inspiradas na análise exploratória do domínio.
2. Para as 7 variáveis COM PAIS, usamos um sistema de PONTOS DE RISCO:
   - Cada característica dos pais recebe uma pontuação de dificuldade (ex.: Sem bolsa = +2.0).
   - O aluno com 0 pontos recebe as probabilidades do 'melhor_caso'.
   - O aluno com a pontuação máxima recebe as probabilidades do 'pior_caso'.
   - Quem fica no meio do caminho recebe valores proporcionais entre os dois extremos.
"""
from __future__ import annotations

from . import definicao as d

# False indica ao gerador do modelo.json que estas já são as regras oficiais (não mais uniformes)
PRELIMINAR = False

# Piso mínimo exigido pelo projeto: nenhuma probabilidade pode ser 0 ou 1 absolutos
PISO = 0.02


def _normalizar_com_piso(probs: dict[str, float]) -> dict[str, float]:
    """
    Garante que todas as probabilidades fiquem >= PISO (0.02) e somem EXATAMENTE 1.0,
    corrigindo qualquer diferença de arredondamento no estado mais provável.
    """
    ajustadas = {estado: max(PISO, valor) for estado, valor in probs.items()}
    soma = sum(ajustadas.values())
    arredondadas = {estado: round(valor / soma, 4) for estado, valor in ajustadas.items()}

    # Ajuste fino de 0.0001 caso o arredondamento deixe a soma em 0.9999 ou 1.0001
    diferenca = round(1.0 - sum(arredondadas.values()), 4)
    if diferenca != 0:
        maior_estado = max(arredondadas, key=arredondadas.get)
        arredondadas[maior_estado] = round(arredondadas[maior_estado] + diferenca, 4)

    return arredondadas


def _calcular_por_pontos(
    variavel: str,
    pontos_por_pai: dict[str, dict[str, float]],
    melhor_caso: dict[str, float],
    pior_caso: dict[str, float],
    regra_desc: str,
) -> dict:
    """
    Calcula todas as linhas da CPT de uma variável a partir dos pontos de risco de seus pais.
    """
    min_pts = sum(min(opcoes.values()) for opcoes in pontos_por_pai.values())
    max_pts = sum(max(opcoes.values()) for opcoes in pontos_por_pai.values())
    amplitude = max(max_pts - min_pts, 1e-9)

    linhas = []
    # d.configuracoes_pais(variavel) já gera as combinações na ordem exata exigida pelo pgmpy
    for cfg in d.configuracoes_pais(variavel):
        pontos_atuais = sum(pontos_por_pai[pai][estado] for pai, estado in cfg.items())
        # Fator vai de 0.0 (melhor cenário possível) até 1.0 (pior cenário possível)
        fator = (pontos_atuais - min_pts) / amplitude

        probs_brutas = {}
        for estado in d.ESTADOS[variavel]:
            p_inicio = melhor_caso[estado]
            p_fim = pior_caso[estado]
            probs_brutas[estado] = p_inicio + fator * (p_fim - p_inicio)

        linhas.append({
            "configuracao_pais": cfg,
            "probabilidades": _normalizar_com_piso(probs_brutas),
        })

    return {
        "variavel": variavel,
        "pais": list(d.PAIS[variavel]),
        "estados": list(d.ESTADOS[variavel]),
        "linhas": linhas,
        "regra_geracao": regra_desc,
    }


# ===========================================================================
# BLOCO 1: AS 7 VARIÁVEIS RAIZ (Sem pais — probabilidades definidas à mão)
# ===========================================================================
PRIORIS_RAIZES: dict[str, tuple[dict[str, float], str]] = {
    "Area_Curso": (
        {
            "Saude": 0.20,
            "Ciencias_Sociais": 0.15,
            "Gestao_Turismo": 0.20,
            "Comunicacao_Design": 0.25,
            "Ciencias_Agricolas": 0.15,
            "Engenharias_Tecnologia": 0.05,
        },
        "Distribuição equilibrada entre as 6 áreas de conhecimento agrupadas do dataset.",
    ),
    "Faixa_Etaria": (
        {"Jovem": 0.60, "Adulto": 0.15, "Maduro": 0.25},
        "Predomínio de ingressantes jovens (<=20 anos) vindos do ensino secundário.",
    ),
    "Escolaridade_Pais": (
        {"Baixa": 0.30, "Media": 0.50, "Alta": 0.20},
        "Maior proporção de famílias com escolaridade básica/secundária no contexto analisado.",
    ),
    "Bolsista": (
        {"Sim": 0.25, "Nao": 0.75},
        "Aproximadamente um quarto dos estudantes conta com bolsa de estudos.",
    ),
    "Deslocado": (
        {"Sim": 0.55, "Nao": 0.45},
        "Pouco mais da metade dos estudantes reside fora da cidade de origem.",
    ),
    "Nota_Admissao": (
        {"Baixa": 0.20, "Media": 0.55, "Alta": 0.25},
        "Concentração na faixa intermediária de nota de ingresso (115 a 135 pontos).",
    ),
    "Desemprego": (
        {"Baixo": 0.45, "Alto": 0.55},
        "Cenário macroeconômico dividido entre períodos favoráveis e adversos pode ajudar a entender o desempenho dos alunos.",
    ),
}


def _cpt_raiz(variavel: str) -> dict:
    probs, justificativa = PRIORIS_RAIZES[variavel]
    return {
        "variavel": variavel,
        "pais": [],
        "estados": list(d.ESTADOS[variavel]),
        "linhas": [
            {
                "configuracao_pais": {},
                "probabilidades": _normalizar_com_piso(probs),
            }
        ],
        "regra_geracao": justificativa,
    }


# ===========================================================================
# BLOCO 2: AS 7 VARIÁVEIS COM PAIS (Calculadas por pontos de risco)
# ===========================================================================

def _cpt_turno() -> dict:
    # Pais: Area_Curso, Faixa_Etaria
    # Pontuação mede a tendência de o aluno estudar no período NOTURNO.
    pontos = {
        "Faixa_Etaria": {
            "Jovem": 0.5,   # Jovens geralmente têm disponibilidade integral
            "Adulto": 1.5,  # Parte já trabalha durante o dia
            "Maduro": 2.5,  # Estudantes >25 anos costumam conciliar emprego e faculdade
        },
        "Area_Curso": {
            "Saude": 0.0,                   # Cursos de saúde são majoritariamente diurnos
            "Ciencias_Agricolas": 0.0,      # Atividades práticas diurnas
            "Engenharias_Tecnologia": 0.5,  # Predomínio diurno, com algumas turmas noturnas
            "Comunicacao_Design": 1.0,      # Oferta mista
            "Ciencias_Sociais": 1.5,        # Forte oferta noturna
            "Gestao_Turismo": 2.0,          # Cursos tradicionalmente noturnos
        },
    }
    return _calcular_por_pontos(
        variavel="Turno",
        pontos_por_pai=pontos,
        melhor_caso={"Diurno": 0.98, "Noturno": 0.02},  # Jovem em Saúde/Agrárias
        pior_caso={"Diurno": 0.70, "Noturno": 0.30},    # Maduro em Gestão/Turismo
        regra_desc="Pontuação de adesão ao noturno: idade mais avançada (até +2.5) e áreas com oferta noturna (até +2.0).",
    )


def _cpt_pressao_financeira() -> dict:
    # Pais: Escolaridade_Pais, Bolsista, Deslocado
    # Pontuação mede o nível de aperto financeiro sobre o estudante.
    pontos = {
        "Bolsista": {
            "Sim": 0.0,  # Bolsa alivia os custos acadêmicos
            "Nao": 2.0,  # Sem bolsa aumenta o peso financeiro
        },
        "Deslocado": {
            "Nao": 0.0,  # Mora com a família
            "Sim": 1.5,  # Gastos extras com moradia, alimentação e transporte
        },
        "Escolaridade_Pais": {
            "Alta": 0.0,   # Maior estabilidade socioeconômica familiar
            "Media": 0.5,  # Suporte intermediário
            "Baixa": 1.5,  # Menor capacidade de suporte financeiro familiar
        },
    }
    return _calcular_por_pontos(
        variavel="Pressao_Financeira",
        pontos_por_pai=pontos,
        melhor_caso={"Baixa": 0.95, "Alta": 0.05},
        pior_caso={"Baixa": 0.30, "Alta": 0.70},
        regra_desc="Pontuação de risco: ausência de bolsa (+2.0), deslocamento (+1.5) e baixa escolaridade dos pais (+1.5).",
    )


def _cpt_devedor() -> dict:
    # Pai: Pressao_Financeira
    # Sintoma observável: alta pressão financeira aumenta a chance de contrair dívidas.
    pontos = {
        "Pressao_Financeira": {"Baixa": 0.0, "Alta": 1.0},
    }
    return _calcular_por_pontos(
        variavel="Devedor",
        pontos_por_pai=pontos,
        melhor_caso={"Sim": 0.02, "Nao": 0.98},
        pior_caso={"Sim": 0.18, "Nao": 0.82},
        regra_desc="Sintoma de Pressao_Financeira: pressão alta eleva probabilidade de dívida de 2% para 18%.",
    )


def _cpt_mensalidade_em_dia() -> dict:
    # Pai: Pressao_Financeira
    # Sintoma observável: alta pressão financeira aumenta atrasos nas taxas acadêmicas.
    pontos = {
        "Pressao_Financeira": {"Baixa": 0.0, "Alta": 1.0},
    }
    return _calcular_por_pontos(
        variavel="Mensalidade_Em_Dia",
        pontos_por_pai=pontos,
        melhor_caso={"Sim": 0.98, "Nao": 0.02},
        pior_caso={"Sim": 0.82, "Nao": 0.18},
        regra_desc="Sintoma de Pressao_Financeira: pressão alta eleva atraso de mensalidade de 2% para 18%.",
    )


def _cpt_desempenho_sem1() -> dict:
    # Pais: Nota_Admissao, Faixa_Etaria, Area_Curso
    # Pontuação mede dificuldade acadêmica inicial (quanto maior, maior chance de desempenho Baixo).
    pontos = {
        "Nota_Admissao": {
            "Alta": 0.0,   # Forte base prévia
            "Media": 1.5,  # Base intermediária
            "Baixa": 3.0,  # Maior defasagem na entrada
        },
        "Faixa_Etaria": {
            "Jovem": 0.0,   # Hábito de estudo recente
            "Adulto": 0.5,  # Adaptação intermediária
            "Maduro": 1.0,  # Maior tempo afastado dos estudos formais
        },
        "Area_Curso": {
            "Saude": 0.0,                   # Altas taxas históricas de aprovação inicial
            "Ciencias_Sociais": 0.2,
            "Comunicacao_Design": 0.3,
            "Gestao_Turismo": 0.5,
            "Ciencias_Agricolas": 0.7,
            "Engenharias_Tecnologia": 1.0,  # Maior índice de reprovação nas disciplinas básicas
        },
    }
    return _calcular_por_pontos(
        variavel="Desempenho_Sem1",
        pontos_por_pai=pontos,
        melhor_caso={"Baixo": 0.05, "Medio": 0.25, "Alto": 0.70},
        pior_caso={"Baixo": 0.65, "Medio": 0.25, "Alto": 0.10},
        regra_desc="Pontuação de dificuldade inicial: nota de admissão (+3.0), faixa etária (+1.0) e exigência da área (+1.0).",
    )


def _cpt_desempenho_sem2() -> dict:
    # Pais: Desempenho_Sem1, Pressao_Financeira, Turno
    # Pontuação mede risco de queda de rendimento no 2º semestre.
    pontos = {
        "Desempenho_Sem1": {
            "Alto": 0.0,   # Inércia positiva de bom desempenho
            "Medio": 2.0,  # Desempenho regular
            "Baixo": 4.0,  # Dificuldades acumuladas do 1º semestre
        },
        "Pressao_Financeira": {
            "Baixa": 0.0,
            "Alta": 1.0,   # Preocupação financeira reduz foco e dedicação
        },
        "Turno": {
            "Diurno": 0.0,
            "Noturno": 0.5,  # Menor tempo livre para estudo extraclasse
        },
    }
    return _calcular_por_pontos(
        variavel="Desempenho_Sem2",
        pontos_por_pai=pontos,
        melhor_caso={"Baixo": 0.04, "Medio": 0.21, "Alto": 0.75},
        pior_caso={"Baixo": 0.78, "Medio": 0.17, "Alto": 0.05},
        regra_desc="Pontuação de risco no 2º sem: histórico do 1º sem (+4.0), pressão financeira (+1.0) e turno noturno (+0.5).",
    )


def _cpt_desfecho() -> dict:
    # Pais: Desempenho_Sem2, Pressao_Financeira, Desemprego
    # Pontuação mede o risco final de evasão (Dropout).
    pontos = {
        "Desempenho_Sem2": {
            "Alto": 0.0,   # Forte trajetória de conclusão
            "Medio": 1.8,  # Trajetória intermediária (parte permanece matriculada)
            "Baixo": 4.0,  # Principal preditor direto de evasão
        },
        "Pressao_Financeira": {
            "Baixa": 0.0,
            "Alta": 1.5,   # Pode forçar abandono mesmo com notas razoáveis
        },
        "Desemprego": {
            "Baixo": 0.0,
            "Alto": 0.5,   # Crise econômica dificulta manter os estudos
        },
    }
    return _calcular_por_pontos(
        variavel="Desfecho",
        pontos_por_pai=pontos,
        melhor_caso={"Dropout": 0.04, "Enrolled": 0.16, "Graduate": 0.80},
        pior_caso={"Dropout": 0.82, "Enrolled": 0.13, "Graduate": 0.05},
        regra_desc="Pontuação de risco de evasão: desempenho no 2º sem (+4.0), pressão financeira (+1.5) e desemprego (+0.5).",
    )


# ===========================================================================
# FUNÇÃO PRINCIPAL (Contrato chamado pelo gerar_modelo_json.py)
# ===========================================================================
_GERADORES_FILHOS = {
    "Turno": _cpt_turno,
    "Pressao_Financeira": _cpt_pressao_financeira,
    "Devedor": _cpt_devedor,
    "Mensalidade_Em_Dia": _cpt_mensalidade_em_dia,
    "Desempenho_Sem1": _cpt_desempenho_sem1,
    "Desempenho_Sem2": _cpt_desempenho_sem2,
    "Desfecho": _cpt_desfecho,
}


def gerar_todas_cpts() -> dict[str, dict]:
    """Devolve o dicionário completo com as 14 CPTs na ordem topológica da rede."""
    resultado: dict[str, dict] = {}
    for variavel in d.ordem_topologica():
        if variavel in PRIORIS_RAIZES:
            resultado[variavel] = _cpt_raiz(variavel)
        else:
            resultado[variavel] = _GERADORES_FILHOS[variavel]()
    return resultado