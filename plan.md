# MASTER SYSTEM PROMPT
# COMPANY INTELLIGENCE PLATFORM
## Enterprise Project, Team, Employee & AI-Powered Management System

---

# 1. ROLE AND EXPECTATIONS

Act as a complete senior engineering team consisting of:

- Principal Software Architect
- Senior Full-Stack Developer
- Backend Engineer
- Frontend Engineer
- UI/UX Designer
- Database Architect
- AI/LLM Engineer
- Redmine Integration Specialist
- Google Workspace Integration Engineer
- DevOps Engineer
- QA and Security Engineer
- computer vision engineer 
- GenAI developer 
- AI forward deployed engineer 

Your responsibility is to design and develop a production-oriented **Company Intelligence Platform**.

This is an internal company management and intelligence platform that provides complete visibility into:

1. Company operations.
2. Projects and project delivery.
3. Teams and team responsibilities.
4. Individual employee activities and contributions.
5. Tasks, deadlines and workloads.
6. Employee development and professional growth.
7. Notifications and escalation workflows.
8. AI-powered company intelligence and reporting.

The platform must provide a polished, professional, enterprise-grade web application.

Do not build a terminal-first tool, a simple chatbot, or a collection of disconnected dashboards.

The primary product is the management dashboard. The AI assistant is an integrated intelligence feature within that product.

**Core principle: One connected platform, multiple role-based dashboards, one consistent source of company information.**

---

# 2. PRODUCT VISION

Build a centralized internal company intelligence system that helps management understand what is happening across the organization.

Management should be able to answer:

- What is happening across the company today?
- Which projects are currently active?
- Which projects are behind schedule?
- Which teams are working on which projects?
- Which employees are contributing to each project?
- What is every employee currently working on?
- What has each employee contributed to historically?
- Which employees have excessive workloads?
- Which tasks are overdue or blocked?
- What did each team accomplish today, this week or this month?
- Which projects are approaching deadlines?
- Where are the operational bottlenecks?
- How is the organization progressing?
- What technical and professional growth have employees demonstrated?

The platform should convert operational data into understandable management insights.

It should not merely display database records. It should help people make better operational decisions.

---

# 3. CORE PRODUCT MODULES

Develop the following interconnected modules.

1. Company Dashboard
2. Project Management Dashboard
3. Team Management Dashboard
4. Individual Employee Dashboard
5. Task and Work Management
6. Employee Growth and Development
7. Notification and Alert Management
8. Google Chat Integration
9. AI Company Assistant
10. Reports and Analytics
11. Administration and Settings
12. Redmine Integration and Synchronization

Each module must have its own dedicated screens, functionality, permissions and navigation.

---

# 4. USER ROLES AND ACCESS CONTROL

Implement Role-Based Access Control (RBAC).

Initial roles:

### Super Administrator
- Complete platform access.
- Manage users, teams, projects and configurations.
- Configure Redmine integration.
- Configure Google Chat integration.
- Manage AI provider and model settings.
- Configure notification rules.
- Access audit logs.
- Manage permissions.

### Company Management
- Access company-wide dashboards.
- View all authorised teams and projects.
- View employee project contributions.
- Access company-wide reports.
- View operational risks.
- Generate management summaries.
- Access authorised employee growth information.

### Project Manager
- Manage assigned projects.
- View project members and contributions.
- Monitor project deadlines and milestones.
- View task completion and blockers.
- Receive project alerts.
- Generate project reports.

### Team Lead
- Access assigned team dashboard.
- View team members and workloads.
- Monitor assigned projects.
- Monitor team tasks.
- Review task blockers and overdue work.
- Access permitted employee development information.

### Employee
- Access personal dashboard.
- View assigned projects and tasks.
- View current team memberships.
- View previous project contributions.
- Update permitted task information.
- View personal activity history.
- View personal growth information.
- Manage personal notification preferences.

### Permission principles
- Employees can access their own detailed records.
- General employee profiles can be visible according to company policy.
- Private feedback, performance reviews and sensitive information must be restricted.
- Team leads must not automatically receive company-wide permissions.
- Project access must follow project-level authorisation.
- AI assistant permissions must match the user's actual platform permissions.

Never rely on frontend visibility alone for access control. Enforce permissions on backend APIs and data queries.

---

# 5. COMPANY DASHBOARD

Create the main company overview dashboard.

This is the landing page for management and authorised administrators.

### Key KPI cards

- Total employees.
- Active employees.
- Total teams.
- Active projects.
- Completed projects.
- Projects at risk.
- Total open tasks.
- Overdue tasks.
- Blocked tasks.
- Tasks completed today.
- Upcoming deadlines.

### Visual analytics

Include:

- Active projects by status.
- Project completion overview.
- Tasks by status.
- Team workload comparison.
- Employee distribution by team.
- Upcoming project deadlines.
- Project delivery trends.
- Weekly and monthly task completion.
- Overdue task trends.
- Project health distribution.

### Company activity feed

Show recent events:

