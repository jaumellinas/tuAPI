from pydantic import BaseModel
from typing import Optional


class PassatgerCreate(BaseModel):
    nom: str
    llinatge_1: str
    llinatge_2: Optional[str] = None
    document: str
    email: str
    sessio_iniciada: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "nom": "Maria",
                "llinatge_1": "Riera",
                "llinatge_2": "Rotger",
                "document": "19232030H",
                "email": "mariarierar@gmail.com",
                "sessio_iniciada": False
            }
        }


class PassatgerUpdate(BaseModel):
    nom: Optional[str] = None
    llinatge_1: Optional[str] = None
    llinatge_2: Optional[str] = None
    document: Optional[str] = None
    email: Optional[str] = None
    sessio_iniciada: Optional[bool] = None


class PassatgerResponse(BaseModel):
    id: int
    nom: str
    llinatge_1: str
    llinatge_2: Optional[str]
    document: str
    email: str
    sessio_iniciada: bool