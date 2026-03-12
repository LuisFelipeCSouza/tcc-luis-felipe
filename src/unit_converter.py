from typing import Dict

class UnitConverter:
    # Constantes para unidades
    UNITS_NONE   = 0
    UNITS_MILES  = 1
    UNITS_KFT    = 2
    UNITS_KM     = 3
    UNITS_M      = 4
    UNITS_FT     = 5
    UNITS_IN     = 6
    UNITS_CM     = 7
    UNITS_MM     = 8
    UNITS_MAXNUM = 9

    # Fatores de conversão para quilômetros
    CONVERSION_FACTORS: Dict[int, float] = {
        UNITS_NONE: 1.0,          # Sem unidade -> retorna o valor como está
        UNITS_MILES: 1.60934,     # 1 milha = 1.60934 km
        UNITS_KFT: 0.3048,        # 1000 pés = 304.8 m = 0.3048 km
        UNITS_KM: 1.0,            # já está em km
        UNITS_M: 0.001,           # 1 metro = 0.001 km
        UNITS_FT: 0.0003048,      # 1 pé = 0.3048 m = 0.0003048 km
        UNITS_IN: 0.0000254,      # 1 polegada = 0.0254 m = 0.0000254 km
        UNITS_CM: 0.00001,        # 1 cm = 0.01 m = 0.00001 km
        UNITS_MM: 0.000001        # 1 mm = 0.001 m = 0.000001 km
    }

    # Mapeamento de código → string
    UNIT_STRINGS: Dict[int, str] = {
        UNITS_NONE: "none",
        UNITS_MILES: "mi",
        UNITS_KFT: "kft",
        UNITS_KM: "km",
        UNITS_M: "m",
        UNITS_FT: "ft",
        UNITS_IN: "in",
        UNITS_CM: "cm",
        UNITS_MM: "mm"
    }

    @classmethod
    def to_km(cls, dist: float, unit: int) -> float:
        """
        Converte uma distância para quilômetros com base na unidade fornecida.
        """
        if unit not in cls.CONVERSION_FACTORS:
            raise ValueError(f"Unidade inválida: {unit}")
        return cls.CONVERSION_FACTORS[unit] * dist

    @classmethod
    def from_km(cls, dist_km: float, unit: int) -> float:
        """
        Converte uma distância em quilômetros para a unidade especificada.
        """
        if unit not in cls.CONVERSION_FACTORS:
            raise ValueError(f"Unidade inválida: {unit}")
        return dist_km / cls.CONVERSION_FACTORS[unit]

    @classmethod
    def unit_to_str(cls, unit: int) -> str:
        """
        Converte o código da unidade para sua representação em string.
        """
        if unit not in cls.UNIT_STRINGS:
            raise ValueError(f"Unidade inválida: {unit}")
        return cls.UNIT_STRINGS[unit]
