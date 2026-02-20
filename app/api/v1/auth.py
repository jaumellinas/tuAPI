from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
import pymysql
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.core.security import Token, create_access_token, authenticate_user
from app.db.database import get_db_connection

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticació"]
)

CODI_VALIDESA_MINUTS = 5

## Helpers
# Configura servidor SMTP amb els valors .env per a enviar correus amb codis 2FA
def _get_smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from": os.getenv("SMTP_FROM"),
        "starttls": os.getenv("SMTP_STARTTLS", "true").lower() == "true",
    }

# Envia codis 2FA a través de e-mail
def _enviar_email_2fa(destinatari: str, nom: str, codi: int) -> None:
    cfg = _get_smtp_config()

    if not cfg["user"] or not cfg["password"] or not cfg["from"]:
        raise HTTPException(
            status_code=500,
            detail="Configuracio SMTP incompleta. Comprova les variables d'entorn"
        )

    subject = "El teu codi de verificació - Targeta Única"
    body_text = (
        f"Hola, {nom}!\n\n"
        f"El teu codi de verificació és: {codi}\n\n"
        f"Aquest codi és vàlid durant {CODI_VALIDESA_MINUTS} minuts.\n\n"
        f"Si no has sol·licitat aquest codi, ignora aquest missatge."
    )
    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
        <h2 style="color: #2c3e50;">Verificació en 2 passos</h2>
        <p>Hola, <strong>{nom}</strong>!</p>
        <p>El teu codi de verificació és:</p>
        <div style="
          font-size: 36px;
          font-weight: bold;
          letter-spacing: 8px;
          text-align: center;
          padding: 16px;
          background: #f4f4f4;
          border-radius: 8px;
          margin: 16px 0;
        ">{codi}</div>
        <p>Aquest codi és vàlid durant <strong>{CODI_VALIDESA_MINUTS} minuts</strong>.</p>
        <hr style="border: none; border-top: 1px solid #eee;" />
        <p style="color: #999; font-size: 12px;">
          Has rebut aquest missatge perquè has intentat accedir a l'aplicació de Targeta Única del Transport de les Illes Balears. Si no has sol·licitat aquest codi, ignora aquest missatge.
        </p>
      </body>
    </html>
    """

    # Codi adaptat des de Java (Pràctiques UD4 PSP amb Carlos Sola)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = destinatari
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            if cfg["starttls"]:
                server.starttls()
                server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from"], destinatari, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=500,
            detail="Error d'autenticació SMTP. Comprova SMTP_USER i SMTP_PASSWORD al fitxer .env"
        )
    except smtplib.SMTPException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar correu: {str(e)}"
        )



## Endpoints
# i. Login
@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    name="Iniciar sessió",
    summary="Sol·licita un codi de verificació 2FA",
    description=(
        "Rep el document d'identitat d'un passatger, genera un codi numeric de 6 digits valid durant X minuts i l'envia al correu electronic associat al registre"
    )
)
# A l'hora de fer login, es segueixen un parell de passes:
async def login(body: LoginRequest):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Es comprova que el passatger existeix
            cursor.execute(
                "SELECT id, nom, email FROM passatger WHERE document = %s",
                (body.document,)
            )
            row = cursor.fetchone()
            if not row:
                # Si no es troba el document a la base de dades, avisa amb error
                raise HTTPException(
                    status_code=404,
                    detail="No s'ha trobat cap compte associat a aquest document"
                )

            passatger_id, nom, email = row[0], row[1], row[2]

            # 2. Si el passatger existeix, s'invaliden els codis 2FA previs que hagi pogut rebre l'usuari
            # Aquesta lògica s'extén a l'endpoint '/verify'
            cursor.execute(
                "DELETE FROM `2fa` WHERE id_passatger = %s",
                (passatger_id,)
            )

            # 3. Amb els codis anteriors invalidats, es genera un codi nou que serà vàlid durant X minuts
            codi = random.randint(100000, 999999)
            ara = datetime.utcnow()
            data_expiracio = ara + timedelta(minutes=CODI_VALIDESA_MINUTS)

            # 4. S'emmagatzema el codi generat a la base de dades de forma temporal per a poder comprovar-ho amb el valor que introdueix l'usuari
            cursor.execute(
                """
                INSERT INTO `2fa` (id_passatger, codi, data_creacio, data_expiracio)
                VALUES (%s, %s, %s, %s)
                """,
                (passatger_id, codi, ara, data_expiracio)
            )
            conn.commit()

            # 5. Finalment, el codi s'envia al correu de l'usuari
            _enviar_email_2fa(email, nom, codi)

            return LoginResponse(
                detail="Codi de verificacio enviat al correu electrònic"
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


# ii. Verificació 2FA
@router.post(
    "/verify",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    name="Verificar codi 2FA",
    summary="Valida el codi 2FA i retorna un token d'accés",
    description=(
        "Rep el document i el codi de 6 digits enviat per correu. Si el codi és correcte i no ha caducat, marca el passatger com a sessio_iniciada i retorna un JWT d'accés"
    )
)
# A l'hora de fer login, es segueixen un parell de passes:
async def verify(body: VerifyRequest):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. S'obté el passatger
            cursor.execute(
                "SELECT id FROM passatger WHERE document = %s",
                (body.document,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=401,
                    detail="Document o codi incorrectes"
                )

            passatger_id = row[0]

            # 2. Es cerca un codi que no ha caducat i que estigui associat a aquest passatger
            cursor.execute(
                """
                SELECT id, codi, data_expiracio
                FROM `2fa`
                WHERE id_passatger = %s
                ORDER BY data_creacio DESC
                LIMIT 1
                """,
                (passatger_id,)
            )
            fila_2fa = cursor.fetchone()

            if not fila_2fa:
                raise HTTPException(
                    status_code=401,
                    detail="No hi ha cap codi de verificació pendent. Sol·licita'n un de nou"
                )

            id_2fa, codi_bd, data_expiracio = fila_2fa[0], fila_2fa[1], fila_2fa[2]

            # 3. Es comprova la caducitat del codi
            if datetime.utcnow() > data_expiracio:
                cursor.execute("DELETE FROM `2fa` WHERE id = %s", (id_2fa,))
                conn.commit()
                raise HTTPException(
                    status_code=401,
                    detail="El codi ha caducat. Sol·licita'n un de nou"
                )

            # 4. Es comprova que el codi que ha introduit l'usuari coincideix amb el de la base de dades
            if int(codi_bd) != body.codi:
                raise HTTPException(
                    status_code=401,
                    detail="Document o codi incorrectes"
                )

            # 5. Si el codi és correcte, s'esborra i es marca sessio_iniciada = True
            cursor.execute("DELETE FROM `2fa` WHERE id = %s", (id_2fa,))
            cursor.execute(
                "UPDATE passatger SET sessio_iniciada = TRUE WHERE id = %s",
                (passatger_id,)
            )
            conn.commit()

            # 6. Es genera i es retorna el JWT
            access_token = create_access_token(data={"sub": str(passatger_id)})

            return VerifyResponse(access_token=access_token)

        except HTTPException:
            raise
        except pymysql.Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error de base de dades: {str(e)}"
            )
        finally:
            cursor.close()


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    name="Obtenir token",
    summary="Login d'usuari de la API amb username i password",
    description=(
        "Endpoint OAuth2 estàndard. Rep username i password en format form-data i retorna un JWT Bearer si les credencials són correctes. Aquest token és necessari per accedir a la resta d'endpoints"
    )
)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm usa 'username' com a camp fix,
    # pero en aquesta API el login es fa amb email
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasenya incorrectes.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")