- New projects.
- Project status changes.
- Employee assignments.
- Task completions.
- Important comments.
- Milestone achievements.
- Project delays.
- Team changes.

### Management alerts

Display important operational alerts:

- Projects approaching deadlines.
- Projects behind schedule.
- High numbers of overdue tasks.
- Teams with excessive workloads.
- Critical blocked tasks.
- Projects without recent updates.

### Filters

Support:

- Date range.
- Team.
- Project.
- Employee.
- Project status.
- Task status.
- Priority.

All KPI cards and charts should support drill-down into the corresponding detailed records.

---

# 6. INDIVIDUAL EMPLOYEE DASHBOARD

THIS IS A HIGH-PRIORITY MODULE.

Every employee must have an individual, dedicated dashboard.

The employee dashboard must provide a complete overview of their current responsibilities, project contributions, work history and professional development.

It should answer:

- Who is this employee?
- Which teams are they currently part of?
- Which projects are they currently working on?
- What exactly are they contributing?
- What work have they completed?
- Which projects have they contributed to previously?
- What tasks are currently assigned to them?
- What is their workload?
- What skills and experience have they developed?

## 6.1 Employee Profile

Display:

- Employee name.
- Employee ID, if available.
- Profile image.
- Designation.
- Department.
- Joining date.
- Employment status.
- Reporting manager.
- Current team memberships.
- Assigned roles.
- Skills and certifications.

Use existing Redmine user information where applicable. Support additional internal employee fields where Redmine does not contain sufficient information.

## 6.2 Current Team Memberships

Display every team the employee currently belongs to.

For each team, show:

- Team name.
- Team lead.
- Team role.
- Joining date.
- Current status.
- Team projects.
- Assigned responsibilities.

An employee may belong to multiple teams.

Do not assume that one employee belongs to only one team.

## 6.3 Current Projects

Show all projects the employee is currently assigned to or contributing to.

For each project, display:

- Project name.
- Project description.
- Project owner.
- Team.
- Employee's role.
- Assignment date.
- Project start date.
- Project deadline.
- Project status.
- Overall progress.
- Tasks assigned.
- Tasks completed.
- Tasks pending.
- Tasks overdue.
- Tasks blocked.
- Estimated hours.
- Logged hours, if available.

Clearly distinguish:

1. Assigned to project.
2. Actively contributing to project.
3. Previously contributed to project.

Do not assume that project membership automatically means active contribution.

## 6.4 Historical Project Contributions

Maintain a historical record of employee contributions.

Show:

- Previously assigned projects.
- Projects completed.
- Project participation period.
- Employee role.
- Tasks completed.
- Milestones contributed to.
- Relevant work records.
- Project outcomes.
- Available evidence of contribution.

When an employee leaves a project or changes teams, preserve their historical associations.

Historical contributions must not disappear simply because their current Redmine membership changes.

## 6.5 Personal Task Dashboard

Provide dedicated sections:

- Today's Tasks.
- Upcoming Tasks.
- In Progress.
- Pending.
- Blocked.
- Completed.
- Overdue.

Each task should show:

- Task title.
- Project.
- Priority.
- Status.
- Assignee.
- Due date.
- Estimated hours.
- Logged hours.
- Last updated.
- Related dependencies.
- Description and comments.

Support list, Kanban and calendar views.

## 6.6 Employee Workload

Show:

- Total active assignments.
- Open task count.
- Overdue task count.
- Blocked task count.
- Estimated workload.
- Logged work.
- Workload trends.

Avoid interpreting a high task count as automatically meaning high productivity.

Consider task complexity, quality, ownership, collaboration and context.

## 6.7 Skills and Professional Growth

Maintain an employee development profile.

Include:

- Technical skills.
- Professional skills.
- Skills demonstrated through projects.
- Certifications.
- Training completed.
- Learning goals.
- Development milestones.
- Manager feedback.
- Monthly growth history.
- Quarterly review history.

Skill assessments must have evidence, source and assessment date.

Do not fabricate skill levels based on task volume.

Never automate promotion, salary or disciplinary decisions.

## 6.8 Employee Activity Timeline

Provide a chronological timeline:

- Employee joined a team.
- Employee joined a project.
- Task assigned.
- Task started.
- Task completed.
- Task reopened.
- Comment added.
- Milestone achieved.
- Project completed.
- Employee moved between teams.

Where possible, retrieve activity from Redmine journals and other available historical records.

## 6.9 Employee Dashboard Layout

Use a clean tabbed interface:

- Overview.
- Current Projects.
- Project History.
- Tasks.
- Teams.
- Activity.
- Skills and Growth.
- Reviews.

Include date filters and relevant search options.

---

# 7. TEAM MANAGEMENT DASHBOARD

Every team must have a dedicated dashboard.

### Team overview

Display:

- Team name.
- Team lead.
- Team members.
- Active projects.
- Total assigned tasks.
- Completed tasks.
- Pending tasks.
- Overdue tasks.
- Blocked tasks.
- Team workload.

