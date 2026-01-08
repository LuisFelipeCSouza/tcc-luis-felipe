# --- 1. IMPORTACAO DE BIBLIOTECAS E CONFIGURACOES INICIAIS ---
import pandas as pd
import py_dss_interface
import numpy as np
import os
from tqdm import tqdm
import pathlib
import funcoes as fc # Importa o módulo local com as funcoes auxiliares

# Define os caminhos de forma robusta, garantindo que o script encontre os arquivos.
script_path = os.path.dirname(os.path.abspath(__file__))
dss_file = pathlib.Path(script_path).joinpath("34Bus", "Run_IEEE34Mod1.dss")

# Inicializa a interface com o OpenDSS para obter parametros do circuito e dados de pre-falta.
dss = py_dss_interface.DSS()
dss.text('Clear')
dss.text(f'Compile {dss_file}')
dss.solution.solve()

# Carrega o DataFrame com os resultados das simulacoes de falta.
medidas_df = pd.read_csv(pathlib.Path(script_path).joinpath("result", "automacao_falta.csv"), sep=';', decimal=',')

# --- 2. PRÉ-PROCESSAMENTO E DADOS DE PRÉ-FALTA ---

# Carrega um dicionário com os caminhos (listas de linhas) dos circuitos do alimentador.
alimentador = fc.dict_circuitos_func()

# Cria um grafo da rede para referencia (usado para obter a lista de sensores).
G = fc.create_network_graph()
lista_sensores = fc.lista_sensores_fc(G)

# Pre-processa os dados de todas as linhas do circuito (impedancias, comprimentos, etc.).
# Isso cria um dicionário para consulta rápida, otimizando o acesso aos dados.
data = fc.processamento(dss)

# Captura os valores de tensao e corrente na subestacao (Line.L1) ANTES da falta.
# Estes valores sao a condicao de base para os cálculos.
dss.circuit.set_active_element('Line.L1')
V_pre_falta = dss.cktelement.voltages
I_pre_falta = dss.cktelement.currents

# Converte os valores de pre-falta para vetores complexos 1D do NumPy.
Vpre = np.array([V_pre_falta[0] + 1j * V_pre_falta[1],
                 V_pre_falta[2] + 1j * V_pre_falta[3],
                 V_pre_falta[4] + 1j * V_pre_falta[5]])
Ipre = np.array([I_pre_falta[0] + 1j * I_pre_falta[1],
                 I_pre_falta[2] + 1j * I_pre_falta[3],
                 I_pre_falta[4] + 1j * I_pre_falta[5]])

# --- 3. PREPARACAO DO DICIONARIO DE RESULTADOS ---

# Cria um dicionário para armazenar os resultados da análise (distancia e linha estimada).
min_reat_data = {}
for i in ['d', 'line']:
    for j in [f'ckt{z+1}' for z in range(8)]:
        min_reat_data[f'{j}_{i}'] = []

# Adiciona as colunas de referencia do DataFrame original para facilitar a comparacao.
min_reat_data['distancia real'] = medidas_df['distancia']
min_reat_data['linha_faltosa'] = medidas_df['linha_faltosa']
min_reat_data['tipo_de_falta'] = medidas_df['tipo']
min_reat_data['r_f'] = medidas_df['r_f']

# --- 4. LACO PRINCIPAL DE ANALISE (METODO DA MINIMA REATANCIA) ---

