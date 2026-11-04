import uuid
import secrets
import httpx
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from app.core.database import get_db
from app.core.config import settings, ROOT_ADMIN_EMAIL
from app.core.security import verify_password, get_password_hash, create_access_token, oauth2_scheme, decode_access_token
from app.core.permissions import get_current_user, CurrentUser, SignedInUser, RequireAdminOrManagement, RequireSuperAdmin
from app.services.notification_service import notification_service
from app.core.roles import role_label, UNASSIGNED_DEPARTMENT
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserMeResponse,
    RoleResponse,
    EmployeeProfileSummary,
    RegisterRequest,
    GoogleAuthRequest,
    UserListItem,
    UserStatusUpdate,
    UserRoleUpdate,
    UserApprovalUpdate,
)

# Verified identities that bootstrap the platform owner account (Google-verified only)
BOOTSTRAP_SUPER_ADMINS = {"anil.aiindia@gmail.com", ROOT_ADMIN_EMAIL}
# Roles Company Management may grant when approving; SUPER_ADMIN may grant any role
MANAGEMENT_GRANTABLE_ROLES = {"EMPLOYEE", "TEAM_LEAD", "PROJECT_MANAGER"}


async def _approved_admin_from_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    """The approved Super Admin / Company Management account behind a bearer token, if any."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    sub, claimed_email = str(payload["sub"]), payload.get("email")
    match = or_(User.id == sub, User.email == sub, User.email == claimed_email) if claimed_email \
        else or_(User.id == sub, User.email == sub)
    user = (await db.execute(select(User).where(match))).scalars().first()
    if (user and user.is_active and user.approval_status == "APPROVED"
            and user.role and user.role.name in ("SUPER_ADMIN", "COMPANY_MANAGEMENT")):
        return user
    return None


async def _notify_access_request(db: AsyncSession, user: User, name: str, provider: str) -> None:
    """URGENT alert (notification bar + admin email) that someone is waiting for access approval."""
    base = settings.APP_BASE_URL.rstrip("/")
    try:
        # Run notification dispatch in a background task so external SMTP / LLM calls never block signup/login
        async def _dispatch_bg():
            from app.core.database import AsyncSessionLocal
            try:
                async with AsyncSessionLocal() as bg_db:
                    await notification_service.create_and_dispatch(
                        db=bg_db,
                        title=f"Access request: {name} is waiting for approval",
                        message=(
                            f"{name} <{user.email}> signed up with {provider} and cannot see any company data until approved. "
                            f"Review the request in Administration > Access Requests: {base}/?view=admin"
                        ),
                        severity="URGENT",
                        entity_type="USER",
                        entity_id=user.id,
                    )
            except Exception as e:
                print(f"[AccessRequest] Async dispatch failed for {user.email}: {e}")

        asyncio.create_task(_dispatch_bg())
    except Exception as e:  # never block sign-up because an alert could not be delivered
        print(f"[AccessRequest] Notification failed for {user.email}: {e}")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == login_data.email.strip().lower())
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
            detail="Account is disabled. Contact system administrator."
        )

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.name if user.role else "EMPLOYEE"}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60
    )

@router.post("/register", response_model=TokenResponse)
async def register(
    reg_data: RegisterRequest,
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Self sign-up creates an EMPLOYEE account that stays PENDING (no data access)
    until a Super Admin or Company Management approves it. Accounts created by a
    signed-in Super Admin / Company Management from Administration are approved at once.
    """
    email = reg_data.email.strip().lower()
    creator = await _approved_admin_from_token(token, db)
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in."
        )

    # Password sign-ups never self-assign SUPER_ADMIN (the email is not verified)
    is_super = False
    role_name = "EMPLOYEE"
    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if not role:
        # Never escalate to SUPER_ADMIN because a role row is missing
        raise HTTPException(status_code=500, detail=f"Role '{role_name}' is not configured. Contact the administrator.")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        hashed_password=get_password_hash(reg_data.password),
        role_id=role.id,
        is_active=True,
        auth_provider="email",
        approval_status="APPROVED" if creator else "PENDING",
        reviewed_by=creator.email if creator else None,
        reviewed_at=datetime.now(timezone.utc) if creator else None,
    )
    db.add(user)
    await db.flush()

    # Link or create employee record
    emp = (await db.execute(select(Employee).where(Employee.email == email))).scalar_one_or_none()
    if emp:
        emp.user_id = user.id
    else:
        emp = Employee(
            id=str(uuid.uuid4()),
            user_id=user.id,
            employee_number=f"EMP-{secrets.randbelow(90000) + 10000}",
            first_name=reg_data.first_name.strip(),
            last_name=reg_data.last_name.strip(),
            email=email,
            job_title=role_label(role_name),
            department=UNASSIGNED_DEPARTMENT,
            status="ACTIVE",
            weekly_capacity_hours=40.0
        )
        db.add(emp)

    await db.commit()
    await db.refresh(user)

    if user.approval_status == "PENDING":
        name = f"{reg_data.first_name.strip()} {reg_data.last_name.strip()}".strip() or email
        await _notify_access_request(db, user, name, "email / password")

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.name if user.role else "EMPLOYEE"}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60
    )

