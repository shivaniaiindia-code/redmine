from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.permissions import get_current_user, CurrentUser
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse, RoleResponse, EmployeeProfileSummary

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == login_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is disabled"
        )

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.name if user.role else "EMPLOYEE"}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60
    )

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.name if user.role else "EMPLOYEE"}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60
    )

@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: CurrentUser):
    role_resp = RoleResponse(
        id=current_user.role.id,
        name=current_user.role.name,
        description=current_user.role.description,
        permissions=current_user.role.permissions if isinstance(current_user.role.permissions, list) else []
    )
    
    emp_summary = None
    if current_user.employee:
        emp_summary = EmployeeProfileSummary(
            id=current_user.employee.id,
            employee_number=current_user.employee.employee_number,
            first_name=current_user.employee.first_name,
            last_name=current_user.employee.last_name,
            job_title=current_user.employee.job_title,
            department=current_user.employee.department,
            avatar_url=current_user.employee.avatar_url
        )

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=role_resp,
        employee=emp_summary,
        is_active=current_user.is_active
    )

