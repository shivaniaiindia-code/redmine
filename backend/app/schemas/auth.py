from pydantic import BaseModel, EmailStr
from typing import Optional, List

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class EmployeeProfileSummary(BaseModel):
    id: str
    employee_number: str
    first_name: str
    last_name: str
    job_title: str
    department: str
    avatar_url: Optional[str] = None

class UserMeResponse(BaseModel):
    id: str
    email: str
    role: RoleResponse
    employee: Optional[EmployeeProfileSummary] = None
    is_active: bool
    approval_status: str = "APPROVED"



class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    department: Optional[str] = "Engineering"
    job_title: Optional[str] = None  # ignored: titles come only from the assigned role

class GoogleAuthRequest(BaseModel):
    id_token: str

class UserListItem(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str
    auth_provider: str
    approval_status: str = "APPROVED"
    department: Optional[str] = None
    job_title: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserRoleUpdate(BaseModel):
    role: str

class UserApprovalUpdate(BaseModel):
    approve: bool
    role: Optional[str] = None  # role granted on approval (default EMPLOYEE)
