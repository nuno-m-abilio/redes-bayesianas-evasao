# Uso de ferramentas de inteligência artificial

> Esta declaração descreve o uso real de ferramentas de IA neste trabalho.
## 1. Se foram utilizadas ferramentas de IA

Sim.

## 2. Quais ferramentas

- **Claude** (Anthropic) e **Gemini** (Google), via interface de chat.

## 3. Atividades em que foram utilizadas

| Atividade | Ferramenta | Como foi usada |
|---|---|---|
| Revisão e auditoria da implementação | Gemini e Claude | Leitura dos scripts, do `modelo.json`, das tabelas exploratórias e dos testes; verificação de aderência à especificação. |
| Verificação independente das probabilidades | Gemini e Claude | Enumeração exata da distribuição conjunta (fora do pgmpy) para comparar as marginais da rede com as do dataset e conferir os resultados dos cenários. |
| Diagnóstico de calibração | Gemini e Claude | Identificou que as marginais de Turno, Devedor e Mensalidade_Em_Dia ficavam fora da ordem de grandeza do dataset e que o teste de calibração falharia. |
| Sugestão de ajuste das CPTs | Gemini e Claude | Propôs os novos valores de "melhor caso"/"pior caso" de Turno, Pressao_Financeira, Devedor e Mensalidade_Em_Dia. |
| Explicação do código e orientação de execução | Gemini e Claude | Explicação do papel de cada arquivo e de como executar testes, `loader.py` e `scenarios.py`. |
| Redação da documentação | Gemini e Claude | Redação inicial de `justificativas.md` e `uso_de_ia.md`, revisada pela equipe. |

## 4. Quais conteúdos, sugestões, códigos ou probabilidades vieram da IA

- Valores numéricos dos extremos (melhor e pior caso) das CPTs de Turno, Pressao_Financeira, Devedor e Mensalidade_Em_Dia na versão atual, propostos pela IA e aceitos pela equipe depois de verificação.
- Lista de problemas de coerência apontados na revisão (calibração, divergências entre dependências e tabelas cruzadas, descrição incorreta do Turno em `regra_geracao`).
- Textos da documentação, adaptados pela equipe.

A estrutura da rede (variáveis, estados e arcos), as regras de pontuação de risco, os cenários e as utilidades do S4 foram definidos pela equipe. Nenhuma técnica de aprendizado de máquina foi usada para aprender estrutura ou probabilidades.

## 5. Como a equipe verificou e validou os resultados

- **Testes automatizados** (`pytest`): validação estrutural, das CPTs (limites, completude, soma 1, ausência de 0/1, monotonicidade), das consultas, dos cenários e casos inválidos.
- **Cálculo independente:** o teste de inferência compara o pgmpy com uma distribuição conjunta calculada por força bruta em numpy, sem usar o pgmpy, além de uma mini-rede conferida à mão com a regra da cadeia e Bayes.
- **Teste de calibração:** compara as marginais da rede com as frequências do dataset. Ele falhou na primeira versão, o que motivou a recalibração. Depois do ajuste, a suíte inteira passou [conferir contagem final].
- **Consistência do modelo:** o `modelo.json` é gerado por script e comparado com o código (`gerar_modelo_json.py --verificar` e teste de desatualização). Cada célula das CPTs é comparada com a rede construída.
- **Conferência dos números:** os valores citados na documentação foram comparados com a saída real do CLI e com `outputs/cenarios/resultados.md`.
- **Limites reconhecidos:** os valores das CPTs são hipóteses de domínio ajustadas manualmente, não estimativas estatísticas. Divergências em relação ao dataset estão registradas em `docs/justificativas.md`.

## 6. Limitações do uso de IA

A IA pode produzir interpretações imprecisas, e por isso nenhum valor foi aceito sem execução do código e dos testes. A equipe se responsabiliza pelas decisões de modelagem, pelo código e pelos resultados, e está preparada para explicá-los.