# --- 1. IMPORTACAO DE BIBLIOTECAS E CONFIGURACOES INICIAIS ---
import pandas as pd
import py_dss_interface
import numpy as np
import networkx as nx
from tqdm import tqdm
import os
import pathlib
import funcoes as fc # Importa o modulo local com as funcoes auxiliares

# Define os caminhos para os arquivos de forma robusta, baseando-se na localizacao do script.
# Isso garante que o codigo funcione em qualquer computador.
script_path = os.path.dirname(os.path.abspath(__file__))
dss_file = pathlib.Path(script_path).joinpath("34Bus", "Run_IEEE34Mod1.dss")

# Inicializa a interface com o OpenDSS e compila o arquivo mestre do circuito.
# Esta etapa carrega o modelo da rede na memoria do simulador.
dss = py_dss_interface.DSS()
dss.text('Clear')
dss.text(f'Compile {dss_file}')
dss.solution.solve()

# --- 2. PRE-PROCESSAMENTO DOS DADOS DO CIRCUITO ---

# Carrega um dicionario com os caminhos dos 8 circuitos principais do alimentador.
# Cada caminho e uma lista de nomes de linhas.
alimentador = fc.dict_circuitos_func()

# Cria um grafo (usando NetworkX) que representa a topologia da rede.
# Isso e util para analises de conectividade e para identificar os ramais.
G = fc.create_network_graph()

# Gera uma lista de "sensores", que sao definidos como as primeiras linhas
# de cada ramal principal do alimentador.
lista_sensores = fc.lista_sensores_fc(G)

# Executa um pre-processamento completo do circuito, extraindo dados de todas as
# linhas (comprimento, fases, linecode, matriz de impedancia, etc.) e armazenando
# em um dicionario para acesso rapido durante a simulacao.
data = fc.processamento(dss)

# --- 3. DEFINICAO DOS PARAMETROS DA SIMULACAO ---
# Define o passo de varredura da falta ao longo do comprimento de uma linha (10% em 10%).
passo = 0.10

# Cria o dicionario que ira armazenar todos os resultados da simulacao.
# As chaves sao os nomes das medicoes e os valores sao listas vazias.
measurement = fc.measurement_dict_fc()

# Define os tipos de falta a serem simulados.
falta_map = ['at', 'bt', 'ct', 'ab', 'bc', 'ac',
             'abt', 'bct', 'act', 'abc']

# Define as resistencias de falta a serem utilizadas nas simulacoes.
fault_r = {
    'r_0_00001': 0.0001,
    'r_10': 10.0,
    'r_20': 20.0,
    'r_30': 30.0,
    'r_40': 40.0,
}

# --- 4. LACO PRINCIPAL DE SIMULACAO DE FALTAS ---

