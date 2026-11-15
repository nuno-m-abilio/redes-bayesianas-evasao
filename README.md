# Redes Bayesianas para Risco de Evasão no Ensino Superior

Trabalho prático de Aprendizagem de Máquina e Modelagem de Conhecimento Incerto (AMMCI), UEM 2026, Prof. Dr. Wagner Igarashi.

## Integrantes

Preencher com nome completo e RA de cada integrante antes da entrega.

## O que o projeto faz

A rede bayesiana, construída manualmente, responde a uma pergunta principal. Dado o perfil do estudante no ingresso e o seu desempenho acadêmico inicial, qual a probabilidade de evasão, permanência ou conclusão do curso, e quais condições mais alteram esse risco?

As variáveis, os estados, os arcos e as probabilidades condicionais estão todos no arquivo `modelo.json`, que é a fonte única da verdade. O código lê esse arquivo, valida, monta a rede com o pgmpy e responde a consultas. Os arcos representam hipóteses de dependência probabilística, e o dataset não comprova causalidade.

O trabalho cobre quatro tipos de consulta, que correspondem aos cenários do modelo. Há uma consulta preditiva a partir do perfil de ingresso, uma de alerta precoce após o primeiro semestre, uma diagnóstica a partir do desfecho observado e uma prescritiva que compara alternativas com utilidades explícitas.

## Instalação

É preciso ter Python 3.11 ou mais novo. Na raiz do repositório:

```bash
python -m venv .venv
source .venv/bin/activate          # Linux, macOS e Git Bash no Windows (use .venv/Scripts/activate)
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

O `requirements.txt` termina com `-e .`, que instala o próprio projeto em modo editável. Por isso `python -m bn_evasao.cli` funciona a partir de qualquer pasta, sem configurar o `PYTHONPATH`. Ative sempre o ambiente virtual antes de usar os comandos. Se o PowerShell bloquear o script de ativação, rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` na mesma janela e ative de novo.

O Graphviz é opcional. Quando o programa `dot` está instalado, o desenho da rede usa o Graphviz. Sem ele, o desenho é feito automaticamente com matplotlib. Para instalar, use `sudo apt install graphviz` no Ubuntu e WSL, `brew install graphviz` no macOS, ou o instalador oficial no Windows, marcando a opção de adicionar ao PATH.

## Dados

O dataset é o "Predict Students' Dropout and Academic Success", do repositório UCI (id 697, projeto SATDAP, Portugal). As instruções de download e a observação sobre a licença estão em `data/README.md`. O arquivo original fica em `data/raw/data.csv` e não vai no ZIP de entrega. A versão discretizada, `data/processed/dados_discretizados.csv`, vai junto e é a que permite reproduzir as tabelas de análise exploratória.

O dataset serve só para contextualizar o problema e justificar as escolhas de modelagem. Nenhuma estrutura nem probabilidade é aprendida dos dados.

## Como usar

O fluxo completo, a partir do dataset baixado, tem estas etapas.

```bash
# 1. discretiza o dataset e gera as tabelas exploratórias em outputs/eda/
python scripts/discretizar_dataset.py

# 2. gera o modelo.json a partir das regras manuais de src/bn_evasao/cpt_rules.py
python scripts/gerar_modelo_json.py

# 3. valida o modelo e a construção da rede
python -m bn_evasao.cli validar

# 4. consulta P(Desfecho | evidências)
python -m bn_evasao.cli consultar --consulta Desfecho --evidencia Turno=Noturno --evidencia Bolsista=Nao

# 5. executa os cenários de utilização
python -m bn_evasao.cli cenarios
python -m bn_evasao.cli cenarios --id S2_alerta_precoce

# 6. desenha a estrutura da rede em outputs/figuras/
python -m bn_evasao.cli desenhar
```

Todos os comandos aceitam `--modelo caminho.json`, e `consultar` e `cenarios` aceitam `--json` para saída estruturada. Os códigos de saída são 0 para sucesso, 1 para erro de modelo ou de evidência, 2 para uso incorreto da linha de comando e 3 quando algum cenário tem expectativa reprovada.

O modelo.json nunca deve ser editado à mão. Para ajustar uma probabilidade, altere a regra em `cpt_rules.py` e rode o passo 2 de novo.

## Testes

```bash
pytest
pytest --cov=bn_evasao --cov-report=term-missing
```

Não é preciso editar código para rodar os testes. A integração contínua do GitHub Actions instala as dependências em um ambiente limpo e roda a suíte a cada PR, em Python 3.11 e 3.12.

O que cada grupo de testes verifica, com alguns exemplos de resultado esperado.

