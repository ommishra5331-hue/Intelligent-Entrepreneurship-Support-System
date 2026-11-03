"""Parallel execution of independent operations.

[CA&PP | Unit 4 - Parallel Processing]
  * Software-level MIMD (Flynn): different workers run different operations on different data.
  * Only INDEPENDENT work is parallel: one report per department, one notification per employee.
  * Stages of ONE task and updates to the SAME record stay sequential / lock-protected (store.py).
  * `work` simulates the time a heavy report or a network call takes (I/O-bound work, so Python
    threads really overlap). For CPU-bound work use multiprocessing because of the GIL.
"""
import time
from concurrent.futures import ThreadPoolExecutor


def build_report(store, department, work=0.0):
    if work:
        time.sleep(work)
    counts = {}
    for t in store.all_tasks():
        emp = store.employees.get(t.assignee)
        if emp and emp.department == department:
            counts[t.status] = counts.get(t.status, 0) + 1
    return {"department": department, "total": sum(counts.values()), "by_status": dict(sorted(counts.items()))}


def generate_reports(store, departments, workers=1, work=0.0):
    with ThreadPoolExecutor(max_workers=workers) as pool:        # p = workers processing units
        return list(pool.map(lambda d: build_report(store, d, work), departments))


def notify_all(store, text, workers=1, work=0.0):
    def send(emp):
        if work:
            time.sleep(work)
        return f"to {emp.name} ({emp.emp_id}): {text}"
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(send, list(store.employees.values())))


def timed(fn, *args, **kw):
    t0 = time.perf_counter()
    out = fn(*args, **kw)
    return out, time.perf_counter() - t0
