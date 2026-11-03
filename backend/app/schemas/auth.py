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

