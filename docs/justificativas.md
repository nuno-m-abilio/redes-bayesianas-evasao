# Justificativas de Modelagem — Rede Bayesiana de Evasão Acadêmica

## 1. Contextualização do Dataset e Seleção de Variáveis

Para fundamentar a modelagem, utilizou-se o conjunto de dados público *"Predict Students' Dropout and Academic Success"* (UCI Machine Learning Repository, ID 697), originado do projeto SATDAP em uma instituição de ensino superior portuguesa, contendo 4.424 registros de estudantes e 36 atributos sem valores ausentes.

Conforme as diretrizes da disciplina de AMMCI, o *dataset* foi empregado exclusivamente para análise exploratória (EDA), contextualização do domínio e verificação de ordem de grandeza, sem uso de algoritmos de aprendizagem de máquina para estimar a estrutura ou as probabilidades da rede.

### Variáveis selecionadas (14 nós)
Foram selecionadas **13 variáveis observáveis** extraídas do *dataset* e criada **1 variável latente** (`Pressao_Financeira`), totalizando 14 variáveis organizadas em quatro papéis:
* **Raízes (7):** `Area_Curso`, `Faixa_Etaria`, `Escolaridade_Pais`, `Bolsista`, `Deslocado`, `Nota_Admissao` e `Desemprego`.
* **Intermediárias (5):** `Turno`, `Devedor`, `Mensalidade_Em_Dia`, `Desempenho_Sem1` e `Desempenho_Sem2`.
* **Latente (1):** `Pressao_Financeira` (não observada diretamente na planilha, introduzida para sintetizar o impacto conjunto de fatores socioeconômicos sobre a inadimplência e o rendimento).
* **Alvo (1):** `Desfecho` (`Dropout`, `Enrolled` ou `Graduate`).

### O que não modelamos e por quê
Dos 36 atributos originais do *dataset*, 23 foram descartados de forma intencional para evitar explosão combinatória nas tabelas de probabilidade condicional (CPTs) e manter o limite de no máximo 3 pais por nó:
* **Indicadores macroeconômicos redundantes (`Inflation rate`, `GDP`):** Mantivemos apenas `Unemployment rate` (`Desemprego`) como representante do contexto econômico externo, pois o desemprego afeta mais diretamente a capacidade de o estudante se manter ou precisar abandonar o curso para trabalhar.
* **Ocupação dos pais (`Mother's occupation`, `Father's occupation`):** Possuem dezenas de códigos categóricos muito fragmentados; a variável `Escolaridade_Pais` já captura de forma mais limpa e ordinal o capital educacional e socioeconômico da família.
* **Nacionalidade e atributos administrativos (`Nacionality`, `International`, `Application mode`, `Application order`):** Apresentam forte concentração em uma única categoria no *dataset* (estudantes locais) ou dizem respeito apenas ao trâmite burocrático de inscrição, agregando pouco poder explicativo às hipóteses principais da rede.
* **Notas numéricas brutas dos semestres (`Curricular units grade`):** Optou-se pela taxa de aprovação (`aprovadas / inscritas`), que reflete de forma mais direta o progresso curricular efetivo e evita distorções causadas por alunos sem inscrição em disciplinas.

---

## 2. Discretização das Variáveis

Como a rede utiliza variáveis discretas com estados finitos e bem definidos, o script exploratório `scripts/discretizar_dataset.py` converteu as colunas contínuas e códigos numéricos nas seguintes categorias, verificadas via `outputs/eda/marginais.csv` para garantir que nenhum estado ficasse vazio:

* **`Area_Curso` (6 estados):** Agrupamento dos 17 códigos numéricos oficiais de curso do UCI por afinidade de área e perfil curricular:
  * `Saude`: Enfermagem (`9500`) e higiene oral (`9556`).
  * `Ciencias_Sociais`: Serviço social (`8014`, `9238`) e educação básica (`9853`).
  * `Gestao_Turismo`: Gestão (`9147`, `9991`) e turismo (`9254`).
  * `Comunicacao_Design`: Design de comunicação (`9070`), animação/multimídia (`171`), publicidade/gestão de propaganda (`9670`) e jornalismo (`9773`).
  * `Ciencias_Agricolas`: Agronomia (`9003`), enfermagem veterinária (`9085`) e equinocultura (`9130`).
  * `Engenharias_Tecnologia`: Tecnologias de produção de biocombustíveis (`33`) e engenharia informática (`9119`).
