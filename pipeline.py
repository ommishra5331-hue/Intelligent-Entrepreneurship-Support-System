"""Five-stage workflow pipeline (clocked simulation that runs the real workflow actions).

[CA&PP | Unit 3 - Control Unit & Pipelining]
  Stages (like fetch-decode-execute-write-back):  TC -> AS -> AP -> SU -> RP
     TC task creation | AS assignment | AP approval | SU status update | RP reporting/archive
  * self.slots are the PIPELINE REGISTERS: one job per stage, all stages work in the same cycle.
  * The loop below is the CONTROL UNIT: it decides each cycle who advances, waits or is flushed.
  * Hazards handled:
      - DATA/STRUCTURAL hazard: approval needs extra review cycles -> STALL (bubble), earlier
        stages wait because the stage ahead is occupied.
      - CONTROL hazard: a rejected approval sends the task back to AS -> younger jobs in earlier
        stages are FLUSHED and re-fetched, the rejected job re-enters from the start.
"""
from collections import deque
from dataclasses import dataclass, field

STAGES = ("TC", "AS", "AP", "SU", "RP")


@dataclass
class Job:
    params: dict                       # task_id, title, deadline, priority
    assignees: list                    # employee IDs tried in order (next one after a rejection)
    decisions: list = field(default_factory=list)   # manager decisions, True = approve
    review: int = 0                    # extra cycles the approver needs (causes a stall)
    attempt: int = 0
    done: int = -1                     # last stage already executed (avoids repeating work)
    error: str = ""


class WorkflowPipeline:
    def __init__(self, store, cache, approver_id):
        self.store, self.cache, self.approver_id = store, cache, approver_id
        self.cycles = self.stall_cycles = self.flushes = 0
        self.completed, self.failed, self.trace = [], [], []

    # ----------------------------------------------------------- stage actions
    def _execute(self, s, job):
        st, tid = self.store, job.params["task_id"]
        try:
            if s == 0:                                  # TC: create the task (idempotent)
                if tid not in st.tasks:
                    st.add_task(**job.params)
            elif s == 1:                                # AS: find employee (CACHE first) and assign
                emp_id = job.assignees[min(job.attempt, len(job.assignees) - 1)]
                emp = self.cache.get(emp_id, st.get_employee)   # [Unit 4] cache before main store
                st.assign(tid, emp)
            elif s == 2:                                # AP: manager approves / rejects
                if job.review > 0:                      # approver busy -> STALL (bubble)
                    job.review -= 1
                    return "stall"
                approved = job.decisions.pop(0) if job.decisions else True
                st.approve(tid, self.approver_id, approved)
                if not approved:                        # CONTROL HAZARD -> flush
                    job.attempt += 1
                    job.done = -1
                    return "reject"
            elif s == 3:                                # SU: employee marks the task completed
                st.set_status(tid, "completed")
            elif s == 4:                                # RP: archive (secondary storage) for reports
                st.archive_task(tid)
        except ValueError as e:
            job.error = str(e)
            return "fail"
        return "ok"

    # --------------------------------------------------------- control unit loop
    def run(self, jobs):
        pending, slots = deque(jobs), [None] * len(STAGES)
        while pending or any(slots):
            self.cycles += 1
            if slots[0] is None and pending:            # fetch next job into stage 1
                slots[0] = pending.popleft()
            self.trace.append([j.params["task_id"] if j else "-" for j in slots])
            new, stalled = [None] * len(STAGES), False
            for s in range(len(STAGES) - 1, -1, -1):    # last stage first, like hardware
                job = slots[s]
                if job is None:
                    continue
                res = "ok" if job.done == s else self._execute(s, job)
                if res == "ok":
                    job.done = s
                if res == "stall":
                    new[s], stalled = job, True
                elif res == "fail":
                    self.failed.append((job.params["task_id"], job.error))
                elif res == "reject":
                    younger = [slots[t] for t in range(s - 1, -1, -1) if slots[t]]
                    for t in range(s):                  # FLUSH earlier stages
                        slots[t] = None
                    self.flushes += len(younger)
                    pending.extendleft(reversed([job] + younger))   # re-fetch in original order
                elif s == len(STAGES) - 1:
                    self.completed.append(job.params["task_id"])
                elif new[s + 1] is None:                # advance to next stage register
                    new[s + 1] = job
                else:                                   # next stage busy -> wait (pipeline stall)
                    new[s], stalled = job, True
            if stalled:
                self.stall_cycles += 1
            slots = new
        return {"cycles": self.cycles, "stall_cycles": self.stall_cycles, "flushes": self.flushes,
                "completed": self.completed, "failed": self.failed}

    def trace_table(self):
        lines = ["cycle  " + "  ".join(f"{s:>3}" for s in STAGES)]
        for i, row in enumerate(self.trace, 1):
            lines.append(f"{i:>5}  " + "  ".join(f"{str(x):>3}" for x in row))
        return "\n".join(lines)
