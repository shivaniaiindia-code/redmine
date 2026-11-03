# Original User Request

## Initial Request — 2026-11-03T08:43:00Z

Bring the Intelligent Projects Manager platform to full production-ready operational status by resolving UI data visibility and synchronization with live Redmine data, streamlining notifications via SMTP email, and verifying the AI assistant and administration configurations.

Working directory: c:\Users\Anil Abhange\Downloads\intelligent_projects_manager
Integrity mode: development

## Requirements

### R1. Live Redmine Data Synchronization & UI Visibility
Synchronize all operational data from the Redmine instance (`https://redmine.aiindia.ai`) and ensure complete visibility across all primary dashboard views:
- Projects View: Display all synchronized Redmine projects with correct status, health metrics, and metadata without showing empty state messages when data exists.
- Teams View: Display project-wise teams based on current Redmine memberships and role allocations.
- Employees View: Present visual dashboards displaying employee status, current project assignments, and workload distribution.
- Tasks View: Track all Redmine tasks with actual timestamps directly from Redmine, categorized into statuses including overdue, blocked, in progress, and completed.
- Support data refresh through both automated periodic background synchronization and manual on-demand synchronization ("Sync Redmine Now").

### R2. Notification Engine & SMTP Email Alerting
Streamline the system notification and alerting mechanism:
- Remove legacy dispatch settings and interfaces.
- Categorize alert messages based on Redmine categories into urgent messages, critical, and completed/closed states with filter tabs/pills in the UI.
- Deliver all urgent and critical alert notifications exclusively via SMTP email to `anil.aiindia@gmail.com`.

### R3. AI Assistant Integration
Ensure the AI Assistant answers administrative and operational queries (such as current project assignments for specific employees and live project statuses) using grounded, deterministic retrieval from real Redmine data with zero hallucination.

### R4. Administration & Integration
Ensure administration settings and third-party integrations (Redmine API, OpenRouter, SMTP) are fully functional, resilient, easily configurable, and production-ready.

## Verification Resources
- Backend automated test suite (`backend/` pytest tests).
- Frontend lint and build verification (`frontend/` npm run build / lint).
- Automated live API verification against Redmine REST endpoints at `https://redmine.aiindia.ai`.

## Acceptance Criteria

### Data Synchronization & Views
- [ ] Projects view displays all active projects fetched from Redmine with accurate statuses and metadata instead of empty states.
- [ ] Teams view groups and renders team members project-wise based on Redmine project memberships.
- [ ] Employees view displays individual employee statuses, current project allocations, and workload visualizations.
- [ ] Tasks view displays all tasks with original Redmine timestamps, properly categorized by status (overdue, blocked, in progress, completed).
- [ ] Data synchronization succeeds both on automated background intervals and when triggered manually from the UI.

### Notifications & Alerting
- [ ] UI notification panel contains functional category filtering (urgent, critical, completed/closed) and custom dispatch configuration cards are completely removed.
- [ ] Triggered urgent and critical alerts successfully send email notifications to `anil.aiindia@gmail.com` via SMTP.

### AI Assistant & Administration
- [ ] AI Assistant answers questions regarding employee project assignments and project statuses accurately matching live database/Redmine records.
- [ ] Backend test suite (`pytest`) passes without errors.
- [ ] Frontend build (`npm run build`) compiles cleanly without type or lint errors.

