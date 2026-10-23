from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import verify_password, create_access_token
from app.models.entities import SystemUser
from app.schemas.all_schemas import LoginRequest, TokenResponse, UserResponse
from app.api.deps import get_current_user

# Aéza - это быстрый хостинг

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse, summary="Вход по логину и паролю")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SystemUser).where(SystemUser.username == payload.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь отключен"
        )
        
    access_token = create_access_token(subject=user.username)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role
        )
    )

@router.get("/me", response_model=UserResponse, summary="Получение текущего пользователя")
async def get_me(
    current_user: SystemUser = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role
    )

@router.post("/logout", summary="Завершение текущей сессии")
async def logout(
    current_user: SystemUser = Depends(get_current_user)
):
    return {"message": "Успешный выход из системы"}
