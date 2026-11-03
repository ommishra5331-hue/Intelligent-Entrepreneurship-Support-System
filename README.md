# Employee Workflow Management System (CA&PP PBL, Group 87)

Working prototype for the PBL Final Report (CCSE0304, Computer Architecture & Parallel Processing).
Pure Python 3.8+, no extra packages.

## Run
```
python main.py              # interactive app (login by Employee ID)
python main.py --demo       # pipeline trace + cache + parallel reports
python main.py --benchmark  # timings for Section 12 "Evaluation"
python testcases.py         # TC-01 ... TC-13 with expected vs actual result
python -m unittest -v       # same 13 cases as unit tests
```
Sample logins: `1` admin, `2` / `3` manager, `12` `31` `33` `19` employee. Data is saved to `data.json`.

## Where each CA&PP topic is used (search the code for `[CA&PP`)
| File | CA&PP topic | What it does |
|---|---|---|
| `pipeline.py` | Unit 3 Control unit & pipelining | 5-stage pipeline TC-AS-AP-SU-RP, control loop, stall (approval review), flush (rejected approval) |
| `metrics.py` | Unit 3 and Unit 4 formulas | pipeline speedup, hit ratio, average access time, speedup, efficiency, Amdahl's law |
| `cache.py` | Unit 4 Memory organization | direct-mapped cache (line = ID mod 4), hit/miss counters |
| `store.py` | Unit 4 Memory organization / Parallel | main store (slow access), archive = secondary storage, lock for shared records |
| `parallel.py` | Unit 4 Parallel processing | department reports and notifications on parallel workers (MIMD) |
| `testcases.py` | Section 12 | the 13 test cases of the report, run on the real code |

## Role based access
Admin: add/list employees, parallel department reports, cache stats. Manager: create+assign task,
approve/reject, run a batch through the pipeline, list tasks. Employee: view own tasks, update status.

## Notes
* The pipeline is a software model (one "cycle" = one time unit), as stated in the report.
* Parallel work uses threads with simulated I/O time (`work`), so speedup is visible; for CPU-bound
  work use `multiprocessing` (Python GIL).
