"""Health Check Endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["Health & Status"])


@router.get("/healthz")

def health_check():
    """System health check endpoint."""
    return {"status": "healthy"}
