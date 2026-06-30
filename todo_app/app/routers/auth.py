from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import User, RefreshToken
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing_user = await db.execute(select(User).where((User.email == data.email) | (User.username == data.username)))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where((User.email == data.email)))
    user: User | None = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )
    access_token = create_access_token(str(user.id))
    refresh_token, expires_at = create_refresh_token(str(user.id))
    db.add(RefreshToken(token=refresh_token, user_id=user.id, expires_at=expires_at))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None or token_type != "refresh":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == data.refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.expires_at < datetime.now(timezone.utc):
        raise credentials_exception
    db_token.is_revoked = True

    new_access = create_access_token(user_id)
    new_refresh, new_expires = create_refresh_token(user_id)

    db.add(RefreshToken(
        token=new_refresh,
        user_id=db_token.user_id,
        expires_at=new_expires,
    ))
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == data.refresh_token))
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.is_revoked = True
        await db.commit()