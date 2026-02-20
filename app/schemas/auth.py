from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    document: str

    class Config:
        json_schema_extra = {
            "example": {
                "document": "12345678A"
            }
        }


class LoginResponse(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Codi de verificacio enviat al correu electronic"
            }
        }


class VerifyRequest(BaseModel):
    document: str
    codi: int

    @field_validator("codi")
    @classmethod
    def codi_sis_digits(cls, v: int) -> int:
        if not (100000 <= v <= 999999):
            raise ValueError("El codi ha de ser un numero de 6 digits entre 100000 i 999999")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "document": "12345678A",
                "codi": 482910
            }
        }


class VerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }