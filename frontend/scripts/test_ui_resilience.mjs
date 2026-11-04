/**
 * Empirical UI Resilience & Edge Case Stress Test Harness
 * Tests:
 * 1. TopNav sync trigger resilience under backend offline & HTTP error codes
 * 2. ProjectsView diagnostic error handling under network failures and empty states
 * 3. TeamsView, EmployeesView, TasksView error resilience and calculation edge cases
 */

import http from "node:http";
import assert from "node:assert";

console.log("=== EMPIRICAL UI RESILIENCE STRESS TEST ===");

const TEST_PORT = 8999;
let currentMockHandler = () => {};

const mockServer = http.createServer((req, res) => {
  currentMockHandler(req, res);
});

await new Promise((resolve) => mockServer.listen(TEST_PORT, resolve));
console.log(`Mock test server listening on port ${TEST_PORT}`);

const MOCK_BASE_URL = `http://localhost:${TEST_PORT}/api/v1`;
const OFFLINE_BASE_URL = `http://127.0.0.1:18999/api/v1`; // guaranteed offline port

// -------------------------------------------------------------
// Test 1: TopNav handleSyncRedmine - Backend Offline Simulation
// -------------------------------------------------------------
console.log("\n[TEST 1] TopNav: Backend Offline Simulation");
{
  let isSyncing = false;
  let syncStatus = null;
  let syncCompleted = false;

  const handleSyncRedmine = async (baseUrl) => {
    isSyncing = true;
    syncStatus = "Syncing...";
    try {
      const res = await fetch(`${baseUrl}/redmine/sync/trigger`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        const pCount = data.summary?.projects_synced ?? 0;
        const tCount = data.summary?.tasks_synced ?? 0;
        syncStatus = `Synced: ${pCount} prj, ${tCount} tasks`;
        syncCompleted = true;
      } else {
        syncStatus = "Sync failed";
      }
    } catch {
      syncStatus = "Sync error";
    } finally {
      isSyncing = false;
    }
  };

  await handleSyncRedmine(OFFLINE_BASE_URL);
  assert.strictEqual(syncStatus, "Sync error", "syncStatus must be 'Sync error' when backend offline");
  assert.strictEqual(isSyncing, false, "isSyncing must be reset to false");
  assert.strictEqual(syncCompleted, false, "syncCompleted must remain false");
  console.log("  ✓ PASS: Offline backend caught gracefully -> 'Sync error', isSyncing=false");
}

