from pathlib import Path

# Raiz do projeto (um nível acima da pasta src)
PROJECT_ROOT = Path(__file__).parent.parent

# Caminho relativo para o arquivo DSS
DSS_PATH = PROJECT_ROOT / "data" / "34Bus" / "Run_IEEE34Mod1.dss"

# Pasta de saída
OUTPUT_DIR = PROJECT_ROOT / "output"

if __name__ == "__main__":
    print("DSS_PATH:", DSS_PATH)