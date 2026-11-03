# API DESIGN & SPECIFICATION
## Backend Agent: Modular FastAPI REST API Blueprint

---

## 1. Overview & Standard Conventions

The backend exposes a versioned REST API (`/api/v1`) using FastAPI with automatic OpenAPI 3.1 documentation (`/docs` and `/redoc`).

### 1.1 Standard JSON Response Envelope
All API endpoints return predictable responses:

#### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional descriptive status message",
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150
  }
}
```

#### Error Response
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "User does not have access to view this project",
    "details": []
  }
}
```

---

## 2. API Router Hierarchy

```
/api/v1
│
├── /auth                               # Authentication & Current Identity
│   ├── POST   /login                   # OAuth2 password token login (returns JWT + refresh)
│   ├── POST   /refresh                 # Refresh expired access token
│   ├── GET    /me                      # Current user profile & permitted roles
│   └── POST   /logout                  # Invalidate active session
│
├── /company                            # Company Dashboard & Executive KPIs
│   ├── GET    /kpis                    # Overall health, active projects, velocity, overload
│   ├── GET    /activity-feed           # Recent updates across all teams
│   └── GET    /alerts                  # Critical company-wide risks & bottlenecks
│
├── /projects                           # Project Management
│   ├── GET    /                        # List projects (filterable by status, health, team)
│   ├── POST   /                        # Create project (Admin/Manager)
│   ├── GET    /{id}                    # Project 360: details, health reason, timeline
│   ├── PATCH  /{id}                    # Update project status or dates
│   ├── GET    /{id}/members            # Assigned members & allocation
│   ├── GET    /{id}/tasks              # Tasks list & Kanban groupings
│   └── GET    /{id}/burndown           # Milestone burn-down metrics
│
├── /teams                              # Team Management
│   ├── GET    /                        # List teams & headcount
│   ├── POST   /                        # Create team (Admin)
│   ├── GET    /{id}                    # Team overview & primary projects
│   ├── GET    /{id}/members            # Team members & individual workloads
│   └── GET    /{id}/velocity           # Historical task completion & velocity
│
├── /employees                          # Employee Directory & 360 Profile
│   ├── GET    /                        # Directory list (filterable by dept, skill)
│   ├── GET    /{id}                    # Full Employee 360 profile
│   ├── GET    /{id}/projects           # Current & past project contributions
│   ├── GET    /{id}/tasks              # Active assigned tasks & deadlines
│   ├── GET    /{id}/workload           # Weekly hours allocated vs 40h capacity
│   └── GET    /{id}/skills             # Verified skills & development history
│
├── /tasks                              # Task & Work Management
│   ├── GET    /                        # List tasks (filtered by assignee, project, status)
│   ├── POST   /                        # Create task (or write to Redmine)
│   ├── GET    /{id}                    # Task details, history, time entries
│   ├── PATCH  /{id}                    # Update task status/progress
│   └── POST   /{id}/blocker            # Flag task as blocked with explanation
│
├── /notifications                      # Notification Center
│   ├── GET    /                        # User notification feed (filter unread/severity)
│   ├── PATCH  /{id}/read               # Mark notification as read
│   ├── POST   /read-all                # Mark all notifications read
│   ├── GET    /briefing/today          # Today's personalized daily briefing
│   └── GET    /preferences             # User notification preferences
│
├── /redmine                            # Redmine Integration & Sync
│   ├── GET    /status                  # Redmine connection health & last sync stats
│   ├── POST   /sync/trigger            # Trigger manual delta sync (Admin)
│   ├── GET    /sync/logs               # View recent synchronization logs
│   └── POST   /test-connection         # Verify Redmine URL & API Key
│
├── /google-chat                        # Google Chat Webhook Management
│   ├── GET    /spaces                  # List configured Google Chat spaces
│   ├── POST   /spaces                  # Register new webhook space (Admin)
│   ├── POST   /spaces/{id}/test        # Send test card notification to space
│   └── GET    /delivery-logs           # Webhook delivery audit logs
│
├── /ai                                 # Conversational Intelligence
│   ├── POST   /chat                    # Streamed or REST AI question answering
│   ├── GET    /conversations           # List past AI chat sessions
│   ├── GET    /conversations/{id}      # Load conversation message history
│   └── GET    /models                  # Available OpenRouter models & active model
│
├── /reports                            # Reports & Analytics
│   ├── GET    /company-summary         # Executive monthly/weekly summary
│   ├── GET    /project-health          # Cross-project delivery risk report
│   ├── GET    /team-productivity       # Workload & delivery velocity report
│   └── GET    /export/csv              # Export formatted CSV / JSON data
│
└── /admin                              # Administration Console (Super Admin)
    ├── GET    /users                   # Manage users & assign roles
    ├── PATCH  /users/{id}/role         # Change user role
    ├── GET    /audit-logs              # View immutable system audit logs
    └── GET    /settings                # System environment & integration settings
```

---

## 3. RBAC Dependency Injection Pattern

FastAPI dependency injection enforces access control at the endpoint definition:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.permissions import require_roles, CurrentUser
from app.models.user import UserRole

router = APIRouter()

@router.get("/company/kpis", dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.COMPANY_MANAGEMENT]))])
async def get_company_kpis(current_user: CurrentUser):
    # Only Super Admin and Company Management can access company-wide metrics
    return await analytics_service.get_company_kpis()

@router.get("/employees/{employee_id}/workload")
async def get_employee_workload(employee_id: str, current_user: CurrentUser):
    # Employees can view their own workload; Team Leads & Managers can view subordinates
    if not permissions_service.can_view_employee(current_user, employee_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await employee_service.get_workload(employee_id)
```

