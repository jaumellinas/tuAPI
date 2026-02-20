from fastapi import APIRouter
from app.api.v1 import auth, passatger, targeta, targeta_virtual, user

router = APIRouter()
router.include_router(auth.router)
router.include_router(passatger.router)
router.include_router(targeta.router)
router.include_router(targeta_virtual.router)
router.include_router(user.router)