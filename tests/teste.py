import py_dss_interface
import sys
from pathlib import Path

# adiciona a pasta src ao caminho do Python
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from config import DSS_PATH
from unit_converter import UnitConverter


def teste():
    dss = py_dss_interface.DSS()

    dss.text("Clear")
    dss.text(f"Redirect {str(DSS_PATH)}")
    dss.solution.solve()

    # cria elementos auxiliares desconectados
    dss.text("New Line.aux bus1=dummy bus2=dummy length=1 units=km r1=0.1 x1=0.2")
    dss.text("New Fault.F1 bus1=dummy phases=1 r=0.001")

    # mapeia distâncias dos buses
    buses_names = dss.circuit.buses_names
    buses_distances = dss.circuit.buses_distances
    bus_dist_map = {b: d for b, d in zip(buses_names, buses_distances)}

    # percorre linhas do circuito
    dss.lines.first()
    for _ in range(dss.lines.count):

        if dss.lines.name == "aux":
            continue  # pula a linha auxiliar

        name = dss.lines.name
        length = dss.lines.length
        bus1 = dss.lines.bus1.split('.')[0]
        bus2 = dss.lines.bus2.split('.')[0]
        units = UnitConverter.unit_to_str(dss.lines.units)

        print(name, bus1, bus2, units)

        dss.lines.next()

    dss.linecodes.first()
    linecode_map = {}
    for _ in range(dss.linecodes.count):
        linecode_map[dss.linecodes.name] = dss.linecodes 


if __name__ == "__main__":
    teste()
