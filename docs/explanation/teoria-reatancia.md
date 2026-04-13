# O Método da Mínima Reatância

A localização da falta é baseada na estimativa da distância $d$ a partir da subestação, utilizando as medições de tensão ($V$) e corrente ($I$) durante o regime permanente de falta.

A reatância vista pela subestação é dada por:
$$X_{app} = \text{Im}\left(\frac{V_{sub}}{I_{sub}}\right)$$

O algoritmo busca o trecho da rede onde $X_{app}$ coincide com a reatância acumulada da linha.