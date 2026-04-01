import py_dss_interface
import networkx as nx
import numpy as np
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict, Tuple

from unit_converter import UnitConverter
from topologia import FeederTopology


class FaultSimulator:

    """Classe responsável por orquestrar a simulação de curtos-circuitos no OpenDSS."""

    def __init__(self, path_file, origin_bus='sourcebus'):

        self.path_file = path_file
        self.dss = py_dss_interface.DSS()
        self.dss.text('Clear')
        self.dss.text(f'Compile "{self.path_file}"')
        # Resolve o fluxo base para habilitar a medição de distânciasdo OpenDSS
        self.dss.solution.solve()  

        # Inicializa a topologia e extrai os dados estáticos das linhas
        self.topology = FeederTopology(self.dss, source_bus=origin_bus)
        self.lines = list(self.topology.line_data.keys())

        # Pega o codigo da unidade de comprimento das linhas do circuito base
        self.dss.lines.first()
        self.units = self.dss.lines.units

        # 4. Cria o dicionário mapeando {nome_da_barra: distancia_em_km}
        self.buses_distance = {
            str(name).split('.')[0].lower(): float(UnitConverter.to_km(distance, self.units))
            for name, distance in zip(self.dss.circuit.buses_names, self.dss.circuit.buses_distances)
        }
        
        self.fault_map = ['at', 'bt', 'ct', 'ab', 'bc', 'ac',
                         'abt', 'bct', 'act', 'abc']
        
        self.fault_configs = self._get_fault_configs()

    def run_simulation(self,
                       r_list: List[float],
                       step_pct: float = None,
                       step_abs_m: float = None):
        
        """
        Executa a varredura linear de faltas iterando nas linhas únicas.
        
        Args:
            r_list (List[float]): Lista de resistências de falta.
            step_pct (float, opcional): Passo percentual ao longo da linha (ex: 0.1 para 10%).
            step_abs_m (float, opcional): Passo absoluto em metros (ex: 1.0 para 1 metro).
        """

        if step_pct is None and step_abs_m is None:
            raise ValueError("Você deve fornecer 'step_pct' ou 'step_abs_m'.")
        
        # Pré-calcular os valores de 'm' para cada linha e o total de iterações
        m_ranges = {}
        total_iters = 0

        for line in self.lines:
            line_data = self.topology.line_data[line]

            if step_abs_m is not None:
                len_km = UnitConverter.to_km(line_data['length'], self.units)
                len_m = len_km * 1000.0

                # Se o passo for maior que a linhaa, a falta não é aplicada no meio dela
                if step_abs_m >= len_m:
                    m_ranges[line] = []
                else:
                    # Gera array de distâncias absolutas (ex: 10, 20, 30, ... metros)
                    # O np.arange vai do passo até o limite da linha (exclusivo)
                    dist_range = np.arange(step_abs_m, len_m, step_abs_m)

                    # Converte as distâncias absolutas para porcentagem 'm'
                    m_ranges[line] = (dist_range / len_m).tolist()

            else:
                # Usa a lógica de porcentagem
                m_ranges[line] = np.arange(step_pct, 1.0, step_pct).tolist()

            total_iters += len(m_ranges[line]) * len(r_list) * len(self.fault_map)
        
        with tqdm(total=total_iters, desc="Simulando Faltas") as pbar:
            for r_fault in r_list:
                for line in self.lines:

                    line_data = self.topology.line_data[line]
                    for m in m_ranges[line]:
                        for fault_type in self.fault_map:
                            pbar.update(1)
                            
                            # CORREÇÃO 2: Usar 'continue' em vez de 'return False'
                            if not self.is_fault_applicable(fault_type, line_data['phases']):
                                continue
                            
                            # Como a validação já foi feita acima, basta chamar o método.
                            # Se você removeu o 'return True/False' de dentro do apply_fault, 
                            # o 'if' não é mais necessário aqui.
                            self.apply_fault(m, line, r_fault, fault_type)
                            self.dss.solution.solve()

                            dist_bus1 = self.buses_distance[line_data['bus1']]
                            
                            delta_dist = UnitConverter.to_km(line_data['length'], self.units) * m

                            dist_fault = dist_bus1 + delta_dist
                            
                            # Aqui você adicionará sua lógica para extrair as correntes/tensões
                            # self._take_measurements(...)

    def apply_fault(self, m: float, line: str, r: float, fault_type: str) -> bool:
        """Divide a linha e aplica a falta na distância m (%). Retorna False se a falta for inválida."""
        
        # Aproveita os dados pré-carregados da topologia
        line_data = self.topology.line_data[line]
        
        # Validação: a linha possui as fases necessárias para este tipo de falta?
        config = self.fault_configs[fault_type]
        if not set(config['phases_needed']).issubset(set(line_data['phases'])):
            return False

        line_length = line_data['length']
        bus2_line = line_data['bus2']
        line_n_phase = line_data['num_phases']
        linecode = line_data['linecode']
        
        # Garante a formatação do sufixo (ex: ".1.2.3" ou apenas ".1")
        sufix = "." + ".".join(line_data['phases'])

        # Reset e Recompilação do circuito limpo
        self.dss.text("Clear")
        self.dss.text(f'Compile "{self.path_file}"')

        # Edição da Linha Original (trecho a montante da falta)
        self.dss.text(f"Edit Line.{line} Length={line_length * m}")
        self.dss.text(f"Edit Line.{line} bus2=barra_falta{sufix}")

        # Criação da Linha Auxiliar (trecho a jusante da falta)
        self.dss.text(f"New Line.Auxiliar Phases={line_n_phase}")
        self.dss.text(f"~ Bus1=barra_falta{sufix}")
        self.dss.text(f"~ Bus2={bus2_line}{sufix}")
        self.dss.text(f"~ Linecode={linecode}")
        self.dss.text(f"~ Length={(1 - m) * line_length}")
        self.dss.text(f"~ units={UnitConverter.unit_to_str(self.units)}")

        # Configuração do Objeto Fault
        bus1_fault = config['bus1']
        bus2_fault = config['bus2']
        num_phases = config['num_phases']

        self.dss.text('New Fault.Falta')
        self.dss.text(f'~ phases={num_phases}') 
        self.dss.text(f'~ bus1=barra_falta{bus1_fault}')

        if fault_type in ['ab', 'bc', 'ac']:
            self.dss.text(f'~ bus2=barra_falta{bus2_fault}')

        self.dss.text(f'~ R={r}')

        return True
    
    def is_fault_applicable(self, fault_type: str, line_phases: List[str]) -> bool:
        """
        Verifica se as fases requeridas para um determinado tipo de falta 
        estão presentes nas fases disponíveis da linha.
        
        Args:
            fault_type (str): Chave do tipo de falta (ex: 'at', 'bc', 'abc').
            line_phases (List[str]): Lista de fases da linha (ex: ['1', '2', '3']).
            
        Returns:
            bool: True se a falta puder ser aplicada, False caso contrário.
        """
        config = self.fault_configs.get(fault_type)
        
        # Se o tipo de falta não existir no dicionário, retorna falso
        if not config:
            return False
            
        required_phases = set(config['phases_needed'])
        available_phases = set(line_phases)
        
        # Verifica se o conjunto de fases requeridas está contido nas fases da linha
        return required_phases.issubset(available_phases)
    
    def _get_fault_configs(self) -> Dict:
        return {
        "at": {"phases_needed": ['1'], "bus1": ".1", "bus2": ".0", "num_phases": "1"},
        "bt": {"phases_needed": ['2'], "bus1": ".2", "bus2": ".0", "num_phases": "1"},
        "ct": {"phases_needed": ['3'], "bus1": ".3", "bus2": ".0", "num_phases": "1"},
        "abt": {"phases_needed": ['1', '2'], "bus1": ".1.2", "bus2": ".0", "num_phases": "2"},
        "bct": {"phases_needed": ['2', '3'], "bus1": ".2.3", "bus2": ".0", "num_phases": "2"},
        "act": {"phases_needed": ['1', '3'], "bus1": ".1.3", "bus2": ".0", "num_phases": "2"},
        "ab": {"phases_needed": ['1', '2'], "bus1": ".1", "bus2": ".2", "num_phases": "1"},
        "bc": {"phases_needed": ['2', '3'], "bus1": ".2", "bus2": ".3", "num_phases": "1"},
        "ac": {"phases_needed": ['1', '3'], "bus1": ".1", "bus2": ".3", "num_phases": "1"},
        "abc": {"phases_needed": ['1', '2', '3'], "bus1": ".1.2.3", "bus2": ".0", "num_phases": "3"},
    }
    
