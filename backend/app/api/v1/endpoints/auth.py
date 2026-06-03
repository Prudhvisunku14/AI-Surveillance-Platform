"""Auth endpoints — spec: JWT 1-hour expiry, roles: Operator/Analyst/Admin."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.core.security import authenticate_user, create_access_token, create_refresh_token, get_current_user
from app.schemas.schemas import TokenResponse, UserInfo
from app.db.database import get_db
from app.models.sql_models import AuditLog

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password")

    access_token = create_access_token(user["username"], user["role"])
    refresh_token = create_refresh_token(user["username"])

    # Audit log
    log = AuditLog(user_id=user["username"], action="login",
                   resource_type="auth", ip_address=request.client.host,
                   details={"role": user["role"]})
    db.add(log)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfo(username=current_user["username"],
                    role=current_user["role"],
                    full_name=current_user["full_name"])
