import urllib.request
import json

base_url = "https://redmine.aiindia.ai"
headers = {"User-Agent": "Mozilla/5.0"}

print("--- Testing Redmine Public Endpoints ---")
for endpoint in ["/projects.json?limit=100", "/issues.json?limit=20"]:
    url = base_url + endpoint
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            key = "projects" if "projects" in endpoint else "issues"
            items = data.get(key, [])
            print(f"Endpoint {endpoint} -> Status 200, Found {len(items)} {key}")
            for item in items[:5]:
                name = item.get("name") or item.get("subject")
                print(f"  - [{item.get('id')}] {name}")
    except Exception as e:
        print(f"Endpoint {endpoint} -> Error: {e}")

print("\n--- Detailed Issue Inspection ---")
req = urllib.request.Request("https://redmine.aiindia.ai/issues.json?include=journals", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for issue in data.get("issues", [])[:3]:
            print(f"Issue #{issue.get('id')}: {issue.get('subject')}")
            print(f"  Project: {issue.get('project')}")
            print(f"  Assigned: {issue.get('assigned_to')}")
            print(f"  Author: {issue.get('author')}")
            print(f"  Status: {issue.get('status')}")
            print(f"  Due: {issue.get('due_date')}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- All Issues (status_id=*) ---")
req = urllib.request.Request("https://redmine.aiindia.ai/issues.json?status_id=*&limit=100", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Total issues found: {len(data.get('issues', []))}")
        for issue in data.get("issues", []):
            print(f"  - #{issue.get('id')} [{issue.get('status', {}).get('name')}] {issue.get('subject')} (Assigned: {issue.get('assigned_to', {}).get('name', 'Unassigned')}, Due: {issue.get('due_date')})")
except Exception as e:
    print(f"Error: {e}")