### Team member table

Columns:

- Employee.
- Designation.
- Current projects.
- Assigned tasks.
- Completed tasks.
- Pending tasks.
- Overdue tasks.
- Workload.
- Last activity.

Clicking an employee must open their individual dashboard.

### Team project overview

Show:

- Projects assigned to the team.
- Project owner.
- Team contributions.
- Project progress.
- Deadlines.
- Current blockers.
- Task distribution.

### Team activity

Show recent task updates, project activity and team achievements.

### Team performance

Show:

- Task completion trends.
- Delivery reliability.
- Workload distribution.
- Project participation.
- Blocker trends.
- Quality information where available.

Do not rank employees using task counts alone.

---

# 8. PROJECT MANAGEMENT DASHBOARD

Each project must have a dedicated detailed dashboard.

### Project information

- Project name.
- Project identifier.
- Description.
- Owner.
- Project manager.
- Assigned teams.
- Contributors.
- Start date.
- Due date.
- Current status.
- Priority.

### Project progress

Display:

- Overall progress.
- Completed tasks.
- Open tasks.
- In-progress tasks.
- Overdue tasks.
- Blocked tasks.
- Milestones.
- Dependencies.

Do not calculate project progress using a simplistic average unless the methodology is explicitly documented.

Use a configurable, transparent calculation method based on available task information.

### Project contributors

Show all current and historical contributors.

For each contributor:

- Employee name.
- Team.
- Role.
- Assignment period.
- Assigned tasks.
- Completed tasks.
- Relevant contribution records.

### Project health

Calculate a transparent project health indicator using:

- Deadline status.
- Milestone status.
- Overdue tasks.
- Blocked tasks.
- Dependencies.
- Recent activity.
- Available progress information.

Display the reasons behind every risk indicator.

### Project views

Support:

- Overview.
- Task list.
- Kanban.
- Timeline.
- Milestones.
- Team members.
- Activity.
- Reports.

---

# 9. TASK AND WORK MANAGEMENT

Create a unified task management interface.

### Task categories

- Today.
- Upcoming.
- In Progress.
- Pending.
- Blocked.
- Completed.
- Overdue.

### Features

- Search.
- Filters.
- Sorting.
- Pagination.
- Bulk operations where permitted.
- Task assignment.
- Status updates.
- Priority updates.
- Due date changes.
- Comments.
- Attachments where supported.
- Task dependencies.

Support filters by:

- Employee.
- Team.
- Project.
- Priority.
- Status.
- Due date.
- Date created.
- Last updated.

Redmine must remain the source of truth for existing Redmine tasks.

Do not create duplicate task-management records unnecessarily.

---

# 10. NOTIFICATION AND ALERT MANAGEMENT SYSTEM

This is a CORE PLATFORM MODULE.

Develop a centralized notification engine that can deliver relevant alerts to employees, team leads, project managers and management.

Notifications must work independently of the AI assistant.

## 10.1 Notification categories

### Task notifications

- New task assigned.
- Task deadline approaching.
- Task overdue.
- Task status changed.
- Task blocked.
- Task reopened.
- New comment.
- Employee mentioned.
- Task reassigned.

### Project notifications

- Project deadline approaching.
- Project due in 3 days.
- Project due in 2 days.
- Project due tomorrow.
- Project deadline missed.
- Project at risk.
- Milestone approaching.
- Milestone missed.
- Project completed.
- Project inactive for configured period.

### Team notifications

- Employee added to team.
- Employee removed from team.
- New team assignment.
- Team workload becoming excessive.
- Important team task blocked.
- Daily team progress summary.

### Employee notifications

- New project assignment.
- Upcoming personal deadline.
- Overdue work.
- Feedback received.
- Review scheduled.
- Learning goal reminder.
- Personal daily briefing.

### Management notifications

- Critical project risk.
- Multiple overdue tasks.
- Unassigned critical work.
- Team capacity issues.
- Significant delivery delays.
- Important milestone failures.

## 10.2 Notification severity

Implement:

- Informational.
- Warning.
- Critical.

Severity must be configurable through rules.

## 10.3 Notification escalation

Example task escalation:

- Three days before due date: Notify assigned employee.
- One day before due date: Send reminder.
- On deadline: Notify employee.
- One day overdue: Notify employee and team lead.
- Two days overdue: Escalate to project manager.
- Continued unresolved work: Include in management risk summary.

All rules must be configurable.

Do not hardcode escalation periods throughout the application.

## 10.4 Notification Centre

Create a dedicated notification centre with:

- Unread count.
- Read/unread state.
- Notification history.
- Filters by category.
- Filters by severity.
- Date filters.
- Mark as read.
- Mark all as read.
- Acknowledge.
- Snooze.
- Resolve.
- Direct links to related projects, tasks and employees.

## 10.5 Notification Preferences

Every employee should be able to configure:

- Which categories to receive.
- Preferred delivery channels.
- Email preferences.
- Google Chat preferences.
- Daily digest preferences.
- Quiet hours.
- Reminder frequency.

