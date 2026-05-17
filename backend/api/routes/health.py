from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/readiness")
async def readiness():
    # TODO: check DB / Redis connectivity when added
    return {"status": "ready"}
