from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List
import pymysql
import random
from app.schemas.targeta import TargetaCreate, TargetaResponse, TargetaUpdate
from app.db.database import get_db_connection
from app.core.security import User, get_current_user

# Definim router

## Endpoints
# i. Targetes (general)
router = APIRouter(
    prefix="/api/v1/targetes",
    tags=["Targetes"]
)

# Definim diccionari amb prefixes de targetes
PERFIL_PREFIX = {
    "General": "GE",
    "Jove": "JV",
    "Infantil": "IN",
    "Pensionista": "PE",
    "Altres": "AT",
}

MAX_INTENTS_CODI = 10

## Helpers
# Genera un codi de targeta únic entre 000001 - 999999
def _generar_codi_targeta(perfil: str, cursor) -> str:
    prefix = PERFIL_PREFIX[perfil]
    for _ in range(MAX_INTENTS_CODI):
        numero = random.randint(1, 999999)
        codi = f"{prefix}{numero:06d}"
        cursor.execute(
            "SELECT id FROM targeta WHERE codi_targeta = %s",
            (codi,)
        )
        if not cursor.fetchone():
            return codi
    raise HTTPException(
        status_code=500,
        detail="No s'ha pogut generar un codi de targeta únic. Torna-ho a intentar"
    )

# Si la petició que feim és un POST, cream una targeta nova
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TargetaResponse,
    name="Crear targeta",
    summary="Registra una nova targeta",
    description=(
        "Crea una nova targeta associada a un passatger. El codi de targeta es genera automàticament amb el format AABBBBBB, on AA es el prefix del perfil (GE, JV, IN, PE, AT) i BBBBBB és un número aleatori unic entre 000001 i 999999"
    )
)
async def create_targeta(
    targeta: TargetaCreate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            codi_targeta = _generar_codi_targeta(targeta.perfil, cursor)

            query = """
                INSERT INTO targeta
                (id_passatger, codi_targeta, perfil, saldo, estat)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                targeta.id_passatger,
                codi_targeta,
                targeta.perfil,
                targeta.saldo,
                targeta.estat
            ))
            conn.commit()

            targeta_id = cursor.lastrowid
            cursor.execute(
                "SELECT * FROM targeta WHERE id = %s",
                (targeta_id,)
            )
            row = cursor.fetchone()

            return TargetaResponse(
                id=row[0],
                id_passatger=row[1],
                codi_targeta=row[2],
                perfil=row[3],
                saldo=row[4],
                estat=row[5]
            )
        except pymysql.IntegrityError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error d'integritat: {str(e)}"
            )
        finally:
            cursor.close()

# En canvi, si la petició que feim és un GET, rebem una llista amb totes les targetes del sistema
@router.get(
    "",
    response_model=List[TargetaResponse],
    name="Llistar targetes",
    summary="Retorna totes les targetes",
    description="Retorna una llista amb totes les targetes que existeixen a la base de dades"
)
async def get_targetes(
    skip: int = Query(0, ge=0),
    limit: int = Query(None, ge=1),
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if limit is None:
                cursor.execute(
                    "SELECT * FROM targeta ORDER BY id "
                    "LIMIT 18446744073709551615 OFFSET %s",
                    (skip,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM targeta ORDER BY id "
                    "LIMIT %s OFFSET %s",
                    (limit, skip)
                )
            rows = cursor.fetchall()

            targetes = []
            for row in rows:
                targetes.append(TargetaResponse(
                    id=row[0],
                    id_passatger=row[1],
                    codi_targeta=row[2],
                    perfil=row[3],
                    saldo=row[4],
                    estat=row[5]
                ))

            return targetes
        finally:
            cursor.close()

# ii. Targeta específica (filtrada per ID)
# Si la petició que feim és un GET, obtenim tots els detalls d'una targeta específica
@router.get(
    "/{targeta_id}",
    response_model=TargetaResponse,
    name="Llistar targeta concreta",
    summary="Llistar targeta concreta per ID",
    description="Retorna informacio detallada sobre una targeta especifica, filtrant-la per ID"
)
async def get_targeta(
    targeta_id: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM targeta WHERE id = %s",
                (targeta_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Targeta no trobada"
                )

            return TargetaResponse(
                id=row[0],
                id_passatger=row[1],
                codi_targeta=row[2],
                perfil=row[3],
                saldo=row[4],
                estat=row[5]
            )
        finally:
            cursor.close()

# En canvi, si la petició que feim és un PUT, podem modificar una targeta ja existent
@router.put(
    "/{targeta_id}",
    response_model=TargetaResponse,
    name="Modificar targeta",
    summary="Modifica el saldo o l'estat d'una targeta concreta",
    description=("Actualitza el saldo i/o l'estat d'una targeta. No es pot modificar una targeta 'Caducada' o 'Robada'. Una targeta no pot passar a 'Activa' des de 'Robada' o 'Caducada'"
    )
)
async def update_targeta(
    targeta_id: int,
    body: TargetaUpdate,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, estat FROM targeta WHERE id = %s",
                (targeta_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Targeta no trobada"
                )

            estat_actual = row[1]
            ESTATS_BLOQUEJATS = {"Caducada", "Robada"}

            # Si la targeta ja està bloquetjada, impedeix la modificació
            if estat_actual in ESTATS_BLOQUEJATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"No es pot modificar una targeta en estat '{estat_actual}'"
                )

            # Si la targeta ja està bloquetjada i s'intenta marcar com a activa, impedeix la modificació
            if body.estat == "Activa" and estat_actual in ESTATS_BLOQUEJATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"No es pot reactivar una targeta en estat '{estat_actual}'"
                )

            updates = []
            values = []

            if body.saldo is not None:
                if body.saldo < 0:
                    raise HTTPException(
                        status_code=400,
                        detail="El saldo no pot ser negatiu"
                    )
                updates.append("saldo = %s")
                values.append(body.saldo)

            if body.estat is not None:
                updates.append("estat = %s")
                values.append(body.estat)

            if not updates:
                raise HTTPException(
                    status_code=400,
                    detail="No hi ha canvis a aplicar"
                )

            values.append(targeta_id)
            query = (
                f"UPDATE targeta SET {', '.join(updates)} "
                f"WHERE id = %s"
            )
            cursor.execute(query, tuple(values))
            conn.commit()

            cursor.execute(
                "SELECT * FROM targeta WHERE id = %s",
                (targeta_id,)
            )
            row = cursor.fetchone()

            return TargetaResponse(
                id=row[0],
                id_passatger=row[1],
                codi_targeta=row[2],
                perfil=row[3],
                saldo=row[4],
                estat=row[5]
            )
        finally:
            cursor.close()

# iii. Targetes associades a un passatger concret
# Si la petició que feim és un GET, rebem totes les targetes que estàn associades a un passatger concret
@router.get(
    "/passatger/{passatger_id}",
    response_model=List[TargetaResponse],
    name="Obtenir targetes per passatger",
    summary="Retorna totes les targetes d'un passatger concret",
    description="Retorna totes les targetes associades a un passatger especific, filtrant el passatger per ID"
)
async def get_targetes_passatger(
    passatger_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
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
                "SELECT * FROM targeta WHERE id_passatger = %s "
                "ORDER BY id LIMIT %s OFFSET %s",
                (passatger_id, limit, skip)
            )
            rows = cursor.fetchall()

            targetes = []
            for row in rows:
                targetes.append(TargetaResponse(
                    id=row[0],
                    id_passatger=row[1],
                    codi_targeta=row[2],
                    perfil=row[3],
                    saldo=row[4],
                    estat=row[5]
                ))

            return targetes
        finally:
            cursor.close()