@router.post("/google", response_model=TokenResponse)
async def google_auth(
    auth_data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": auth_data.id_token}
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Google authentication token."
                )
            payload = resp.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to reach Google OAuth service: {str(e)}"
        )

    # Validate audience matches Google Client ID
    aud = payload.get("aud")
    if settings.GOOGLE_CLIENT_ID and aud != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token audience mismatch."
        )

    email = payload.get("email")
    if str(payload.get("email_verified", "true")).lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified."
        )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token does not contain an email address."
        )

    email = email.strip().lower()
    first_name = payload.get("given_name") or payload.get("name", "Google User").split(" ")[0]
    last_name = payload.get("family_name") or (
        payload.get("name", "").split(" ")[1] if len(payload.get("name", "").split(" ")) > 1 else ""
    )
    picture = payload.get("picture")

    user_query = select(User).where(User.email == email)
    user = (await db.execute(user_query)).scalar_one_or_none()
    new_google_user = False

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is disabled. Contact system administrator."
            )
        user.auth_provider = "google"
        if user.employee:
            if picture and not user.employee.avatar_url:
                user.employee.avatar_url = picture
        else:
            emp = (await db.execute(select(Employee).where(Employee.email == email))).scalar_one_or_none()
            if emp:
                emp.user_id = user.id
                if picture and not emp.avatar_url:
                    emp.avatar_url = picture
    else:
        is_super = email in BOOTSTRAP_SUPER_ADMINS
        role_name = "SUPER_ADMIN" if is_super else "EMPLOYEE"
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=500, detail=f"Role '{role_name}' is not configured. Contact the administrator.")

        user_id = str(uuid.uuid4())
        dummy_hash = get_password_hash(secrets.token_urlsafe(32))
        user = User(
            id=user_id,
            email=email,
            hashed_password=dummy_hash,
            role_id=role.id,
            is_active=True,
            auth_provider="google",
            approval_status="APPROVED" if is_super else "PENDING",
        )
        new_google_user = True
        db.add(user)
        await db.flush()

        emp = (await db.execute(select(Employee).where(Employee.email == email))).scalar_one_or_none()
        if emp:
            emp.user_id = user.id
            if picture and not emp.avatar_url:
                emp.avatar_url = picture
        else:
            emp = Employee(
                id=str(uuid.uuid4()),
                user_id=user.id,
                employee_number=f"EMP-{secrets.randbelow(90000) + 10000}",
                first_name=first_name,
                last_name=last_name or first_name,
                email=email,
                job_title=role_label(role_name),
                department=UNASSIGNED_DEPARTMENT,
                status="ACTIVE",
                weekly_capacity_hours=40.0,
                avatar_url=picture
            )
            db.add(emp)

    await db.commit()
    await db.refresh(user)

    if new_google_user and user.approval_status == "PENDING":
        await _notify_access_request(db, user, f"{first_name} {last_name}".strip() or email, "Google")

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.name if user.role else "EMPLOYEE"}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60
    )

def _is_super_admin(user: User) -> bool:
    return bool(user.role and user.role.name == "SUPER_ADMIN")


@router.get("/users", response_model=List[UserListItem])
async def list_users(
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    query = select(User).order_by(User.created_at.desc())
    users = (await db.execute(query)).scalars().all()

    result = []
    for u in users:
        name = u.email.split("@")[0].capitalize()
        if u.employee:
            name = f"{u.employee.first_name} {u.employee.last_name}".strip()
        result.append(UserListItem(
            id=u.id,
            email=u.email,
            name=name,
            role=u.role.name if u.role else "EMPLOYEE",
            is_active=u.is_active,
            created_at=u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
            auth_provider=u.auth_provider or "email",
            approval_status=u.approval_status or "APPROVED",
            department=u.employee.department if u.employee else None,
            job_title=u.employee.job_title if u.employee else None,
        ))
    return result

@router.put("/users/{user_id}/approval")
async def review_access_request(
    user_id: str,
    payload: UserApprovalUpdate,
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or decline a pending sign-up. Approval grants the chosen role
    (default EMPLOYEE). Company Management may grant Employee, Team Lead or
    Project Manager; only a Super Admin may grant management/admin roles.
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot review your own access request")

    granted_role = None
    if payload.approve:
        role_name = (payload.role or (user.role.name if user.role else "EMPLOYEE")).strip().upper().replace(" ", "_")
        if not _is_super_admin(current_user) and role_name not in MANAGEMENT_GRANTABLE_ROLES:
            raise HTTPException(status_code=403, detail=f"Only a Super Admin can grant the {role_name} role")
        granted_role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if not granted_role:
            raise HTTPException(status_code=400, detail=f"Invalid role '{payload.role}'")
        user.role_id = granted_role.id
        if user.employee:
            user.employee.job_title = role_label(granted_role.name)
        user.approval_status = "APPROVED"
        user.is_active = True
    else:
        if _is_super_admin(user):
            raise HTTPException(status_code=403, detail="A Super Admin account cannot be declined")
        user.approval_status = "REJECTED"

    user.reviewed_by = current_user.email
    user.reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    name = f"{user.employee.first_name} {user.employee.last_name}".strip() if user.employee else user.email
    verdict = f"approved as {granted_role.name}" if granted_role else "declined"
    try:
        await notification_service.create_and_dispatch(
            db=db,
            title=f"Access request {verdict.split(' ')[0]}: {name}",
            message=f"{name} <{user.email}> was {verdict} by {current_user.email}.",
            severity="INFO",
            entity_type="USER",
            entity_id=user.id,
        )
    except Exception as e:
        print(f"[AccessRequest] Review notification failed: {e}")

    return {
        "message": f"{user.email} {verdict}",
        "user_id": user.id,
        "approval_status": user.approval_status,
        "role": granted_role.name if granted_role else (user.role.name if user.role else None),
    }

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_data: UserStatusUpdate,
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    if user_id == current_user.id and not status_data.is_active:
        raise HTTPException(status_code=400, detail="Cannot block your own active account")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email == ROOT_ADMIN_EMAIL and not status_data.is_active:
        raise HTTPException(status_code=400, detail="Primary system administrator account cannot be blocked")

    if _is_super_admin(user) and not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only a Super Admin can change another Super Admin's account")

    user.is_active = status_data.is_active
    await db.commit()
    label = "active" if user.is_active else "blocked"
    return {"message": f"User status set to {label}", "is_active": user.is_active}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own active account")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email in (ROOT_ADMIN_EMAIL, "admin@company.com", "admin@aiindia.com"):
        raise HTTPException(status_code=400, detail="Primary system administrator account cannot be deleted")

    if _is_super_admin(user) and not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only a Super Admin can delete another Super Admin's account")

    # Invariant: Historical Continuity. Never delete or orphan historical contributions.
    # Nullify foreign key references so historical data is preserved
    await db.execute(update(Employee).where(Employee.user_id == user_id).values(user_id=None))
    await db.execute(update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None))
    await db.execute(update(Notification).where(Notification.recipient_id == user_id).values(recipient_id=None))

    # Mark any pending access request notifications for this user as read
    await db.execute(
        update(Notification)
        .where(Notification.entity_type == "USER", Notification.entity_id == user_id)
        .values(is_read=True)
    )

    # Detach in-memory relationship to prevent SQLAlchemy unit-of-work foreign key collision
    if user.employee:
        user.employee.user_id = None
        user.employee = None

    user_email = user.email
    await db.delete(user)
    await db.commit()
    return {"message": f"User account '{user_email}' deleted successfully. Historical project contributions preserved."}

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: RequireSuperAdmin,
    db: AsyncSession = Depends(get_db)
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_input = role_data.role.strip().upper().replace(" ", "_")
    if user.email == ROOT_ADMIN_EMAIL and role_input != "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Primary system administrator account cannot be demoted.")

    target_role = (await db.execute(
        select(Role).where(
            or_(
                Role.name == role_input,
                Role.name == role_data.role.strip()
            )
        )
    )).scalar_one_or_none()

    if not target_role:
        raise HTTPException(status_code=400, detail=f"Invalid role '{role_data.role}'")

    user.role_id = target_role.id
    if user.employee:
        user.employee.job_title = role_label(target_role.name)

    await db.commit()
    return {"message": f"User role updated to {target_role.name}", "role": target_role.name, "user_id": user.id}

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.email == form_data.username.strip().lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is disabled."
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
async def get_me(current_user: SignedInUser):
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
        is_active=current_user.is_active,
        approval_status=current_user.approval_status or "APPROVED",
    )