if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    dss_file = BASE_DIR / "data" / "34Bus" / "Run_IEEE34Mod1.dss"

    print("⚡ Inicializando o Simulador de Faltas no OpenDSS...")
    
    # 2. Instancia a classe do simulador
    # Isso fará o compile inicial, o solve do fluxo de potência,
    # descobrirá a topologia e calculará as distâncias de todas as barras.
    simulador = FaultSimulator(str(dss_file))

    # 3. (Opcional) Imprime o resumo da topologia descoberta automaticamente
    # Isso chamará aquele método de print bonito que configuramos na FeederTopology
    simulador.topology.print_circuits_info()

    # 4. Configura os parâmetros da varredura
    # Varrendo a linha de 10% em 10%
    passo_distancia = 0.30  
    
    # Lista de resistências de falta (em Ohms)
    resistencias_falta = [0.0001, 10.0, 20.0, 30.0, 40.0]  

    # 5. Executa o laço principal da simulação
    print("\n🚀 Iniciando a varredura linear de curtos-circuitos...")
    simulador.run_simulation(step_pct=passo_distancia, r_list=resistencias_falta)

    # 6. Pós-processamento
    # Aqui você chamaria o seu método de exportar para CSV (se implementado)
    # simulador.export_results(output_dir="result", filename="resultados_poo.csv")
    
    print("\n✅ Automação concluída com sucesso!")

    