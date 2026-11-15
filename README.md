# Rede Bayesiana para Risco de Evasão no Ensino Superior (AMMCI 2026)

Aplicação baseada em uma **Rede Bayesiana construída manualmente** (14 variáveis discretas e 16 arcos) para investigar o risco de evasão (`Dropout`), permanência (`Enrolled`) e conclusão (`Graduate`) no ensino superior, contextualizada pelo dataset *Predict Students' Dropout and Academic Success* (UCI Machine Learning Repository, ID 697).

> **Nota metodológica:** Os arcos representam hipóteses de dependência probabilística fundamentadas no domínio educacional. Nenhuma estrutura ou distribuição de probabilidade foi aprendida automaticamente a partir dos dados.

## Bibliotecas Utilizadas e Contribuições

| Biblioteca | Contribuição no Projeto |
| :--- | :--- |
| **`pgmpy`** | Representação da rede (`DiscreteBayesianNetwork`), definição das tabelas condicionais (`TabularCPD`) e inferência exata (`VariableElimination`). |
| **`networkx`** | Verificação formal de propriedade acíclica (DAG) e ordenação topológica por camadas para layout do grafo. |
| **`jsonschema`** | Validação sintática e estrutural do arquivo `modelo.json` contra o esquema oficial. |
| **`matplotlib` e `pydot`** | Geração da representação gráfica da estrutura da rede em PNG e exportação no formato DOT. |
| **`pandas` e `numpy`** | Exclusivamente para discretização exploratória e tabelas de contextualização do dataset (`scripts/discretizar_dataset.py`), fora do motor da rede. |
| **`pytest`** | Execução da suíte de testes automatizados (estrutura, CPTs, inferência, cenários e casos inválidos). |

## Instalação

Requer **Python 3.11+**.

```bash
python3 -m venv .venv
source .venv/bin/activate        # No Windows (Git Bash): source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt