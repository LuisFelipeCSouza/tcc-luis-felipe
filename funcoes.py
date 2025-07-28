import py_dss_interface
import networkx as nx
import numpy as np

def dict_circuitos_func():
    """
        Define e retorna um dicionario com os caminhos dos circuitos principais do alimentador IEEE 34 Barras.

        Cada circuito representa um caminho unico da subestacao ate um ponto terminal da rede.
        Esta funcao utiliza valores 'hardcoded', ou seja, fixos no codigo. Uma abordagem mais
        avancada poderia gerar esses caminhos dinamicamente a partir do grafo da rede.

        Retorna:
            dict: Um dicionario onde as chaves sao os nomes dos circuitos (ex: 'circuito1') e
                  os valores sao listas de strings com os nomes das linhas que compoem o caminho.
    """

    circuito1 = ['l1', 'l2', 'l3', 'l4']
    circuito2 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l8', 'l10', 'l11']
    circuito3 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l12']
    circuito4 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l13', 'l14', 'l15', 'l26']
    circuito5 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l13', 'l14', 'l15', 'l27', 'l25', 'l16', 'l28']
    circuito6 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l13', 'l14', 'l15', 'l27', 'l25', 'l16', 'l29', 'l18',
                 'l21', 'l22', 'l23']
    circuito7 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l13', 'l14', 'l15', 'l27', 'l25', 'l16', 'l29', 'l17',
                 'l30', 'l20', 'l31']
    circuito8 = ['l1', 'l2', 'l3', 'l5', 'l6', 'l7', 'l24', 'l9', 'l13', 'l14', 'l15', 'l27', 'l25', 'l16', 'l29', 'l17',
                 'l30', 'l19']
    
    dict_circuitos = {'circuito1': circuito1,
                      'circuito2': circuito2,
                      'circuito3': circuito3,
                      'circuito4': circuito4,
                      'circuito5': circuito5,
                      'circuito6': circuito6,
                      'circuito7': circuito7,
                      'circuito8': circuito8} 

    return dict_circuitos
    
def create_network_graph():
 
    """
    Cria e retorna um grafo direcionado (networkx.DiGraph) que representa a topologia da rede IEEE 34 Barras.

    As arestas do grafo representam os segmentos de linha, e os nos representam as barras.
    Cada aresta possui um 'label' que corresponde ao nome da linha no OpenDSS.

    Retorna:
        nx.DiGraph: Um objeto de grafo do NetworkX representando a rede.
    """

    g = nx.DiGraph()
    arestas = [
        ('800', '802', 'l1'), ('802', '806', 'l2'), ('806', '808', 'l3'),
        ('808', '810', 'l4'), ('808', '812', 'l5'), ('812', '814', 'l6'),
        ('814r', '850', 'l7'), ('816', '818', 'l8'), ('816', '824', 'l9'),
        ('818', '820', 'l10'), ('820', '822', 'l11'), ('824', '826', 'l12'),
        ('824', '828', 'l13'), ('828', '830', 'l14'), ('830', '854', 'l15'),
        ('832', '858', 'l16'), ('834', '860', 'l17'), ('834', '842', 'l18'),
        ('836', '840', 'l19'), ('836', '862', 'l20'), ('842', '844', 'l21'),
        ('844', '846', 'l22'), ('846', '848', 'l23'), ('850', '816', 'l24'),
        ('852r', '832', 'l25'), ('854', '856', 'l26'), ('854', '852', 'l27'),
        ('858', '864', 'l28'), ('858', '834', 'l29'), ('860', '836', 'l30'),
        ('862', '838', 'l31'), ('814', '814r', 'reg1'), ('852', '852r', 'reg2')
    ]
    for bus1, bus2, label in arestas:
        g.add_edge(bus1, bus2, label=label)
    return g
    
def get_sensor_locations(g, origem, aresta_consulta_label):
    """
    Identifica a aresta mais a montante (mais proxima da fonte) dentro do caminho
    onde a aresta informada esta contida. Por caminho, define-se como os trechos
    compreendidos em que suas extremidades sao uma barra que possui uma derivacao
    e barra terminal, ou extremidades em que as barras possuem derivacao

    Nota: Esta funcao tem uma complexidade elevada e pode ser lenta para grafos grandes,
          pois gera todos os caminhos a partir de nos de derivacao.

    Parametros:
        G (nx.DiGraph): O grafo direcionado da rede.
        origem (str): O no de referência (raiz do sistema, ex: '800').
        aresta_consulta_label (str): O nome (label) da aresta para a qual se quer encontrar o sensor.

    Retorna:
        tuple: Uma tupla (aresta_montante, label_montante) ou None se nao encontrada.
    """
    # 1. Encontrar a aresta correspondente ao label informado
    aresta_consulta = None
    for u, v, data in g.edges(data=True):
        if data['label'] == aresta_consulta_label:
            aresta_consulta = (u, v)
            break

    if aresta_consulta is None:
        return None  # Se o label nao existir no grafo

    # 2. Encontrar todos os caminhos conectados no grafo
    caminhos = []
    for u in g.nodes:
        vizinhos = list(g.successors(u))

        # Se um no tiver mais de um sucessor, ele e uma derivacao
        if len(vizinhos) > 1 or u == origem:
            for v in vizinhos:
                caminho = [(u, v)]
                while len(list(g.successors(v))) == 1:  # Continua ate encontrar derivacao ou extremidade
                    prox = list(g.successors(v))[0]
                    caminho.append((v, prox))
                    v = prox
                caminhos.append(caminho)

    # 3. Identificar em qual caminho esta a aresta informada
    for caminho in caminhos:
        if aresta_consulta in caminho:
            aresta_montante = caminho[0]
            label_montante = g.edges[aresta_montante]['label']
            return aresta_montante, label_montante

    return None  # Se nao encontrar um caminho correspondente

def lista_sensores_fc(g):
    """
        Gera uma lista de 'sensores' unicos para o alimentador.

        Um 'sensor' e definido como a primeira linha de um ramal principal. Esta funcao
        itera sobre todas as linhas do grafo e usa get_sensor_locations para encontrar
        a linha "mae" de cada uma, compilando uma lista sem duplicatas.

        Parametros:
            G (nx.DiGraph): O grafo da rede.

        Retorna:
            list: Uma lista de strings com os nomes (labels) unicos dos sensores.
        """

    lista_sensores = []

    for linha in [data['label'] for _, _, data in g.edges(data=True)]:
        _, sensor_label = get_sensor_locations(g, '800', linha)
        if not sensor_label in lista_sensores:
            lista_sensores.append(sensor_label)

    return lista_sensores

def measurement_dict_fc():
    """
        Cria e retorna um dicionario modelo (template) para armazenar os resultados da simulacao.

        As chaves sao pre-definidas para armazenar tensoes, correntes, dados da falta e
        medicoes dos sensores. Cada valor e uma lista vazia, pronta para ser preenchida.

        """

    measurement_dict = {}
    
    for i in ['v', 'i']:
        for j in ['a', 'b', 'c']:
            for k in ['r', 'i']:
                measurement_dict[f'{i}{j}_{k}'] = []

    for i in ['linha_faltosa', 'distancia', 'tipo', 'r_f']:
        measurement_dict[i] = []
      
    g = create_network_graph()
    
    lista_sensores = lista_sensores_fc(g)

    for sensor in lista_sensores:
        for fase in ['a', 'b', 'c']:
            measurement_dict[f'{sensor}_i{fase}'] = []
            
    return measurement_dict


def processamento(dss):
    """
        Realiza um pre-processamento de todos os elementos 'Line' do circuito OpenDSS,
        extraindo seus parametros e calculando suas matrizes de impedancia.

        Parametros:
            dss (py_dss_interface.DSS): A instancia do objeto DSS.

        Retorna:
            dict: Um dicionario aninhado onde cada chave e o nome de uma linha e o valor
                  e outro dicionario com os parametros daquela linha.
    """

    processamento_data = {}
    
    dss.lines.first()
    for _ in range(dss.lines.count):
        processamento_data[dss.lines.name] = {}
        processamento_data[dss.lines.name]['linecode'] = dss.lines.linecode
        processamento_data[dss.lines.name]['length'] = dss.lines.length
        processamento_data[dss.lines.name]['num_phases'] = dss.lines.phases
        processamento_data[dss.lines.name]['bus1'] = dss.lines.bus1.split('.')[0]
        processamento_data[dss.lines.name]['bus2'] = dss.lines.bus2.split('.')[0]
        processamento_data[dss.lines.name]['phases'] = (dss.lines.bus1.split('.'))[::-1][:processamento_data[dss.lines.name]['num_phases']]
        
        dss.linecodes.first()
        for __ in range(dss.linecodes.count):
            if dss.lines.linecode == dss.linecodes.name:
                if len(dss.linecodes.rmatrix) == 9:
                    r = np.array(dss.linecodes.rmatrix).reshape(3,3)
                    x = np.array(dss.linecodes.xmatrix).reshape(3,3)
                    
                    processamento_data[dss.lines.name]['zmatrix'] = r + 1j * x
                    
                elif len(dss.linecodes.rmatrix) == 1:
                    phase_map = {'1': 0, '2': 1, '3': 2}
                    
                    indice_fase = phase_map[processamento_data[dss.lines.name]['phases'][0]]
                    r = np.zeros((3,3))
                    r[indice_fase, indice_fase] = dss.linecodes.rmatrix[0]
                    x = np.zeros((3,3))
                    x[indice_fase, indice_fase] = dss.linecodes.xmatrix[0]
                    
                    processamento_data[dss.lines.name]['zmatrix'] = r + 1j * x
            
            dss.linecodes.next()        
        dss.lines.next()


    return processamento_data
      
