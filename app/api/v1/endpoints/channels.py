"""
Channels endpoints
"""
from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_channels(current_user: User = Depends(get_current_user)):
    """
    List channels
    """
    return {"message": "Channels endpoint - implementation pending"}
