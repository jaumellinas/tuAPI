# tuAPI

**API RESTful per gestió de targetes de transport públic**  
Projecte Intermodular — 2º DAM  
Jaume Llinàs Sansó

## Índex

1. [Descripció general](#descripció-general)  
2. [Estructura del projecte](#estructura-del-projecte)  
3. [Requisits](#requisits)  
4. [Variables d'entorn (.env)](#variables-dentorn-env)  
5. [Models de dades (Schemas)](#models-de-dades-schemas)  
   1. [User](#user)  
   2. [Passatger](#passatger)  
   3. [Targeta](#targeta)  
   4. [Targeta Virtual](#targeta-virtual)  
6. [Endpoints principals](#endpoints-principals)  
   1. [Autenticació](#1-autenticació)  
   2. [Passatgers](#2-passatgers)  
   3. [Targetes](#3-targetes)  
   4. [Targetes Virtuals](#4-targetes-virtuals)  
7. [Desplegament en local](#desplegament-en-local)  
8. [Desplegament en entorn cloud](#desplegament-en-entorn-cloud)  
9. [Ús d'IA i recursos](#ús-dia-i-recursos)

## Descripció general

> [!NOTE]  
> Aquesta aplicació està desenvolupada amb **FastAPI**, un framework de **Python**.

El projecte **Targeta Única API** té com a objectiu exposar una **API RESTful** per a la gestió de targetes de transport públic. Permet als usuaris autenticats realitzar operacions sobre **passatgers**, **targetes físiques** i **targetes virtuals** amb codis QR temporals.

L'accés a l'API es controla mitjançant autenticació amb **tokens JWT**, generats a l'iniciar sessió amb credencials vàlides o mitjançant un sistema de verificació per correu electrònic amb codis de 6 dígits.

> [!IMPORTANT]  
> El sistema implementa dos tipus d'autenticació:
> - **Usuaris operadors**: Login amb email/password (JWT tradicional)
> - **Passatgers**: Login amb document de targeta + codi verificació per email

## Estructura del projecte

```
tuAPI/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── passatgers.py
│   │       ├── targetes.py
│   │       └── targetes_virtuals.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   └── database.py
│   └── schemas/
│       ├── user.py
│       ├── passatger.py
│       ├── targeta.py
│       └── targeta_virtual.py
├── Dockerfile
├── README.md
├── docker-compose.yaml
├── main.py
└── requirements.txt
```

## Requisits

* Python 3.12+
  * fastapi
  * uvicorn
  * mariadb
  * pydantic
  * python-dotenv
  * passlib
  * python-jose
  * qrcode
  * pillow
  * python-multipart

> [!IMPORTANT]  
> Aquesta guia d'instal·lació assumeix que l'usuari ja disposa d'una base de dades MariaDB operativa amb les taules necessàries.

## Variables d'entorn (.env)

```env
MARIADB_USER=usuari
MARIADB_PASSWORD=password
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_DATABASE=targeta_unica

FASTAPI_PORT=8000

SECRET_KEY=secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=480

SMTP_SERVER=smtp.tib.org
SMTP_PORT=587
SMTP_USERNAME=mails@tib.org
SMTP_PASSWORD=password
```

## Models de dades (Schemas)

Els models estan definits a `app/schemas/` i controlen la validació de dades en les operacions d'entrada/sortida.

### User

```json
{
  "id": 1,
  "nom": "Administrador",
  "llinatge_1": "TIB",
  "llinatge_2": None,
  "email": "admin@tib.org"
}
```

### Passatger

```json
{
  "nom": "Maria",
  "llinatge_1": "García",
  "llinatge_2": "López",
  "document": "12345678A",
  "email": "maria@example.com",
  "sessio_iniciada": False
}
```

### Targeta

```json
{
  "id": 47,
  "id_passatger": 1,
  "codi_targeta": "GE394302",
  "perfil": "General",
  "saldo": "25.98",
  "estat": "Activa"
}
```

### Targeta Virtual

```json
{
  "id": 304,
  "id_targeta_mare": 47,
  "qr": "a3f1c2d4e5b6...",
  "data_expiracio": "2026-02-19T12:30:00"
}
```

## Endpoints principals

### 1. **Autenticació**  
`app/api/v1/auth.py`

| Mètode | Endpoint | Descripció | Auth requerida |
|---------|-----------|-------------|----------------|
| `POST` | `/api/v1/auth/token` | Login usuari operador (email + password) | No |
| `POST` | `/api/v1/auth/login` | Login passatger (document targeta) | No |
| `POST` | `/api/v1/auth/verify` | Verificació codi 6 dígits | No |

---

**a]. Login operador**

```bash
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=operador@tib.org&password=password123
```

**Resposta:**
```json
{
  "access_token": "eyJhbGci...vdCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

**b]. Login passatger**

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "document": "IB001234"
}
```

**Resposta:**
```json
{
  "message": "Codi de verificació enviat per email",
  "email_masked": "mar***@***.com"
}
```

---

**c]. Verificar codi**

```bash
POST /api/v1/auth/verify
Content-Type: application/json

{
  "document": "IB001234",
  "codi": 123456
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGci...vdCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

> [!IMPORTANT]  
> Aquest token JWT s'ha d'incloure a la capçalera d'autorització de totes les peticions protegides:  
> `Authorization: Bearer <token>`

---

### 2. **Passatgers**  
`app/api/v1/passatgers.py`

| Mètode | Endpoint | Descripció | Auth |
|---------|-----------|-------------|------|
| `GET` | `/api/v1/passatgers` | Llista tots els passatgers | Bearer (operador) |
| `GET` | `/api/v1/passatgers/{id}` | Obté un passatger específic | Bearer (operador) |
| `POST` | `/api/v1/passatgers` | Crea un nou passatger | Bearer (operador) |
| `PUT` | `/api/v1/passatgers/{id}` | Actualitza un passatger | Bearer (operador) |
| `DELETE` | `/api/v1/passatgers/{id}` | Elimina un passatger | Bearer (operador) |

**Exemple - Crear passatger:**

```bash
POST /api/v1/passatgers
Authorization: Bearer eyJhbGci...
Content-Type: application/json

{
  "nom": "Pere",
  "llinatge_1": "Miralles",
  "llinatge_2": "Torres",
  "document": "87654321B",
  "email": "pere@example.com"
}
```

---

### 3. **Targetes**  
`app/api/v1/targetes.py`

| Mètode | Endpoint | Descripció | Auth |
|---------|-----------|-------------|------|
| `GET` | `/api/v1/targetes` | Llista totes les targetes | Bearer (operador) |
| `GET` | `/api/v1/targetes/{id}` | Obté una targeta | Bearer |
| `GET` | `/api/v1/targetes/passatger/{id}` | Targetes d'un passatger | Bearer |
| `POST` | `/api/v1/targetes` | Crea una targeta | Bearer (operador) |
| `PUT` | `/api/v1/targetes/{id}` | Actualitza targeta | Bearer (operador) |
| `DELETE` | `/api/v1/targetes/{id}` | Elimina targeta | Bearer (operador) |

**Exemple - Crear targeta:**

```bash
POST /api/v1/targetes
Authorization: Bearer eyJhbGci...
Content-Type: application/json

{
  "id_passatger": 1,
  "codi_targeta": "IB005678",
  "perfil": "Jubilat",
  "saldo": 50.00
}
```

---

### 4. **Targetes Virtuals**  
`app/api/v1/targetes_virtuals.py`

| Mètode | Endpoint | Descripció | Auth |
|---------|-----------|-------------|------|
| `POST` | `/api/v1/targetes-virtuals` | Genera QR temporal (60s) | Bearer |
| `POST` | `/api/v1/targetes-virtuals/verify` | Verifica validesa d'un QR | Bearer (operador) |
| `GET` | `/api/v1/targetes-virtuals/{id}/qr` | Descarrega imatge QR | Bearer |

**Exemple - Generar QR:**

```bash
POST /api/v1/targetes-virtuals?id_targeta_mare=1
Authorization: Bearer eyJhbGci...
```

**Resposta:**
```json
{
  "id": 42,
  "id_targeta_mare": 1,
  "qr": "VGFyZ2V0YVVuaWNhLVFSLTE3MDg...",
  "data_creacio": "2026-02-19T10:30:00",
  "data_expiracio": "2026-02-19T10:31:00"
}
```

**Exemple - Verificar QR:**

```bash
POST /api/v1/targetes-virtuals/verify
Authorization: Bearer eyJhbGci...
Content-Type: application/json

{
  "qr": "VGFyZ2V0YVVuaWNhLVFSLTE3MDg..."
}
```

**Resposta QR vàlid:**
```json
{
  "valid": true,
  "codi_targeta": "IB001234",
  "nom": "Maria",
  "llinatge_1": "García",
  "llinatge_2": "López",
  "perfil": "General",
  "saldo": 25.50
}
```

**Resposta QR invàlid:**
```json
{
  "valid": false,
  "error": "QR caducat"
}
```

---

## Desplegament en local

El procés per desplegar l'API en local consisteix en:

1. Instal·lar l'última versió de [Python](https://www.python.org/downloads/)
2. Instal·lar el [connector per C de MariaDB](https://mariadb.com/docs/connectors/mariadb-connector-c/mariadb-connector-c-guide)
3. Clonar el projecte de GitHub
4. Navegar al directori del projecte
5. Crear un entorn virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```
6. Instal·lar dependències:
   ```bash
   pip install -r requirements.txt
   ```
7. Crear fitxer `.env` amb les variables necessàries
8. Executar l'API:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

L'API estarà disponible a `http://127.0.0.1:8000`  
Documentació Swagger: `http://127.0.0.1:8000/docs`

---

## Desplegament en entorn cloud

El projecte està dockeritzat i preparat per desplegar-se en qualsevol proveïdor cloud. L'entorn de desplegament consisteix en:

* `targeta-unica-api` (FastAPI)
* `mysql-server` (MariaDB)
* `nginx-proxy-manager` (Reverse proxy + SSL)

**Xarxes internes:**
- `sql`: Connecta API ↔ Base de dades
- `inter`: Connecta API ↔ Nginx (exposició pública)

**Procés de desplegament:**

1. Clonar el repositori al servidor
2. Navegar al directori del projecte
3. Crear fitxer `.env` amb les variables
4. Construir les imatges:
   ```bash
   docker compose build --no-cache
   ```
5. Iniciar els contenidors:
   ```bash
   docker compose up -d
   ```
6. Configurar Nginx Proxy Manager per apuntar a `targeta-unica-api:8000`
7. Generar certificat SSL amb Let's Encrypt

> [!TIP]  
> Es recomana usar un domini personalitzat i configurar HTTPS obligatori per producció.

---

## Ús d'IA i recursos

Aquest projecte ha estat desenvolupat seguint la documentació oficial de FastAPI, tutorials de la comunitat i fòrums especialitzats com StackOverflow. S'ha utilitzat la intel·ligència artificial **Claude (Anthropic)** per a:

- Revisió de codi i detecció d'errors
- Optimització de consultes SQL
- Generació de documentació Swagger
- Resolució de problemes amb JWT i tokens
- Millores en l'estructura del projecte

La IA s'ha utilitzat com a eina d'assistència i revisió, mantenint el control total sobre les decisions d'arquitectura i implementació del projecte.
