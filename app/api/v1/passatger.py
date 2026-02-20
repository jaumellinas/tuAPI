from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
import pymysql
from app.schemas.passatger import (
    PassatgerCreate,
    PassatgerUpdate,
    PassatgerResponse,
)
from app.db.database import get_db_connection
from app.core.security import User, get_current_user

# Definim router

## Endpoints
# i. Passatgers (general)
router = APIRouter(
    prefix="/api/v1/passatgers",
    tags=["Passatgers"]
)


# Si la petició és POST, es crea un passatger
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PassatgerResponse,
    name="Crear passatger",
    summary="Crea un nou passatger",
    description="Registra un nou passatger a la base de dades amb les dades associades: nom, llinatges, document, e-mail i estat de sessió"
)
async def create_passatger(
    passatger: PassatgerCreate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                INSERT INTO passatger
                (nom, llinatge_1, llinatge_2, document, email, sessio_iniciada)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                passatger.nom,
                passatger.llinatge_1,
                passatger.llinatge_2,
                passatger.document,
                passatger.email,
                passatger.sessio_iniciada
            ))
            conn.commit()

            passatger_id = cursor.lastrowid
            cursor.execute(
                "SELECT * FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=500,
                    detail="Error al recuperar el passatger creat"
                )

            return PassatgerResponse(
                id=row[0],
                nom=row[1],
                llinatge_1=row[2],
                llinatge_2=row[3],
                document=row[4],
                email=row[5],
                sessio_iniciada=bool(row[6])
            )
        except pymysql.IntegrityError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error d'integritat: {str(e)}"
            )
        finally:
            cursor.close()

# En canvi, si la petició és GET, retorna tots els passatgers del sistema
@router.get(
    "",
    response_model=List[PassatgerResponse],
    name="Llistar passatgers",
    summary="Retorna tots els passatgers",
    description="Retorna un .json amb totes les dades dels passatgers registrats a la base de dades en aquell moment"
)
async def get_passatgers(
    skip: int = Query(0, ge=0),
    limit: int = Query(None, ge=1),
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if limit is None:
                cursor.execute(
                    "SELECT * FROM passatger ORDER BY id "
                    "LIMIT 18446744073709551615 OFFSET %s",
                    (skip,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM passatger ORDER BY id "
                    "LIMIT %s OFFSET %s",
                    (limit, skip)
                )
            rows = cursor.fetchall()

            passatgers = []
            for row in rows:
                passatgers.append(PassatgerResponse(
                    id=row[0],
                    nom=row[1],
                    llinatge_1=row[2],
                    llinatge_2=row[3],
                    document=row[4],
                    email=row[5],
                    sessio_iniciada=bool(row[6])
                ))

            return passatgers
        finally:
            cursor.close()

# ii. Passatger específic (filtra per ID)
# Si la petició és un GET, llista tots els detalls del passatger específic
@router.get(
    "/{passatger_id}",
    response_model=PassatgerResponse,
    name="Llistar passatger concret",
    summary="Llistar passatger concret per ID",
    description="Retorna tota la informació emmagatzemada sobre un passatger especific, filtrant-lo per ID"
)
async def get_passatger(
    passatger_id: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Passatger no trobat"
                )

            return PassatgerResponse(
                id=row[0],
                nom=row[1],
                llinatge_1=row[2],
                llinatge_2=row[3],
                document=row[4],
                email=row[5],
                sessio_iniciada=bool(row[6])
            )
        finally:
            cursor.close()

# Si la petició és un PUT, permet modificar els detalls del passatger
@router.put(
    "/{passatger_id}",
    response_model=PassatgerResponse,
    name="Modificar dades d'un passatger",
    summary="Modificar dades d'un passatger concret",
    description="Modifica un o més camps d'un passatger concret ja existent a traves del seu ID"
)
async def update_passatger(
    passatger_id: int,
    passatger: PassatgerUpdate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Passatger no trobat"
                )

            updates = []
            values = []

            # Si els valors canvie, actualitza'ls. Si estàn en blanc, no les canviis.
            if passatger.nom is not None:
                updates.append("nom = %s")
                values.append(passatger.nom)
            if passatger.llinatge_1 is not None:
                updates.append("llinatge_1 = %s")
                values.append(passatger.llinatge_1)
            if passatger.llinatge_2 is not None:
                updates.append("llinatge_2 = %s")
                values.append(passatger.llinatge_2)
            if passatger.document is not None:
                updates.append("document = %s")
                values.append(passatger.document)
            if passatger.email is not None:
                updates.append("email = %s")
                values.append(passatger.email)
            if passatger.sessio_iniciada is not None:
                updates.append("sessio_iniciada = %s")
                values.append(passatger.sessio_iniciada)

            if not updates:
                raise HTTPException(
                    status_code=400,
                    detail="No hi ha canvis a aplicar"
                )

            values.append(passatger_id)

            query = (
                f"UPDATE passatger SET {', '.join(updates)} "
                f"WHERE id = %s"
            )
            cursor.execute(query, tuple(values))
            conn.commit()

            cursor.execute(
                "SELECT * FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            row = cursor.fetchone()

            return PassatgerResponse(
                id=row[0],
                nom=row[1],
                llinatge_1=row[2],
                llinatge_2=row[3],
                document=row[4],
                email=row[5],
                sessio_iniciada=bool(row[6])
            )
        finally:
            cursor.close()

# Si la petició és un DELETE, elimina al passatger del sistema (sempre i quan mai hagi tengut una TU associada)
@router.delete(
    "/{passatger_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Eliminar passatger",
    summary="Eliminar passatger concret",
    description="Elimina un passatger de la base de dades. No es pot eliminar si té targetes associades"
)
async def delete_passatger(
    passatger_id: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Passatger no trobat"
                )

            cursor.execute(
                "DELETE FROM passatger WHERE id = %s",
                (passatger_id,)
            )
            conn.commit()

            return None
        except pymysql.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="No es pot eliminar un passatger amb targetes associades"
            )
        finally:
            cursor.close()