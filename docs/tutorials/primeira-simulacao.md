# Tutorial: Sua Primeira Simulação de Falta

Neste tutorial, você aprenderá a realizar uma simulação de curto-circuito no sistema IEEE 34 Barras e entenderá como a **Resistência de Falta ($R_f$)** influencia as medições coletadas na subestação.

## 📋 Pré-requisitos

Antes de começar, certifique-se de que você:

1. Clonou o repositório.
2. Ativou o ambiente com `uv` (`uv sync`).
3. Possui o OpenDSS instalado no Windows (necessário para a interface COM).

---

## 1. Localizando as Variáveis de Controle

Abra o arquivo `automacao.py` na raiz do projeto. Este script é o "maestro" que comanda o OpenDSS. Procure pelo loop ou pela lista que define as resistências de falta. Geralmente, ela se parece com isto:

```python
# Trecho do código em automacao.py
resistencias = [1, 5, 10, 20, 40] # Valores em Ohms
tipos_falta = ['1PH', '2PH', '3PH']

```

## 2. Modificando a Intensidade da Falta

A resistência de falta simula o contato do condutor com diferentes superfícies (asfalto, solo seco, vegetação).

> **Conceito Teórico:** Quanto maior a $R_f$, menor será a corrente de falta detectada, tornando o defeito mais "difícil" de ser localizado pelos relés de proteção convencionais.

Para este tutorial, vamos testar um cenário de **alta impedância**. Altere a lista de resistências para focar em um valor alto:

```python
# Altere para testar apenas uma falta de 50 Ohms
resistencias = [50] 

```

## 3. Executando o Script

No seu terminal, execute o comando:

```bash
uv run automacao.py

```

Você verá o terminal processando cada barra do sistema IEEE 34. O script está inserindo uma falta em cada ponto da rede, resolvendo o fluxo de carga e exportando os resultados.

---

## 4. Analisando o Impacto no CSV

Após o término, abra o arquivo gerado em `result/automacao_falta.csv`. Note as seguintes colunas:

| Coluna | Descrição | Impacto da $R_f$ |
| --- | --- | --- |
| `I_sub_A` | Corrente na Fase A na Subestação | Deve diminuir conforme $R_f$ aumenta. |
| `V_sub_A` | Tensão na Fase A na Subestação | Sofre um "afundamento" (sag) menos severo com $R_f$ alta. |

### Por que isso importa?

Se você observar que para $R_f = 50 \Omega$ a corrente de falta é muito próxima da corrente de carga nominal, seu algoritmo de **Mínima Reatância** terá um desafio maior para distinguir a falta do carregamento normal da rede.

---

## ✅ Conclusão

Você acaba de:

1. Manipular os parâmetros de entrada de um simulador de redes elétricas.
2. Gerar um dataset sintético para estudos de proteção.
3. Observar a relação entre impedância de falta e resposta do sistema.

---