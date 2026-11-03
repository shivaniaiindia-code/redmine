---
name: employee-360-growth
description: >-
  Use this skill whenever developing, modifying, or querying Employee 360 profiles,
  historical project contributions, career growth ladders, skills matrices, or capacity allocation.
---

# Employee 360 & Historical Continuity Skill

This skill ensures that individual employee contributions are permanently retained and that professional development, workload balance, and skills tracking remain accurate across organizational changes.

---

## 1. Historical Continuity Invariant

```mermaid
flowchart LR
    E[Employee: Sarah Connor] -->|2024-Q1| PRJ1[Project: ANPR System<br/>Deliverable: Custom OCR Pipeline<br/>Tasks: 42 | Hours: 180h]
    E -->|2024-Q3| PRJ2[Project: Mobile App<br/>Deliverable: Auth & Biometrics<br/>Tasks: 28 | Hours: 120h]
    
    CHANGE[Reassigned to New Team: 'AI Research'] -.->|Assignment Changes| E
    
    PRJ1 & PRJ2 ==> HIST[(historical_contributions Table<br/>PERMANENTLY RETAINED)]
```

### Invariant Rules:
1. **Never Orphan Historical Records**: When an employee transitions between teams or is removed from an active project, their historical milestones, completed tasks, and logged hours in `historical_contributions` remain permanently accessible on their profile.
2. **Immutable Achievement Logs**: An employee's past deliverables cannot be retroactively altered without an authorized audit log entry.

---

## 2. Workload & True Burnout Index

In enterprise intelligence platforms, workload is evaluated through a multi-factor calculation:

$$\text{Workload Score} = \left(\frac{\text{Allocated Hours}}{\text{Weekly Capacity}}\right) \times \left(1 + 0.15 \times (\text{Active Projects} - 1)\right)$$

- **Context-Switching Penalty**: Being assigned to 4 concurrent projects introduces cognitive fragmentation, reflected by the context multiplier.
- **Overload Threshold**: When score exceeds 1.25 (or hours > 45h/week), a `WORKLOAD_EXCEEDED` warning is automatically dispatched to the team lead.

---

## 3. Skills Matrix & Career Progression Ladder

- Each skill belongs to an engineering taxonomy (e.g., Python, PyTorch, Next.js, Kubernetes).
- Demonstrations are tied to delivered tasks (e.g. "Completed 12 PyTorch tasks with 99% accuracy").
- Career ladder milestones: Junior -> Mid -> Senior -> Staff / Lead with clear expectations.

