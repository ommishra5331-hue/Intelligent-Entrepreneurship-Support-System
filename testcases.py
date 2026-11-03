"""Runs test cases TC-01 ... TC-13 of the report (Section 12) and prints expected vs actual.

Run:  python testcases.py      -> table you can paste into the 'Actual result' column.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import metrics
from cache import DirectMappedCache
from parallel import generate_reports
from pipeline import Job, WorkflowPipeline
from store import DataStore, seed_sample

FUTURE = (date.today() + timedelta(days=30)).isoformat()


def system():
    store = seed_sample(DataStore())
    cache = DirectMappedCache(4)
    return store, cache, WorkflowPipeline(store, cache, approver_id=2)


def jobs(n, start=100, review=None, decisions=None):
    review, decisions = review or {}, decisions or {}
    ids = [12, 31, 33, 19]
    return [Job({"task_id": start + i, "title": f"Task {i}", "deadline": FUTURE, "priority": 2},
                [ids[i % 4], ids[(i + 1) % 4]], list(decisions.get(i, [])), review.get(i, 0)) for i in range(n)]


def run_all():
    R = []
    def add(tid, scenario, expected, actual, ok):
        R.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))

    # [Unit 3] TC-01..TC-04: pipeline timing measured on the real pipeline simulation
    _, _, p = system(); c1 = p.run(jobs(1))["cycles"]
    add("TC-01", "One task through the 5-stage pipeline", "5 time units", f"{c1} time units", c1 == 5)
    seq = 0
    for i in range(4):                       # one after another = no overlap
        _, _, p = system(); seq += p.run(jobs(1, start=100 + i))["cycles"]
    add("TC-02", "4 tasks without pipelining", "20 time units", f"{seq} time units", seq == 20)
    _, _, p = system(); c3 = p.run(jobs(4))["cycles"]
    add("TC-03", "4 tasks, 5-stage pipeline, no hazards", "8 time units; speedup 2.5",
        f"{c3} time units; speedup {seq / c3:.2f}", c3 == 8 and seq / c3 == 2.5)
    _, _, p = system(); r4 = p.run(jobs(4, review={1: 1}))
    add("TC-04", "4 tasks, one 1-unit stall at approval", "9 time units; speedup 2.22",
        f"{r4['cycles']} time units; speedup {seq / r4['cycles']:.2f}", r4["cycles"] == 9 and round(seq / 9, 2) == 2.22)
    st, _, p = system(); r5 = p.run(jobs(3, decisions={0: [False, True]}))
    t100 = st.archive[100]
    add("TC-05", "Approval rejected (3 tasks, task 100 rejected once)",
        "Task re-enters AS; later-stage slots discarded; status shows reassigned",
        f"flushed slots={r5['flushes']}; history={t100.history}; all completed={len(r5['completed']) == 3}",
        r5["flushes"] == 2 and "rejected" in t100.history and t100.history.count("assigned") == 2 and len(r5["completed"]) == 3)

    # [Unit 4] TC-06..TC-08: direct-mapped cache and average access time
    cache = DirectMappedCache(4)
    for k in (12, 31, 33, 19, 2, 31, 12):
        cache.get(k, lambda x: x)
    add("TC-06", "Cache order 12,31,33,19,2,31,12 (4 lines, direct-mapped)", "1 hit, 6 misses",
        f"{cache.hits} hit, {cache.misses} misses", (cache.hits, cache.misses) == (1, 6))
    add("TC-07", "Hit ratio of TC-06", "1/7 = 0.14", f"{cache.ratio():.2f}", round(cache.ratio(), 2) == 0.14)
    a = metrics.amat(0.8, 2, 20)
    add("TC-08", "Average access time h=0.8, tc=2, tm=20", "5.6 units (20 without cache)", f"{a:.1f} units", round(a, 1) == 5.6)

    # [Unit 4] TC-09..TC-12: parallel processing
    f, pw, t1 = 0.8, 4, 100
    s = metrics.amdahl(f, pw); tp = t1 / s
    add("TC-09", "Parallel job: 100 units, 80 parallel, 4 workers", "Time 40; speedup 2.5; efficiency 0.625",
        f"Time {tp:.0f}; speedup {s:.1f}; efficiency {metrics.efficiency(s, pw):.3f}", round(tp) == 40 and s == 2.5)
    lim = metrics.amdahl(0.8, 10 ** 9)
    add("TC-10", "Amdahl limit for f=0.8, very many workers", "Speedup tends to 5", f"{lim:.2f}", round(lim, 2) == 5.0)
    st, _, _ = system(); st.add_task(1, "Shared", "2099-01-01", 2)
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda _: [st.touch_task(1) for _ in range(500)], range(2)))
    add("TC-11", "Two workers update the same task 500 times each", "Lock allows one at a time; no lost update",
        f"final version = {st.tasks[1].version}", st.tasks[1].version == 1000)
    st, _, p = system(); p.run(jobs(4))
    depts = ["IT", "Sales", "HR"]
    same = generate_reports(st, depts, 1) == generate_reports(st, depts, 3)
    add("TC-12", "Reports for 3 departments, parallel vs sequential", "Same content as a sequential run",
        "identical" if same else "different", same)

    # validation
    st = seed_sample(DataStore()); msgs = []
    for fn in (lambda: st.add_employee(12, "Dup", "IT", "employee"), lambda: st.get_employee(999)):
        try:
            fn()
        except ValueError as e:
            msgs.append(str(e))
    add("TC-13", "Duplicate Employee ID; non-existent employee", "Rejected with a clear message",
        " | ".join(msgs), len(msgs) == 2)
    return R


if __name__ == "__main__":
    rows = run_all()
    for tid, sc, exp, act, ok in rows:
        print(f"{tid} [{ok}]\n   scenario : {sc}\n   expected : {exp}\n   actual   : {act}")
    bad = [r for r in rows if r[4] != "PASS"]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} test cases passed")
    sys.exit(1 if bad else 0)
