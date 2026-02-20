from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TargetaVirtualResponse(BaseModel):
    id: int
    id_targeta_mare: int
    qr: str
    data_creacio: datetime
    data_expiracio: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "id_targeta_mare": 42,
                "qr": "a3f1c2d4e5b6...",
                "data_creacio": "2024-01-15T10:00:00",
                "data_expiracio": "2024-01-15T10:01:00"
            }
        }


class VerifyQRRequest(BaseModel):
    qr: str

    class Config:
        json_schema_extra = {
            "example": {
                "qr": "a3f1c2d4e5b6..."
            }
        }


class VerifyQRResponse(BaseModel):
    valid: bool
    id_targeta_mare: int
    codi_targeta: str
    perfil: str
    saldo: float
    passatger_id: int
    nom: str
    llinatge_1: str
    llinatge_2: Optional[str]
    document: str
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "id_targeta_mare": 42,
                "codi_targeta": "GE000384",
                "perfil": "General",
                "saldo": 12.50,
                "passatger_id": 7,
                "nom": "Joan",
                "llinatge_1": "Garcia",
                "llinatge_2": "Lopez",
                "document": "12345678A",
                "email": "joan.garcia@example.com"
            }
        }