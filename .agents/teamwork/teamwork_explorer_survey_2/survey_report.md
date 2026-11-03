# Frontend Views & UI Synchronization Survey Report

**Explorer**: Explorer 2 (Frontend Views Explorer)  
**Date**: 2026-11-03  
**Working Directory**: `frontend/`  
**Target Specification**: `ORIGINAL_REQUEST.md` (R1: Live Redmine Data Synchronization & UI Visibility; R2: Notification Engine & Alerting)

---

## Executive Summary

The frontend is built using **Next.js 15.1.7** (App Router), **React 19.0.0**, **Tailwind CSS 3.4.17**, and **Lucide-react 0.475.0**. It implements a single-page tabbed executive dashboard shell (`src/app/page.tsx`) that dynamically switches views based on active navigation tabs: Dashboard, Projects, Teams, Employees, Tasks, and Administration.

While the UI layout, styling tokens, and production build (`npm run build`) pass successfully, the investigation uncovered several critical architectural and data-visibility gaps between the current UI implementation and the authoritative requirements in `ORIGINAL_REQUEST.md`:

1. **Teams View Defect**: Does not group or render team members project-wise based on Redmine memberships and role allocations. It only renders pre-seeded internal team cards without member lists.
2. **Employees View Defect**: Does not display employee status badges, current project assignments, or workload distribution visualizations.
3. **Tasks View Defect**: Only displays `due_date`; it completely omits original Redmine timestamps (`created_on`, `updated_on`).
4. **Projects View Empty State Trigger**: Triggers empty state whenever the backend returns `[]` or when fetch fails/errors without distinguishing network or auth issues.
5. **Manual Sync ("Sync Redmine Now")**: Implemented in `ProjectsView.tsx` and `AdminView.tsx`, but missing on top-level navigation, and views other than Projects/Admin do not provide a sync trigger or auto-refresh.
6. **ESLint Configuration Error**: `npm run lint` fails with `ERR_MODULE_NOT_FOUND` in `eslint.config.mjs`.
7. **Hardcoded API URLs**: All components hardcode `http://localhost:8000/api/v1/...` instead of using an environment variable or unified API client.
8. **Notification Filtering & Legacy Dispatch**: `NotificationModal.tsx` lacks category filter pills (urgent, critical, completed/closed) and still contains legacy custom dispatch forms.

---

## 1. Codebase Architecture & Structure

### 1.1 Directory Layout
```
frontend/
├── eslint.config.mjs              # Flat config (Currently failing due to missing .js extension)
├── next.config.ts                 # Next.js configuration
├── package.json                   # Next 15.1.7, React 19, Lucide-react 0.475.0, Tailwind 3.4
├── postcss.config.mjs
├── tailwind.config.ts             # Tailwind design tokens
├── tsconfig.json
└── src/
    ├── app/
    │   ├── globals.css            # Custom scrollbars, Tailwind directives
    │   ├── layout.tsx             # Root layout with Geist font and title metadata
    │   └── page.tsx               # Main tabbed dashboard shell
    └── components/
        ├── AIAssistantDrawer.tsx  # OpenRouter AI assistant drawer
        ├── ActivitiesFeed.tsx     # Recent activity stream
        ├── DeadlinesFeed.tsx      # Upcoming project deadlines feed
        ├── KPICards.tsx           # 6 top KPI cards
        ├── NotificationModal.tsx  # System notification modal
        ├── NotificationsFeed.tsx  # Dashboard notification feed widget
        ├── OmniSearchModal.tsx    # Command palette (Ctrl+K)
        ├── ProjectStatusDonut.tsx # SVG Donut chart for project statuses
        ├── Sidebar.tsx            # Left dark sidebar navigation
        ├── TaskDistributionBar.tsx# CSS/SVG bar chart for task distribution
        ├── TeamWorkloadStacked.tsx# Stacked horizontal workload bars
        ├── TopNav.tsx             # Top navigation bar
        └── views/
            ├── AdminView.tsx      # Administration & Redmine sync trigger
            ├── EmployeesView.tsx  # Employee 360 directory
            ├── ProjectsView.tsx   # Company projects portfolio & sync button
            ├── TasksView.tsx      # Operational tasks & issues table
            └── TeamsView.tsx      # Organizational teams & capacity
```

### 1.2 State & Routing Paradigm
- Next.js App Router is used, but all primary views (`projects`, `teams`, `employees`, `tasks`, `admin`) are client-side components rendered within a single route (`/`) via tab switching in `src/app/page.tsx:93-160`.
- Data fetching occurs via component-level `useEffect` hooks issuing raw `fetch()` calls to `http://localhost:8000/api/v1/...`.
- No global cache (e.g. TanStack React Query or SWR) is currently utilized.

---

## 2. In-Depth View-by-View Investigation