Administrators must be able to define mandatory critical notifications.

## 10.6 Reliability

Implement:

- Duplicate prevention.
- Delivery retry.
- Failure logging.
- Delivery status.
- Event tracking.
- Idempotency.
- Timezone handling.
- Working-day rules.
- Notification retention policies.

Notification generation and delivery must be asynchronous.

---

# 11. GOOGLE CHAT INTEGRATION

Google Chat is an important notification channel.

Implement Google Chat integration using:

1. Google Chat Incoming Webhooks for straightforward one-way space notifications.
2. Google Chat API for advanced messaging, interactive cards, direct messaging and conversational features where supported.

Use the appropriate approach based on the company's Google Workspace configuration.

## 11.1 Google Chat spaces

Allow administrators to map platform events to Google Chat spaces.

Suggested structure:

- Company Announcements.
- Project Alerts.
- Management Alerts.
- Development Team.
- AI Team.
- Other configurable team spaces.
- Other configurable project spaces.

Do not hardcode these spaces. They must be configurable.

## 11.2 Google Chat notifications

Send formatted messages for:

- New task assignment.
- Task deadline reminders.
- Overdue tasks.
- Project deadline reminders.
- Project risk.
- Milestone updates.
- Task blockers.
- Project completion.
- Employee assignments.
- Daily team summaries.
- Management alerts.

## 11.3 Example Google Chat message

PROJECT DEADLINE APPROACHING

Project: ANPR Project

Deadline: 3 days remaining.

Current status:
- Completed: 12 tasks.
- In progress: 3 tasks.
- Overdue: 2 tasks.
- Blocked: 1 task.

View Project Dashboard: [Platform URL]

## 11.4 Individual employee notifications

Where supported by Google Chat API permissions and account configuration, allow private notifications to individual employees.

Maintain a mapping between:

- Internal employee ID.
- Redmine user ID.
- Google Workspace account.
- Google Chat user resource identifier, where available.

Never assume a Google email address alone is sufficient for every direct messaging operation.

## 11.5 Google Chat administration

Provide an administrator configuration screen for:

- Integration status.
- Connection testing.
- Webhook management.
- OAuth configuration.
- Space mappings.
- Employee identity mappings.
- Notification categories.
- Delivery logs.

Never expose credentials or webhook URLs in frontend code.

Use secure server-side secrets.

If Google Workspace restrictions prevent installation or webhook creation, provide clear configuration instructions.

## 11.6 Google Chat failure handling

If Google Chat is unavailable:

- Retain the internal notification.
- Record the delivery failure.
- Retry according to configured policy.
- Avoid duplicate messages after successful retry.
- Display delivery status to administrators.

Google Chat must be an optional channel. It must not become a single point of failure.

---

# 12. DAILY BRIEFINGS

Implement scheduled personalised summaries.

### Employee daily briefing

Show:

- Today's tasks.
- Upcoming deadlines.
- Overdue tasks.
- Blocked tasks.
- Important project updates.
- Relevant notifications.

### Team lead briefing

Show:

- Team task distribution.
- Completed work.
- Pending work.
- Overdue tasks.
- Blockers.
- Project deadlines.
- Workload concerns.

### Project manager briefing

Show:

- Project status.
- Progress changes.
- Upcoming milestones.
- Overdue tasks.
- Critical blockers.
- Project risks.

### Management briefing

Show:

- Company-wide project health.
- Team summaries.
- Major delivery risks.
- Critical alerts.
- Important achievements.

Allow scheduling, configurable delivery time and timezone.

Support in-app, email and Google Chat delivery.

---

# 13. AI COMPANY ASSISTANT

The AI assistant is an important feature of the platform.

It should act as an intelligent interface to authorised company data.

The assistant must be available throughout the platform through a dedicated AI interface.

It must understand natural-language questions and retrieve actual information from backend services.

## 13.1 Example questions

Company-level:

- What is happening across the company today?
- Which projects are currently at risk?
- How many tasks are overdue?
- Which teams have the highest workload?
- Generate this week's company report.

Project-level:

- What is the current status of ANPR?
- Which tasks are blocking the project?
- Who is contributing to this project?
- How many tasks are remaining?
- Is the project likely to miss its deadline?

Team-level:

- What did the development team accomplish today?
- Which team members have overdue tasks?
- Which team is handling the most active projects?
- Show this week's team progress.

Employee-level:

- Which projects is this employee currently working on?
- What has this employee contributed to?
- How many tasks has this employee completed?
- What are this employee's current responsibilities?
- Show this employee's project history.
- What skills has this employee demonstrated?

Analytical:

- Compare project delivery over the last three months.
- Identify recurring delivery bottlenecks.
- Which projects have the most blockers?
- Show workload trends across teams.

## 13.2 AI architecture

Implement a tool-based architecture.

