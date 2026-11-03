"""Employee Workflow Management System - command line application.

Run:  python main.py              interactive app (login by Employee ID, role based menus)
      python main.py --demo       full scenario: pipeline, cache, parallel reports
      python main.py --benchmark  timings for Section 12 'Evaluation'
      python main.py --tests      the 13 test cases of the report

CA&PP concepts used (tagged in the code as [CA&PP | Unit ...]):
  Unit 3  Control unit & pipelining : pipeline.py   (5-stage workflow, stalls, flush)
  Unit 4  Memory organization       : cache.py, store.py  (cache, main store, archive)
  Unit 4  Parallel processing       : parallel.py, store.py (parallel reports, lock)
"""
import argparse
import os
import sys
from datetime import date, timedelta

import metrics
import testcases
from cache import DirectMappedCache
from parallel import generate_reports, notify_all, timed
from pipeline import WorkflowPipeline
from store import DataStore, seed_sample

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
LATENCY = 0.005          # simulated main-memory access time: 5 ms


def build_system(persist=True):
    if persist and os.path.exists(DATA_FILE):
        store = DataStore.load(DATA_FILE, LATENCY)
    else:
        store = seed_sample(DataStore(LATENCY))
    cache = DirectMappedCache(4)                                  # [Unit 4] cache in front of store
    return store, cache


def ask(prompt):
    return input(prompt).strip()


def ask_int(prompt):
    try:
        return int(ask(prompt))
    except ValueError:
        raise ValueError("Please enter a number")


# ------------------------------------------------------------------ role menus
def admin_menu(store, cache, user):
    print("\n1 Add employee  2 List employees  3 Department reports (parallel)  4 Cache stats  0 Logout")
    c = ask("> ")
    if c == "1":
        store.add_employee(ask_int("Employee ID: "), ask("Name: "), ask("Department: "), ask("Role (employee/manager/admin): "))
        print("Employee added.")
    elif c == "2":
        for e in store.employees.values():
            print(f"  {e.emp_id:>4}  {e.name:<14} {e.department:<6} {e.role}")
    elif c == "3":
        depts = sorted({e.department for e in store.employees.values()})
        reports, secs = timed(generate_reports, store, depts, 4)   # [Unit 4] one worker per department
        for r in reports:
            print(f"  {r['department']:<6} total={r['total']} {r['by_status']}")
        print(f"  generated in parallel in {secs * 1000:.1f} ms")
    elif c == "4":
        print(f"  hits={cache.hits} misses={cache.misses} hit ratio={cache.ratio():.2f} main-store reads={store.reads}")
    return c != "0"


def manager_menu(store, cache, user):
    print("\n1 Create+assign task  2 Approve/reject  3 Run batch through pipeline  4 List tasks  0 Logout")
    c = ask("> ")
    if c == "1":
        tid = ask_int("Task ID: ")
        store.add_task(tid, ask("Title: "), ask("Deadline (YYYY-MM-DD): "), ask_int("Priority 1/2/3: "))
        emp = cache.get(ask_int("Assign to Employee ID: "), store.get_employee)   # [Unit 4] cache lookup
        store.assign(tid, emp)
        print(f"Task {tid} assigned to {emp.name}. Waiting for approval.")
    elif c == "2":
        tid = ask_int("Task ID: ")
        store.approve(tid, user.emp_id, ask("Approve? (y/n): ").lower() == "y")
        print("Decision recorded.")
    elif c == "3":
        run_pipeline_batch(store, cache, user.emp_id, verbose=True)
    elif c == "4":
        for t in sorted(store.all_tasks(), key=lambda t: (t.priority, t.task_id)):
            print(f"  #{t.task_id:<4} P{t.priority} {t.status:<11} -> {t.assignee or '-':<4} {t.title}")
    return c != "0"


def employee_menu(store, cache, user):
    print("\n1 My tasks  2 Update task status  0 Logout")
    c = ask("> ")
    if c == "1":
        for t in store.tasks_of(user.emp_id):
            print(f"  #{t.task_id} {t.title} [{t.status}] due {t.deadline}")
    elif c == "2":
        tid = ask_int("Task ID: ")
        mine = [t.task_id for t in store.tasks_of(user.emp_id)]
        if tid not in mine:
            raise ValueError("You can only update your own tasks")
        status = ask("New status (in_progress/completed): ")
        if status not in ("in_progress", "completed"):
            raise ValueError("Status must be in_progress or completed")
        store.set_status(tid, status)
        print("Status updated.")
    return c != "0"