### 2.1 Projects View (`src/components/views/ProjectsView.tsx`)

#### Findings & Capabilities
- **Endpoint**: `GET http://localhost:8000/api/v1/projects/`
- **Rendered Fields**:
  - Project Code (badge)
  - Health Status (`ON_TRACK`, `AT_RISK`, `BLOCKED`) with color-coded badge (`getHealthBadge`)
  - Project Name (`name`) and Description (`description`)
  - Health Indicator rationale (`health_reason`)
  - Tasks summary: Total, Overdue, Blocked, Done counts
  - Visual progress bar calculating percentage: `Math.round((completed_tasks / total_tasks) * 100)`

#### Empty State Analysis
- **Trigger**: Lines 114–116:
  ```tsx
  projects.length === 0 ? (
    <div className="p-12 text-center text-slate-400">
      No projects found. Click "Sync Redmine Now" to populate.
    </div>
  )
  ```
- **Root Causes Triggering Empty State**:
  1. **Initial Unsynchronized State**: If Redmine delta sync has never been run, the database `projects` table is empty.
  2. **Silenced Fetch Failure**: Lines 35–37 catch fetch errors with `console.error("Failed to load projects", err);` without setting an error state, causing the component to display the "No projects found" empty state even if the backend is down, throwing 500, or refusing connection.
  3. **Authentication 401**: Backend `projects.py:13-16` requires `current_user: CurrentUser`. If the backend database lacks the default admin user `admin@company.com`, `get_current_user` in `permissions.py:32-36` raises `401 UNAUTHORIZED`. The frontend fetch returns a 401 response without setting `projects`, triggering the empty state.
  4. **CORS / Port Mismatch**: `fetch("http://localhost:8000/api/v1/projects/")` is hardcoded. If the API runs on another host or port, requests fail silently.

---

### 2.2 Teams View (`src/components/views/TeamsView.tsx`)

#### Findings & Capabilities
- **Endpoint**: `GET http://localhost:8000/api/v1/teams/`
- **Current Rendered Fields**:
  - Department badge (`team.department`)
  - Team Name (`team.name`)
  - Description (`team.description`)
  - Assigned Projects list (`team.projects.map(p => p.name)`)
  - Members count (`team.members_count`) and Projects count (`team.projects_count`)

#### Compliance Gap with Requirement R1
- **Authoritative Requirement**:
  - *"Teams View: Display project-wise teams based on current Redmine memberships and role allocations."*
  - *"Acceptance Criteria: Teams view groups and renders team members project-wise based on Redmine project memberships."*
- **Current Implementation Gap**:
  - **Zero Project-Wise Member Grouping**: The view only displays internal departmental teams (AI Team, Development, QA Team, Research, Operations).
  - **No Member Names or Roles**: Neither team members nor their Redmine roles (e.g. Manager, Developer, Reporter) are shown.
  - **No Role Allocations**: Project-wise role allocations are completely absent.
- **Root Cause**:
  1. Frontend `TeamsView.tsx` was coded against the static `Team` model rather than project-based memberships.
  2. Backend `redmine_service.py` currently fetches projects (`/projects.json`), users (`/users.json`), and issues (`/issues.json`), but does NOT fetch Redmine project memberships (`/projects/{id}/memberships.json`) to populate `project_members`.
  3. Backend `teams.py` only queries `Team` and `TeamMember`, not project-wise memberships.

---

### 2.3 Employees View (`src/components/views/EmployeesView.tsx`)

#### Findings & Capabilities
- **Endpoint**: `GET http://localhost:8000/api/v1/employees/`
- **Current Rendered Fields**:
  - Avatar initials (`split(" ").map(n => n[0]).join("")`)
  - Employee Full Name (`name`) and Job Title (`job_title`)
  - Email (`email`) and Department (`department`)
  - Tasks summary grid: Total Tasks, Overdue, Done

#### Compliance Gap with Requirement R1
- **Authoritative Requirement**:
  - *"Employees View: Present visual dashboards displaying employee status, current project assignments, and workload distribution."*
  - *"Acceptance Criteria: Employees view displays individual employee statuses, current project allocations, and workload visualizations."*
- **Current Implementation Gap**:
  1. **Employee Status Missing in UI**: Although `status` is in `EmployeeItem`, it is never rendered in JSX (no "ACTIVE", "ON_LEAVE", or availability indicator).
  2. **No Current Project Assignments**: No project badges, list of assigned projects, or project allocation details are displayed.
  3. **No Workload Distribution Visualization**:
     - No visual representation of workload (e.g. allocated hours vs 40h capacity, utilization bar, or burnout index).
     - The `employee-360-growth` skill defines the Workload Score formula:
       $$\text{Workload Score} = \left(\frac{\text{Allocated Hours}}{\text{Weekly Capacity}}\right) \times \left(1 + 0.15 \times (\text{Active Projects} - 1)\right)$$
       This calculation and visual gauge are completely missing from `EmployeesView.tsx`.

