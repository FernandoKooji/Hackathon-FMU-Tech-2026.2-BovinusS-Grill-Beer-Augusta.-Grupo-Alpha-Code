from datetime import date

from pydantic import BaseModel


class PeriodoRelatorio(BaseModel):
    inicio: date
    fim: date


class ConsumoDiario(BaseModel):
    data: date
    consumo_g: int


class PratoRelatorio(BaseModel):
    prato: str
    consumo_g: int
    consumo_kg: float
    total_alertas: int
    consumo_diario: list[ConsumoDiario]


class RelatorioSemanalResponse(BaseModel):
    periodo: PeriodoRelatorio
    consumo_total_g: int
    consumo_total_kg: float
    total_alertas: int
    pratos: list[PratoRelatorio]
