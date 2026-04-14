import numpy as np
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from topologia import FeederTopology
from unit_converter import UnitConverter
import py_dss_interface

class FaultLocator:
    """Classe responsável por localizar curtos-circuitos e aplicar o filtro de sensores MI."""

    def __init__(self, dss_file: str, topology: FeederTopology, df_medidas: pd.DataFrame):
        self.topology = topology
        self.df = df_medidas.copy()
        
        # Inicia uma nova instância DSS para extrair os dados de pré-falta limpos
        self.dss = py_dss_interface.DSS()
        self.dss.text('Clear')
        self.dss.text(f'Compile "{dss_file}"')
        self.dss.solution.solve()
        
        # Unidade base de comprimento para conversões
        self.dss.lines.first()
        self.units = self.dss.lines.units

        self._get_pre_fault_data()

    def _get_pre_fault_data(self):
        """Extrai Tensão e Corrente da subestação no regime permanente (Pré-falta)."""
        feeder_head = self.topology.find_feeder_head()
        self.dss.circuit.set_active_element(f'Line.{feeder_head}')
        
        v_dss = self.dss.cktelement.voltages
        i_dss = self.dss.cktelement.currents
        phases = self.topology.line_data[feeder_head]['phases']

        self.Vpre = np.zeros(3, dtype=complex)
        self.Ipre = np.zeros(3, dtype=complex)
        map_fase = {'1': 0, '2': 1, '3': 2}

        for idx, num_fase in enumerate(phases):
            if num_fase in map_fase:
                i_mat = map_fase[num_fase]
                self.Vpre[i_mat] = v_dss[2*idx] + 1j * v_dss[2*idx+1]
                self.Ipre[i_mat] = i_dss[2*idx] + 1j * i_dss[2*idx+1]

    @staticmethod
    def _calcular_reatancia(tipo_falta: str, V_f: np.ndarray, I_f: np.ndarray) -> float:
        """Calcula a reatância aparente no ponto de falta."""
        if tipo_falta == 'at': return (V_f[0] / I_f[0]).imag
        elif tipo_falta == 'bt': return (V_f[1] / I_f[1]).imag
        elif tipo_falta == 'ct': return (V_f[2] / I_f[2]).imag
        elif tipo_falta in ['ab', 'abt']: return ((V_f[1] - V_f[0]) / (I_f[1] - I_f[0])).imag
        elif tipo_falta in ['bc', 'bct']: return ((V_f[2] - V_f[1]) / (I_f[2] - I_f[1])).imag
        elif tipo_falta in ['ac', 'act']: return ((V_f[0] - V_f[2]) / (I_f[0] - I_f[2])).imag
        elif tipo_falta == 'abc': return ((V_f[1] - V_f[0]) / (I_f[1] - I_f[0])).imag
        return 0.0

    def run_minimum_reactance(self):
        """Aplica o método da mínima reatância para todos os circuitos da topologia."""
        
        circuit_names = list(self.topology.main_circuits.keys())
        
        # Cria colunas vazias no DataFrame para as estimativas
        for c_name in circuit_names:
            self.df[f'{c_name}_d'] = np.nan
            self.df[f'{c_name}_line'] = ""

        # Pré-calcula a impedância total de cada circuito
        z_ckts = {}
        for c_name, lines in self.topology.main_circuits.items():
            z = np.zeros((3,3), dtype=complex)
            for linha in lines:
                z += self.topology.line_data[linha]['zmatrix'] * self.topology.line_data[linha]['length']
            z_ckts[c_name] = z

        # Laço principal iterando sobre as simulações
        for index, row in tqdm(self.df.iterrows(), total=self.df.shape[0], desc="Analisando Reatâncias"):
            Vfalta = np.array([row['va_r'] + 1j*row['va_i'], row['vb_r'] + 1j*row['vb_i'], row['vc_r'] + 1j*row['vc_i']])
            Ifalta = np.array([row['ia_r'] + 1j*row['ia_i'], row['ib_r'] + 1j*row['ib_i'], row['ic_r'] + 1j*row['ic_i']])

            for c_name in circuit_names:
                lines = self.topology.main_circuits[c_name]
                z_ckt = z_ckts[c_name]

                # Impedância de Carga (Zc)
                Zc = np.zeros((3,3), dtype=complex)
                for i in range(3):
                    if abs(self.Ipre[i]) > 1e-6:
                        Zc[i,i] = (self.Vpre[i] / self.Ipre[i]) - ((z_ckt[0,i]*self.Ipre[0] + z_ckt[1,i]*self.Ipre[1] + z_ckt[2,i]*self.Ipre[2])/self.Ipre[i])
                z_total = z_ckt + Zc

                dist_accum_units = 0.0
                z_montante = np.zeros((3,3), dtype=complex)
                falta_encontrada = False
                reatancia_anterior = None
                dist_anterior = 0.0

                for linha in lines:
                    line_data = self.topology.line_data[linha]
                    z_linha = line_data['zmatrix']
                    l_linha = line_data['length']

                    passo_m = np.arange(0.01, 1.01, 0.01)
                    for m in passo_m:
                        dist_accum_units += l_linha * 0.01
                        z_montante += z_linha * (l_linha * 0.01)

                        z_jusante = z_total - z_montante
                        Vf = Vfalta - z_montante @ Ifalta
                        
                        try:
                            Yeq = np.linalg.inv(z_jusante)
                        except np.linalg.LinAlgError:
                            Yeq = np.linalg.pinv(z_jusante) # Fallback robusto para matrizes singulares

                        If = Ifalta - Yeq @ Vf
                        reatancia = self._calcular_reatancia(row['tipo'], Vf, If)

                        if reatancia < 0:
                            falta_encontrada = True
                            if reatancia_anterior is not None:
                                # Interpolação linear
                                dist_interp = dist_accum_units - (reatancia * ((dist_accum_units - dist_anterior) / (reatancia - reatancia_anterior)))
                            else:
                                dist_interp = dist_accum_units

                            # Salva os resultados convertendo a unidade nativa para Metros
                            dist_meters = UnitConverter.to_km(dist_interp, self.units) * 1000.0
                            self.df.at[index, f'{c_name}_line'] = linha
                            self.df.at[index, f'{c_name}_d'] = dist_meters
                            break

                        reatancia_anterior = reatancia
                        dist_anterior = dist_accum_units
                        
                    if falta_encontrada: break
                
                # Se terminou a linha e não cruzou zero, associa ao último nó
                if not falta_encontrada:
                    dist_meters = UnitConverter.to_km(dist_accum_units, self.units) * 1000.0
                    self.df.at[index, f'{c_name}_line'] = lines[-1]
                    self.df.at[index, f'{c_name}_d'] = dist_meters

    def apply_mi_filter(self):
        """Aplica o filtro de sensores baseado na Maximização de Corrente (MI)."""
        
        self.df['linha_estimada'] = ""
        self.df['dist_estimada'] = np.nan
        self.df['erro_percentual'] = np.nan

        circuit_names = list(self.topology.main_circuits.keys())

        # Pega a linha mais longa do alimentador para calcular o erro (como feito no seu original)
        caminho_mais_longo = max(self.topology.main_circuits.values(), key=len)
        comp_total_m = sum((UnitConverter.to_km(self.topology.line_data[l]['length'], self.units) * 1000.0) for l in caminho_mais_longo)

        for index, row in tqdm(self.df.iterrows(), total=self.df.shape[0], desc="Aplicando Filtro MI"):
            tipo = row['tipo']
            
            # Qual fase da corrente devemos olhar no sensor?
            fase_medida = 'a'
            if tipo in ['bt', 'bc', 'bct']: fase_medida = 'b'
            elif tipo == 'ct': fase_medida = 'c'

            maior_corrente = -1.0
            melhor_circuito = None

            for c_name in circuit_names:
                linha_alvo = row.get(f'{c_name}_line')
                if pd.isna(linha_alvo) or linha_alvo == "":
                    continue

                # Pergunta para a Topologia qual sensor monitora este trecho!
                sensor = self.topology.get_sensor_for_line(linha_alvo)
                if sensor:
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
        self.df.to_csv(filepath, sep=';', decimal=",", index=False)
        print(f"✅ Análise concluída. Resultados salvos em: {filepath}")