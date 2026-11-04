import asyncio
import uuid
import httpx
from app.core.roles import NO_PLATFORM_ROLE
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.config import settings
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskJournal
from app.models.team import Team, TeamMember
from app.models.employee import Employee
from app.models.redmine_sync import RedmineSyncState, RedmineMapping
from app.services.notification_service import notification_service

class RedmineService:
    def __init__(self):
        # One sync at a time: periodic loop, "Sync Redmine Now" and admin triggers share this lock
        self._sync_lock = asyncio.Lock()
        self.last_sync_summary: dict | None = None
        self.next_sync_at = None  # set by the background loop in main.py
        self.base_url = settings.REDMINE_URL.rstrip("/") if settings.REDMINE_URL else "https://redmine.aiindia.ai"
        self.api_key = settings.REDMINE_API_KEY
        self._cached_conn: dict | None = None
        self._cached_conn_time: float = 0.0

    def _get_headers(self) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CIP-RedmineAgent/1.0",
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-Redmine-API-Key"] = self.api_key
        return headers

    def _parse_iso_datetime(self, dt_str: str | None) -> datetime | None:
        if not dt_str:
            return None
        try:
            clean = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except Exception:
            return None

    async def _fetch_paginated(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        key: str,
        params: dict = None
    ) -> list:
        """
        Generic helper for offset-based pagination in Redmine REST API.
        Ensures records > 100 are never dropped.
        """
        results = []
        offset = 0
        limit = 100
        base_params = params.copy() if params else {}
        while True:
            p = {**base_params, "limit": limit, "offset": offset}
            resp = await client.get(f"{self.base_url}/{endpoint}", headers=self._get_headers(), params=p)
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get(key, [])
            results.extend(items)
            total_count = data.get("total_count", len(items))
            offset += len(items)
            if offset >= total_count or len(items) == 0 or len(items) < limit:
                break
        return results

    async def test_connection(self, force: bool = False) -> dict:
        """Verify connectivity to Redmine server (with 30s in-memory cache to prevent blocking UI)."""
        import time
        now = time.time()
        if not force and self._cached_conn and (now - self._cached_conn_time) < 30.0:
            return self._cached_conn

        url = f"{self.base_url}/projects.json?limit=1"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    res = {
                        "connected": True,
                        "base_url": self.base_url,
                        "status_code": resp.status_code,
                        "projects_count": len(data.get("projects", []))
                    }
                else:
                    res = {
                        "connected": False,
                        "base_url": self.base_url,
                        "status_code": resp.status_code,
                        "error": resp.text[:200]
                    }
        except Exception as e:
            res = {
                "connected": False,
                "base_url": self.base_url,
                "error": str(e)
            }
        self._cached_conn = res
        self._cached_conn_time = now
        return res

    async def sync_all(self, db: AsyncSession) -> dict:
        """Serialized entry point. A request arriving mid-sync waits for it and then runs its own pass."""
        async with self._sync_lock:
            summary = await self._sync_all_unlocked(db)
            self.last_sync_summary = summary
            return summary

    def is_syncing(self) -> bool:
        return self._sync_lock.locked()

    async def _sync_all_unlocked(self, db: AsyncSession) -> dict:
        """
        Full bidirectional discovery and watermark delta sync from Redmine:
        1. Projects (with pagination and stale project marking)
        2. Users / Employees (paginated)
        3. Project Memberships -> ProjectMember & Delivery Teams (paginated)
        4. Issues -> Tasks (preserving exact Redmine timestamps) & TaskJournals
        5. Triggers Automated Alert Generation for Admin
        """
        summary = {
            "projects_synced": 0,
            "memberships_synced": 0,
            "employees_synced": 0,
            "tasks_synced": 0,
            "journals_synced": 0,
            "alerts_generated": 0,
            "status": "SUCCESS",
            "synced_at": datetime.now(timezone.utc).isoformat()
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ---------------------------------------------------------
            # 1. Fetch & Sync Projects (with pagination)
            # ---------------------------------------------------------
            projects_data = await self._fetch_paginated(client, "projects.json", "projects")
            active_redmine_project_ids = set()

            for p_data in projects_data:
                redmine_pid = p_data["id"]
                active_redmine_project_ids.add(redmine_pid)

                # Check mapping
                map_res = await db.execute(
                    select(RedmineMapping).where(
                        and_(
                            RedmineMapping.entity_type == "PROJECT",
                            RedmineMapping.redmine_id == redmine_pid
                        )
                    )
                )
                mapping = map_res.scalars().first()

                project = None
                if mapping:
                    p_res = await db.execute(select(Project).where(Project.id == mapping.internal_id))
                    project = p_res.scalars().first()

                if not project:
                    code = p_data.get("identifier") or f"REDMINE-{redmine_pid}"
                    p_res = await db.execute(select(Project).where(Project.code == code))
                    project = p_res.scalars().first()

                if not project:
                    project = Project(
                        id=str(uuid.uuid4()),
                        name=p_data.get("name", f"Project {redmine_pid}"),
                        code=p_data.get("identifier") or f"REDMINE-{redmine_pid}",
                        description=p_data.get("description"),
                        status="ACTIVE",
                        health_status="ON_TRACK",
                        health_reason="Synchronized from Redmine"
                    )
                    db.add(project)
                    await db.flush()
                else:
                    project.name = p_data.get("name", project.name)
                    project.status = "ACTIVE"
                    if p_data.get("description"):
                        project.description = p_data.get("description")

                if not mapping:
                    mapping = RedmineMapping(
                        entity_type="PROJECT",
                        redmine_id=redmine_pid,
                        internal_id=project.id,
                        raw_metadata=p_data,
                        last_synced_at=datetime.now(timezone.utc)
                    )
                    db.add(mapping)
                else:
                    mapping.raw_metadata = p_data
                    mapping.last_synced_at = datetime.now(timezone.utc)

                summary["projects_synced"] += 1

            await db.flush()

            # Mark inactive stale projects in SQLite no longer present in Redmine
            all_proj_mappings = (await db.execute(
                select(RedmineMapping).where(RedmineMapping.entity_type == "PROJECT")
            )).scalars().all()
            for p_map in all_proj_mappings:
                if p_map.redmine_id not in active_redmine_project_ids:
                    stale_p = (await db.execute(
                        select(Project).where(Project.id == p_map.internal_id)
                    )).scalars().first()
                    if stale_p and stale_p.status != "INACTIVE":
                        stale_p.status = "INACTIVE"
                        stale_p.health_status = "ON_TRACK"
                        stale_p.health_reason = "Archived (no longer active in Redmine)"

            await db.commit()

            # ---------------------------------------------------------
            # 2. Fetch & Sync Full Employee Roster (/users.json)
            # ---------------------------------------------------------
            users_data = await self._fetch_paginated(client, "users.json", "users")
            for u_data in users_data:
                r_uid = u_data["id"]
                u_email = u_data.get("mail") or f"{u_data.get('login', f'user{r_uid}')}@company.com"
                first_name = u_data.get("firstname") or u_data.get("login") or "Team"
                last_name = u_data.get("lastname") or f"Member {r_uid}"

                u_map_res = await db.execute(
                    select(RedmineMapping).where(
                        and_(
                            RedmineMapping.entity_type == "USER",
                            RedmineMapping.redmine_id == r_uid
                        )
                    )
                )
                u_map = u_map_res.scalars().first()

                emp = None
                if u_map:
                    emp_res = await db.execute(select(Employee).where(Employee.id == u_map.internal_id))
                    emp = emp_res.scalars().first()

                if not emp:
                    emp_res = await db.execute(select(Employee).where(Employee.email == u_email))
                    emp = emp_res.scalars().first()

                if not emp:
                    emp = Employee(
                        id=str(uuid.uuid4()),
                        employee_number=f"EMP-R{r_uid:03d}",
                        first_name=first_name,
                        last_name=last_name,
                        email=u_email,
                        job_title=NO_PLATFORM_ROLE,
                        department="Administration" if u_data.get("admin") else "Engineering",
                        weekly_capacity_hours=40.0,
                        status="ACTIVE"
                    )
                    db.add(emp)
                    await db.flush()
                    summary["employees_synced"] += 1
                else:
                    emp.first_name = first_name
                    emp.last_name = last_name

                if not u_map:
                    u_map = RedmineMapping(
                        entity_type="USER",
                        redmine_id=r_uid,
                        internal_id=emp.id,
                        raw_metadata=u_data,
                        last_synced_at=datetime.now(timezone.utc)
                    )
                    db.add(u_map)
                else:
                    u_map.raw_metadata = u_data
                    u_map.last_synced_at = datetime.now(timezone.utc)

            await db.commit()

            # ---------------------------------------------------------
            # 3. Fetch & Sync Project Memberships & Delivery Teams
            # ---------------------------------------------------------
            for redmine_pid in active_redmine_project_ids:
                p_map_res = await db.execute(
                    select(RedmineMapping).where(
                        and_(
                            RedmineMapping.entity_type == "PROJECT",
                            RedmineMapping.redmine_id == redmine_pid
                        )
                    )
                )
                p_map = p_map_res.scalars().first()
                if not p_map:
                    continue

                p_res = await db.execute(select(Project).where(Project.id == p_map.internal_id))
                project = p_res.scalars().first()
                if not project:
                    continue

                # Ensure project is linked to a delivery team
                team_name = f"{project.name} Team"
                t_res = await db.execute(select(Team).where(Team.name == team_name))
                team = t_res.scalars().first()
                if not team and project.primary_team_id:
                    team = (await db.execute(select(Team).where(Team.id == project.primary_team_id))).scalars().first()
                if not team:
                    team = Team(
                        id=str(uuid.uuid4()),
                        name=team_name,
                        department="Engineering",
                        description=f"Delivery team for {project.name}",
                        is_active=True
                    )
                    db.add(team)
                    await db.flush()

                project.primary_team_id = team.id

                # Fetch memberships for this project
                mems_data = await self._fetch_paginated(
                    client, f"projects/{redmine_pid}/memberships.json", "memberships"
                )

                for m_item in mems_data:
                    m_user = m_item.get("user")
                    if not m_user:
                        continue
                    r_uid = m_user.get("id")

                    # Resolve Employee
                    emp_map_res = await db.execute(
                        select(RedmineMapping).where(
                            and_(
                                RedmineMapping.entity_type == "USER",
                                RedmineMapping.redmine_id == r_uid
                            )
                        )
                    )
                    emp_map = emp_map_res.scalars().first()

                    emp = None
                    if emp_map:
                        emp = (await db.execute(select(Employee).where(Employee.id == emp_map.internal_id))).scalars().first()

                    if not emp:
                        u_name = m_user.get("name", f"User {r_uid}").strip()
                        parts = u_name.split()
                        first_name = parts[0] if parts else "Team"
                        last_name = " ".join(parts[1:]) if len(parts) > 1 else f"Member {r_uid}"
                        safe_email = f"{first_name.lower()}.{last_name.lower().replace(' ', '')}@company.com"

                        emp_res = await db.execute(select(Employee).where(Employee.email == safe_email))
                        emp = emp_res.scalars().first()
                        if not emp:
                            emp = Employee(
                                id=str(uuid.uuid4()),
                                employee_number=f"EMP-R{r_uid:03d}",
                                first_name=first_name,
                                last_name=last_name,
                                email=safe_email,
                                job_title=NO_PLATFORM_ROLE,
                                department="Engineering",
                                weekly_capacity_hours=40.0,
                                status="ACTIVE"
                            )
                            db.add(emp)
                            await db.flush()
                            summary["employees_synced"] += 1

                        new_u_map = RedmineMapping(
                            entity_type="USER",
                            redmine_id=r_uid,
                            internal_id=emp.id,
                            raw_metadata=m_user,
                            last_synced_at=datetime.now(timezone.utc)
                        )
                        db.add(new_u_map)
                        await db.flush()

                    # Extract roles
                    roles = m_item.get("roles", [])
                    role_names = [r.get("name") for r in roles if r.get("name")]
                    role_str = ", ".join(role_names) if role_names else "CONTRIBUTOR"

                    # Upsert ProjectMember
                    pm_res = await db.execute(
                        select(ProjectMember).where(
                            and_(
                                ProjectMember.project_id == project.id,
                                ProjectMember.employee_id == emp.id
                            )
                        )
                    )
                    pm = pm_res.scalars().first()
                    if not pm:
                        pm = ProjectMember(
                            id=str(uuid.uuid4()),
                            project_id=project.id,
                            employee_id=emp.id,
                            role_in_project=role_str,
                            allocated_hours_per_week=20.0,
                            joined_at=date.today()
                        )
                        db.add(pm)
                    else:
                        pm.role_in_project = role_str

                    # Upsert TeamMember
                    tm_res = await db.execute(
                        select(TeamMember).where(
                            and_(
                                TeamMember.team_id == team.id,
                                TeamMember.employee_id == emp.id
                            )
                        )
                    )
                    tm = tm_res.scalars().first()
                    if not tm:
                        tm = TeamMember(
                            id=str(uuid.uuid4()),
                            team_id=team.id,
                            employee_id=emp.id,
                            role_in_team=role_str,
                            is_active=True
                        )
                        db.add(tm)
                    else:
                        tm.role_in_team = role_str
                        tm.is_active = True

                    summary["memberships_synced"] += 1

            await db.flush()

            # ---------------------------------------------------------
            # 4. Fetch & Sync Issues -> Tasks & TaskJournals
            # ---------------------------------------------------------
            issues_data = await self._fetch_paginated(
                client, "issues.json", "issues", params={"status_id": "*"}
            )

            for i_data in issues_data:
                redmine_iid = i_data["id"]

                # 4a. Sync Assignee / Employee
                assigned_to_user = i_data.get("assigned_to")
                assigned_emp_id = None
                if assigned_to_user:
                    r_user_id = assigned_to_user["id"]
                    u_map_res = await db.execute(
                        select(RedmineMapping).where(
                            and_(
                                RedmineMapping.entity_type == "USER",
                                RedmineMapping.redmine_id == r_user_id
                            )
                        )
                    )
                    u_map = u_map_res.scalars().first()
                    if u_map:
                        assigned_emp_id = u_map.internal_id
                    else:
                        full_name = assigned_to_user.get("name", f"User {r_user_id}").strip()
                        parts = full_name.split()
                        first_name = parts[0] if parts else "Redmine"
                        last_name = " ".join(parts[1:]) if len(parts) > 1 else f"User{r_user_id}"
                        safe_email = f"{first_name.lower()}.{last_name.lower().replace(' ', '')}@company.com"

                        emp_res = await db.execute(select(Employee).where(Employee.email == safe_email))
                        emp = emp_res.scalars().first()
                        if not emp:
                            emp = Employee(
                                id=str(uuid.uuid4()),
                                employee_number=f"EMP-R{r_user_id:03d}",
                                first_name=first_name,
                                last_name=last_name,
                                email=safe_email,
                                job_title=NO_PLATFORM_ROLE,
                                department="Engineering",
                                weekly_capacity_hours=40.0,
                                status="ACTIVE"
                            )
                            db.add(emp)
                            await db.flush()
                            summary["employees_synced"] += 1

                        assigned_emp_id = emp.id
                        new_u_map = RedmineMapping(
                            entity_type="USER",
                            redmine_id=r_user_id,
                            internal_id=emp.id,
                            raw_metadata=assigned_to_user,
                            last_synced_at=datetime.now(timezone.utc)
                        )
                        db.add(new_u_map)

                # Author resolution
                author_user = i_data.get("author")
                author_emp_id = None
                if author_user:
                    a_uid = author_user.get("id")
                    au_map_res = await db.execute(
                        select(RedmineMapping).where(
                            and_(
                                RedmineMapping.entity_type == "USER",
                                RedmineMapping.redmine_id == a_uid
                            )
                        )
                    )
                    au_map = au_map_res.scalars().first()
                    if au_map:
                        author_emp_id = au_map.internal_id

                # 4b. Map Project
                r_proj = i_data.get("project", {})
                r_pid = r_proj.get("id")
                project_id = None
                if r_pid:
                    p_map = (await db.execute(
                        select(RedmineMapping).where(
                            and_(
                                RedmineMapping.entity_type == "PROJECT",
                                RedmineMapping.redmine_id == r_pid
                            )
                        )
                    )).scalars().first()
                    if p_map:
                        project_id = p_map.internal_id

                if not project_id:
                    first_p = (await db.execute(select(Project).where(Project.status == "ACTIVE").limit(1))).scalars().first()
                    if first_p:
                        project_id = first_p.id
                    else:
                        continue

                # 4c. Parse Exact Timestamps & Dates
                due_date_str = i_data.get("due_date")
                due_date = None
                if due_date_str:
                    try:
                        due_date = date.fromisoformat(due_date_str)
                    except ValueError:
                        pass

                start_date_str = i_data.get("start_date")
                start_date = None
                if start_date_str:
                    try:
                        start_date = date.fromisoformat(start_date_str)
                    except ValueError:
                        pass

                created_at = self._parse_iso_datetime(i_data.get("created_on")) or datetime.now(timezone.utc)
                updated_at = self._parse_iso_datetime(i_data.get("updated_on")) or created_at

                r_status_name = i_data.get("status", {}).get("name", "New")
                status_normalized = "New"
                if "progress" in r_status_name.lower():
                    status_normalized = "In Progress"
                elif "closed" in r_status_name.lower() or "resolved" in r_status_name.lower() or "complet" in r_status_name.lower():
                    status_normalized = "DONE"
                elif "feedback" in r_status_name.lower():
                    status_normalized = "Feedback"

                r_priority = i_data.get("priority", {}).get("name", "Normal")
                done_ratio = int(i_data.get("done_ratio") or 0)
                if done_ratio >= 100:
                    status_normalized = "DONE"

                est_hours = float(i_data.get("estimated_hours") or 0.0)
                spent_hours = float(i_data.get("spent_hours") or 0.0)

                today = date.today()
                is_completed = (status_normalized == "DONE" or done_ratio >= 100)
                is_overdue = bool(due_date and due_date < today and not is_completed)

                # Check Task mapping
                t_map_res = await db.execute(
                    select(RedmineMapping).where(
                        and_(
                            RedmineMapping.entity_type == "ISSUE",
                            RedmineMapping.redmine_id == redmine_iid
                        )
                    )
                )
                t_map = t_map_res.scalars().first()

                task = None
                if t_map:
                    t_res = await db.execute(select(Task).where(Task.id == t_map.internal_id))
                    task = t_res.scalars().first()

                if not task:
                    task = Task(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        assigned_to_id=assigned_emp_id,
                        author_id=author_emp_id,
                        title=f"#{redmine_iid}: {i_data.get('subject', 'Untitled Task')}",
                        description=i_data.get("description"),
                        tracker=i_data.get("tracker", {}).get("name", "Feature"),
                        status=status_normalized,
                        priority=r_priority,
                        estimated_hours=est_hours,
                        spent_hours=spent_hours,
                        progress_percentage=done_ratio,
                        start_date=start_date,
                        due_date=due_date,
                        is_overdue=is_overdue,
                        is_blocked=False,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    db.add(task)
                    await db.flush()

                    new_t_map = RedmineMapping(
                        entity_type="ISSUE",
                        redmine_id=redmine_iid,
                        internal_id=task.id,
                        raw_metadata=i_data,
                        last_synced_at=datetime.now(timezone.utc)
                    )
                    db.add(new_t_map)
                else:
                    task.project_id = project_id
                    task.assigned_to_id = assigned_emp_id
                    if author_emp_id:
                        task.author_id = author_emp_id
                    task.title = f"#{redmine_iid}: {i_data.get('subject', task.title)}"
                    task.description = i_data.get("description") or task.description
                    task.tracker = i_data.get("tracker", {}).get("name", task.tracker)
                    task.status = status_normalized
                    task.priority = r_priority
                    task.estimated_hours = est_hours
                    task.spent_hours = spent_hours
                    task.progress_percentage = done_ratio
                    task.due_date = due_date
                    task.start_date = start_date
                    task.is_overdue = is_overdue
                    task.created_at = created_at
                    task.updated_at = updated_at
                    t_map.raw_metadata = i_data
                    t_map.last_synced_at = datetime.now(timezone.utc)

                summary["tasks_synced"] += 1
                await db.flush()

                # 4d. Fetch & Sync Issue Journals (Change History)
                journals = i_data.get("journals")
                if journals is None:
                    try:
                        detail_resp = await client.get(
                            f"{self.base_url}/issues/{redmine_iid}.json?include=journals",
                            headers=self._get_headers()
                        )
                        if detail_resp.status_code == 200:
                            journals = detail_resp.json().get("issue", {}).get("journals", [])
                    except Exception:
                        journals = []

                if journals:
                    for j in journals:
                        j_id = j.get("id")
                        if not j_id:
                            continue

                        # Resolve journal author
                        j_user = j.get("user")
                        j_author_id = None
                        if j_user:
                            ju_id = j_user.get("id")
                            ju_map = (await db.execute(
                                select(RedmineMapping).where(
                                    and_(
                                        RedmineMapping.entity_type == "USER",
                                        RedmineMapping.redmine_id == ju_id
                                    )
                                )
                            )).scalars().first()
                            if ju_map:
                                j_author_id = ju_map.internal_id

                        j_created_at = self._parse_iso_datetime(j.get("created_on")) or datetime.now(timezone.utc)
                        notes = j.get("notes") or None
                        changes = [
                            {
                                "field": d.get("name"),
                                "property": d.get("property"),
                                "old_value": d.get("old_value"),
                                "new_value": d.get("new_value")
                            }
                            for d in j.get("details", [])
                        ]

                        j_map = (await db.execute(
                            select(RedmineMapping).where(
                                and_(
                                    RedmineMapping.entity_type == "JOURNAL",
                                    RedmineMapping.redmine_id == j_id
                                )
                            )
                        )).scalars().first()

                        if not j_map:
                            t_journal = TaskJournal(
                                id=str(uuid.uuid4()),
                                task_id=task.id,
                                author_id=j_author_id,
                                notes=notes,
                                changes=changes,
                                created_at=j_created_at
                            )
                            db.add(t_journal)
                            await db.flush()
                            db.add(RedmineMapping(
                                entity_type="JOURNAL",
                                redmine_id=j_id,
                                internal_id=t_journal.id,
                                raw_metadata=j,
                                last_synced_at=datetime.now(timezone.utc)
                            ))
                        else:
                            tj_res = await db.execute(select(TaskJournal).where(TaskJournal.id == j_map.internal_id))
                            tj = tj_res.scalars().first()
                            if tj:
                                tj.notes = notes
                                tj.changes = changes
                                tj.created_at = j_created_at
                            j_map.raw_metadata = j
                            j_map.last_synced_at = datetime.now(timezone.utc)

                        summary["journals_synced"] += 1

            # ---------------------------------------------------------
            # 5. Update Sync State Watermark
            # ---------------------------------------------------------
            state_res = await db.execute(select(RedmineSyncState).where(RedmineSyncState.entity_type == "ISSUES"))
            sync_state = state_res.scalars().first()
            if not sync_state:
                sync_state = RedmineSyncState(
                    entity_type="ISSUES",
                    records_synced=summary["tasks_synced"],
                    status="IDLE",
                    last_sync_timestamp=datetime.now(timezone.utc)
                )
                db.add(sync_state)
            else:
                sync_state.records_synced = summary["tasks_synced"]
                sync_state.last_sync_timestamp = datetime.now(timezone.utc)
                sync_state.status = "IDLE"

            await db.commit()

            # ---------------------------------------------------------
            # 6. Automated Alert Generation Engine Trigger
            # ---------------------------------------------------------
            alerts = await notification_service.generate_automated_alerts(db)
            summary["alerts_generated"] = len(alerts)

        return summary

redmine_service = RedmineService()
