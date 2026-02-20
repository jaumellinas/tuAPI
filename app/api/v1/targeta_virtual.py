from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import Response
from datetime import datetime, timedelta
import pymysql
import secrets
import hashlib
import io

import qrcode
from qrcode.image.pil import PilImage
from PIL import Image

from app.schemas.targeta_virtual import (
    TargetaVirtualResponse,
    VerifyQRRequest,
    VerifyQRResponse,
)
from app.db.database import get_db_connection
from app.core.security import User, get_current_user

router = APIRouter(
    prefix="/api/v1/targetes-virtuals",
    tags=["Targetes Virtuals"]
)

QR_VALIDESA_SEGONS = 60
QR_HASH_LENGTH     = 255

## Helpers
# Genera hash que servirà després per a crear el codi QR
def _generar_hash_qr() -> str:
    token = secrets.token_hex(128)
    salt = hashlib.sha256(token.encode()).hexdigest()
    combinat = token + salt
    return combinat[:QR_HASH_LENGTH]

# Estructura la resposta que es reb al cridar a una targeta virtual
def _row_to_response(row) -> TargetaVirtualResponse:
    return TargetaVirtualResponse(
        id=row[0],
        id_targeta_mare=row[1],
        qr=row[2],
        data_creacio=row[3],
        data_expiracio=row[4]
    )


## Endpoints
# i. Targetes virtuals (general)

# Si la petició és un POST, generam una nova targeta virtual
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TargetaVirtualResponse,
    name="Crear targeta virtual",
    summary="Genera una targeta virtual amb QR",
    description=(
        "Crea una targeta virtual associada a una targeta física. "
        "Genera un hash únic de X caràcters que s'emmagatzema al camp 'qr' i és vàlid durant Y segons. Només es pot crear una targeta virtual per a targetes en estat 'Activa'"
    )
)
# A l'hora de generar una targeta virtual es segueixen un parell de passes:
async def create_targeta_virtual(
    id_targeta_mare: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Es comprova que la targeta de la que depèn existeix i està activa
            cursor.execute(
                "SELECT id, estat FROM targeta WHERE id = %s",
                (id_targeta_mare,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Targeta no trobada"
                )
            if row[1] != "Activa":
                raise HTTPException(
                    status_code=400,
                    detail=f"No es pot generar una targeta virtual per a una targeta en estat '{row[1]}'"
                )

            # 2. Si la targeta mare existeix, totes les targetes virtuals anteriors de la mateixa targeta mare queden invalidades
            cursor.execute(
                "DELETE FROM targeta_virtual WHERE id_targeta_mare = %s",
                (id_targeta_mare,)
            )

            # 3. Es genera el hash del QR i es defineix la validesa del codi
            qr_hash = _generar_hash_qr()
            ara = datetime.utcnow()
            data_expiracio = ara + timedelta(seconds=QR_VALIDESA_SEGONS)

            # 4. Es crea la targeta virtual a la base de dades
            cursor.execute(
                """
                INSERT INTO targeta_virtual
                    (id_targeta_mare, qr, data_creacio, data_expiracio)
                VALUES (%s, %s, %s, %s)
                """,
                (id_targeta_mare, qr_hash, ara, data_expiracio)
            )
            conn.commit()

            targeta_virtual_id = cursor.lastrowid
            cursor.execute(
                "SELECT * FROM targeta_virtual WHERE id = %s",
                (targeta_virtual_id,)
            )
            return _row_to_response(cursor.fetchone())

        except HTTPException:
            raise
        except pymysql.Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error de base de dades: {str(e)}"
            )
        finally:
            cursor.close()

# ii. Targeta virtual concreta (QR)

# Feim una petició GET per a obtenir el codi QR d'una targeta
@router.get(
    "/{targeta_virtual_id}/qr",
    status_code=status.HTTP_200_OK,
    response_class=Response,
    responses={
        200: {
            "content": {"image/jpeg": {}},
            "description": "Imatge QR en format JPEG"
        }
    },
    name="Obtenir QR",
    summary="Retorna la imatge QR d'una targeta virtual",
    description=(
        "Genera i retorna la imatge QR associada al hash d'una targeta virtual en format JPEG. Retorna 410 Gone si el QR ha caducat"
    )
)
async def get_qr(
    targeta_virtual_id: int,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT qr, data_expiracio FROM targeta_virtual WHERE id = %s",
                (targeta_virtual_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Targeta virtual no trobada"
                )

            qr_hash, data_expiracio = row[0], row[1]

            # Si el codi QR ja ha caducat, retornem un status "410 Gone"
            if datetime.utcnow() > data_expiracio:
                raise HTTPException(
                    status_code=410,
                    detail="El QR ha caducat. Genera una nova targeta virtual"
                )

            # Si no ha caducat, rebem el hash i generam el QR
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=2,
                border=2,
            )
            qr.add_data(qr_hash)
            qr.make(fit=True)

            img: PilImage = qr.make_image(fill_color="black", back_color="white")

            # Assignam perfil de color al QR i l'escalam a 256x256 per a que càpiga a l'aplicació
            img_rgb = img.convert("RGB").resize((256, 256), Image.NEAREST)

            buffer = io.BytesIO()
            img_rgb.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)

            return Response(
                content=buffer.read(),
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f'inline; filename="qr_{targeta_virtual_id}.jpg"'
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generant el QR: {str(e)}"
            )
        finally:
            cursor.close()


