import py_dss_interface
import networkx as nx
from typing import List, Dict, Optional

class FeederTopology:
    """Classe para descoberta automática de topologia radial no OpenDSS."""
    
    def __init__(self, dss: py_dss_interface.DSS, source_bus: str):
        self.dss = dss
        self.source_bus = source_bus.lower()
        self.graph = nx.DiGraph()

        self._build_full_topology()
        self.line_data = self._extract_line_parameters()
        self.main_circuits = self._discover_line_circuits()

        self._map_sensors()

    def _build_full_topology(self):
        """
        Mapeia todos os elementos de potência (PD Elements).
        Trata bancos de transformadores monofásicos como uma única conexão no grafo.
        """
        # 1. Mapear Linhas
        self.dss.lines.first()
        for _ in range(self.dss.lines.count):
            name = self.dss.lines.name.lower()
            b1 = self.dss.lines.bus1.split('.')[0].lower()
            b2 = self.dss.lines.bus2.split('.')[0].lower()
            self.graph.add_edge(b1, b2, label=name, type='line')
            self.dss.lines.next()

        # 2. Mapear Transformadores (incluindo reguladores monofásicos)
        self.dss.transformers.first()
        for _ in range(self.dss.transformers.count):
            name = self.dss.transformers.name.lower()
            self.dss.circuit.set_active_element(f'transformer.{name}')
            buses = self.dss.cktelement.bus_names
            
            # Limpa os nomes dos barramentos (remove .1.2.3)
            b1 = buses[0].split('.')[0].lower()
            b2 = buses[1].split('.')[0].lower()
            
            # Se a aresta já existe (ex: banco de transformadores reg1a, reg1b, reg1c),
            # o nx.DiGraph apenas mantém uma única conexão.
            if not self.graph.has_edge(b1, b2):
                self.graph.add_edge(b1, b2, label=name, type='transformer')
            else:
                # Opcional: Se quiser saber que é um banco, pode concatenar os nomes
                existing_label = self.graph[b1][b2]['label']
                if name not in existing_label:
                    self.graph[b1][b2]['label'] = f"{existing_label}/{name}"
            
            self.dss.transformers.next()

    def _extract_line_parameters(self) -> Dict[str, dict]:
        """Extrai parâmetros técnicos apenas das linhas para uso na simulação de falta."""
        data = {}
        self.dss.lines.first()
        for _ in range(self.dss.lines.count):
            name = self.dss.lines.name.lower()
            bus1_full = self.dss.lines.bus1
            bus1 = bus1_full.split('.')[0].lower()
            bus2 = self.dss.lines.bus2.split('.')[0].lower()
            num_phases = self.dss.lines.phases
            
            # Identifica as fases (ex: .1.2.3 -> ['1', '2', '3'])
            phases = bus1_full.split('.')[1:]
            if not phases: 
                phases = ['1', '2', '3'][:num_phases]
                
            data[name] = {
                'linecode': self.dss.lines.linecode,
                'length': self.dss.lines.length,
                'num_phases': num_phases,
                'bus1': bus1,
                'bus2': bus2,
                'phases': phases
            }
            self.dss.lines.next()
        return data

    def _discover_line_circuits(self) -> Dict[str, List[str]]:
        """
        Identifica caminhos da raiz até as extremidades (leaf nodes).
        Filtra os caminhos para retornar apenas os nomes das Linhas.
        """
        # Verifica se a barra de origm informada existe no grafo
        if self.source_bus in self.graph.nodes:
            root = self.source_bus
        else:
            # Fallback: Localiza a raiz dinamicamente (nó com grau de entrada zero)
            roots = [n for n, d in self.graph.in_degree() if d == 0]
            if not roots:
                print(f"⚠️ Aviso: Barra de origem '{self.source_bus}' não encontrada e não há nós com grau de entrada zero.")
                return {}
        
            root = roots[0]
            print(f"⚠️ Aviso: Barra '{self.source_bus}' não encontrada no grafo. Assumindo a barra '{root}' como raiz do alimentador.")

        # Localiza os nós terminais (nós com grau de saída zero)
        leaves = [n for n, d in self.graph.out_degree() if d == 0]
        
        circuits = {}
        for i, leaf in enumerate(leaves):
            try:
                # Encontra o caminho simples (assumindo radialidade)
                path_nodes = nx.shortest_path(self.graph, root, leaf)
                line_path = []
                
                # Traduz o caminho de nós em nomes de linhas
                for j in range(len(path_nodes) - 1):
                    u, v = path_nodes[j], path_nodes[j+1]
                    edge_data = self.graph.get_edge_data(u, v)
                    
                    # Filtramos apenas elementos do tipo 'line' conforme solicitado
                    if edge_data['type'] == 'line':
                        line_path.append(edge_data['label'])
                
                if line_path:
                    circuits[f'circuito_{i+1}'] = line_path
                    
            except nx.NetworkXNoPath:
                continue
                
        return circuits
    
    def _map_sensors(self):
        """
        Mapeia os sensores da rede usando busca em largura (BFS).
        Garante que um sensor seja sempre uma linha, ignorando transformadores
        no início do alimentador ou nas derivações até encontrar a primeira seção de cabo.
        """
        self.sensor_map = {}  # Mapeia {nome_da_linha: nome_do_sensor}
        self.sensors = []     # Lista contendo os sensores únicos

        # Determina a raiz da busca
        if self.source_bus in self.graph.nodes:
            root = self.source_bus
        else:
            roots = [n for n, d in self.graph.in_degree() if d == 0]
            if not roots:
                return
            root = roots[0]

        # Fila armazena: (nó_atual, sensor_ativo_no_ramal, precisa_de_novo_sensor)
        # Iniciamos a raiz avisando que o circuito precisa de um sensor inicial.
        queue = [(root, None, True)]
        
        while queue:
            u, passed_sensor, passed_needs_sensor = queue.pop(0)
            
            # Verifica se o nó atual é uma derivação ou a raiz do alimentador
            is_fork_or_root = (u == root) or (self.graph.out_degree(u) > 1)
            
            for v in self.graph.successors(u):
                edge_data = self.graph.get_edge_data(u, v)
                edge_label = edge_data['label']
                edge_type = edge_data['type']
                
                # Se for raiz ou derivação, forçamos o ramal a buscar um novo sensor.
                # Caso contrário, mantemos o status de busca que veio do nó anterior.
                branch_needs_sensor = is_fork_or_root or passed_needs_sensor
                
                if branch_needs_sensor:
                    if edge_type == 'line':
                        # Encontramos a primeira LINHA deste ramal! Ela é o sensor.
                        active_sensor = edge_label
                        next_needs_sensor = False
                        if active_sensor not in self.sensors:
                            self.sensors.append(active_sensor)
                    else:
                        # É um transformador iniciando o ramal. Ainda precisamos de um sensor.
                        # Herdamos temporariamente o sensor anterior (caso exista) até achar a linha.
                        active_sensor = passed_sensor
                        next_needs_sensor = True
                else:
                    # O ramal já encontrou seu sensor lá atrás. Apenas repassa a informação.
                    active_sensor = passed_sensor
                    next_needs_sensor = False
                
                # Apenas mapeamos as linhas no sensor_map (ignoramos transformadores)
                if edge_type == 'line' and active_sensor is not None:
                    self.sensor_map[edge_label] = active_sensor
                
                # Repassa o estado para o próximo nó
                queue.append((v, active_sensor, next_needs_sensor))

    def get_all_sensors(self) -> List[str]:
        """
        Substitui a antiga 'lista_sensores_fc'.
        Retorna a lista com os nomes (labels) únicos de todos os sensores do alimentador.
        """
        return self.sensors

    def get_sensor_for_line(self, line_label: str) -> Optional[str]:
        """
        Substitui a antiga 'get_sensor_locations'.
        Retorna o nome do sensor que monitora uma seção de linha específica de forma instantânea.
        
        Args:
            line_label (str): Nome da linha consultada.
            
        Returns:
            str: O nome da linha que atua como sensor, ou None se a linha não existir.
        """
        return self.sensor_map.get(line_label.lower())

    def print_circuits_info(self):
        """
        Imprime no terminal os circuitos mapeados em ordem crescente de tamanho,
        utilizando uma formatação compacta em uma única linha por circuito.
        """
        # Ordena o dicionário de circuitos com base no tamanho da lista de linhas (quantidade de seções)
        circuitos_ordenados = sorted(self.main_circuits.items(), key=lambda item: len(item[1]))

        print("\n" + "="*60)
        print("🗺️  RESUMO DA TOPOLOGIA DOS CIRCUITOS MAPEADOS")
        print("="*60 + "\n")

        # Utilizamos o enumerate para gerar o índice C_1, C_2, etc.
        for idx, (nome_circuito, linhas) in enumerate(circuitos_ordenados, start=1):
            comprimento_total = 0.0
            
            for linha in linhas:
                # Soma os comprimentos consultando os dados extraídos
                comprimento_total += self.line_data[linha]['length']
                
                # Ativa o elemento no DSS. Caso precise usar os barramentos no futuro 
                # (ex: para validar faltas em nós específicos), a variável está acessível aqui.
                self.dss.circuit.set_active_element(f'Line.{linha}')
                bus_names = self.dss.cktelement.bus_names 

            quantidade = len(linhas)
            
            # Formata a lista de linhas para uppercase e junta com hífens
            secoes_str = "-".join([linha.upper() for linha in linhas])
            
            # Imprime exatamente no formato solicitado
            print(f"C_{idx}: L = {comprimento_total:.2f} | Q = {quantidade} | seçoes: [{secoes_str}]")
            
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    # Exemplo de uso
    dss = py_dss_interface.DSS()
    dss.text("compile path_to_your_circuit.dss")
    
    topologia = FeederTopology(dss, source_bus='sourcebus')
    topologia.print_circuits_info()