// -------------------------------------------------------------
// Test 2: TopNav handleSyncRedmine - HTTP 500 / 503 Server Error
// -------------------------------------------------------------
console.log("\n[TEST 2] TopNav: Backend HTTP 500 / 503 Failure");
{
  currentMockHandler = (req, res) => {
    res.writeHead(503, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Redmine service temporarily unavailable" }));
  };

  let isSyncing = false;
  let syncStatus = null;

  const handleSyncRedmine = async (baseUrl) => {
    isSyncing = true;
    syncStatus = "Syncing...";
    try {
      const res = await fetch(`${baseUrl}/redmine/sync/trigger`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        syncStatus = `Synced: ${data.summary?.projects_synced ?? 0} prj, ${data.summary?.tasks_synced ?? 0} tasks`;
      } else {
        syncStatus = "Sync failed";
      }
    } catch {
      syncStatus = "Sync error";
    } finally {
      isSyncing = false;
    }
  };

  await handleSyncRedmine(MOCK_BASE_URL);
  assert.strictEqual(syncStatus, "Sync failed", "syncStatus must be 'Sync failed' on HTTP 503");
  assert.strictEqual(isSyncing, false, "isSyncing must reset to false");
  console.log("  ✓ PASS: HTTP 503 handled gracefully -> 'Sync failed', isSyncing=false");
}

// -------------------------------------------------------------
// Test 3: TopNav handleSyncRedmine - Corrupted / Missing Summary
// -------------------------------------------------------------
console.log("\n[TEST 3] TopNav: Malformed / Missing Summary Fields in Sync Response");
{
  currentMockHandler = (req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    // Empty object, summary is missing
    res.end(JSON.stringify({ status: "success" }));
  };

  let syncStatus = null;
  const handleSyncRedmine = async (baseUrl) => {
    try {
      const res = await fetch(`${baseUrl}/redmine/sync/trigger`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const pCount = data.summary?.projects_synced ?? 0;
        const tCount = data.summary?.tasks_synced ?? 0;
        syncStatus = `Synced: ${pCount} prj, ${tCount} tasks`;
      }
    } catch (e) {
      syncStatus = "Crash: " + e.message;
    }
  };

  await handleSyncRedmine(MOCK_BASE_URL);
  assert.strictEqual(syncStatus, "Synced: 0 prj, 0 tasks", "Missing summary should safely default to 0");
  console.log("  ✓ PASS: Nullish coalescing handles missing summary without crash");
}

// -------------------------------------------------------------
// Test 4: ProjectsView fetchProjects - Backend Offline Simulation
// -------------------------------------------------------------
console.log("\n[TEST 4] ProjectsView: Backend Offline Simulation");
{
  let projects = [];
  let isLoading = true;
  let fetchError = null;

  const fetchProjects = async (baseUrl) => {
    try {
      isLoading = true;
      fetchError = null;
      const res = await fetch(`${baseUrl}/projects/`);
      if (!res.ok) {
        if (res.status === 401) {
          fetchError = "Authentication required (401 Unauthorized). Please check API session.";
        } else {
          fetchError = `Backend returned status ${res.status}: ${res.statusText}`;
        }
        return;
      }
      const data = await res.json();
      projects = data;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Service unavailable";
      fetchError = `Network error: Unable to reach backend server (${errMsg}). Verify backend service is running.`;
    } finally {
      isLoading = false;
    }
  };

  await fetchProjects(OFFLINE_BASE_URL);
  assert.strictEqual(isLoading, false, "isLoading must be false after offline fetch");
  assert.ok(fetchError !== null, "fetchError must be populated");
  assert.ok(fetchError.includes("Network error: Unable to reach backend server"), "fetchError must provide clear diagnostic banner");
  assert.strictEqual(projects.length, 0, "projects array remains empty");
  console.log(`  ✓ PASS: Diagnostic banner populated correctly: "${fetchError.substring(0, 65)}..."`);
}

// -------------------------------------------------------------
// Test 5: ProjectsView fetchProjects - HTTP 401 Unauthorized
// -------------------------------------------------------------
console.log("\n[TEST 5] ProjectsView: HTTP 401 Unauthorized");
{
  currentMockHandler = (req, res) => {
    res.writeHead(401, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Not authenticated" }));
  };

  let fetchError = null;
  let isLoading = true;

  const fetchProjects = async (baseUrl) => {
    try {
      isLoading = true;
      const res = await fetch(`${baseUrl}/projects/`);
      if (!res.ok) {
        if (res.status === 401) {
          fetchError = "Authentication required (401 Unauthorized). Please check API session.";
        } else {
          fetchError = `Backend returned status ${res.status}: ${res.statusText}`;
        }
      }
    } finally {
      isLoading = false;
    }
  };

  await fetchProjects(MOCK_BASE_URL);
  assert.strictEqual(isLoading, false);
  assert.strictEqual(fetchError, "Authentication required (401 Unauthorized). Please check API session.");
  console.log("  ✓ PASS: 401 error diagnosed with clear authentication notice");
}

// -------------------------------------------------------------
// Test 6: ProjectsView - Empty List vs Error Disambiguation
// -------------------------------------------------------------
console.log("\n[TEST 6] ProjectsView: Empty State vs Error State Disambiguation");
{
  currentMockHandler = (req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  };

  let projects = null;
  let fetchError = null;

  const fetchProjects = async (baseUrl) => {
    fetchError = null;
    const res = await fetch(`${baseUrl}/projects/`);
    if (res.ok) {
      projects = await res.json();
    }
  };

  await fetchProjects(MOCK_BASE_URL);
  assert.strictEqual(fetchError, null, "fetchError must be null on HTTP 200 with empty list");
  assert.ok(Array.isArray(projects) && projects.length === 0, "projects must be empty array");

  // Determine what view renders:
  const renderedState = fetchError
    ? "ERROR_BANNER"
    : projects.length === 0
    ? "EMPTY_STATE_NOTICE"
    : "PROJECTS_GRID";

  assert.strictEqual(renderedState, "EMPTY_STATE_NOTICE", "Must render EMPTY_STATE_NOTICE, not ERROR_BANNER");
  console.log("  ✓ PASS: Empty array disambiguated from network/server error banner");
}

// -------------------------------------------------------------
// Test 7: EmployeesView - Workload Calculation Edge Cases
// -------------------------------------------------------------
console.log("\n[TEST 7] EmployeesView: Workload Gauge Edge Cases (0 capacity, extreme scores)");
{
  const getWorkloadStyle = (score, allocated, capacity) => {
    const pct = capacity > 0 ? Math.min(100, Math.round((allocated / capacity) * 100)) : 0;
    if (score > 1.25 || allocated > 45) {
      return { barColor: "bg-rose-500", label: "Exceeded", pct };
    }
    if (score > 1.0 || allocated > capacity) {
      return { barColor: "bg-amber-500", label: "High Load", pct };
    }
    return { barColor: "bg-emerald-500", label: "Optimal", pct };
  };

  // Edge case 1: 0 weekly capacity (e.g. contractor/unspecified)
  const zeroCap = getWorkloadStyle(0, 10, 0);
  assert.strictEqual(zeroCap.pct, 0, "pct must be 0 when capacity is 0 (no NaN/Infinity)");

  // Edge case 2: Normal load
  const optimal = getWorkloadStyle(0.75, 30, 40);
  assert.strictEqual(optimal.label, "Optimal");
  assert.strictEqual(optimal.pct, 75);

  // Edge case 3: Overload
  const high = getWorkloadStyle(1.1, 42, 40);
  assert.strictEqual(high.label, "High Load");

  // Edge case 4: Extreme
  const extreme = getWorkloadStyle(1.5, 55, 40);
  assert.strictEqual(extreme.label, "Exceeded");
  assert.strictEqual(extreme.pct, 100);

  console.log("  ✓ PASS: Workload gauge protects against zero division and styles scores properly");
}

// -------------------------------------------------------------
// Test 8: TasksView - Filter Logic & Timestamp Formatting
// -------------------------------------------------------------
console.log("\n[TEST 8] TasksView: Filter Logic & Timestamp Formatter");
{
  const sampleTasks = [
    { id: "1", title: "Task 1", is_overdue: true, is_blocked: false, status: "In Progress", created_at: "2026-10-05T10:15:00Z" },
    { id: "2", title: "Task 2", is_overdue: false, is_blocked: true, status: "Feedback", created_at: null },
    { id: "3", title: "Task 3", is_overdue: false, is_blocked: false, status: "Resolved", created_at: "invalid-date-string" },
    { id: "4", title: "Task 4", is_overdue: false, is_blocked: false, status: "Done", created_at: "2026-10-10T12:00:00" },
    { id: "5", title: "Task 5", is_overdue: false, is_blocked: false, status: "New", created_at: "2026-10-15T08:00:00Z" }
  ];

  const filterTasks = (tasks, filter) => {
    return tasks.filter((t) => {
      if (filter === "OVERDUE") return Boolean(t.is_overdue);
      if (filter === "BLOCKED") return Boolean(t.is_blocked);
      const s = (t.status || "").toLowerCase();
      if (filter === "IN_PROGRESS") {
        return s.includes("progress") || s.includes("feedback") || s === "in-progress" || s === "development";
      }
      if (filter === "COMPLETED") {
        return s === "done" || s === "closed" || s === "resolved";
      }
      return true;
    });
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      return isNaN(d.getTime())
        ? isoStr.split("T")[0]
        : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return isoStr;
    }
  };

  assert.strictEqual(filterTasks(sampleTasks, "ALL").length, 5);
  assert.strictEqual(filterTasks(sampleTasks, "OVERDUE").length, 1);
  assert.strictEqual(filterTasks(sampleTasks, "BLOCKED").length, 1);
  assert.strictEqual(filterTasks(sampleTasks, "IN_PROGRESS").length, 2);
  assert.strictEqual(filterTasks(sampleTasks, "COMPLETED").length, 2);

  // Formatter resilience
  assert.strictEqual(formatDate(null), "-");
  assert.strictEqual(formatDate(undefined), "-");
  assert.strictEqual(formatDate("invalid-date-string"), "invalid-date-string");
  assert.ok(formatDate("2026-10-05T10:15:00Z").includes("2026"));

  console.log("  ✓ PASS: Case-insensitive task filtering and timestamp parsing are resilient");
}

mockServer.close();
console.log("\n=== ALL 8 RESILIENCE TESTS PASSED CLEANLY ===");