* **`Faixa_Etaria` (3 estados):** `Jovem` ($\le 20$ anos, ingresso logo após o ensino médio), `Adulto` ($21\text{ a }25$ anos, transição para o mercado de trabalho) e `Maduro` ($> 25$ anos, perfil frequentemente trabalhador).
* **`Escolaridade_Pais` (3 estados):** Considerou-se o maior nível educacional entre mãe e pai, agrupando todos os códigos oficiais de qualificação do UCI em `Baixa` (ensino básico, sem escolaridade ou desconhecida — códigos `34` a `38`), `Media` (ensino secundário e equivalentes — códigos `1, 9–14, 18–20, 22, 25–27, 29–31, 33`) e `Alta` (ensino superior — códigos `2–6, 39–44`).
* **`Nota_Admissao` (3 estados):** Escala original de $0$ a $200$ dividida em `Baixa` ($< 115$), `Media` ($115 \le \text{nota} < 135$) e `Alta` ($\ge 135$), separando ingressantes com defasagem, preparo intermediário e alto rendimento prévio.
* **`Desemprego` (2 estados):** Taxa macroeconômica dividida em `Baixo` ($\le 11\%$) e `Alto` ($> 11\%$), refletindo períodos econômicos favoráveis e adversos registrados no *dataset*.
* **`Desempenho_Sem1` e `Desempenho_Sem2` (3 estados):** Calculados pela razão entre unidades curriculares aprovadas e inscritas em cada semestre (atribuindo taxa $0{,}0$ quando não há inscrição): `Baixo` ($< 0{,}50$, reprovação em mais da metade das disciplinas), `Medio` ($0{,}50 \le \text{taxa} < 0{,}85$, aprovação parcial) e `Alto` ($\ge 0{,}85$, aproveitamento pleno ou quase pleno).
* **Variáveis binárias e alvo:** `Bolsista`, `Deslocado`, `Devedor` e `Mensalidade_Em_Dia` foram mapeadas para `Sim`/`Nao`; `Turno` para `Diurno`/`Noturno`; e `Desfecho` manteve as três classes originais (`Dropout`, `Enrolled`, `Graduate`).

---

## 3. Estrutura da Rede (DAG) e Justificativa dos 16 Arcos

A rede foi estruturada como um Grafo Direcionado Acíclico (DAG) com 14 nós e 16 arcos, respeitando o teto de 3 pais por nó. Os arcos representam **hipóteses de dependência probabilística** fundamentadas na literatura sobre evasão no ensino superior (incluindo Realinho et al., 2022), não configurando prova de causalidade estrita a partir dos dados observacionais.

### Decisões estruturais relevantes
* **Papel da variável latente `Pressao_Financeira`:** Em vez de ligar `Bolsista`, `Deslocado` e `Escolaridade_Pais` diretamente a todos os indicadores financeiros e acadêmicos, a variável latente condensa a vulnerabilidade econômica do estudante. Assim, `Devedor` e `Mensalidade_Em_Dia` atuam como sintomas observáveis dessa pressão latente, permitindo raciocínio diagnóstico quando o estado financeiro real não é diretamente conhecido.
* **Por que `Turno` aponta para `Desempenho_Sem2` e não para `Desempenho_Sem1`:** `Desempenho_Sem1` já possui 3 pais (`Nota_Admissao`, `Faixa_Etaria` e `Area_Curso`), totalizando 54 configurações; adicionar `Turno` dobraria a tabela para 108 linhas. Além disso, os fatores que determinam a escolha do turno (`Area_Curso` e `Faixa_Etaria`) já influenciam diretamente o 1º semestre, enquanto o desgaste acumulado de conciliar trabalho e estudo noturno manifesta-se com maior intensidade na persistência do 2º semestre (`Desempenho_Sem2`).