---

### 2.4 Tasks View (`src/components/views/TasksView.tsx`)

#### Findings & Capabilities
- **Endpoint**: `GET http://localhost:8000/api/v1/tasks/`
- **Current Controls & Table**:
  - Status filter pills: `ALL`, `OVERDUE`, `BLOCKED`, `IN_PROGRESS`, `COMPLETED`
  - Columns: Task/Issue, Project, Assignee, Status, Due Date, Blocker Action
  - Operational blocker toggle: `handleToggleBlocker` calls `POST /api/v1/tasks/{id}/toggle-blocker`

#### Compliance Gap with Requirement R1
- **Authoritative Requirement**:
  - *"Tasks View: Track all Redmine tasks with actual timestamps directly from Redmine, categorized into statuses including overdue, blocked, in progress, and completed."*
  - *"Acceptance Criteria: Tasks view displays all tasks with original Redmine timestamps, properly categorized by status (overdue, blocked, in progress, completed)."*
- **Current Implementation Gap**:
  1. **Missing Actual Redmine Timestamps**:
     - Only `due_date` is displayed (or "None").
     - Redmine's actual creation timestamp (`created_on`) and last updated timestamp (`updated_on`) are not rendered in the table.
     - `TaskItem` interface does not include `created_at` or `updated_at`.
  2. **Status Normalization Sensitivity**:
     - `IN_PROGRESS` filter strictly checks `t.status === "In Progress"`. Tasks with status "Feedback", "In Development", or lowercase are missed unless mapped.

---

### 2.5 Manual Synchronization ("Sync Redmine Now") Flow

#### Implementation Location
1. **`src/components/views/ProjectsView.tsx:46-66`**:
   - Header button: `<button onClick={handleSyncNow} disabled={isSyncing}>`
   - Calls: `POST http://localhost:8000/api/v1/redmine/sync/trigger`
   - User notification: Displays a banner with `data.summary` counts for 6 seconds.
   - View refresh: Calls `await fetchProjects()` immediately upon sync completion.
2. **`src/components/views/AdminView.tsx:118-140`**:
   - Card button: `<button onClick={handleSyncRedmine} disabled={isSyncing}>`
   - Calls: `POST http://localhost:8000/api/v1/redmine/sync/trigger`
   - User notification: Displays `statusNotice` banner for 6 seconds.
   - View refresh: Calls `await fetchRedmineStatus()`.

#### Limitations & Deficiencies
- **No Global Sync Button**: Sync can only be triggered from the Projects or Admin tabs. If an operator is in Teams, Employees, or Tasks, there is no manual sync button.
- **No Cross-Tab Invalidation**: When sync completes in ProjectsView, the top-level KPI metrics in `page.tsx` (`dashboardData`) are NOT refreshed unless the user clicks the "Refresh" button on the dashboard.
- **Error Handling**: Network errors produce a generic banner message ("Error connecting to backend server") without retries or diagnostics.

---

### 2.6 Notification & Alerting Interface (`NotificationModal.tsx` & `AdminView.tsx`)

#### Compliance Gap with Requirement R2
- **Authoritative Requirement**:
  - *"Remove legacy dispatch settings and interfaces."*
  - *"Categorize alert messages based on Redmine categories into urgent messages, critical, and completed/closed states with filter tabs/pills in the UI."*
  - *"Deliver all urgent and critical alert notifications exclusively via SMTP email to anil.aiindia@gmail.com."*
- **Current Implementation Gap**:
  1. **Missing Category Filter Tabs/Pills**: `NotificationModal.tsx` lists alerts sequentially without category filter pills (`urgent`, `critical`, `completed/closed`).
  2. **Legacy Dispatch Interfaces Present**:
     - `NotificationModal.tsx:228-283` contains a collapsible "Dispatch Custom Test Alert" form (`testTitle`, `testMessage`, `severity`).
     - `AdminView.tsx:183-320` contains the legacy "Default Alert Recipient & Dispatch Routing" card with "Dispatch Channels (Separately Tracked)" and Google Chat Webhook URL input.
     - Per R2 and Acceptance Criteria, these custom dispatch configuration cards must be completely removed.

---

## 3. Build & Lint Verification Results

### 3.1 Next.js Production Build (`npm run build`)
- **Status**: **PASS (Exit code 0)**
- **Output Details**:
  ```
  > frontend@0.1.0 build
  > next build

     ▲ Next.js 15.1.7

     Creating an optimized production build ...
   ✓ Compiled successfully
     Skipping linting
     Checking validity of types ...
     Collecting page data ...
   ✓ Generating static pages (5/5)
     Finalizing page optimization ...
     Collecting build traces ...

  Route (app)                              Size     First Load JS
  ┌ ○ /                                    17.8 kB         123 kB
  └ ○ /_not-found                          979 B           106 kB
  + First Load JS shared by all            105 kB
    ├ chunks/4bd1b696-42d6eb02049d68c2.js  52.9 kB
    ├ chunks/517-95f59670fc8c76d6.js       50.5 kB
    └ other shared chunks (total)          1.95 kB

  ○  (Static)  prerendered as static content
  ```
