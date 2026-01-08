# --- 1. IMPORTACÕES E CONFIGURACÃO INICIAL ---
import py_dss_interface
import pandas as pd
import networkx as nx
from tqdm import tqdm
import os
import pathlib
import funcoes as fc # Importa o módulo local com as funcoes auxiliares

# --- 2. PRÉ-PROCESSAMENTO E CARGA DE DADOS ---

# Define os caminhos de forma robusta, baseando-se na localizacao do script.
script_path = os.path.dirname(os.path.abspath(__file__))

# O script precisa de alguns dados estaticos do circuito (como comprimentos de linha)
# que sao obtidos ao carregar o modelo no OpenDSS.
dss_file = pathlib.Path(script_path).joinpath("34Bus", "Run_IEEE34Mod1.dss")
dss = py_dss_interface.DSS()
dss.text('Clear')
dss.text(f'Compile {dss_file}')
dss.solution.solve()

# Pre-processa os dados de todas as linhas para obter seus parametros.
data = fc.processamento(dss)

# Cria um grafo da rede para ser usado pelas funcoes auxiliares.
G = fc.create_network_graph()

# Define o "ramal principal" do alimentador de forma manual
ramal_principal =['l1', 'l2', 'l3', 'l5', 'l6', 'l24', 'l9', 'l13', 'l14', 'l15', 'l27', 'l16', 'l29', 'l17',
             'l30', 'l20']

# Calcula o comprimento total do ramal principal em metros.
# Este valor sera usado como base para o calculo do erro percentual da localizacao.
length_ramal = sum(data[sec_linha]['length']*304.8 for sec_linha in ramal_principal)

# Carrega o arquivo com as multiplas estimativas geradas pelo script 'minima_reatancia.py'.
resultado = pd.read_csv(pathlib.Path(script_path).joinpath("result", "minima_reatancia.csv"), sep=';', decimal=',')

# Inicializa as listas que irao armazenar os resultados filtrados.
linha_identificada = []
distancia_identificada = []

# --- 3. LOGICA DE FILTRAGEM DAS ESTIMATIVAS ---

# Itera sobre cada linha do DataFrame, onde cada linha e um caso de falta
# com 8 possiveis localizacoes estimadas (ckt1_d, ckt2_d, etc.).
for index, row in tqdm(resultado.iterrows(), total=resultado.shape[0], desc="Analisando Casos de Falta"):

    # Determina qual fase da corrente do sensor deve ser analisada com base no tipo de falta.
    # Ex: Para uma falta na fase 'A' (tipo '.1.0'), devemos olhar a corrente 'ia'.
    if row['tipo_de_falta'] in {'.1.0', '.1.2', '.1.2.0', '.3.1', '.3.1.0', '.1.2.3.0'}:
        prefixo = '_ia'
    elif row['tipo_de_falta'] in {'.2.0', '.2.3', '.2.3.0'}:
        prefixo = '_ib'
    elif row['tipo_de_falta'] in {'.3.0'}:
        prefixo = '_ic'

    lista_leitura_sensores = []

    # Para cada uma das 8 estimativas de circuito (de ckt1 a ckt8)...
    for i in range(8):
        # 1. Determina qual sensor e responsavel por monitorar essa linha.
        _, sensor_responsavel = fc.get_sensor_locations(G, '800', row[f'ckt{i+1}_line'])

        # 3. Busca no DataFrame o valor da corrente medida por aquele sensor na fase de interesse.
        # Ex: Busca o valor da coluna 'l9_ia' e o adiciona à lista.
        lista_leitura_sensores.append(row[f'{sensor_responsavel}{prefixo}'])

    # O PRINCÍPIO DA FILTRAGEM: O caminho correto da falta e aquele cujo sensor
    # de monitoramento registrou a maior corrente.
    # Encontra o indice da maior leitura de corrente. Este indice corresponde ao circuito correto.
    indice = lista_leitura_sensores.index(max(lista_leitura_sensores)) + 1

    # Usa o indice encontrado para selecionar a linha e a distancia corretas.
    linha_identificada.append(row[f'ckt{indice}_line'])
    distancia_identificada.append(row[f'ckt{indice}_d'])

# --- 4. POS-PROCESSAMENTO E EXPORTACÃO DOS RESULTADOS ---

# Cria um dicionario com os resultados finais e ja filtrados.
resultado_multipla = {'linha_identificada': linha_identificada,
                      'distancia_identificada': distancia_identificada}

# Converte o dicionario para um DataFrame do Pandas.
df_resultado = pd.DataFrame(resultado_multipla)

# Junta os resultados filtrados com os dados originais da falta para comparacao.
df_resultado = df_resultado.join(resultado[['linha_faltosa', 'distancia real', 'tipo_de_falta', 'r_f']])

# Calcula o erro percentual da estimativa em relacao ao comprimento total do ramal principal.
df_resultado['erro'] = 100 * ((df_resultado['distancia_identificada'] - df_resultado['distancia real']) / length_ramal)

# Salva o DataFrame final com os resultados filtrados em um novo arquivo CSV.
df_resultado.to_csv(pathlib.Path(script_path).joinpath("result", "filtragem_MI.csv"), sep=';', decimal=',')

print('Analise de filtragem concluida com sucesso!')