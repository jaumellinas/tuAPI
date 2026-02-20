from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.db.database import get_db_connection

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

'''
Aquest arxiu fa referència a com s'autentiquen els usuaris de la plataforma (no els passatgers).
S'emprarà a l'hora de logar-se a eines d'administració de la plataforma, com a el backoffice
d'usuaris, a l'app o a la validadora (sempre amb el seu pertinent usuari).
'''

## Models interns

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class User(BaseModel):
    id: int
    email: str


class UserInDB(User):
    hashed_password: str


## Helpers

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


## Autenticació (dependències)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No s'han pogut validar les credencials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credential_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credential_exception

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM user WHERE email = %s",
                (token_data.email,)
            )
            row = cursor.fetchone()
        finally:
            cursor.close()

    if not row:
        raise credential_exception

    return User(id=row[0], email=token_data.email)


## Autenticació en si (amb correu i contrasenya)

async def authenticate_user(email: str, password: str) -> Optional[User]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, contrasenya FROM user WHERE email = %s",
                (email,)
            )
            row = cursor.fetchone()
        finally:
            cursor.close()

    if not row:
        return None
    if not verify_password(password, row[1]):
        return None

    return User(id=row[0], email=email)