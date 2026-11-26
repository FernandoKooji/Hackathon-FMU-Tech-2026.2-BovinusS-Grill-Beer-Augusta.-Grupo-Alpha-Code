from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.constants import (
    BALANCA_ID_MAX,
    BALANCA_ID_MIN,
    CAPACIDADE_PADRAO_G,
    ORIGEM_PADRAO,
    ORIGENS_VALIDAS,
    PESO_MINIMO_G,
)


class LeituraRequest(BaseModel):
    balanca_id: int = Field(ge=BALANCA_ID_MIN, le=BALANCA_ID_MAX, strict=True)
    prato: str
    peso_atual_g: int = Field(ge=PESO_MINIMO_G, strict=True)
    capacidade_max_g: int = Field(default=CAPACIDADE_PADRAO_G, gt=0, strict=True)
    origem: str = ORIGEM_PADRAO
    criado_em: datetime | None = None

    @field_validator("prato")
    @classmethod
    def validar_prato(cls, valor: str) -> str:
        prato = valor.strip()
        if not prato:
            raise ValueError("O nome do prato não pode estar vazio.")
        return prato

    @field_validator("origem")
    @classmethod
    def validar_origem(cls, valor: str) -> str:
        if valor not in ORIGENS_VALIDAS:
            raise ValueError(f"A origem deve ser uma destas: {', '.join(ORIGENS_VALIDAS)}.")
        return valor

    @field_validator("criado_em", mode="before")
    @classmethod
    def normalizar_criado_em(cls, valor: object) -> datetime | None:
        if valor is None:
            return None

        if isinstance(valor, str):
            try:
                valor = datetime.fromisoformat(valor)
            except ValueError as erro:
                raise ValueError("criado_em deve ser uma data e hora em formato ISO 8601.") from erro

        if not isinstance(valor, datetime) or valor.utcoffset() is None:
            raise ValueError("criado_em deve informar uma data e hora com fuso horário.")

        try:
            criado_em = valor.astimezone(timezone.utc)
        except OverflowError as erro:
            raise ValueError("criado_em está fora do intervalo representável em UTC.") from erro

        if criado_em > datetime.now(timezone.utc):
            raise ValueError("criado_em não pode estar no futuro.")
        return criado_em

    @model_validator(mode="after")
    def validar_peso_e_capacidade(self) -> "LeituraRequest":
        if self.peso_atual_g > self.capacidade_max_g:
            raise ValueError("peso_atual_g não pode ultrapassar capacidade_max_g.")
        return self


class LeituraResponse(BaseModel):
    id: int
    balanca_id: int
    prato: str
    peso_atual_g: int
    capacidade_max_g: int
    percentual: float
    consumo_g: int
    status: str
    novo_alerta: int
    origem: str
    criado_em: datetime


class EstadoBalancaResponse(BaseModel):
    balanca_id: int
    prato: str
    peso_atual_g: int
    capacidade_max_g: int
    percentual: float
    status: str


class EstadoAtualResponse(BaseModel):
    balancas: list[EstadoBalancaResponse]
    total_monitoradas: int
    total_acabando: int
