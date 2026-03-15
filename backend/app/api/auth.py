"""Authentication and role/session endpoints for PRITHVINET."""

from fastapi import APIRouter, Depends

from app.models.schemas import AuthResponse, CitizenAccessRequest, LoginRequest
from app.services.auth import auth_service, get_current_user
from app.models.schemas import AuthenticatedUser

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    return await auth_service.login(payload)


@router.post("/citizen/continue", response_model=AuthResponse)
async def citizen_continue(payload: CitizenAccessRequest):
    return await auth_service.citizen_continue(payload)


@router.get("/me")
async def get_me(user: AuthenticatedUser = Depends(get_current_user)):
    return user


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(user: AuthenticatedUser = Depends(get_current_user)):
    return auth_service.refresh_session(user)


@router.post("/logout")
async def logout():
    return {"status": "ok"}
