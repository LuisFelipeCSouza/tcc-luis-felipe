import numpy as np
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from topologia import FeederTopology
from unit_converter import UnitConverter
import py_dss_interface

class FaultLocator:
    """Classe responsável por localizar faltas usando Mínima Reatância e Medidores Inteligentes."""

    def __init__(self, dss_file: str, topology: FeederTopology, df_medidas: pd.DataFrame):
        self.topology = topology
        self.df = df_medidas.copy()
        
        # Inicia uma nova instância DSS para extrair os dados de pré-falta limpos
        self.dss = py_dss_interface.DSS()
        self.dss.text('Clear')
        self.dss.text(f'Compile "{dss_file}"')
        self.dss.solution.solve()
        
        self.dss.lines.first()
        self.units = self.dss.lines.units

        self._get_pre_fault_data()

    def _get_pre_fault_data(self):
        """Mapeia Tensão e Corrente no regime permanente (Pré-falta) para TODOS os sensores MI."""
        self.pre_fault = {}
        map_fase = {'1': 'a', '2': 'b', '3': 'c'}
        
        for sensor in self.topology.get_all_sensors():
            self.dss.circuit.set_active_element(f'Line.{sensor}')
            phases = self.topology.line_data[sensor]['phases']
            
            v_dss = self.dss.cktelement.voltages
            i_dss = self.dss.cktelement.currents
            
            v_dict = {'a': 0j, 'b': 0j, 'c': 0j}
            i_dict = {'a': 0j, 'b': 0j, 'c': 0j}
            
            for idx, num_fase in enumerate(phases):
                letra = map_fase.get(num_fase)
                if letra:
                    v_dict[letra] = complex(v_dss[2*idx], v_dss[2*idx+1])
                    i_dict[letra] = complex(i_dss[2*idx], i_dss[2*idx+1])
                    
            # Armazena as matrizes 3x1 para cada sensor independentemente
            self.pre_fault[sensor] = {
                'v': np.array([[v_dict['a']], [v_dict['b']], [v_dict['c']]]),
                'i': np.array([[i_dict['a']], [i_dict['b']], [i_dict['c']]])
            }

    @staticmethod
    def _calcular_reatancia(tipo_falta: str, V_f: np.ndarray, I_f: np.ndarray) -> float:
        """Calcula a reatância aparente no ponto de falta com proteção contra divisão por zero."""
        tol = 1e-6 # Tolerância para considerar a corrente como zero

        # Helper interno para extrair a parte imaginária com segurança
        def safe_imag(v, i):
            # Extrai o valor do array numpy caso seja passado como matriz (3,1)
            v_val = v.item() if isinstance(v, np.ndarray) else v
            i_val = i.item() if isinstance(i, np.ndarray) else i
            
            if abs(i_val) > tol:
                return (v_val / i_val).imag
            # Retorna um valor positivo altíssimo (infinito/circuito aberto) se não houver corrente.
            # Isso impede que o algoritmo cruze o zero e ache falsas faltas.
            return 1e6 

        if tipo_falta == 'at': return safe_imag(V_f[0], I_f[0])
        elif tipo_falta == 'bt': return safe_imag(V_f[1], I_f[1])
        elif tipo_falta == 'ct': return safe_imag(V_f[2], I_f[2])
        elif tipo_falta in ['ab', 'abt']: return safe_imag(V_f[1] - V_f[0], I_f[1] - I_f[0])
        elif tipo_falta in ['bc', 'bct']: return safe_imag(V_f[2] - V_f[1], I_f[2] - I_f[1])
        elif tipo_falta in ['ac', 'act']: return safe_imag(V_f[0] - V_f[2], I_f[0] - I_f[2])
        elif tipo_falta == 'abc': return safe_imag(V_f[1] - V_f[0], I_f[1] - I_f[0])
        
        return 0.0

    def run_minimum_reactance(self):
        """Aplica o algoritmo buscando dados dinamicamente dos Medidores Inteligentes locais."""
        
        circuit_names = list(self.topology.main_circuits.keys())

        for c_name in circuit_names:
            self.df[f'{c_name}_line'] = None
            self.df[f'{c_name}_d'] = np.nan

        for index, row in tqdm(self.df.iterrows(), total=len(self.df), desc="Localizando Faltas"):
            tipo_falta = row['tipo']
            
            # 1. Varredura por circuito principal
            for c_name, circuit_lines in self.topology.main_circuits.items():
                dist_accum_units = 0.0
                falta_encontrada = False
                reatancia_anterior = None
                dist_anterior = 0.0
                
                # 2. Varredura por linha do circuito, acumulando impedância e buscando os dados dos sensores MI
                for idx_linha, linha_alvo in enumerate(circuit_lines):
                    
                    # 1. Identifica o Sensor responsável por esta zona do circuito
                    sensor = self.topology.get_sensor_for_line(linha_alvo)
                    
                    if not sensor:
                        continue # Rede mal configurada ou sem sensor a montante
                        
                    # 2. Busca o Regime Permanente (Pré-falta) DESTE Sensor
                    V_pref = self.pre_fault[sensor]['v']
                    I_pref = self.pre_fault[sensor]['i']
                    
                    # 3. Busca o Regime Faltoso (Pós-falta) DESTE Sensor
                    v_pos_a = complex(row[f'{sensor}_va_r'], row[f'{sensor}_va_i'])
                    v_pos_b = complex(row[f'{sensor}_vb_r'], row[f'{sensor}_vb_i'])
                    v_pos_c = complex(row[f'{sensor}_vc_r'], row[f'{sensor}_vc_i'])
                    
                    i_pos_a = complex(row[f'{sensor}_ia_r'], row[f'{sensor}_ia_i'])
                    i_pos_b = complex(row[f'{sensor}_ib_r'], row[f'{sensor}_ib_i'])
                    i_pos_c = complex(row[f'{sensor}_ic_r'], row[f'{sensor}_ic_i'])
                    
                    V_pos = np.array([[v_pos_a], [v_pos_b], [v_pos_c]])
                    I_pos = np.array([[i_pos_a], [i_pos_b], [i_pos_c]])

                    # 4. PROPAGAÇÃO DE ESTADO (Stateful Propagation)
                    Z_accum = np.zeros((3,3), dtype=complex)
                    idx_sensor = circuit_lines.index(sensor)
                    
                    for prev_line in circuit_lines[idx_sensor : idx_linha]:
                        z_matrix = self.topology.line_data[prev_line]['zmatrix']
                        # Usa o comprimento brutp (nativo) para que as unidades se cancelem resultando em Ohms
                        length = self.topology.line_data[prev_line]['length']
                        Z_accum += z_matrix * length


                    # --- CHEGAMOS NO INÍCIO DA LINHA ALVO ---
                    z_matrix_alvo = self.topology.line_data[linha_alvo]['zmatrix']
                    length_alvo_native = self.topology.line_data[linha_alvo]['length']
                    
                    Z_L = z_matrix_alvo * length_alvo_native
                    Z_ckt = Z_accum + Z_L
                    
                    # Impedância de Carga (Zc) - Muito mais simples e robusta agora!
                    # O V_calc_pref já é a tensão exata no nó superior da linha alvo.
                    Zc = np.zeros((3,3), dtype=complex)
                    
                    # Tensão no final da linha alvo (em regime permanente)
                    for i in range(3):
                        if abs(I_pref[i]) > 1e-6:
                            Zc[i,i] = (V_pref[i] / I_pref[i]) - ((Z_ckt[0,i]*I_pref[0] + Z_ckt[1,i]*I_pref[1] + Z_ckt[2,i]*I_pref[2])/I_pref[i])

                    Z_total = Z_ckt + Zc

                    length_alvo_m = UnitConverter.to_km(length_alvo_native, self.units) * 1000.0

                    # 5. Varredura passo a passo ao longo da linha alvo
                    passo_m = 0.01 
                    m_steps = np.arange(0.0, 1.0 + passo_m, passo_m)

                    for m in m_steps:
                        dist_atual_units = dist_accum_units + (length_alvo_native * m)
                        Z_trecho = z_matrix_alvo * length_alvo_native * m

                        # A matemática fica restrita APENAS à linha alvo
                        Z_montante = Z_accum + Z_trecho
                        Z_jusante = Z_total - Z_montante

                        V_f = V_pos - Z_trecho @ I_pos

                        try:
                            Yeq = np.linalg.inv(Z_jusante)
                        except np.linalg.LinAlgError:
                            Yeq = np.linalg.pinv(Z_jusante)

                        I_f = I_pos - Yeq @ V_f

                        reatancia = self._calcular_reatancia(row['tipo'], V_f, I_f)

                        if reatancia < 0:
                            falta_encontrada = True
                            if reatancia_anterior is not None:
                                # Interpolação linear
                                dist_interp = dist_anterior - (reatancia * ((dist_atual_units - dist_anterior) / (reatancia - reatancia_anterior)))
                            else:
                                dist_interp = dist_accum_units

                            # Salva os resultados convertendo a unidade nativa para Metros
                            dist_meters = UnitConverter.to_km(dist_interp, self.units) * 1000.0
                            self.df.at[index, f'{c_name}_line'] = linha_alvo
                            self.df.at[index, f'{c_name}_d'] = dist_meters
                            break

                        reatancia_anterior = reatancia
                        dist_anterior = dist_accum_units

                    if falta_encontrada:
                        break
                        
                    # Se terminou a linha e não cruzou zero, associa ao último nó
                if not falta_encontrada:
                    dist_meters = UnitConverter.to_km(dist_accum_units, self.units) * 1000.0
                    self.df.at[index, f'{c_name}_line'] = circuit_lines[-1]
                    self.df.at[index, f'{c_name}_d'] = dist_meters

    def apply_mi_filter(self):
        """Identifica a linha correta cruzando a maior corrente dos Medidores Inteligentes."""
        circuit_names = list(self.topology.main_circuits.keys())
        
        comp_total_m = sum(self.topology.line_data[l]['length'] for l in self.topology.get_main_branch())
        comp_total_m = UnitConverter.to_km(comp_total_m, self.units) * 1000.0

        for index, row in self.df.iterrows():
            tipo = row['tipo']
            fase_medida = 'a'
            if tipo in ['at', 'ab', 'abt', 'abc', '.1.2.3.0']: fase_medida = 'a'
            elif tipo in ['bt', 'bc', 'bct']: fase_medida = 'b'
            elif tipo == 'ct': fase_medida = 'c'

            maior_corrente = -1.0
            melhor_circuito = None

            for c_name in circuit_names:
                linha_alvo = row.get(f'{c_name}_line')
                if pd.isna(linha_alvo) or linha_alvo == "":
                    continue

                sensor = self.topology.get_sensor_for_line(linha_alvo)
                if sensor:
                    # O Filtro MI continua usando a magnitude da corrente (i_mag) que mapeamos
                    corrente = row.get(f'{sensor}_i{fase_medida}', 0.0)
                    if corrente > maior_corrente:
                        maior_corrente = corrente
                        melhor_circuito = c_name

            if melhor_circuito:
                est_line = row[f'{melhor_circuito}_line']
                est_dist = row[f'{melhor_circuito}_d']
                self.df.at[index, 'linha_estimada'] = est_line
                self.df.at[index, 'dist_estimada'] = est_dist
                self.df.at[index, 'erro_percentual'] = 100 * (est_dist - row['distancia']) / comp_total_m

    def export_results(self, output_dir: str = "result", filename: str = "localizacao_filtrada.csv"):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filepath = Path(output_dir) / filename
        self.df.to_csv(filepath, sep=';', decimal=',', index=False)
        print(f"✅ Análise concluída. Resultados exportados para: {filepath}")