MENUS = {"admin": admin_menu, "manager": manager_menu, "employee": employee_menu}   # role-based access


def run_pipeline_batch(store, cache, approver_id, verbose=False):
    """Batch of 4 new tasks through the pipeline (one needs extra review, one is rejected once)."""
    base = max([*store.tasks, *store.archive, 200]) + 1
    ids = [e.emp_id for e in store.employees.values() if e.role == "employee"]
    due = (date.today() + timedelta(days=14)).isoformat()
    from pipeline import Job
    jobs = [Job({"task_id": base + i, "title": f"Batch task {i + 1}", "deadline": due, "priority": 1 + i % 3},
                [ids[i % len(ids)], ids[(i + 1) % len(ids)]],
                [False, True] if i == 2 else [], 1 if i == 1 else 0) for i in range(4)]
    p = WorkflowPipeline(store, cache, approver_id)
    r = p.run(jobs)
    if verbose:
        print(p.trace_table())
        print(f"cycles={r['cycles']} stall cycles={r['stall_cycles']} flushed={r['flushes']} completed={r['completed']} failed={r['failed']}")
    return p, r


# ------------------------------------------------------------------- app modes
def interactive():
    store, cache = build_system()
    print("Employee Workflow Management System\nSample logins: 1 admin, 2 or 3 manager, 12/31/33/19 employee")
    try:
        user = store.employees.get(ask_int("Login Employee ID: "))
        if user is None:
            print("Unknown employee ID.")
            return
        print(f"Welcome {user.name} ({user.role})")
        while True:
            try:
                if not MENUS[user.role](store, cache, user):
                    break
            except ValueError as e:                    # validation errors are shown, app continues
                print("Error:", e)
    except (EOFError, KeyboardInterrupt):
        print()
    store.save(DATA_FILE)
    print("Data saved.")


def demo():
    store, cache = seed_sample(DataStore(LATENCY)), DirectMappedCache(4)
    print("== Unit 3: 4 tasks through the 5-stage workflow pipeline (task 3 is rejected once, task 2 needs a review stall) ==")
    p, r = run_pipeline_batch(store, cache, approver_id=2, verbose=True)
    n = 4
    ideal = metrics.pipelined_cycles(n)
    extra = r["cycles"] - ideal - r["stall_cycles"]
    print(f"without pipeline: {metrics.sequential_cycles(n)} units | pipelined ideal: {ideal} units | actual: {r['cycles']} units "
          f"(+{r['stall_cycles']} stall, +{extra} flush/re-fetch after the rejection)")
    print("\n== Unit 4: cache hit/miss on the employee records used by the pipeline ==")
    print(f"hits={cache.hits} misses={cache.misses} hit ratio={cache.ratio():.2f} main-store reads={store.reads}")
    print("\n== Unit 4: department reports and notifications in parallel ==")
    depts = sorted({e.department for e in store.employees.values()})
    for w in (1, 2, 4):
        _, secs = timed(generate_reports, store, depts, w, 0.05)
        print(f"  {w} worker(s): {secs * 1000:6.1f} ms")
    for line in notify_all(store, "Your task status changed", workers=4)[:3]:
        print("  ", line)


def benchmark():
    print("Evaluation timings (copy into Section 12):")
    store = seed_sample(DataStore(LATENCY)); ids = [12, 31, 33, 19, 12, 12, 31, 12] * 25   # repeated use = locality
    _, t_no = timed(lambda: [store.get_employee(i) for i in ids])
    cache = DirectMappedCache(4)
    _, t_c = timed(lambda: [cache.get(i, store.get_employee) for i in ids])
    print(f"  fetch {len(ids)} employee records: no cache {t_no * 1000:.0f} ms | with cache {t_c * 1000:.0f} ms | hit ratio {cache.ratio():.2f}")
    depts = ["IT", "Sales", "HR", "Admin", "Ops", "Finance", "Legal", "Support"]
    for w in (1, 2, 4):
        _, secs = timed(generate_reports, store, depts, w, 0.05)
        print(f"  reports for {len(depts)} departments, {w} worker(s): {secs * 1000:.0f} ms")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true"); ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--tests", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
    elif a.benchmark:
        benchmark()
    elif a.tests:
        sys.exit(__import__("subprocess").call([sys.executable, "testcases.py"]))
    else:
        interactive()
