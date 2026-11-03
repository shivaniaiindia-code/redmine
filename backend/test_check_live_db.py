import urllib.request
import json

print("--- Synced Projects ---")
req = urllib.request.Request("http://localhost:8000/api/v1/projects/")
with urllib.request.urlopen(req) as resp:
    projs = json.loads(resp.read().decode("utf-8"))
    print(f"Total projects in DB: {len(projs)}")
    for p in projs:
        print(f"  [{p['code']}] {p['name']} -> Health: {p['health_status']}, Tasks: {p['total_tasks']}, Overdue: {p['overdue_tasks']}")

print("\n--- Synced Tasks ---")
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/")
with urllib.request.urlopen(req) as resp:
    tasks = json.loads(resp.read().decode("utf-8"))
    print(f"Total tasks in DB: {len(tasks)}")
    for t in tasks[:8]:
        print(f"  #{t['id'][:8]} | {t['title']} | Due: {t['due_date']} | Overdue: {t['is_overdue']} | Assignee: {t['assigned_to']}")

print("\n--- Notifications for Admin ---")
req = urllib.request.Request("http://localhost:8000/api/v1/notifications/")
with urllib.request.urlopen(req) as resp:
    notifs = json.loads(resp.read().decode("utf-8"))
    print(f"Total notifications: {len(notifs)}")
    for n in notifs[:5]:
        print(f"  [{n['severity']}] {n['title']} -> {n['message'][:60]}...")

