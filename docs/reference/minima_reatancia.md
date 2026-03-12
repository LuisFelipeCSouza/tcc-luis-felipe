# Algoritmo de Mínima Reatância

Este módulo implementa a lógica analítica para estimativa da localização de faltas em sistemas de distribuição radial, baseando-se na premissa de que a reatância da rede é linearmente proporcional à distância.

## Fundamentação Matemática

A distância estimada \( d \) da subestação até o ponto de falta é calculada pela relação entre a reatância aparente medida (\( X_{app} \)) e a reatância unitária do trecho (\( x_{L} \)):

\[ d = \frac{\text{Im}\left( \frac{\dot{V}_{sub}}{\dot{I}_{sub}} \right)}{x_{L}} \]

Onde:
* \( \dot{V}_{sub} \): Fasor de tensão de fase na subestação durante a falta.
* \( \dot{I}_{sub} \): Fasor de corrente de sequência positiva/fase.
* \( x_{L} \): Reatância por unidade de comprimento do condutor (\(\Omega/km\)).

---

## Referência da API

Abaixo está a documentação automática das funções e classes implementadas no script `minima_reatancia.py`.

::: src.minima_reatancia
    handler: python
    options:
      show_source: true
      show_root_heading: false
      members_order: alphabetical