# E2E Testing Infrastructure (TEST_INFRA.md)
## Intelligent Projects Manager Platform

---

## 1. Dual Track Testing Architecture

The Intelligent Projects Manager uses a **Dual Track Engineering & Testing Strategy** that decouples feature implementation from comprehensive requirement-driven end-to-end verification. The E2E testing infrastructure acts as an independent authoritative oracle, validating functional correctness, data fidelity, interface contracts, and system invariants.

### Dual Track Principles
1. **Opaque-Box Requirement Verification**: Tests interact with the platform through HTTP API endpoints and verified database ground truth, asserting against interface contracts rather than internal implementation details.
2. **Progressive Testability**: Tests run against available milestone endpoints and verify backward compatibility without breaking on future planned interfaces.
3. **Deterministic & Resilient**: Real external services (Redmine REST API, OpenRouter AI, SMTP/Google Chat notifications) are tested both with live integration and resilient test fixtures.
4. **Authoritative Invariants**:
   - **Admin Google Chat / SMTP Mirroring**: Operational alerts are tracked with delivery records.
   - **Zero Hallucination AI Grounding**: Assistant answers are strictly verified against real database records.
   - **RBAC Boundary Enforcement**: Single-User Admin Mode and token authorization guard sensitive operations.
   - **Historical Continuity**: Data updates and re-syncs preserve historical contributions and timestamps.

---

## 2. 4-Tier Testing Methodology

```
+---------------------------------------------------------------------------------+
|                         TIER 4: REAL-WORLD SCENARIOS                            |
| (Redmine Delta Sync, Blocker Escalation, Workload Rebalance, Executive AI Chat) |
+---------------------------------------------------------------------------------+
|                   TIER 3: CROSS-FEATURE INTEGRATION FLOWS                       |
|   (Sync -> Project -> Team -> Employee -> Task; Blocker -> Notification Flow)   |
+---------------------------------------------------------------------------------+
|                     TIER 2: BOUNDARY & CORNER CASES                             |
| (Invalid IDs, Boundary Dates, Empty Filters, Extreme Payloads, Auth Violations) |
+---------------------------------------------------------------------------------+
|                       TIER 1: CORE FEATURE COVERAGE                             |
|    (>= 5 tests per feature: Projects, Teams, Employees, Tasks, Sync, Notif,     |
|                             AI Grounding, Admin Config)                         |
+---------------------------------------------------------------------------------+
```

---

## 3. Tier Specifications & Test Inventory

### Tier 1: Core Feature Coverage (>=5 tests per feature, 40+ tests total)

| Feature | Scope & Endpoint | Primary Test Cases |
|---------|------------------|--------------------|
| **1. Projects View** | `GET /api/v1/projects/` | 1. `test_projects_list_structure_and_status`<br>2. `test_projects_health_status_and_reasons`<br>3. `test_projects_task_metrics_aggregation`<br>4. `test_projects_progress_percentage_bounds`<br>5. `test_projects_start_and_target_dates` |
| **2. Teams View** | `GET /api/v1/teams/` | 1. `test_teams_list_structure_and_attributes`<br>2. `test_teams_project_association_and_health`<br>3. `test_teams_members_count_and_composition`<br>4. `test_teams_active_status_filtering`<br>5. `test_teams_department_categorization` |
| **3. Employees View** | `GET /api/v1/employees/` | 1. `test_employees_list_roster_data_fidelity`<br>2. `test_employees_weekly_capacity_and_workload`<br>3. `test_employees_task_metrics_correlation`<br>4. `test_employees_department_and_job_title`<br>5. `test_employees_active_status_reporting` |
| **4. Tasks View** | `GET /api/v1/tasks/`<br>`POST /api/v1/tasks/{id}/toggle-blocker` | 1. `test_tasks_list_fidelity_and_attributes`<br>2. `test_tasks_project_id_filtering`<br>3. `test_tasks_overdue_flag_filtering`<br>4. `test_tasks_blocked_flag_filtering`<br>5. `test_tasks_toggle_blocker_operational_trigger` |
| **5. Redmine Sync Engine** | `GET /api/v1/redmine/status`<br>`POST /api/v1/redmine/sync/trigger` | 1. `test_redmine_status_connectivity`<br>2. `test_redmine_manual_sync_trigger_execution`<br>3. `test_redmine_sync_summary_response_schema`<br>4. `test_redmine_sync_watermark_state_persistence`<br>5. `test_redmine_repeated_sync_idempotency` |
| **6. Notifications & Alerting** | `GET /api/v1/notifications/`<br>`POST /api/v1/notifications/trigger`<br>`PATCH /api/v1/notifications/{id}/read`<br>`POST /api/v1/notifications/read-all`<br>`POST /api/v1/notifications/generate-alerts` | 1. `test_notifications_list_retrieval`<br>2. `test_notifications_manual_trigger_creation`<br>3. `test_notifications_mark_single_as_read`<br>4. `test_notifications_mark_all_as_read`<br>5. `test_notifications_automated_alerts_scan` |
| **7. AI Assistant Grounding** | `POST /api/v1/ai/chat`<br>`AIService.get_grounded_context` | 1. `test_ai_chat_grounded_response_flag`<br>2. `test_ai_chat_conversation_history_handling`<br>3. `test_ai_grounded_context_projects_extraction`<br>4. `test_ai_grounded_context_overdue_tasks_extraction`<br>5. `test_ai_grounded_context_employee_extraction` |
| **8. Admin Settings & Config** | `GET /api/v1/admin/recipient-config`<br>`PUT /api/v1/admin/recipient-config` | 1. `test_admin_get_recipient_config_defaults`<br>2. `test_admin_update_recipient_email`<br>3. `test_admin_update_recipient_name`<br>4. `test_admin_toggle_notification_channels`<br>5. `test_admin_update_google_chat_webhook_url` |

