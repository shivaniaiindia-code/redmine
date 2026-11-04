from typing import Annotated, Sequence, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import oauth2_scheme, decode_access_token
from app.models.user import User, UserRole

async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    # 1. If a valid Bearer token is provided, validate it strictly
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            sub = str(payload["sub"])
            email = payload.get("email")
            query = (
                select(User)
                .options(selectinload(User.role), selectinload(User.employee))
                .where(
                    or_(
                        User.id == sub,
                        User.email == sub,
                        User.email == email if email else False
                    )
                )
            )
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. No token: the request is anonymous. Never fall back to a default account —
    #    that would grant Super Admin rights to anyone who is signed out.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_signed_in_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Valid, active account — approved or still waiting for approval (used by /auth/me)."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive")
    return current_user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_signed_in_user)]
) -> User:
    """Approved account: required for every endpoint that exposes company data."""
    approval = getattr(current_user, "approval_status", "APPROVED") or "APPROVED"
    if approval != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCOUNT_REJECTED" if approval == "REJECTED" else "ACCOUNT_PENDING_APPROVAL",
        )
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
                detail=f"Access denied: This resource is restricted to {allowed_role_strs}. Your role is {user_role_str}."
            )
        return current_user
    return role_checker

CurrentUser = Annotated[User, Depends(get_current_active_user)]
SignedInUser = Annotated[User, Depends(get_current_signed_in_user)]
RequireAdminOrManagement = Annotated[
    User, Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.COMPANY_MANAGEMENT]))
]
RequireSuperAdmin = Annotated[User, Depends(require_roles([UserRole.SUPER_ADMIN]))]
