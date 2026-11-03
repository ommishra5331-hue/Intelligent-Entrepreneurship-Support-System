"""Data layer: employee, task, approval and archive records.

[CA&PP | Unit 4 - Memory Organization] This module plays two levels of the memory hierarchy:
  * MAIN MEMORY / working store -> self.employees, self.tasks (slow access, see _access)
  * SECONDARY STORAGE / archive -> self.archive (completed tasks) and the JSON file on disk
The cache (cache.py) sits in front of this store.
"""
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import date

ROLES = ("employee", "manager", "admin")
STATUSES = ("created", "assigned", "approved", "rejected", "in_progress", "completed")


@dataclass
class Employee:
    emp_id: int
    name: str
    department: str
    role: str


@dataclass
class Task:
    task_id: int
    title: str
    deadline: str
    priority: int                    # 1 = urgent, 2 = standard, 3 = low
    status: str = "created"
    assignee: int = 0                # 0 = nobody yet
    version: int = 0                 # counts updates (used by the lock test)
    history: list = field(default_factory=lambda: ["created"])


class DataStore:
    def __init__(self, latency=0.0):
        self.employees, self.tasks, self.archive, self.approvals = {}, {}, {}, []
        self.latency = latency       # simulated main-memory access time (seconds)
        self.reads = 0               # number of slow main-store accesses
        # [CA&PP | Unit 4 - Parallel Processing] one lock = mutual exclusion on shared records
        self._lock = threading.RLock()

    # [CA&PP | Unit 4 - Memory Organization] every call here is one slow main-store access (tm).
    def _access(self):
        with self._lock:
            self.reads += 1
        if self.latency:
            time.sleep(self.latency)

    # ---------------------------------------------------------------- employees
    def add_employee(self, emp_id, name, department, role):
        if emp_id in self.employees:
            raise ValueError(f"Duplicate Employee ID {emp_id}")
        if emp_id <= 0 or not str(name).strip() or not str(department).strip():
            raise ValueError("Employee ID must be positive; name and department are required")
        if role not in ROLES:
            raise ValueError(f"Role must be one of {ROLES}")
        self.employees[emp_id] = Employee(emp_id, name.strip(), department.strip(), role)

    def get_employee(self, emp_id):
        self._access()
        emp = self.employees.get(emp_id)
        if emp is None:
            raise ValueError(f"Employee {emp_id} does not exist")
        return emp

    # -------------------------------------------------------------------- tasks
    def add_task(self, task_id, title, deadline, priority):
        if task_id in self.tasks or task_id in self.archive:
            raise ValueError(f"Duplicate Task ID {task_id}")
        if priority not in (1, 2, 3):
            raise ValueError("Priority must be 1, 2 or 3")
        if not str(title).strip():
            raise ValueError("Task title is required")
        try:
            d = date.fromisoformat(deadline)
        except ValueError:
            raise ValueError("Deadline must be in YYYY-MM-DD format")
        if d < date.today():
            raise ValueError("Deadline is in the past")
        self.tasks[task_id] = Task(task_id, title.strip(), deadline, priority)

    def _find(self, task_id):
        t = self.tasks.get(task_id) or self.archive.get(task_id)
        if t is None:
            raise ValueError(f"Task {task_id} does not exist")
        return t

    def set_status(self, task_id, status):
        if status not in STATUSES:
            raise ValueError(f"Unknown status {status}")
        with self._lock:
            t = self._find(task_id)
            t.status = status
            t.history.append(status)

    def assign(self, task_id, emp):
        with self._lock:
            t = self._find(task_id)
            t.assignee = emp.emp_id
        self.set_status(task_id, "assigned")

    def approve(self, task_id, approver_id, approved):
        approver = self.employees.get(approver_id)
        if approver is None or approver.role != "manager":
            raise ValueError("Only a manager can approve or reject a task")
        t = self._find(task_id)
        if t.assignee == 0:
            raise ValueError("Task must be assigned before approval")
        self.approvals.append({"task_id": task_id, "approver": approver_id, "approved": approved})
        self.set_status(task_id, "approved" if approved else "rejected")

    # [CA&PP | Unit 4 - Parallel Processing] read-modify-write on a shared record.
    # With the lock only one worker updates at a time (no lost update / race condition).
    def touch_task(self, task_id, use_lock=True):
        t = self._find(task_id)
        if use_lock:
            with self._lock:
                t.version += 1
        else:
            v = t.version
            time.sleep(0)            # lets another thread interleave -> lost updates
            t.version = v + 1

    # [CA&PP | Unit 4 - Memory Organization] move a finished task to secondary storage (archive).
    def archive_task(self, task_id):
        with self._lock:
            if task_id in self.tasks:
                self.archive[task_id] = self.tasks.pop(task_id)

    def all_tasks(self):
        with self._lock:
            return list(self.tasks.values()) + list(self.archive.values())

    def tasks_of(self, emp_id):
        return [t for t in self.all_tasks() if t.assignee == emp_id]

    # ------------------------------------------------------------- persistence
    def save(self, path):
        data = {"employees": [asdict(e) for e in self.employees.values()],
                "tasks": [asdict(t) for t in self.tasks.values()],
                "archive": [asdict(t) for t in self.archive.values()],
                "approvals": self.approvals}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path, latency=0.0):
        s = cls(latency)
        with open(path) as f:
            data = json.load(f)
        s.employees = {e["emp_id"]: Employee(**e) for e in data["employees"]}
        s.tasks = {t["task_id"]: Task(**t) for t in data["tasks"]}
        s.archive = {t["task_id"]: Task(**t) for t in data["archive"]}
        s.approvals = data["approvals"]
        return s


def seed_sample(store):
    """Sample organization used by the demo and by the test cases."""
    for row in [(1, "Admin HR", "HR", "admin"), (2, "Rohit Sharma", "IT", "manager"),
                (3, "Neha Gupta", "Sales", "manager"), (12, "Amit Singh", "IT", "employee"),
                (31, "Priya Das", "IT", "employee"), (33, "Karan Mehta", "Sales", "employee"),
                (19, "Sana Khan", "Sales", "employee")]:
        store.add_employee(*row)
    return store