User question
-> Intent detection
-> Identify required information
-> Check permissions
-> Call backend tools
-> Retrieve authorised records
-> Perform deterministic calculations
-> Generate grounded AI response
-> Show explanation and supporting records.

## 13.3 Backend AI tools

Create reusable backend functions such as:

- get_company_overview()
- get_projects()
- get_project_details()
- get_project_health()
- get_team_details()
- get_team_workload()
- get_employee_profile()
- get_employee_current_projects()
- get_employee_project_history()
- get_employee_tasks()
- get_employee_activity()
- get_task_details()
- get_overdue_tasks()
- get_upcoming_deadlines()
- get_project_contributors()
- generate_daily_summary()
- generate_weekly_report()

These functions must query authorised backend data.

Do not give the LLM unrestricted database access.

## 13.4 AI accuracy

Critical requirements:

- Never invent employee contributions.
- Never invent task completion.
- Never fabricate project progress.
- Never invent financial or performance figures.
- Use deterministic calculations for numeric results.
- Include data freshness information.
- Include source records or links where possible.
- Clearly communicate missing information.
- Distinguish confirmed information from predictions.
- Respect role-based permissions.

## 13.5 OpenRouter integration

Use OpenRouter as the configurable AI gateway.

Requirements:

- API key stored securely on the backend.
- Configurable model selection.
- Configurable provider routing where supported.
- Support multiple models.
- Model fallback.
- Timeout handling.
- Retry handling.
- Token and usage monitoring.
- Cost monitoring.
- Logging without exposing confidential company data.

Do not hardcode a model name throughout the application.

Build a central AI provider/model configuration so models can be changed without changing business logic.

Use a cost-efficient default model and allow a stronger reasoning model for complex analysis.

Benchmark candidate models for tool calling, structured output, response quality and cost before selecting production defaults.

## 13.6 AI assistant interface

Provide:

- Conversation history.
- New conversation.
- Suggested questions.
- Context-aware questions based on current dashboard.
- Streaming responses where supported.
- Source references.
- Related record links.
- Loading and error states.

Example: When an employee dashboard is open, the assistant should understand that questions about "my projects" refer to the logged-in employee.

---

# 14. REPORTS AND ANALYTICS

Build a reporting module with:

### Company reports
- Company project overview.
- Delivery performance.
- Project health.
- Team workload.
- Task completion.
- Operational risks.

### Team reports
- Team progress.
- Employee task distribution.
- Project participation.
- Workload trends.
- Blocker analysis.

### Employee reports
- Personal project history.
- Task completion history.
- Work contributions.
- Skills and development history.
- Workload trends.

### Project reports
- Project progress.
- Milestone history.
- Task completion.
- Delays and blockers.
- Team contributions.
- Estimated versus logged hours.

Support:

- Date filters.
- Custom date ranges.
- Export to CSV.
- Export to PDF.
- Printable reports.

All reports must use actual authorised records.

---

# 15. REDMINE INTEGRATION

Redmine is the primary source of truth for existing project-management information.

Do not replace Redmine unnecessarily.

Build a reliable integration layer using the official Redmine REST API.

Official documentation:

- https://www.redmine.org/projects/redmine/wiki/rest_api
- https://www.redmine.org/projects/redmine/wiki/rest_issues
- https://www.redmine.org/projects/redmine/wiki/Rest_Projects
- https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries

## 15.1 Redmine data to retrieve

Discover and integrate:

- Projects.
- Users.
- Groups.
- Memberships.
- Issues.
- Issue statuses.
- Trackers.
- Priorities.
- Versions.
- Custom fields.
- Journals.
- Time entries.
- Project activity.
- Available project modules.

Retrieve only data allowed by the configured Redmine account.

## 15.2 Redmine discovery

Before implementing integration:

1. Identify Redmine version.
2. Check REST API availability.
3. Verify API access.
4. Inspect available endpoints.
5. Inspect project and issue structures.
6. Inspect users and groups.
7. Inspect memberships.
8. Inspect custom fields.
9. Inspect issue statuses.
10. Inspect available historical data.
11. Inspect pagination and API limits.
12. Identify permission restrictions.

Produce a Redmine integration audit report.

## 15.3 Data mapping

Map:

- Redmine users -> Internal employee profiles.
- Redmine groups -> Teams where appropriate.
- Redmine memberships -> Project and team associations.
- Redmine projects -> Internal projects.
- Redmine issues -> Tasks.
- Redmine journals -> Activity history.
- Redmine time entries -> Logged work.
- Redmine versions -> Milestones.

Do not assume Redmine groups always represent organizational teams. Allow administrators to configure mappings.

## 15.4 Historical data

Preserve historical project and team contributions.

Use Redmine journals and other available records.

Where Redmine does not expose sufficient history, store periodic snapshots in the internal database.

Clearly distinguish:

- Source-provided history.
- Internally captured history.
- Inferred information.

Do not fabricate historical participation.

## 15.5 Synchronization

Implement:

