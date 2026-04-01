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

    def __init__(self, path_file, feeder_output_line=None):

        self.path_file = path_file
        self.dss = py_dss_interface.DSS()
        self.dss.text('Clear')
        self.dss.text(f'Compile "{self.path_file}"')

        # Dicionário para armazenar as distâncias dos barramentos
        # Chave: Nome do barramento, Valor: Distância do barramento
        self.buses_distance = {
            f"{(str(name))}: {float(UnitConverter.to_km(distance, self.units))}" for name, distance in zip(self.dss.circuit.buses_names,
                                                                                                         self.dss.circuit.buses_distances)
            }
        
        self.units = self.dss.lines.units
        self.lines = self.dss.lines.names

        self.fault_map = ['at', 'bt', 'ct', 'ab', 'bc', 'ac',
                         'abt', 'bct', 'act', 'abc']
        self.fault_configs = self._get_fault_configs()

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

    def run_simulation(self, r_list, m):

        for line in self.lines:
            pass

        pass

    def apply_fault(self, m, line, r, fault_type):

        self.dss.lines.name = line

        # Dados da linha
        line_length = self.dss.lines.length
        bus1_line = self.dss.lines.bus1
        bus2_line = self.dss.lines.bus2
        line_n_phase = self.dss.lines.phases
        linecode = self.dss.lines.linecode
        line_unit_code = self.dss.lines.units

        sufix = "."+".".join(bus1_line.split('.')[1:])


        bus1_dist = self.buses_distance[bus1_line.split('.')[0].lower()]

        self.dss.text("Clear")
        self.dss.text(f'Compile "{self.path_file}"')

        self.dss.text(f"Edit Line.{line} Length={line_length * m}")
        self.dss.text(f"Edit Line.{line} bus2=barra_falta{sufix}")

        self.dss.text(f"New Line.Auxiliar Phases={line_n_phase}")
        self.dss.text(f"~ Bus1=barra_falta{sufix}")
        self.dss.text(f"~ Bus2={bus2_line}")
        self.dss.text(f"~ Linecode={linecode}")
        self.dss.text(f"~ Length={(1 - m) * line_length}")
        self.dss.text(f"~ units={UnitConverter.unit_to_str(line_unit_code)}")

        bus1_fault = self.fault_configs[phase]['bus1']
        bus2_fault = self.fault_configs[phase]['bus2']

        self.dss.text('New Fault.Falta')
        self.dss.text(f'~ phases={phase}') 
        self.dss.text(f'~ bus1=barra_falta{bus1_fault}')

        if fault_type in ['ab', 'bc', 'ac']:
            self.dss.text(f'~ bus2=barra_falta{bus2_fault}')

        self.dss.text(f'~ R={r}')

        return True