- **Assessment**: TypeScript compilation passes cleanly without type errors.

### 3.2 Lint Verification (`npm run lint`)
- **Status**: **FAIL (Exit code 1)**
- **Verbatim Error Output**:
  ```
  > frontend@0.1.0 lint
  > eslint

  Oops! Something went wrong! :(

  ESLint: 9.39.5

  Error [ERR_MODULE_NOT_FOUND]: Cannot find module 'C:\Users\Anil Abhange\Downloads\intelligent_projects_manager\frontend\node_modules\eslint-config-next\core-web-vitals' imported from C:\Users\Anil Abhange\Downloads\intelligent_projects_manager\frontend\eslint.config.mjs
  Did you mean to import "eslint-config-next/core-web-vitals.js"?
  ```
- **Root Cause**: In `frontend/eslint.config.mjs:2-3`:
  ```javascript
  import nextVitals from "eslint-config-next/core-web-vitals";
  import nextTs from "eslint-config-next/typescript";
  ```
  Because `eslint.config.mjs` is an ES module and `eslint-config-next` lacks an `exports` subpath mapping in `package.json`, Node ESM requires explicit `.js` extensions:
  ```javascript
  import nextVitals from "eslint-config-next/core-web-vitals.js";
  import nextTs from "eslint-config-next/typescript.js";
  ```

---

## 4. Synthesis of Primary Deficiencies & Remediation Recommendations

| Primary View / Area | Current State | Authoritative Requirement (R1/R2) | Required Remediation |
|---|---|---|---|
| **Projects View** | Displays project cards, health metrics, and tasks progress. | Display all synchronized Redmine projects with correct status, health metrics, and metadata without empty state when data exists. | Enhance error handling in fetch so network/auth errors show distinct error banners rather than "No projects found". Ensure default admin account is seeded to avoid 401. |
| **Teams View** | Renders static pre-seeded teams (`Team` table) with project name tags. No team member names or roles. | Group and render team members project-wise based on Redmine memberships and role allocations. | 1. Update Redmine sync to fetch project memberships (`/projects/{id}/memberships.json`) into `project_members`.<br>2. Add backend endpoint `GET /api/v1/teams/project-wise` (or include members in projects/teams API).<br>3. Refactor `TeamsView.tsx` to group by Project, rendering member cards with their Redmine role badges (e.g. Manager, Developer, QA). |
| **Employees View** | Renders name, email, department, and task counts. Status is in interface but not rendered. | Visual dashboards displaying employee status, current project assignments, and workload distribution. | 1. Add status badge (Active/Inactive) to each card.<br>2. Fetch and render assigned projects per employee.<br>3. Add visual workload distribution gauge / bar (allocated hours vs 40h capacity and calculated Workload Score). |
| **Tasks View** | Renders task table with `due_date` only. | Track all Redmine tasks with actual timestamps directly from Redmine, categorized into statuses (overdue, blocked, in progress, completed). | 1. Include Redmine `created_at` (created_on) and `updated_at` (updated_on) in backend `tasks.py` response.<br>2. Update `TaskItem` interface and render original Redmine timestamps in `TasksView.tsx`.<br>3. Ensure status categorization covers all Redmine status variations. |
| **Sync Redmine Button** | Present in Projects and Admin views with 6s toast and local view refresh. | Manual on-demand synchronization ("Sync Redmine Now") with proper refresh. | Add a global Sync button in TopNav or provide consistent sync triggers across views; notify dashboard to reload KPIs. |
| **Notification Panel** | No category filter pills; legacy test dispatch form present. | Category filtering tabs/pills (urgent, critical, completed/closed); remove legacy custom dispatch configuration cards. | 1. Add filter pills for Urgent, Critical, and Completed/Closed.<br>2. Remove the collapsible custom test dispatch form in `NotificationModal.tsx`.<br>3. Remove legacy custom dispatch configuration card in `AdminView.tsx`. |
| **Build & Lint** | `next build` passes; `npm run lint` fails on ESM import. | Clean build and lint (`npm run build`, `npm run lint`). | Fix `eslint.config.mjs` imports by appending `.js` (`core-web-vitals.js`, `typescript.js`). |
| **API Architecture** | Hardcoded `http://localhost:8000/api/v1/...` in all views. | Resilient and production-ready configuration. | Centralize API base URL using `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`. |

---
*Report compiled by Explorer 2 (Frontend Views Explorer)*
