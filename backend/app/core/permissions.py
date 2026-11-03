from typing import Annotated, Sequence, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import oauth2_scheme, decode_access_token
from app.models.user import User, UserRole

async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    # If a valid Bearer token is provided, validate it
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user:
                return user

    # Single-User Admin Mode:
    # Per user instruction: "we will design everything for admin for now ... no other user .. in future we will role based access with customized permissions"
    admin_query = select(User).where(User.email == "admin@company.com")
    result = await db.execute(admin_query)
    admin_user = result.scalar_one_or_none()
    if admin_user:
        return admin_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin account not initialized",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def require_roles(allowed_roles: Sequence[UserRole]):
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_role_str = current_user.role.name if current_user.role else ""
        allowed_role_strs = [r.value for r in allowed_roles]
        if user_role_str not in allowed_role_strs and user_role_str != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {allowed_role_strs}, you have {user_role_str}"
            )
        return current_user
    return role_checker

CurrentUser = Annotated[User, Depends(get_current_active_user)]