# Laco externo: itera sobre cada valor de resistencia de falta.
cont_tqdm = ((1.0 / passo) - 1) * len(falta_map) * len(fault_r) *  sum(len(linhas) for linhas in alimentador.values())
with tqdm(total=cont_tqdm, desc="Simulando casos de falta") as pbar:
    for fault_r_chave in fault_r.keys():

        # Laco do circuito: itera sobre cada um dos 8 caminhos principais do alimentador.
        for circuito in alimentador.keys():

            distancia_falta = 0

            # Laco que varre todas as secoes de linhas de cada circuito do alimentador
            for linha in alimentador[circuito]:

                # Gera uma lista de pontos percentuais ao longo da linha para aplicar a falta.
                porcentagem_linha = np.arange(passo, 1, passo).tolist()

                # Laco da localizacao: itera sobre cada ponto percentual na linha.
                for porcentagem_distancia in porcentagem_linha:

                    # Atualiza a distancia acumulada da falta a partir da subestacao.
                    distancia_falta = distancia_falta + passo * data[linha]['length']

                    # Laco do tipo de falta: itera sobre todos os tipos de falta definidos.
                    for tipo_falta in falta_map:
                        pbar.update(1)

                        dss.text('Clear')
                        dss.text(f'Compile {dss_file}')

                        # Chama uma funcao para verificar se o tipo de falta e aplicavel às fases desta linha.
                        # Se nao for, pula para a proxima iteracao com 'continue'.
                        if fc.parametro_de_falta(tipo_falta, data[linha]['phases']) is None:
                            continue

                        # Se a falta for aplicavel, obtem os parametros necessarios para o OpenDSS.
                        fault_bus1, fault_bus2, n_phases = fc.parametro_de_falta(tipo_falta, data[linha]['phases'])

                        # Define a string de nos do barramento (ex: '.1.2.3')
                        bus_nodes = '.' + '.'.join(data[linha]['phases'][::-1])

                        # --- MODIFICACAO DINAMICA DO CIRCUITO PARA INSERIR A FALTA ---
                        # 1. Edita a linha original, encurtando seu comprimento e conectando-a a uma nova "barra de falta".
                        dss.text(f'Edit Line.{linha} Length={data[linha]["length"] * porcentagem_distancia}')
                        dss.text(f'Edit Line.{linha} bus2=barra_falta{bus_nodes}')

                        # 2. Cria uma linha auxiliar para representar o trecho restante da linha original.
                        dss.text(f'New Line.Auxiliar Phases={data[linha]["num_phases"]}')
                        dss.text(f'~ Bus1=barra_falta{bus_nodes}')
                        dss.text(f'~ Bus2={data[linha]["bus2"]}{bus_nodes}')
                        dss.text(f'~ Linecode={data[linha]["linecode"]}')
                        dss.text(f'~ Length={(1 - porcentagem_distancia) * data[linha]["length"]}')
                        dss.text(f'~ units=kft')

                        # 3. Cria o objeto 'Fault' na "barra de falta", aplicando o curto-circuito.
                        dss.text('New Fault.Falta')
                        dss.text(f'~ phases={n_phases}')
                        dss.text(f'~ bus1=barra_falta{fault_bus1}')

                        # Para faltas entre fases, define o segundo terminal do objeto 'Fault'.
                        if set([tipo_falta]).issubset({'ab', 'bc', 'ac'}):
                            dss.text(f'~ bus2=barra_falta{fault_bus2}')
                        dss.text(f'~ R={fault_r[fault_r_chave]}')

                        # 4. Resolve o fluxo de potencia para o cenario com falta.
                        dss.solution.solve()

                        # --- ARMAZENAMENTO DOS DADOS ---
                        # Coleta as medicoes na saida da subestacao (Linha L1).
                        dss.circuit.set_active_element('Line.L1')

                        # Coleta e armazena as tensoes (parte real e imaginaria).
                        for indice, medida in enumerate(['va_r', 'va_i', 'vb_r', 'vb_i', 'vc_r', 'vc_i']):
                            measurement[medida].append(dss.cktelement.voltages[indice])

                        # Coleta e armazena as correntes (parte real e imaginaria).
                        for indice, medida in enumerate(['ia_r', 'ia_i', 'ib_r', 'ib_i', 'ic_r', 'ic_i']):
                            measurement[medida].append(dss.cktelement.currents[indice])

                        # Armazena os metadados da falta
                        measurement['linha_faltosa'].append(linha)
                        measurement['distancia'].append(distancia_falta * 304.8)
                        measurement['tipo'].append(str(fault_bus1 + fault_bus2))
                        measurement['r_f'].append(fault_r_chave)

                        # Coleta os dados de magnitude de corrente dos sensores.
                        for linha_sensor in lista_sensores:
                            dss.circuit.set_active_element(f'line.{linha_sensor}')
                            for indice, medida in enumerate(['ia', 'ib', 'ic']):
                                measurement[f'{linha_sensor}_{medida}'].append(fc.format_abs_sensor(dss.cktelement.currents,
                                                                                                    data[linha_sensor][
                                                                                                        'phases'][::-1])[indice])
                    # Atualiza a distancia acumulada com o ultimo trecho da linha.
                    if porcentagem_distancia == 1 - passo:
                        distancia_falta = distancia_falta + passo * data[linha]['length']

# --- 5. PÓS-PROCESSAMENTO E EXPORTACAO DOS DADOS ---
resultado_df = pd.DataFrame(measurement)

resultado_df_sem_duplicada = resultado_df.drop_duplicates()

# Salva o DataFrame final em um arquivo CSV.
resultado_df_sem_duplicada.to_csv(pathlib.Path(script_path).joinpath("result", "automacao_falta.csv"), sep=';', decimal=",",
                                  index=False)

print("\nSimulacao concluida e resultados salvos com sucesso!")