# iii. Verificació del QR

# Feim una petició POST amb el hash d'un QR
@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    response_model=VerifyQRResponse,
    name="Verificar QR",
    summary="Valida un hash QR i retorna les dades del passatger i la targeta",
    description=(
        "Rep el hash extret d'un QR i comprova que existeix i no ha caducat. Si és vàlid, retorna les dades de la targeta física i del passatger associat. Un cop verificat, el QR s'invalida per evitar reutilitzacions"
    )
)

# Per a dur a terme dita verificació seguim un parell de passes:
async def verify_qr(
    body: VerifyQRRequest,
    current_user: User = Depends(get_current_user)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Buscam el hash del QR a la base de dades
            cursor.execute(
                """
                SELECT tv.id, tv.id_targeta_mare, tv.data_expiracio,
                       t.codi_targeta, t.perfil, t.saldo, t.estat,
                       p.id, p.nom, p.llinatge_1, p.llinatge_2, p.document, p.email
                FROM targeta_virtual tv
                INNER JOIN targeta   t ON t.id = tv.id_targeta_mare
                INNER JOIN passatger p ON p.id = t.id_passatger
                WHERE tv.qr = %s
                """,
                (body.qr,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="QR no valid"
                )

            (tv_id, id_targeta_mare, data_expiracio,
             codi_targeta, perfil, saldo, estat,
             passatger_id, nom, llinatge_1, llinatge_2,
             document, email) = row

            # 2. Comprovam si el hash està marcat com a caducat
            if datetime.utcnow() > data_expiracio:
                cursor.execute(
                    "DELETE FROM targeta_virtual WHERE id = %s", (tv_id,)
                )
                conn.commit()
                raise HTTPException(
                    status_code=410,
                    detail="El QR ha caducat. Cal generar una nova targeta virtual"
                )

            # 3. Si el codi no està caducat, comprovam que la targeta estigui marcada com a activa
            # En tot cas, l'aplicació mòbil (tuAPP) des d'un principi no permet generar un QR si la targeta no és vàlida
            if estat != "Activa":
                raise HTTPException(
                    status_code=400,
                    detail=f"La targeta associada a aquest QR no esta activa (estat: '{estat}')"
                )

            # 4. Si el codi passa totes les validacions i és vàlid, es marca com a usat i s'elimina de la base de dades
            cursor.execute(
                "DELETE FROM targeta_virtual WHERE id = %s", (tv_id,)
            )
            conn.commit()

            return VerifyQRResponse(
                valid=True,
                id_targeta_mare=id_targeta_mare,
                codi_targeta=codi_targeta,
                perfil=perfil,
                saldo=float(saldo),
                passatger_id=passatger_id,
                nom=nom,
                llinatge_1=llinatge_1,
                llinatge_2=llinatge_2,
                document=document,
                email=email,
            )

        except HTTPException:
            raise
        except pymysql.Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error de base de dades: {str(e)}"
            )
        finally:
            cursor.close()