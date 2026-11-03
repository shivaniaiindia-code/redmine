# AGENTS.md
## Autonomous Agent Guidelines for Intelligent Projects Manager

This file provides root-level operating instructions for autonomous coding agents (Antigravity, Cursor, Gemini, Claude) operating in this codebase.

---

## 1. Operating Protocol
1. **Source of Truth**: All architectural designs, database schemas, API specs, and implementation roadmaps are maintained in [`docs/`](./docs/).
2. **Master Guidelines**: Read [`CLAUDE.md`](./CLAUDE.md) before writing or refactoring any code.
3. **Workspace Skills**: Specialized runbooks for each agent are available in [`.agents/skills/`](./.agents/skills/):
   - `company-intel-workflow`: Main Orchestrator Agent phase-by-phase quality gates.
   - `project-manager`: Planning, milestones, risk register, RACI matrix, and closure (Asana + VoltAgent).
   - `frontend-dashboard`: Frontend Agent Next.js 14 App Router, Recharts, design tokens.
   - `backend-fastapi-rbac`: Backend Agent FastAPI routes, async SQLAlchemy 2.0, RBAC guards.
   - `redmine-sync`: Redmine Agent API discovery, delta watermarking, journals history, and offline resilience.
   - `notification-google-chat`: Notification Agent System Notification Bar + Admin Google Chat Mirroring.
   - `ai-openrouter-grounding`: AI Agent OpenRouter gateway, deterministic tools, and source citations.
   - `qa-security-testing`: QA Agent pytest fixtures, RBAC penetration, and API validation.
   - `employee-360-growth`: Employee 360, career ladder rubrics, and historical continuity.

---

## 2. Critical System Invariants
- **Admin Google Chat Mirroring**: Every notification in the System Notification Bar **MUST** be mirrored 1:1 to the Administrator's Google Chat webhook.
- **Zero Hallucination**: AI queries must be answered using pre-authorized Python tools with deterministic database calculations. Never fabricate employee records or project health percentages.
- **RBAC Enforcement**: All API routes and tool calls must validate the caller's JWT token and enforce strict role boundaries.
- **Historical Continuity**: Never delete or orphan an employee's historical contributions when team assignments change.