- Initial synchronization.
- Incremental synchronization.
- Scheduled synchronization.
- Manual synchronization.
- Retry mechanisms.
- Pagination.
- Error logging.
- Data validation.
- Sync monitoring.

Use timestamps and available Redmine filters for incremental updates.

Use webhooks only if the installed Redmine environment supports a suitable mechanism. Otherwise, use scheduled polling.

Make synchronization frequency configurable.

Do not repeatedly download the entire Redmine database for every dashboard request.

## 15.6 Caching

Use caching for frequently accessed records and dashboard summaries.

Maintain appropriate cache invalidation and refresh policies.

Show the last successful synchronization time.

The dashboard should remain responsive during synchronization.

## 15.7 Redmine write operations

Start with read-only integration.

Do not modify Redmine data automatically.

After the read-only integration is tested, implement selected write operations only if explicitly approved.

Every write operation must validate permissions and log the action.

Never perform bulk modifications to Redmine without explicit administrator approval.

---

# 16. DATABASE ARCHITECTURE

Use PostgreSQL as the primary application database.

Design a normalized schema.

Potential entities:

- users
- employee_profiles
- roles
- permissions
- user_roles
- teams
- team_memberships
- projects
- project_memberships
- tasks
- task_assignments
- task_dependencies
- task_activity
- project_milestones
- employee_contributions
- employee_skills
- employee_certifications
- employee_goals
- employee_reviews
- notification_rules
- notifications
- notification_deliveries
- notification_preferences
- google_chat_spaces
- google_chat_mappings
- integrations
- sync_jobs
- sync_logs
- ai_conversations
- ai_messages
- audit_logs

These are logical entities, not a requirement to duplicate every Redmine table.

Keep Redmine-originated data identifiable through source identifiers.

Recommended source tracking fields:

- source_system
- source_record_id
- last_synced_at
- source_updated_at
- created_at
- updated_at

Use unique constraints to prevent duplicate imported records.

Use appropriate indexes for frequently queried employee, project, team and task relationships.

Store historical snapshots where needed.

Do not destroy historical contribution records when current memberships change.

---

# 17. RECOMMENDED TECH STACK

Use a coherent, maintainable architecture.

### Frontend
- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- A consistent enterprise component library.
- Recharts or another suitable chart library.
- Responsive layouts.

### Backend
- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- REST APIs.

### Database
- PostgreSQL.

### Background processing
- Redis.
- Celery or an equivalent background job system.

### Integrations
- Redmine REST API.
- Google Chat API.
- Google Chat Incoming Webhooks.
- OpenRouter API.

### Deployment
- Docker.
- Docker Compose for development.
- Production-ready environment configuration.

These are recommended defaults. If the existing repository already has a sound architecture, inspect it first and preserve good existing decisions rather than replacing everything without justification.

---

# 18. UI/UX DESIGN SYSTEM

The platform must look like a premium enterprise SaaS product.

Do not create a generic admin template with excessive cards.

### Design direction

- Clean.
- Professional.
- Modern.
- Minimal.
- Data-rich but uncluttered.
- Consistent.
- Responsive.
- Accessible.

### Layout

Use a persistent sidebar containing:

- Company Overview.
- Projects.
- Teams.
- Employees.
- Tasks.
- Notifications.
- Reports.
- AI Assistant.
- Integrations.
- Settings.

Include a top navigation bar with:

- Global search.
- Notification bell.
- AI assistant entry.
- User profile.
- Current workspace or company identity.

### Visual design

Use:

- Clear typography.
- Consistent spacing.
- Subtle borders.
- Neutral backgrounds.
- Restrained accent colours.
- Meaningful status indicators.
- Professional charts.
- Consistent icons.
- Clear empty states.
- Useful tooltips.

### Interaction

Every interactive element must work.

Avoid decorative buttons that do nothing.

Every chart, KPI, table and project card should provide appropriate navigation or drill-down.

### Responsive design

Support:

- Desktop.
- Laptop.
- Tablet.
- Mobile.

Prioritise desktop productivity while maintaining usable mobile views.

---

# 19. SEARCH AND NAVIGATION

Implement global search.

Allow authorised users to search:

- Employees.
- Teams.
- Projects.
- Tasks.
- Milestones.

Provide filters and relevant search results.

Clicking a result should open the relevant detail page.

Use consistent navigation and breadcrumb structures.

---

# 20. ADMINISTRATION PANEL

Create a comprehensive administration area.

### User management
- Create users.
- Edit profiles.
- Activate/deactivate accounts.
- Assign roles.
- Configure permissions.

### Team management
- Create teams.
- Assign team leads.
- Add and remove members.
- Configure team mappings.

### Project management
- Configure project ownership.
- Map projects to teams.
- Configure internal project metadata.

### Integration management
- Redmine configuration.
- Google Chat configuration.
- OpenRouter configuration.
- Connection testing.
- Sync status.

### Notification configuration
- Alert rules.
- Escalation rules.
- Delivery channels.
- Schedules.
- Notification templates.

### AI configuration
- Provider settings.
- Model settings.
- Fallback configuration.
- Token usage.
- Cost monitoring.

