from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
from enum import Enum


class PerfilEnum(str, Enum):
    infantil   = "Infantil"
    jove       = "Jove"
    general    = "General"
    pensionista = "Pensionista"
    altres     = "Altres"


class EstatEnum(str, Enum):
    activa      = "Activa"
    robada      = "Robada"
    caducada    = "Caducada"
    perduda     = "Perduda"
    desactivada = "Desactivada"
    altres      = "Altres"


class TargetaCreate(BaseModel):
    id_passatger: int
    perfil: PerfilEnum
    saldo: Decimal = Decimal("0.00")
    estat: EstatEnum = EstatEnum.activa

    @field_validator("saldo")
    @classmethod
    def saldo_no_negatiu(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El saldo no pot ser negatiu")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id_passatger": 1,
                "perfil": "General",
                "saldo": "10.00",
                "estat": "Activa"
            }
        }


class TargetaUpdate(BaseModel):
    saldo: Optional[Decimal] = None
    estat: Optional[EstatEnum] = None

    @field_validator("saldo")
    @classmethod
    def saldo_no_negatiu(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("El saldo no pot ser negatiu")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "saldo": "25.50",
                "estat": "Desactivada"
            }
        }


class TargetaResponse(BaseModel):
    id: int
    id_passatger: int
    codi_targeta: str
    perfil: PerfilEnum
    saldo: Decimal
    estat: EstatEnum