for index, row in tqdm(medidas_df.iterrows(), total=medidas_df.shape[0], desc="Analisando Casos de Falta"):

    reatancia = 0

    # Converte as medicoes de tensao e corrente DURANTE a falta para vetores complexos.
    Vfalta = np.array([row['va_r'] + 1j * row['va_i'],
                       row['vb_r'] + 1j * row['vb_i'],
                       row['vc_r'] + 1j * row['vc_i']])
    Ifalta = np.array([row['ia_r'] + 1j * row['ia_i'],
                       row['ib_r'] + 1j * row['ib_i'],
                       row['ic_r'] + 1j * row['ic_i']])

    # ATENCAO: Para cada falta, este laco testa a localizacao em TODOS os circuitos possiveis.
    # Isso e necessário porque o algoritmo nao sabe a priori qual e o caminho correto.
    for circuito in alimentador.keys():

        # Inicializa variáveis para a análise deste caminho especifico.
        distancia = 0
        falta_encontrada = False
        regiao = str()
        z_montante = np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        lista_distancia = []
        lista_reatancia = []

        # calculos da impedancia total do circuito e obtendo o parametro de linecode da linha
        # impedancia do circuito
        z_ckt = np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0]])
        for linha_2 in alimentador[circuito]:
            z_ckt = z_ckt + data[linha_2]['zmatrix'] * float(data[linha_2]['length'])

        # Itera sobre cada linha que compoe o circuito (caminho) atual
        for linha in alimentador[circuito]:

            regiao = linha # Armazena o nome do segmento de linha atual

            # Obtem a impedancia por unidade de comprimento da linha atual
            linecode_linha = data[linha]['zmatrix']
            l_linha = data[linha]['length']

            # Calcula a impedancia de carga equivalente vista da subestacao.
            Zca = (Vpre[0] / Ipre[0] - (z_ckt[0, 0] * Ipre[0] + z_ckt[1, 0] * Ipre[1] + z_ckt[2, 0] * Ipre[2]) / Ipre[0])
            Zcb = (Vpre[1] / Ipre[1] - (z_ckt[0, 1] * Ipre[0] + z_ckt[1, 1] * Ipre[1] + z_ckt[2, 1] * Ipre[2]) / Ipre[1])
            Zcc = (Vpre[2] / Ipre[2] - (z_ckt[0, 2] * Ipre[0] + z_ckt[1, 2] * Ipre[1] + z_ckt[2, 2] * Ipre[2]) / Ipre[2])
            z_carga = np.array([[Zca, 0, 0], [0, Zcb, 0], [0, 0, Zcc]])

            # A impedancia total do sistema e a impedancia da linha + a da carga.
            z_total = z_ckt + z_carga

            # Laco interno que "varre" a linha atual em pequenos passos.
            parametro_m = np.arange(0.01, 1.01, 0.01).tolist()
            for m in parametro_m:

                # Atualiza a distancia e a impedancia a montante a cada passo.
                distancia += l_linha * 0.01
                z_montante = z_montante + l_linha * 0.01 * linecode_linha

                # Calcula a impedancia a jusante (do ponto de análise ate a carga).
                z_jusante = z_total - z_montante

                # Calcula a tensao e corrente no ponto de falta teórico (metodo de Thevenin).
                Vf = Vfalta - z_montante @ Ifalta
                Yeq = np.linalg.inv(z_jusante)
                If = Ifalta - Yeq @ Vf

                # Calcula a reatancia aparente vista do ponto de falta.
                reatancia = fc.reatancia_calc(row['tipo'], Vf, If)

                lista_distancia.append(distancia)
                lista_reatancia.append(reatancia)

                # CONDICAO DE DETECCAO: Se a reatancia cruza zero (torna-se negativa),
                # significa que passamos do ponto de falta.
                if reatancia < 0:
                    falta_encontrada = True

                    # Realiza uma interpolacao linear para encontrar a distancia mais precisa.
                    distancia_precisa = lista_distancia[-1] - (lista_reatancia[-1] * ((lista_distancia[-1] - lista_distancia[-2]) / (lista_reatancia[-1] - lista_reatancia[-2])))
                    distancia = distancia_precisa
                    break # Sai do laco 'm'

            # Se a falta foi encontrada no circuito atual, armazena os resultados e para de procurar.
            if (falta_encontrada == True) or ((m == 1.0) and linha == alimentador[circuito][-1]):
                indice = [f'circuito{u+1}' for u in range(8)].index(circuito)
                min_reat_data[f'ckt{indice+1}_d'].append(distancia*304.8)
                min_reat_data[f'ckt{indice+1}_line'].append(regiao)
                break # Sai do laco 'linha'

# --- 5. PÓS-PROCESSAMENTO E EXPORTACAO DOS DADOS ---

# Converte o dicionário com todas as estimativas em um DataFrame.
resultado_estimativa_df = pd.DataFrame(min_reat_data)

# Prepara para adicionar os dados dos sensores ao DataFrame de resultados.
colunas_adicionar = []
for sensor in lista_sensores:
    for fase in ['a', 'b', 'c']:
        colunas_adicionar.append(f'{sensor}_i{fase}')

# Junta os dados dos sensores (do df original) com o df de estimativas.
resultado_estimativa_df = resultado_estimativa_df.join(medidas_df[colunas_adicionar])

# Salva o DataFrame final com as análises em um novo arquivo CSV.
resultado_estimativa_df.to_csv(pathlib.Path(script_path).joinpath("result", "minima_reatancia.csv"), sep=';', decimal=',')

print("\nAnálise concluida e resultados salvos com sucesso!")