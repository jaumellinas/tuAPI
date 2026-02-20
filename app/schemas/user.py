from pydantic import BaseModel, field_validator
from typing import Optional
import re

class UserCreate(BaseModel):
    nom: str
    llinatge_1: str
    llinatge_2: Optional[str] = None
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_prou_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contrasenya ha de tenir com a minim 8 caracters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contrasenya ha de contenir com a minim una lletra majuscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("La contrasenya ha de contenir com a minim un numero")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nom": "Admin",
                "llinatge_1": "Sistema",
                "llinatge_2": None,
                "email": "admin@targeta-unica.com",
                "password": "Contrasenya1"
            }
        }


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    llinatge_1: Optional[str] = None
    llinatge_2: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_prou_segura(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("La contrasenya ha de tenir com a minim 8 caracters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contrasenya ha de contenir com a minim una lletra majuscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("La contrasenya ha de contenir com a minim un numero")
        return v


class UserResponse(BaseModel):
    id: int
    nom: str
    llinatge_1: str
    llinatge_2: Optional[str]
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nom": "Admin",
                "llinatge_1": "Sistema",
                "llinatge_2": None,
                "email": "admin@targeta-unica.com"
            }
        }