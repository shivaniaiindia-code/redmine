from pydantic import BaseModel
from typing import List, Optional

class KPICard(BaseModel):
    id: str
    label: str
    value: str
    trend: str # e.g. "+12% vs last week"
    trend_type: str # "up", "down", "neutral", "danger"
    icon: str

class DonutSegment(BaseModel):
    name: str
    count: int
    percentage: float
    color: str

class ProjectStatusOverview(BaseModel):
    total_projects: int
    segments: List[DonutSegment]

class TaskDistributionItem(BaseModel):
    status: str
    count: int
    color: str

class TeamWorkloadItem(BaseModel):
    team_name: str
    completed: int
    in_progress: int
    overdue: int
    total_tasks: int

class DeadlineItem(BaseModel):
    id: str
    project_name: str
    team_name: str
    deadline_text: str # e.g. "Deadline: in 2 days"
    severity_pill: str # "Critical", "Warning", "Upcoming"
    severity_type: str # "critical", "warning", "upcoming"

class ActivityItem(BaseModel):
    id: str
    title: str # e.g. "Task completed: Model training pipeline"
    subtitle: str # e.g. "by Riya Sharma • ANPR System"
    time_ago: str # e.g. "10 min ago"
    activity_type: str # "task_completed", "task_assigned", "status_updated", "team_assignment"

class SystemNotificationBarItem(BaseModel):
    id: str
    title: str # e.g. "ANPR System deadline in 2 days"
    subtitle: str # e.g. "5 tasks pending, 2 blocked"
    time_ago: str # e.g. "10 min ago"
    severity: str # "CRITICAL", "WARNING", "INFO"
    deep_link: str
    is_mirrored_to_admin_chat: bool = True

class IntegrationStatus(BaseModel):
    name: str # "Redmine", "Google Chat"
    status: str # "Synced", "Connected", "Disconnected"
    is_healthy: bool
    last_synced_at: Optional[str] = None

class CompanyDashboardData(BaseModel):
    kpis: List[KPICard]
    project_status: ProjectStatusOverview
    task_distribution: List[TaskDistributionItem]
    team_workload: List[TeamWorkloadItem]
    upcoming_deadlines: List[DeadlineItem]
    recent_activities: List[ActivityItem]
    notifications: List[SystemNotificationBarItem]
    integrations: List[IntegrationStatus]