def parametro_de_falta(type_fault, available_phases):

    """
       Retorna os parametros de uma falta (bus1, bus2, num_phases) se ela for aplicavel
       às fases disponiveis na linha.

       Utiliza um dicionario de configuracao para mapear uma chave de falta (ex: 'at')
       aos seus parametros no OpenDSS.

       Parametros:
           type_fault (str): A chave que identifica o tipo de falta (ex: "at", "bct").
           available_phases (list): Lista de strings com as fases disponiveis (ex: ['1', '2', '3']).

       Retorna:
           tuple: Uma tupla com (bus1, bus2, num_phases) se a falta for valida, ou None caso contrario.
    """

    fault_config = {
        # ... (seu dicionario fault_config aqui, igual ao anterior) ...
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
    
    # Melhoria 1: Usar .get() para evitar erro se a 'type_fault' nao existir
    config = fault_config.get(type_fault)
    
    if not config:
        return None  # Retorna None se o tipo de falta for invalido

    # Melhoria 2: Corrigido o bug. Você precisa pegar a lista de 'phases_needed'
    required = set(config['phases_needed'])
    available = set(available_phases)
    
    if required.issubset(available):
        # Se o IF for atendido, retorna a lista com os parametros
        return [config['bus1'],
                config['bus2'],
                config['num_phases']]
    else:
        # Se o IF NAO for atendido, retorna None
        return None
      
def format_abs_sensor(list_measurement, phases):
    """
        Formata uma medicao de corrente bruta do DSS e retorna uma lista com os valores
        de magnitude (absolutos) para as fases A, B e C.

        Parametros:
            list_measurement (list): Lista de floats do DSS (partes real e imaginaria).
            phases (list): Lista de strings com as fases presentes (ex: ['1']).

        Retorna:
            list: Uma lista de 3 floats com as magnitudes das correntes [IA, IB, IC].
    """

    sensor_abs = []
    if len(list_measurement) == 12:
        sensor_abs = [abs(list_measurement[0] + 1j*list_measurement[1]),
                      abs(list_measurement[2] + 1j*list_measurement[3]),
                      abs(list_measurement[4] + 1j*list_measurement[5])]
                      
    elif len(list_measurement) == 4:
        if phases == ['1']:
            sensor_abs = [abs(list_measurement[0] + 1j*list_measurement[1]),
                          0.0,
                          0.0]
            
        elif phases == ['2']:
            sensor_abs = [0.0,
                          abs(list_measurement[0] + 1j*list_measurement[1]),
                          0.0]
                
        elif phases == ['3']:
            sensor_abs = [0.0,
                          0.0,
                          abs(list_measurement[0] + 1j*list_measurement[1])]
    
    return sensor_abs
    
def reatancia_calc(tipo_falta, v_f, i_f):

    """
        Calcula a reatancia aparente no ponto de falta com base no tipo de falta.

        Parametros:
            tipo_falta (str): String que descreve os nos da falta (ex: '.1.0', '.1.2').
            Vf (np.ndarray): Vetor de tensoes complexas no ponto de falta.
            If (np.ndarray): Vetor de correntes complexas de falta.

        Retorna:
            float: O valor da reatancia calculada. Retorna 0.0 se o tipo for desconhecido.
    """

    xf = 0.0

    if set([tipo_falta]).issubset({'.1.0'}):
        xf = (v_f[0] / i_f[0]).imag
    elif set([tipo_falta]).issubset({'.2.0'}):
        xf = (v_f[1] / i_f[1]).imag
    elif set([tipo_falta]).issubset({'.3.0'}):
        xf = (v_f[2] / i_f[2]).imag
    elif set([tipo_falta]).issubset({'.1.2', '.1.2.0'}):
        xf = ((v_f[1] - v_f[0])/ (i_f[1] - i_f[0])).imag
    elif set([tipo_falta]).issubset({'.2.3', '.2.3.0'}):
        xf = ((v_f[2] - v_f[1]) / (i_f[2] - i_f[1])).imag
    elif set([tipo_falta]).issubset({'.3.1', '.3.1.0', '.1.3', '.1.3.0'}):
        xf = ((v_f[0] - v_f[2]) / (i_f[0] - i_f[2])).imag
    elif set([tipo_falta]).issubset({'.1.2.3.0'}):
        xf = ((v_f[1] - v_f[0])/(i_f[1] - i_f[0])).imag
        
    return xf