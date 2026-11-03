#!/usr/bin/env python3
"""
Intelligent Projects Manager - Production E2E Test Suite Runner
Runs the full 4-tier E2E testing matrix and outputs an executive summary.
Usage:
    python run_e2e_tests.py
    python run_e2e_tests.py --tier 1
    python run_e2e_tests.py --tier 2
    python run_e2e_tests.py --tier 3
    python run_e2e_tests.py --tier 4
"""

import sys
import os
import time
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Run Intelligent Projects Manager E2E Test Suite")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only a specific tier")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose pytest output")
    args = parser.parse_args()

    # Ensure backend directory is in path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)

    print("=" * 80)
    print(" INTELLIGENT PROJECTS MANAGER - E2E PRODUCTION VERIFICATION SUITE")
    print("=" * 80)
    print(f"Working Directory: {backend_dir}")
    print(f"Python Executable: {sys.executable}")
    print(f"Timestamp:         {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("-" * 80)

    tier_map = {
        1: ("Tier 1: Feature Coverage (40 tests across 8 core features)", "tests/e2e/test_tier1_features.py"),
        2: ("Tier 2: Boundary & Corner Cases (8 tests)", "tests/e2e/test_tier2_boundaries.py"),
        3: ("Tier 3: Cross-Feature Combinations (5 tests)", "tests/e2e/test_tier3_combinations.py"),
        4: ("Tier 4: Real-World Scenarios (4 tests)", "tests/e2e/test_tier4_real_world.py")
    }

    tiers_to_run = [args.tier] if args.tier else [1, 2, 3, 4]

    results = []
    overall_start = time.time()
    total_passed = 0
    total_failed = 0

    for tier_num in tiers_to_run:
        name, test_file = tier_map[tier_num]
        print(f"\n[RUNNING] {name}...")
        tier_start = time.time()

        pytest_cmd = [sys.executable, "-m", "pytest", test_file]
        if args.verbose:
            pytest_cmd.append("-v")
        else:
            pytest_cmd.append("-q")

        res = subprocess.run(pytest_cmd, capture_output=True, text=True)
        elapsed = time.time() - tier_start

        passed = res.returncode == 0
        status_label = "PASS" if passed else "FAIL"
        
        # Parse pytest output
        output_line = res.stdout.strip().split("\n")[-1] if res.stdout.strip() else ""
        if not output_line and res.stderr:
            output_line = res.stderr.strip().split("\n")[-1]

        results.append({
            "tier": tier_num,
            "name": name,
            "status": status_label,
            "elapsed": elapsed,
            "summary": output_line,
            "stdout": res.stdout,
            "stderr": res.stderr
        })

        if passed:
            print(f"  --> [{status_label}] Completed in {elapsed:.2f}s ({output_line})")
        else:
            print(f"  --> [{status_label}] Failed in {elapsed:.2f}s")
            print(f"\nPytest Output:\n{res.stdout}\n{res.stderr}")

    total_elapsed = time.time() - overall_start

    print("\n" + "=" * 80)
    print(" E2E VERIFICATION SUITE SUMMARY")
    print("=" * 80)
    print(f"{'Tier':<8} | {'Status':<6} | {'Time':<8} | {'Description'}")
    print("-" * 80)
    all_passed = True
    for r in results:
        if r["status"] != "PASS":
            all_passed = False
        print(f"Tier {r['tier']:<3} | {r['status']:<6} | {r['elapsed']:>6.2f}s | {r['name']}")

    print("-" * 80)
    print(f"Total Execution Time: {total_elapsed:.2f}s")
    print(f"Overall Result:       {'ALL TIERS PASSED (100% OPERATIONAL)' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 80)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