* Leitura e validação do modelo, em `test_loader.py`. Uma chave duplicada no JSON, um ciclo no grafo, uma CPT incompleta ou uma linha cuja soma difere de 1 devem levantar o erro específico, com mensagem que indica onde está o problema.
* Construção da rede e inferência, em `test_network_inference.py`. Os resultados do pgmpy são comparados com contas de Bayes feitas à mão e com uma enumeração da distribuição conjunta escrita no teste. Também há uma rede com um filho de dois pais, declarados em ordem diferente da dos arcos, para pegar CPTs montadas por posição.
* Propriedades probabilísticas, também em `test_network_inference.py`. Resultados somam 1, a ordem das evidências não altera a resposta, variáveis irmãs são independentes dado o pai, e observar o filho torna os pais dependentes.
* Evidências inválidas. Variável ou estado inexistente, variável consultada também presente nas evidências e evidência de probabilidade zero levantam `EvidenciaInvalidaError`.
* Estrutura, CPTs, cenários e consistência entre o JSON e a rede, em `test_structure.py`, `test_cpts.py`, `test_scenarios.py`, `test_json_consistency.py` e `test_invalid_cases.py`. Verificam o mínimo de 10 variáveis, o DAG, valores entre 0 e 1, soma 1 em cada configuração dos pais, a monotonicidade das probabilidades de evasão e as expectativas qualitativas definidas antes de rodar cada cenário.
* Desenho e linha de comando, em `test_visualize.py` e `test_cli.py`, incluindo o caminho sem Graphviz.
* Regra do enunciado, em `test_regras_do_trabalho.py`. Varre `src/` e `scripts/` e falha se encontrar estimadores do pgmpy, buscas de estrutura, chamadas `fit` ou bibliotecas de aprendizagem de máquina.
* Script de entrega, em `test_montar_zip.py`.

Nenhum teste usa como resposta correta um número copiado da saída do código.

## Estrutura do repositório

```
redes-bayesianas-evasao/
├── README.md
├── requirements.txt
├── pytest.ini
├── pyproject.toml               torna o pacote bn_evasao instalável
├── modelo.json                  fonte única da verdade
├── .github/workflows/tests.yml  integração contínua
├── data/
│   ├── README.md                origem, licença e como baixar
│   ├── raw/                     dataset original, fora do ZIP
│   └── processed/               dados discretizados
├── docs/
│   ├── modelo_json_guia.md      como interpretar o modelo.json
│   ├── justificativas.md        discretização, arcos e regras das CPTs
│   ├── uso_de_ia.md             declaração de uso de IA e validações
│   └── exemplos/modelo_exemplo.json
├── scripts/
│   ├── discretizar_dataset.py
│   ├── gerar_modelo_json.py
│   └── montar_zip.py
├── src/bn_evasao/
│   ├── erros.py                 exceções do projeto
│   ├── schema.py                JSON Schema do modelo.json
│   ├── loader.py                leitura e validação
│   ├── cpt_rules.py             regras manuais que geram as CPTs
│   ├── network.py               constrói a rede pgmpy
│   ├── inference.py             consultas com validação de evidências
│   ├── scenarios.py             execução dos cenários
│   ├── visualize.py             desenho da rede
│   └── cli.py                   linha de comando
├── tests/
├── outputs/                     tabelas exploratórias e figuras geradas
├── notebooks/
└── slides/
```

## Bibliotecas e o que cada uma faz

* pgmpy representa a rede (`DiscreteBayesianNetwork`), define as CPTs (`TabularCPD`) e faz a inferência exata (`VariableElimination`), em `network.py` e `inference.py`. Nenhum estimador nem busca de estrutura do pgmpy é usado.
* networkx verifica o DAG e calcula as camadas do desenho, em `network.py` e `visualize.py`.
* jsonschema valida a forma do `modelo.json` contra o schema, em `schema.py`.
* pandas e numpy discretizam o dataset e geram as tabelas exploratórias, em `scripts/discretizar_dataset.py`. Ficam fora do núcleo da rede.
* matplotlib desenha a rede quando o Graphviz não está disponível, em `visualize.py`.
* Graphviz, programa externo e opcional, é o desenho principal da rede.
* pytest e pytest-cov rodam os testes e medem a cobertura.
* A biblioteca padrão do Python cobre argparse no CLI, json na leitura do modelo e zipfile na montagem da entrega.

## O modelo.json

O guia de interpretação está em `docs/modelo_json_guia.md`, e um exemplo válido e pequeno, com três variáveis, está em `docs/exemplos/modelo_exemplo.json`. Cada CPT identifica a variável, a configuração dos pais e as probabilidades pelo nome do estado, nunca pela posição, o que elimina ambiguidade de ordem de colunas.

## Uso de ferramentas de inteligência artificial

A declaração completa, com as ferramentas usadas, as atividades, o que foi obtido com ajuda delas e como cada item foi verificado, está em `docs/uso_de_ia.md`.

## Entrega

Para montar o ZIP no padrão `2026.AMMCI.<Integrante1>.<Integrante2>.<Integrante3>.zip`:

```bash
python scripts/montar_zip.py JoaoDS PauloC --verificar-testes
```

O script recusa nomes fora do padrão, confere se os arquivos obrigatórios existem, verifica a integridade do ZIP e, com `--verificar-testes`, extrai o ZIP numa pasta temporária e roda a suíte ali, para garantir que ele funciona sem depender do repositório.

## Limitações

A discretização é grosseira e os pontos de corte são decisões do grupo. As CPTs foram especificadas por regras de domínio e não estimadas, e os arcos são hipóteses. O dataset vem de uma única instituição portuguesa. As variáveis do primeiro e do segundo semestre quase determinam o desfecho, por isso o modelo é pensado em estágios, como sistema de alerta precoce. Os resultados dos cenários comparam evidências e não devem ser lidos como efeito causal garantido.