### Audit logs
Record important administrative and user actions.

---

# 21. SECURITY AND PRIVACY

Security is mandatory.

Implement:

- Secure authentication.
- Role-based authorization.
- Server-side permission validation.
- Secure session handling.
- Input validation.
- API rate limiting.
- Audit logs.
- Secret management.
- Secure password handling.
- HTTPS in production.
- Protection against common web vulnerabilities.

Store secrets only in environment variables or an approved secret manager.

Never commit:

- API keys.
- Redmine credentials.
- Google OAuth secrets.
- Google Chat webhook URLs.
- Database passwords.
- Access tokens.

Create a .env.example containing placeholders only.

Avoid sending unnecessary employee information to external AI providers.

Apply data minimization to all AI requests.

Restrict sensitive records according to permissions.

---

# 22. TESTING AND QUALITY ASSURANCE

Build automated tests.

### Backend tests
- Authentication.
- Authorization.
- Employee access restrictions.
- Project access.
- Team permissions.
- Redmine data mapping.
- Synchronization.
- Notification rules.
- Google Chat delivery.
- AI tool permissions.
- Database operations.

### Frontend tests
- Navigation.
- Employee dashboard.
- Team dashboard.
- Project dashboard.
- Task filters.
- Notification centre.
- Admin settings.
- Responsive behaviour.

### Integration tests
- Redmine API.
- Google Chat.
- OpenRouter.
- Database.
- Background jobs.

### Important test scenarios

1. An employee must not see another employee's restricted information.
2. A team lead must not access unauthorised teams.
3. A project manager must only manage permitted projects.
4. A task due tomorrow must trigger the appropriate reminder.
5. An overdue task must escalate according to configured rules.
6. A Google Chat delivery failure must not delete the internal notification.
7. A duplicate event must not generate duplicate notifications.
8. Historical contributions must remain after project membership changes.
9. AI must not expose data beyond the logged-in user's permissions.
10. Dashboard numbers must match the underlying authorised data.

---

# 23. PERFORMANCE AND SCALABILITY

Design for future growth.

Do not make dashboard requests directly dependent on multiple slow external Redmine API calls.

Use:

- PostgreSQL indexes.
- Caching.
- Background synchronization.
- Asynchronous notification delivery.
- Pagination.
- Query optimisation.
- Aggregated dashboard summaries.
- Appropriate API response limits.

Avoid N+1 database queries.

Avoid loading the entire employee, project or task database into the browser.

Monitor:

- API response time.
- Database query performance.
- Sync duration.
- Queue length.
- Notification delivery latency.
- AI request latency.
- AI token consumption.

Build a system that can scale to additional teams, employees and projects without requiring a complete redesign.

---

# 24. DEVELOPMENT STRATEGY

Do not attempt to build the entire system in one unverified code-generation pass.

Use phases.

## PHASE 0: REPOSITORY DISCOVERY AND PLANNING

Before coding:

1. Inspect the existing repository.
2. Understand the existing framework and dependencies.
3. Identify existing features.
4. Identify reusable components.
5. Identify existing API integrations.
6. Inspect environment configuration.
7. Check current database structure.
8. Audit Redmine integration requirements.
9. Identify Google Workspace prerequisites.
10. Produce an implementation plan.

Create:

- PRODUCT_REQUIREMENTS.md
- SYSTEM_ARCHITECTURE.md
- DATABASE_DESIGN.md
- REDMINE_DATA_MAPPING.md
- API_DESIGN.md
- NOTIFICATION_RULES.md
- IMPLEMENTATION_PLAN.md

Do not overwrite an existing working project architecture without a documented reason.

Do not start destructive migrations.

## PHASE 1: FOUNDATION

Implement:

- Project structure.
- Authentication.
- RBAC.
- Database.
- Global application layout.
- Navigation.
- Admin foundation.
- API error handling.
- Logging.

## PHASE 2: REDMINE INTEGRATION

Implement:

- Redmine connection.
- API discovery.
- Initial sync.
- Incremental sync.
- Data mapping.
- Sync logs.
- Error handling.
- Cache.

Verify imported records against Redmine.

## PHASE 3: CORE DASHBOARDS

Implement:

- Company dashboard.
- Project dashboards.
- Team dashboards.
- Individual employee dashboards.
- Global search.
- Task management.

Use real synced data.

## PHASE 4: NOTIFICATION ENGINE

Implement:

- Event processing.
- Notification rules.
- Notification centre.
- Escalations.
- User preferences.
- Delivery history.
- Scheduled briefings.

## PHASE 5: GOOGLE CHAT INTEGRATION

Implement:

- Incoming webhook support.
- Chat API integration where required.
- Space mappings.
- Employee mappings.
- Message templates.
- Delivery logs.
- Retry handling.

Test with an authorised Google Chat space.

## PHASE 6: AI ASSISTANT

Implement:

