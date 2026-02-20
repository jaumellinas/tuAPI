from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List
import pymysql

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.db.database import get_db_connection
from app.core.security import User, get_current_user, get_password_hash

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Usuaris"]
)

## Helpers
def _row_to_response(row) -> UserResponse:
    return UserResponse(
        id=row[0],
        nom=row[1],
        llinatge_1=row[2],
        llinatge_2=row[3],
        email=row[4],
    )

## Endpoints
# i. Usuaris (general)

# Si la petició és POST, es crea un usuari nou
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    name="Crear usuari",
    summary="Registra un nou usuari autoritzat",
    description="Crea un nou usuari amb acces a la API. La contrasenya s'emmagatzema hashejada amb bcrypt"
)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM user WHERE email = %s",
                (user.email,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Ja existeix un usuari amb aquest correu electronic"
                )

            hashed_password = get_password_hash(user.password)

            cursor.execute(
                """
                INSERT INTO user (nom, llinatge_1, llinatge_2, email, contrasenya)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user.nom,
                    user.llinatge_1,
                    user.llinatge_2,
                    user.email,
                    hashed_password,
                )
            )
            conn.commit()

            user_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, nom, llinatge_1, llinatge_2, email FROM user WHERE id = %s",
                (user_id,)
            )
            return _row_to_response(cursor.fetchone())

        except HTTPException:
            raise
        except pymysql.IntegrityError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error d'integritat: {str(e)}"
            )
        finally:
            cursor.close()


# En canvi, si la petició és GET, es reb una llista amb tots els usuaris del sistema
@router.get(
    "",
    response_model=List[UserResponse],
    name="Llistar usuaris",
    summary="Retorna tots els usuaris autoritzats",
    description="Retorna la llista de tots els usuaris amb acces a la API. La contrasenya no s'inclou en la resposta"
)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(None, ge=1),
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if limit is None:
                cursor.execute(
                    "SELECT id, nom, llinatge_1, llinatge_2, email "
                    "FROM user ORDER BY id "
                    "LIMIT 18446744073709551615 OFFSET %s",
                    (skip,)
                )
            else:
                cursor.execute(
                    "SELECT id, nom, llinatge_1, llinatge_2, email "
                    "FROM user ORDER BY id "
                    "LIMIT %s OFFSET %s",
                    (limit, skip)
                )
            rows = cursor.fetchall()
            return [_row_to_response(row) for row in rows]
        finally:
            cursor.close()

# ii. Usuari actual

# Si es fa una petició GET, es retorna l'informació de l'usuari loguejat actualment
@router.get(
    "/me",
    response_model=UserResponse,
    name="Perfil propi",
    summary="Retorna les dades de l'usuari autenticat",
    description="Retorna la informacio de l'usuari que ha fet la peticio, identificat pel JWT"
)
async def get_me(current_user: User = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, nom, llinatge_1, llinatge_2, email FROM user WHERE id = %s",
                (current_user.id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Usuari no trobat")
            return _row_to_response(row)
        finally:
            cursor.close()


# iii. Usuari concret

# Si es fa una petició GET, es reb l'informació d'un usuari concret filtrat per ID
@router.get(
    "/{user_id}",
    response_model=UserResponse,
    name="Llistar usuari concret",
    summary="Retorna un usuari concret per ID",
    description="Retorna la informacio d'un usuari especific filtrant per ID"
)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, nom, llinatge_1, llinatge_2, email FROM user WHERE id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Usuari no trobat")
            return _row_to_response(row)
        finally:
            cursor.close()


# En canvi, si es fa una petició PUT, es poden modificar les dades d'un usuari específic
@router.put(
    "/{user_id}",
    response_model=UserResponse,
    name="Modificar usuari",
    summary="Modifica les dades d'un usuari concret",
    description="Actualitza un o mes camps d'un usuari existent. Si s'inclou una nova contrasenya, es torna a hashear"
)
async def update_user(
    user_id: int,
    user: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM user WHERE id = %s", (user_id,)
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Usuari no trobat")

            if user.email is not None:
                cursor.execute(
                    "SELECT id FROM user WHERE email = %s AND id != %s",
                    (user.email, user_id)
                )
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail="Ja existeix un altre usuari amb aquest correu electronic"
                    )

            updates = []
            values = []

            # Si hi ha canvis, es desen. Si no hi ha canvis, no es fa res
            if user.nom is not None:
                updates.append("nom = %s")
                values.append(user.nom)
            if user.llinatge_1 is not None:
                updates.append("llinatge_1 = %s")
                values.append(user.llinatge_1)
            if user.llinatge_2 is not None:
                updates.append("llinatge_2 = %s")
                values.append(user.llinatge_2)
            if user.email is not None:
                updates.append("email = %s")
                values.append(user.email)
            if user.password is not None:
                updates.append("contrasenya = %s")
                values.append(get_password_hash(user.password))

            if not updates:
                raise HTTPException(
                    status_code=400,
                    detail="No hi ha canvis a aplicar"
                )

            values.append(user_id)
            cursor.execute(
                f"UPDATE user SET {', '.join(updates)} WHERE id = %s",
                tuple(values)
            )
            conn.commit()

            cursor.execute(
                "SELECT id, nom, llinatge_1, llinatge_2, email FROM user WHERE id = %s",
                (user_id,)
            )
            return _row_to_response(cursor.fetchone())

        except HTTPException:
            raise
        finally:
            cursor.close()

# Finalment, si es fa una petició DELETE, s'elimina l'usuari del sistema (sempre i quan l'usuari que intenta fer l'esborrament no s'intenti eliminar a si mateix)
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Eliminar usuari",
    summary="Elimina un usuari concret",
    description="Elimina un usuari de la base de dades. Un usuari no es pot eliminar a si mateix"
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Un usuari no es pot eliminar a si mateix"
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM user WHERE id = %s", (user_id,)
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Usuari no trobat")

            cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
            conn.commit()
            return None
        except HTTPException:
            raise
        finally:
            cursor.close()