### Justificativa individual dos arcos
1. **`Area_Curso -> Turno`:** Determinadas áreas (como Gestão, Turismo e Ciências Sociais) possuem oferta tradicionalmente concentrada no período noturno em comparação a cursos de Saúde ou Ciências Agrícolas.
2. **`Faixa_Etaria -> Turno`:** Estudantes mais maduros ($> 25$ anos) tendem a trabalhar em horário comercial, optando majoritariamente por turmas noturnas.
3. **`Escolaridade_Pais -> Pressao_Financeira`:** Menor escolaridade familiar está associada a menor renda domiciliar e menor capacidade de suporte financeiro durante a graduação.
4. **`Bolsista -> Pressao_Financeira`:** O recebimento de bolsa de estudos reduz o custo direto de manutenção acadêmica, aliviando a pressão financeira.
5. **`Deslocado -> Pressao_Financeira`:** Estudantes que residem fora de sua cidade de origem arcam com despesas adicionais de moradia, alimentação e transporte.
6. **`Pressao_Financeira -> Devedor`:** Alta pressão financeira eleva a probabilidade de o estudante contrair dívidas junto à instituição (sintoma observável).
7. **`Pressao_Financeira -> Mensalidade_Em_Dia`:** Dificuldades financeiras aumentam o risco de atraso no pagamento das taxas escolares (sintoma observável).
8. **`Nota_Admissao -> Desempenho_Sem1`:** Melhor desempenho prévio no ingresso indica base acadêmica mais sólida para enfrentar as disciplinas iniciais.
9. **`Faixa_Etaria -> Desempenho_Sem1`:** A idade influencia o tempo de afastamento dos estudos formais e a disponibilidade de dedicação extraclasse na adaptação inicial.
10. **`Area_Curso -> Desempenho_Sem1`:** Diferentes áreas do conhecimento apresentam graus distintos de exigência quantitativa e taxas históricas de aprovação no primeiro período.
11. **`Desempenho_Sem1 -> Desempenho_Sem2`:** Existe forte inércia acadêmica: dificuldades de aprovação no 1º semestre comprometem pré-requisitos e motivação no 2º semestre.
12. **`Pressao_Financeira -> Desempenho_Sem2`:** A vulnerabilidade econômica reduz o tempo e a tranquilidade necessários para os estudos ao longo do ano letivo.
13. **`Turno -> Desempenho_Sem2`:** A frequência noturna reduz as horas livres diárias para estudo autônomo e acompanhamento extraclasse.
14. **`Desempenho_Sem2 -> Desfecho`:** O rendimento acadêmico recente é o indicador mais forte da trajetória de conclusão (`Graduate`), retenção (`Enrolled`) ou evasão (`Dropout`).
15. **`Pressao_Financeira -> Desfecho`:** Mesmo com rendimento acadêmico razoável, a pressão financeira severa pode forçar o abandono do curso.
16. **`Desemprego -> Desfecho`:** Condições macroeconômicas adversas (desemprego elevado) afetam a renda familiar e a decisão de permanência na universidade.

---

## 4. Definição Manual das Probabilidades (CPTs)

Todas as tabelas de probabilidade foram especificadas manualmente no módulo `src/bn_evasao/cpt_rules.py`. As tabelas cruzadas geradas na pasta `outputs/eda/` foram consultadas apenas como referência de ordem de grandeza para validar a plausibilidade dos cenários, sem qualquer extração automática de frequências.

### Garantias matemáticas aplicadas
* **Piso mínimo (`PISO = 0.02`):** Nenhuma probabilidade é exatamente `0` ou `1`, evitando evidências impossíveis durante a inferência.
* **Normalização exata:** Todas as distribuições somam exatamente `1.0`, com eventuais resíduos de arredondamento ajustados no estado mais provável.
* **Monotonicidade:** Configurações piores dos pais aumentam monotonamente a probabilidade dos estados desfavoráveis do filho.