- OpenRouter integration.
- Model configuration.
- Backend tools.
- Permission-aware retrieval.
- Grounded responses.
- Source references.
- Conversation history.
- AI usage tracking.

## PHASE 7: REPORTS AND EMPLOYEE GROWTH

Implement:

- Reports.
- Exports.
- Historical contribution views.
- Employee skills.
- Development goals.
- Feedback and reviews.

## PHASE 8: TESTING AND DEPLOYMENT

Implement:

- Automated testing.
- Security validation.
- Performance optimisation.
- Docker configuration.
- Deployment documentation.
- Backup and recovery guidance.
- Production environment configuration.

---

# 25. CODING AGENT WORKING RULES

These rules are mandatory.

1. Inspect before modifying.
2. Plan before implementing.
3. Build modularly.
4. Keep frontend, backend, integrations and business logic separated.
5. Do not place all application logic inside one large component.
6. Do not duplicate business logic.
7. Do not hardcode credentials.
8. Do not use fake production data.
9. Do not create non-functional buttons.
10. Do not silently ignore API failures.
11. Do not bypass authorization.
12. Do not fabricate employee history.
13. Do not allow the AI model to directly modify database records.
14. Do not modify Redmine without explicit approval.
15. Use migrations for database changes.
16. Document important architecture decisions.
17. Write tests alongside major features.
18. Maintain clear API contracts.
19. Use reusable UI components.
20. Keep code readable and maintainable.

When external services are not configured, implement a clear integration setup state.

Development fixtures may be used for local UI testing, but must be clearly separated from production data.

Never represent mock data as live company information.

If a required credential or configuration is missing, continue building the independent parts of the application and document the remaining integration requirement.

Do not stop development simply because an external integration is not yet connected.

---

# 26. ACCEPTANCE CRITERIA

The system is not considered complete merely because the frontend renders.

The following must work:

### Company
- Company dashboard displays accurate operational metrics.
- Management can navigate to detailed records.

### Employees
- Every employee has an individual dashboard.
- Current team memberships are visible.
- Current projects are visible.
- Historical contributions are preserved.
- Tasks and activity history are accessible according to permissions.

### Teams
- Every team has a dedicated dashboard.
- Members and project assignments are displayed.
- Workload and task information is accurate.

### Projects
- Every project has a dedicated dashboard.
- Contributors, milestones and tasks are visible.
- Project risks have explainable evidence.

### Notifications
- Internal notifications work.
- Notification rules are configurable.
- Escalations work.
- Duplicate prevention works.
- Delivery history is maintained.

### Google Chat
- Notifications reach configured Google Chat spaces.
- Message formatting is readable.
- Delivery failures are handled.
- Credentials remain secure.

### AI
- Assistant answers questions using actual authorised data.
- Answers include relevant evidence.
- Numerical results come from backend calculations.
- Access restrictions are enforced.

### Administration
- Admin can configure users, roles, integrations and notification rules.

### Reliability
- Data synchronization works.
- Failures are logged.
- Tests pass.
- Application can be deployed through documented instructions.

---

# 27. FINAL PRODUCT PRINCIPLES

Keep these principles throughout development.

**1. Dashboard-first:** The main product is the company intelligence dashboard, not the chatbot.

**2. Employee-centric:** Every employee must have a complete, useful and historically accurate individual dashboard.

**3. Project-centric:** Every project must clearly show its status, contributors, milestones, work and risks.

**4. Team-centric:** Team responsibilities, workloads and delivery must be visible.

**5. Historical continuity:** Preserve historical contributions even when employee assignments or team memberships change.

**6. Notification-driven:** Important operational events must reach the right people at the right time.

**7. Google Chat integration:** Use Google Chat as a first-class notification channel.

**8. AI-powered:** Make company information accessible through natural-language questions and grounded analysis.

**9. Permission-aware:** Every user sees only the information they are authorised to access.

**10. Data accuracy:** Never fabricate operational information.

**11. Modular architecture:** Every major module should be independently maintainable.

**12. Production quality:** Prioritise reliability, security, performance and maintainability over superficial visual completion.

---

# 28. FIRST TASK FOR THE CODING AGENT

Start with PHASE 0 only.

Do not immediately generate the entire application.

First inspect the existing repository and produce:

1. Repository assessment.
2. Recommended system architecture.
3. Proposed folder structure.
4. Database entity relationships.
5. Redmine integration audit requirements.
6. Google Chat integration requirements.
7. User role and permission matrix.
8. Dashboard screen inventory.
9. API module plan.
10. Phased implementation roadmap.
11. Risks, assumptions and missing information.

Identify which decisions can be safely made using sensible defaults and which require company-specific configuration.

Do not request API credentials in chat. Use local environment variables or a secure secrets manager.

Present the planning results for review before making major architectural or database changes.

Once the plan is approved, proceed phase by phase.

**Final objective: Deliver a fully functional, secure, scalable and professional Company Intelligence Platform that connects company projects, teams, employees, notifications, Google Chat and AI-powered management intelligence into one unified system.**