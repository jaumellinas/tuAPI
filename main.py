from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv
from app.api.v1 import router as v1_router

load_dotenv()

app = FastAPI(
    title="tuAPI",
    description="API RESTful per a manejar dades de passatgers, targetes i codis QR de l'infraestructura del Transport de les Illes Balears",
    version="1.0.0",
)
app.include_router(v1_router)

@app.get(
    "/",
    name="Endpoint inicial",
    summary="Informació de l'API",
    description="Retorna la informació bàsica de l'API, essent aquesta informació el nom, la versió i els endpoints disponibles",
    tags=["General"]
)
async def root():
    return {
        "message": "tuAPI v1.0.0",
        "endpoints": {
            "passatger": "/api/v1/passatger",
            "targeta": "/api/v1/targeta",
            "targeta_virtual": "/api/v1/targeta/virtual",
            "authentication": "/api/v1/auth",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("FASTAPI_PORT"))
    uvicorn.run(app, host="0.0.0.0", port=port)