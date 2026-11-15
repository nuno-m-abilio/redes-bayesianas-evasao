#!/usr/bin/env python3
"""
Discretização exploratória do dataset "Predict Students' Dropout and Academic Success".

FINALIDADE: contextualizar o domínio e apoiar a justificativa das escolhas de
modelagem (EDA). Este script NÃO aprende estrutura nem estima probabilidades,
e sua saída NÃO alimenta automaticamente as CPTs da rede. As CPTs são
definidas manualmente (ver src/bn_evasao/cpt_rules.py e modelo.json).

Uso:
    python scripts/discretizar_dataset.py
    python scripts/discretizar_dataset.py --entrada data/raw/data.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_ENTRADA = RAIZ / "data" / "raw" / "data.csv"
CSV_SAIDA = RAIZ / "data" / "processed" / "dados_discretizados.csv"
DIR_EDA = RAIZ / "outputs" / "eda"

# ---------------------------------------------------------------------------
# Estados de cada variável observável (a ordem das chaves define as colunas).
# Pressao_Financeira é LATENTE: não existe no dataset e não aparece aqui.
# ---------------------------------------------------------------------------
ESTADOS: dict[str, list[str]] = {
    "Area_Curso": ["Saude", "Ciencias_Sociais", "Gestao_Turismo",
                   "Comunicacao_Design", "Ciencias_Agricolas", "Engenharias_Tecnologia"],
    "Faixa_Etaria": ["Jovem", "Adulto", "Maduro"],
    "Escolaridade_Pais": ["Baixa", "Media", "Alta"],
    "Bolsista": ["Sim", "Nao"],
    "Deslocado": ["Sim", "Nao"],
    "Nota_Admissao": ["Baixa", "Media", "Alta"],
    "Desemprego": ["Baixo", "Alto"],
    "Turno": ["Diurno", "Noturno"],
    "Devedor": ["Sim", "Nao"],
    "Mensalidade_Em_Dia": ["Sim", "Nao"],
    "Desempenho_Sem1": ["Baixo", "Medio", "Alto"],
    "Desempenho_Sem2": ["Baixo", "Medio", "Alto"],
    "Desfecho": ["Dropout", "Enrolled", "Graduate"],
}

COLUNAS_ORIGINAIS = [
    "Course", "Daytime/evening attendance", "Mother's qualification",
    "Father's qualification", "Admission grade", "Displaced", "Debtor",
    "Tuition fees up to date", "Scholarship holder", "Age at enrollment",
    "Curricular units 1st sem (enrolled)", "Curricular units 1st sem (approved)",
    "Curricular units 2nd sem (enrolled)", "Curricular units 2nd sem (approved)",
    "Unemployment rate", "Target",
]

# Códigos de curso (documentação do UCI) agrupados em áreas.
AREA_CURSO = {
    9500: "Saude", 9556: "Saude",
    8014: "Ciencias_Sociais", 9238: "Ciencias_Sociais", 9853: "Ciencias_Sociais",
    9147: "Gestao_Turismo", 9254: "Gestao_Turismo", 9991: "Gestao_Turismo",
    171: "Comunicacao_Design", 9070: "Comunicacao_Design", 9670: "Comunicacao_Design", 9773: "Comunicacao_Design",
    9003: "Ciencias_Agricolas", 9085: "Ciencias_Agricolas", 9130: "Ciencias_Agricolas",
    33: "Engenharias_Tecnologia", 9119: "Engenharias_Tecnologia"
}

# Códigos de qualificação dos pais -> nível 0 (Baixa), 1 (Media), 2 (Alta).
_ALTA = {2, 3, 4, 5, 6, 39, 40, 41, 42, 43, 44}
_MEDIA = {1, 9, 10, 11, 12, 14, 18, 19, 22, 26, 27, 29, 30}
_BAIXA = {34, 35, 36, 37, 38}  # inclui "desconhecido" (34) como nível mais baixo
NIVEL_QUALIFICACAO = {**{c: 2 for c in _ALTA},
                      **{c: 1 for c in _MEDIA},
                      **{c: 0 for c in _BAIXA}}
NOME_NIVEL = {0: "Baixa", 1: "Media", 2: "Alta"}


def nivel_escolaridade(serie: pd.Series) -> pd.Series:
    """Converte códigos de qualificação em nível 0/1/2 (avisa sobre códigos novos)."""
    nivel = serie.map(NIVEL_QUALIFICACAO)
    desconhecidos = sorted(serie[nivel.isna()].unique())
    if desconhecidos:
        print(f"[AVISO] Códigos de qualificação não mapeados (tratados como Baixa): "
              f"{desconhecidos}")
    return nivel.fillna(0).astype(int)


def taxa_aprovacao(aprovadas: pd.Series, inscritas: pd.Series) -> pd.Series:
    """Aprovadas / inscritas. Sem inscrição => taxa 0 (sem aprovação)."""
    return (aprovadas / inscritas.where(inscritas > 0)).fillna(0.0)


def discretizar(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # Idade: <=20 Jovem; 21-25 Adulto; >25 Maduro
    out["Faixa_Etaria"] = pd.cut(
        df["Age at enrollment"], bins=[-np.inf, 20, 25, np.inf],
        labels=ESTADOS["Faixa_Etaria"]).astype(str)

    # Nota de admissão (0-200): <115 Baixa; [115,135) Media; >=135 Alta
    out["Nota_Admissao"] = pd.cut(
        df["Admission grade"], bins=[-np.inf, 115, 135, np.inf],
        labels=ESTADOS["Nota_Admissao"], right=False).astype(str)

    # Escolaridade dos pais: maior nível entre mãe e pai
    nivel = pd.Series(
        np.maximum(nivel_escolaridade(df["Mother's qualification"]),
                   nivel_escolaridade(df["Father's qualification"])),
        index=df.index)
    out["Escolaridade_Pais"] = nivel.map(NOME_NIVEL)

    # Área do curso
    area = df["Course"].map(AREA_CURSO)
    if area.isna().any():
        print(f"[AVISO] Cursos não mapeados: {sorted(df['Course'][area.isna()].unique())}")
    out["Area_Curso"] = area

    # Binárias
    sim_nao = {1: "Sim", 0: "Nao"}
    out["Deslocado"] = df["Displaced"].map(sim_nao)
    out["Bolsista"] = df["Scholarship holder"].map(sim_nao)
    out["Devedor"] = df["Debtor"].map(sim_nao)
    out["Mensalidade_Em_Dia"] = df["Tuition fees up to date"].map(sim_nao)
    out["Turno"] = df["Daytime/evening attendance"].map({1: "Diurno", 0: "Noturno"})

    # Desemprego (macro): <=11% Baixo; >11% Alto
    out["Desemprego"] = np.where(df["Unemployment rate"] <= 11.0, "Baixo", "Alto")

    # Desempenho por semestre: taxa de aprovação (aprovadas/inscritas)
    # <0.5 Baixo; [0.5,0.85) Medio; >=0.85 Alto
    for sem, nome in (("1st", "Desempenho_Sem1"), ("2nd", "Desempenho_Sem2")):
        taxa = taxa_aprovacao(df[f"Curricular units {sem} sem (approved)"],
                              df[f"Curricular units {sem} sem (enrolled)"])
        out[nome] = pd.cut(taxa, bins=[-np.inf, 0.5, 0.85, np.inf],
                           labels=ESTADOS[nome], right=False).astype(str)

    out["Desfecho"] = df["Target"].astype(str).str.strip()

    return out[list(ESTADOS)]  # ordem fixa das colunas


def validar(out: pd.DataFrame) -> None:
    for var, estados in ESTADOS.items():
        if out[var].isna().any():
            raise ValueError(f"{var}: valores ausentes após discretização.")
        invalidos = set(out[var].unique()) - set(estados)
        if invalidos:
            raise ValueError(f"{var}: estados fora do esperado: {invalidos}")


def gerar_eda(out: pd.DataFrame) -> None:
    """Tabelas de leitura para apoiar a justificativa (NÃO alimentam as CPTs)."""
    DIR_EDA.mkdir(parents=True, exist_ok=True)

    marginais = []
    for var in ESTADOS:
        cont = out[var].value_counts().reindex(ESTADOS[var], fill_value=0)
        for estado, n in cont.items():
            marginais.append({"variavel": var, "estado": estado, "contagem": int(n),
                              "proporcao": round(n / len(out), 4)})
    pd.DataFrame(marginais).to_csv(DIR_EDA / "marginais.csv", index=False)

    for var in ESTADOS:
        if var == "Desfecho":
            continue
        prop = pd.crosstab(out[var], out["Desfecho"], normalize="index").round(3)
        prop = prop.reindex(index=ESTADOS[var], columns=ESTADOS["Desfecho"])
        cont = pd.crosstab(out[var], out["Desfecho"]).reindex(
            index=ESTADOS[var], columns=ESTADOS["Desfecho"])
        tabela = prop.join(cont, lsuffix="_prop", rsuffix="_n")
        tabela.to_csv(DIR_EDA / f"cruzada_{var}_x_Desfecho.csv")

    print(f"Tabelas exploratórias salvas em: {DIR_EDA}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", type=Path, default=CSV_ENTRADA)
    ap.add_argument("--saida", type=Path, default=CSV_SAIDA)
    args = ap.parse_args()

    if not args.entrada.exists():
        raise SystemExit(f"Arquivo não encontrado: {args.entrada}\n"
                         "Veja data/README.md para baixar o dataset.")

    df = pd.read_csv(args.entrada, sep=";")
    df.columns = df.columns.str.strip()  # remove espaços/tabs dos cabeçalhos

    faltando = [c for c in COLUNAS_ORIGINAIS if c not in df.columns]
    if faltando:
        raise SystemExit(f"Colunas ausentes no CSV: {faltando}\n"
                         f"Colunas encontradas: {list(df.columns)}")

    out = discretizar(df)
    validar(out)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.saida, index=False)
    print(f"{len(out)} linhas discretizadas -> {args.saida}")

    for var in ESTADOS:
        dist = out[var].value_counts(normalize=True).reindex(ESTADOS[var]).round(3)
        print(f"\n{var}:\n{dist.to_string()}")

    gerar_eda(out)


if __name__ == "__main__":
    main()