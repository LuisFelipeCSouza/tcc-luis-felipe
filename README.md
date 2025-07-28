# Simulador e Analisador de Faltas em Redes de Distribuição Elétrica

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> Este projeto utiliza Python e a interface OpenDSS para simular diferentes tipos de faltas (curtos-circuitos) em um modelo de rede de distribuição de energia elétrica (IEEE 34 Barras). Após a simulação, os dados de tensão e corrente são analisados com o método da Mínima Reatância para estimar a localização da falta.


## Funcionalidades Principais (Key Features)

* **Simulação de Faltas:** Gera dados para faltas monofásicas, bifásicas e trifásicas em múltiplos pontos da rede.
* **Parâmetros Variáveis:** Permite configurar diferentes valores de resistência de falta.
* **Análise de Localização:** Implementa o algoritmo da Mínima Reatância para estimar a distância da falta a partir dos dados medidos na subestação.
* **Pré-processamento de Dados:** Extrai e pré-calcula os parâmetros da rede (impedâncias, topologia) para otimizar a análise.
* **Estrutura Modular:** O código é organizado em módulos para simulação, análise e funções utilitárias.

## 📂 Estrutura do Projeto

```
tcc-luis-felipe/
├── 34Bus/
│   ├── IEEE34_BusXY.csv
│   ├── IEEELineCodes.DSS
│   ├── ieee34Mod1.dss
│   ├── ieee34Mod2.dss
│   ├── Run_IEEE34Mod1.dss      # Arquivo mestre do modelo OpenDSS
│   └── Run_IEEE34Mod2.dss
│
├── __pycache__/              # (Ignorado pelo Git)
├── result/                   # (Ignorado pelo Git - criado automaticamente)
│
├── .gitignore                # Define quais arquivos e pastas o Git deve ignorar
├── automacao.py              # Script principal para rodar as simulações
├── filtroMI.py               # Script para filtrar as estimativas
├── funcoes.py                # Módulo com funções auxiliares
├── minima_reatancia.py       # Script que aplica o método da Mínima Reatância
├── README.md                 # Documentação do projeto (este arquivo)
└── requirements.txt          # Lista de dependências Python para instalação
```

## ⚙️ Instalação

Siga os passos abaixo para configurar o ambiente e rodar o projeto.

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/](https://github.com/)[SEU-USUARIO]/[NOME-DO-REPOSITORIO].git
    cd [NOME-DO-REPOSITORIO]
    ```

2.  **Crie e ative um ambiente virtual:** (Altamente recomendado)
    * No Windows:
      ```bash
      python -m venv venv
      .\venv\Scripts\activate
      ```
    * No macOS/Linux:
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```

3.  **Instale as dependências:**
    Todas as bibliotecas necessárias estão listadas no arquivo `requirements.txt`. Instale todas de uma vez com o comando:
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Como Usar

O projeto opera em três etapas sequenciais: geração de dados, análise de localização e filtragem da estimativa correta.

### 1. Geração do Dataset de Faltas
Primeiro, execute o script de automação para gerar os dados de medição para todos os cenários de falta. Este script simula os eventos na rede e coleta os dados brutos da subestação e dos medidores inteligentes.

```bash
python automacao.py
```
* **Entrada:** O modelo da rede em `34Bus/`.
* **Saída:** Um arquivo CSV (ex: `automacao_falta.csv`) será criado na pasta `result/`.

### 2. Análise e Localização de Faltas
Com o dataset de medições gerado, execute o script de análise. Ele aplicará o método da Mínima Reatância para cada caso de falta, gerando múltiplas estimativas de localização (uma para cada caminho de circuito possível).

```bash
python minima_reatancia.py
```
* **Entrada:** O arquivo CSV gerado na etapa anterior.
* **Saída:** Um novo arquivo CSV (ex: `minima_reatancia.csv`) será criado na pasta `result/`, contendo a distância real e as múltiplas estimativas.

### 3. Filtragem da Estimativa Correta
A etapa final utiliza os dados simulados dos medidores inteligentes (smart meters) para filtrar as múltiplas estimativas de localização, identificando o circuito correto onde a falta ocorreu e, assim, selecionando a estimativa de distância precisa.

```bash
python filtroMI.py
```
* **Entrada:** O arquivo de análise `minima_reatancia.csv` gerado na Etapa 2.
* **Saída:** Um arquivo final (ex: `filtragem_MI.csv`) na pasta `result/`, contendo a estimativa única e correta para a localização da falta.

## Licença
Este projeto está distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.