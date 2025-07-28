# Simulador e Analisador de Faltas em Redes de Distribuição Elétrica

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.2-purple?style=for-the-badge&logo=pandas)
![NumPy](https://img.shields.io/badge/NumPy-2.0-orange?style=for-the-badge&logo=numpy)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## 📋 Sumário
- [Descrição do Projeto](#-descrição-do-projeto)
- [✨ Funcionalidades Principais](#-funcionalidades-principais)
- [🛠️ Tecnologias e Bibliotecas](#️-tecnologias-e-bibliotecas)
- [📂 Estrutura do Projeto](#-estrutura-do-projeto)
- [⚙️ Instalação](#️-instalação)
- [🚀 Como Usar](#-como-usar)
- [📄 Licença](#-licença)

---

## 📄 Descrição do Projeto
Este projeto tem como objetivo simular e analisar curtos-circuitos em sistemas de distribuição de energia elétrica. Utilizando a plataforma OpenDSS controlada por Python, o sistema gera um dataset completo de faltas no modelo IEEE 34 Barras, variando a resistência de falta e a localização ao longo das linhas.

O projeto se baseia em metodologias validadas para localização de faltas. Após a simulação, os dados de tensão e corrente medidos na subestação são processados utilizando o método da **[Mínima Reatância](https://ieeexplore.ieee.org/abstract/document/8684803)** para estimar a localização do defeito. A abordagem também considera a utilização de dados que seriam provenientes de **[Medidores Inteligentes (Smart Meters)](https://www.mdpi.com/1996-1073/14/11/3242)**, servindo como uma ferramenta para estudos em localização de faltas e automação de redes elétricas.

## ✨ Funcionalidades Principais
* **Simulação de Faltas:** Gera dados para faltas monofásicas, bifásicas e trifásicas em múltiplos pontos da rede.
* **Parâmetros Variáveis:** Permite configurar diferentes valores de resistência de falta.
* **Análise de Localização:** Implementa o algoritmo da Mínima Reatância para estimar a distância da falta a partir dos dados medidos na subestação.
* **Pré-processamento de Dados:** Extrai e pré-calcula os parâmetros da rede (impedâncias, topologia) para otimizar a análise.
* **Estrutura Modular:** O código é organizado em um módulo de funções auxiliares e scripts principais para cada etapa do processo.

## 🛠️ Tecnologias e Bibliotecas
Este projeto foi construído utilizando as seguintes tecnologias e bibliotecas principais:

| Biblioteca | Versão | Propósito |
| :--- | :--- | :--- |
| **Python** | 3.11+ | Linguagem principal do projeto. |
| **py-dss-interface** | 2.0.4 | Interface para controlar o simulador OpenDSS. |
| **Pandas** | 2.2.3 | Estruturação, manipulação e exportação dos dados (DataFrames). |
| **NumPy** | 2.0.0 | Cálculos numéricos e operações matriciais de alta performance. |
| **NetworkX** | 3.5 | Criação e análise da topologia da rede em forma de grafo. |
| **comtypes** | 1.4.8 | Dependência (Windows) para a comunicação com o OpenDSS via COM. |

## 📂 Estrutura do Projeto
O projeto utiliza uma estrutura de pasta plana para acesso direto aos scripts e dados a partir da raiz.

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
    Use o comando `git clone` para baixar os arquivos do projeto para o seu computador.
    ```bash
    git clone [https://github.com/LuisFelipeCSouza/tcc-luis-felipe.git](https://github.com/LuisFelipeCSouza/tcc-luis-felipe.git)
    cd tcc-luis-felipe
    ```

2.  **Crie e ative um ambiente virtual:** (Altamente recomendado)
    Isso cria um ambiente Python isolado para o seu projeto, evitando conflitos de bibliotecas.
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
    As bibliotecas necessárias serão instaladas a partir do arquivo `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```
Pronto! Seu ambiente está configurado para executar as simulações.

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
* **Entrada:** O arquivo `automacao_falta.csv` gerado na etapa anterior.
* **Saída:** Um novo arquivo CSV (ex: `minima_reatancia.csv`) será criado na pasta `result/`, contendo a distância real e as múltiplas estimativas.

### 3. Filtragem da Estimativa Correta
A etapa final utiliza os dados simulados dos medidores inteligentes (smart meters) para filtrar as múltiplas estimativas de localização, identificando o circuito correto onde a falta ocorreu e, assim, selecionando a estimativa de distância precisa.

```bash
python filtroMI.py
```
* **Entrada:** O arquivo de análise `minima_reatancia.csv` gerado na Etapa 2.
* **Saída:** Um arquivo final (ex: `filtragem_MI.csv`) na pasta `result/`, contendo a estimativa única e correta para a localização da falta.

## 📄 Licença
Este projeto está distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.