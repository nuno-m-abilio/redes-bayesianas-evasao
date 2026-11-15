# Guia de Interpretação do `modelo.json`

O arquivo `modelo.json` é a fonte única da verdade do sistema. Ele descreve a rede bayesiana de forma declarativa e independente da biblioteca de inferência utilizada.

## Estrutura de Alto Nível

| Chave | Tipo | Descrição |
| :--- | :--- | :--- |
| `projeto` | `object` | Metadados do tema, pergunta principal, procedência do dataset UCI e nota sobre causalidade vs. dependência probabilística. |
| `variaveis` | `array` | Lista das 14 variáveis discretas da rede (`id`, `nome`, `descricao`, `tipo`, `observavel` e lista de `estados` com suas interpretações). |
| `estrutura` | `object` | Topologia do grafo direcionado acíclico (DAG), dividida em `arcos` (com justificativa de domínio) e `pais` (mapeamento explícito `filho -> [pais]`). |
| `probabilidades` | `array` | Tabelas de Probabilidade Condicional (CPTs) completas de todas as variáveis. |
| `cenarios` | `array` | Definição dos 4 cenários de análise (preditiva, alerta precoce, diagnóstica e prescritiva) com evidências, consultas e expectativas. |
| `metadados_execucao` | `object` | Versão mínima do Python e versões das bibliotecas utilizadas na geração do arquivo. |

## Como Ler as CPTs (`probabilidades`)

Cada entrada da lista `probabilidades` especifica:
* `variavel`: identificador do nó condicionado.
* `pais`: lista ordenada dos nós pais (vazia `[]` para nós raiz).
* `estados`: lista ordenada dos estados possíveis da variável.
* `linhas`: conjunto completo de combinações dos estados dos pais (`configuracao_pais`), onde cada linha mapeia explicitamente cada estado da variável à sua probabilidade (`probabilidades`). Todas as probabilidades pertencem a $[0, 1]$ e somam `1.0` por linha.
* `regra_geracao`: documentação da regra de domínio utilizada para especificar manualmente os valores.

## Como Ler os Cenários (`cenarios`)

Cada cenário combina `evidencias_base` com cada item de `variantes` (`evidencias_adicionais`) para consultar a distribuição posterior das variáveis listadas em `consultas`:
* `expectativas`: define comparações qualitativas verificáveis entre variantes (ex.: `maior` vs. `menor` probabilidade para um dado estado).
* `decisao` *(opcional, presente em `S4_prescritivo`)*: especifica `utilidades` por estado da variável consultada e `alternativas` com seus respectivos `custo`s para cálculo de utilidade esperada líquida ($EU = \sum P(s) \cdot U(s) - \text{custo}$).