---

### Tier 2: Boundary & Corner Cases
1. **Nonexistent / Invalid IDs**: Requesting operations on unknown task IDs, project IDs, or malformed UUID strings returns clean 404/422 responses.
2. **Boundary Dates**: Handling epoch dates (`1970-01-01`), far-future dates (`2099-12-31`), leap year dates, and same-day deadlines without time-zone drift.
3. **Empty Data & Empty Filter Sets**: Querying tasks or projects with zero matches returns empty JSON arrays (`[]`) rather than 500 errors.
4. **Extreme Payloads & Unicode**: Handling large text payloads, emojis, non-ASCII characters, and HTML tags in blocker reasons and notification titles.
5. **Unauthorized Access & Auth Token Handling**: Validating access with valid Bearer token, missing token, and corrupted token.
6. **Zero-Capacity & Decimal Workload Calculations**: Handling employees with 0 weekly capacity or fractional task hours without division-by-zero errors.

---

### Tier 3: Cross-Feature Integration Combinations
1. **Sync -> Project -> Team -> Employee -> Task Pipeline**:
   Triggering delta sync verifies that projects map to internal DB, team memberships link employees, and tasks calculate project metrics.
2. **Task Blocker -> Automated Alert -> Delivery Audit**:
   Flagging a task as blocked (`toggle-blocker`) immediately creates a `CRITICAL` notification and registers delivery records.
3. **Overdue Task -> Automated Alert Scan -> Notification Feed -> Read Flow**:
   Creating an overdue task, triggering `/notifications/generate-alerts`, checking the notification appears in the feed, and marking it as read.
4. **Admin Recipient Config -> Notification Dispatch Parameterization**:
   Updating the recipient configuration from Admin Settings and verifying subsequent notifications use the updated parameters.
5. **Task Completion -> Project Metrics Recalculation**:
   Resolving a task updates project completed task counts and clears overdue flags.

---

### Tier 4: Real-World Scenarios
1. **Redmine Delta Update Scenario**:
   Simulates operational updates where project status or task descriptions change in Redmine, and subsequent delta sync updates local models without duplicating records.
2. **High-Priority Blocker Escalation Scenario**:
   An engineer flags a blocker on an immediate-priority task, triggering executive-level notifications and alerting the administrator.
3. **Employee Workload & Capacity Rebalancing Scenario**:
   Demonstrates assigning tasks between team members, verifying employee workload metrics reflect updated allocations.
4. **Executive Management AI Query Scenario**:
   Simulates an administrator asking the AI assistant for an operational summary of project statuses and overdue tasks, verifying zero-hallucination ground truth.

---

## 4. Directory Layout

```
backend/
├── pytest.ini                      # Pytest config (testpaths, pythonpath, asyncio scope)
├── run_e2e_tests.py                # Standalone E2E Test Suite Runner CLI
└── tests/
    ├── conftest.py                 # Core fixtures
    ├── e2e/
    │   ├── conftest.py             # E2E shared fixtures & seed helpers
    │   ├── test_tier1_features.py  # Tier 1: 40 Core Feature Tests (>=5 per feature)
    │   ├── test_tier2_boundaries.py# Tier 2: Boundary & Corner Cases
    │   ├── test_tier3_combinations.py # Tier 3: Cross-Feature Integration Flows
    │   └── test_tier4_real_world.py   # Tier 4: Real-World Scenarios
```

---

## 5. Execution & Verification

### Running Pytest Directly:
```bash
# Run full E2E test suite
cd backend
.\venv\Scripts\pytest tests/e2e -v

# Run a specific tier
.\venv\Scripts\pytest tests/e2e/test_tier1_features.py -v
.\venv\Scripts\pytest tests/e2e/test_tier2_boundaries.py -v
.\venv\Scripts\pytest tests/e2e/test_tier3_combinations.py -v
.\venv\Scripts\pytest tests/e2e/test_tier4_real_world.py -v
```

### Running Standalone Runner:
```bash
cd backend
.\venv\Scripts\python run_e2e_tests.py
```