### Variáveis Raiz (Distribuições a priori)
Definidas manualmente com valores arredondados inspirados nas proporções gerais do domínio:
* **`Area_Curso`:** `Saude` (0,18), `Ciencias_Sociais` (0,17), `Gestao_Turismo` (0,22), `Comunicacao_Design` (0,15), `Ciencias_Agricolas` (0,13), `Engenharias_Tecnologia` (0,15).
* **`Faixa_Etaria`:** `Jovem` (0,55), `Adulto` (0,25), `Maduro` (0,20).
* **`Escolaridade_Pais`:** `Baixa` (0,45), `Media` (0,35), `Alta` (0,20).
* **`Bolsista`:** `Sim` (0,25), `Nao` (0,75).
* **`Deslocado`:** `Sim` (0,55), `Nao` (0,45).
* **`Nota_Admissao`:** `Baixa` (0,25), `Media` (0,50), `Alta` (0,25).
* **`Desemprego`:** `Baixo` (0,50), `Alto` (0,50).

### Variáveis com Pais (Sistema de Pontuação de Risco)
Para as variáveis condicionadas, cada estado dos pais recebe uma pontuação de risco/dificuldade definida por domínio. A pontuação total da configuração é convertida linearmente entre dois extremos fixados manualmente (**Melhor Caso** = 0 pontos; **Pior Caso** = pontuação máxima):

| Variável | Pesos dos Pais (Pontos de Risco) | Melhor Caso (0 pts) | Pior Caso (Máx. pts) |
| :--- | :--- | :--- | :--- |
| **`Turno`** | `Faixa_Etaria`: Jovem (0), Adulto (+1,5), Maduro (+3,0)<br>`Area_Curso`: Saúde/Agrárias (0), Eng/Tec (+0,5), Com/Design (+1,0), Sociais (+1,5), Gestão/Turismo (+2,0) | Diurno: 0,95<br>Noturno: 0,05 | Diurno: 0,25<br>Noturno: 0,75 |
| **`Pressao_Financeira`** | `Bolsista`: Sim (0), Nao (+2,0)<br>`Deslocado`: Nao (0), Sim (+1,5)<br>`Escolaridade_Pais`: Alta (0), Media (+0,5), Baixa (+1,5) | Baixa: 0,90<br>Alta: 0,10 | Baixa: 0,10<br>Alta: 0,90 |
| **`Devedor`** | `Pressao_Financeira`: Baixa (0), Alta (+1,0) | Sim: 0,05<br>Nao: 0,95 | Sim: 0,45<br>Nao: 0,55 |
| **`Mensalidade_Em_Dia`** | `Pressao_Financeira`: Baixa (0), Alta (+1,0) | Sim: 0,95<br>Nao: 0,05 | Sim: 0,55<br>Nao: 0,45 |
| **`Desempenho_Sem1`** | `Nota_Admissao`: Alta (0), Media (+1,5), Baixa (+3,0)<br>`Faixa_Etaria`: Jovem (0), Adulto (+0,5), Maduro (+1,0)<br>`Area_Curso`: Saúde (0), Sociais (+0,2), Com (+0,3), Gestão (+0,5), Agrárias (+0,7), Eng (+1,0) | Baixo: 0,05<br>Medio: 0,25<br>Alto: 0,70 | Baixo: 0,65<br>Medio: 0,25<br>Alto: 0,10 |
| **`Desempenho_Sem2`** | `Desempenho_Sem1`: Alto (0), Medio (+2,0), Baixo (+4,0)<br>`Pressao_Financeira`: Baixa (0), Alta (+1,0)<br>`Turno`: Diurno (0), Noturno (+0,5) | Baixo: 0,04<br>Medio: 0,21<br>Alto: 0,75 | Baixo: 0,78<br>Medio: 0,17<br>Alto: 0,05 |
| **`Desfecho`** | `Desempenho_Sem2`: Alto (0), Medio (+1,8), Baixo (+4,0)<br>`Pressao_Financeira`: Baixa (0), Alta (+1,5)<br>`Desemprego`: Baixo (0), Alto (+0,5) | Dropout: 0,04<br>Enrolled: 0,16<br>Graduate: 0,80 | Dropout: 0,82<br>Enrolled: 0,13<br>Graduate: 0,05 |