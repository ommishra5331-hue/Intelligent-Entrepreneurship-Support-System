"""Test cases TC-01 ... TC-13 for Venturely (Section 12 of the report).
Runs the real Flask app with a temporary database, so your entrepreneurship.db is never touched.
Run:  python test_app.py"""
import os
import tempfile
import time

import app as venturely


def fresh():
    venturely.DB = os.path.join(tempfile.mkdtemp(), "test.db")
    venturely.init_db()
    return venturely.app.test_client()


def register(c, name, email, pw="secret1"):
    return c.post("/auth/register", json={"name": name, "email": email, "password": pw})


def run_all():
    rows = []

    def add(tid, scenario, expected, actual, ok):
        rows.append({"id": tid, "scenario": scenario, "expected": expected, "actual": str(actual), "ok": bool(ok)})

    c = fresh()
    r = register(c, "Asha Rao", "asha@example.com")
    with venturely.db() as con:
        stored = con.execute("SELECT password FROM users WHERE email='asha@example.com'").fetchone()[0]
    hashed = stored != "secret1" and ":" in stored and len(stored) > 40
    add("TC-01", "Register a new user", "Account created; password stored only as a hash",
        f"HTTP {r.status_code}; stored value {'is a hash' if hashed else 'is plain text'}", r.status_code == 200 and hashed)
    r = register(venturely.app.test_client(), "Other Name", "asha@example.com")
    add("TC-02", "Register with an email already used", "Rejected: already registered (HTTP 409)",
        f"HTTP {r.status_code}: {r.get_json()['message']}", r.status_code == 409)
    r = register(venturely.app.test_client(), "Short Pw", "short@example.com", "12345")
    add("TC-03", "Register with a 5-character password", "Rejected with a clear message (HTTP 400)",
        f"HTTP {r.status_code}: {r.get_json()['message']}", r.status_code == 400)
    r = venturely.app.test_client().post("/auth/login", json={"email": "asha@example.com", "password": "wrong"})
    add("TC-04", "Log in with a wrong password", "Rejected: incorrect email or password (HTTP 401)",
        f"HTTP {r.status_code}: {r.get_json()['message']}", r.status_code == 401)
    r = c.post("/api/ideas", json={"title": "   "})
    add("TC-05", "Add an idea with an empty title", "Rejected: title is required (HTTP 400)",
        f"HTTP {r.status_code}: {r.get_json()['message']}", r.status_code == 400)
    a = c.post("/api/ideas", json={"title": "Agri Sensor Kit", "sector": "Agriculture", "stage": "Idea"}).get_json()["id"]
    b = c.post("/api/ideas", json={"title": "Campus Food App", "sector": "Food", "stage": "MVP"}).get_json()["id"]
    titles = [x["title"] for x in c.get("/api/ideas?q=agri").get_json()["ideas"]]
    add("TC-06", "Two ideas saved; search for \"agri\"", "Only Agri Sensor Kit is returned", ", ".join(titles), titles == ["Agri Sensor Kit"])
    c.put(f"/api/ideas/{a}", json={"title": "Agri Sensor Pro", "sector": "Agriculture", "stage": "Idea"})
    renamed = [x["title"] for x in c.get("/api/ideas").get_json()["ideas"] if x["id"] == a]
    d1, d2 = c.delete(f"/api/ideas/{a}"), c.delete(f"/api/ideas/{a}")
    add("TC-07", "Edit an idea, then delete it twice", "Title updated; first delete OK; second delete 404",
        f"title {renamed[0] if renamed else None!r}; delete HTTP {d1.status_code}, then {d2.status_code}",
        renamed == ["Agri Sensor Pro"] and (d1.status_code, d2.status_code) == (200, 404))
    other = venturely.app.test_client()
    register(other, "Ben Roy", "ben@example.com")
    p, dl = other.put(f"/api/ideas/{b}", json={"title": "Stolen"}), other.delete(f"/api/ideas/{b}")
    seen = len(other.get("/api/ideas").get_json()["ideas"])
    add("TC-08", "Second user edits and deletes the first user's idea", "Both refused (HTTP 404); second user sees 0 ideas",
        f"edit HTTP {p.status_code}, delete HTTP {dl.status_code}; sees {seen} ideas", (p.status_code, dl.status_code, seen) == (404, 404, 0))
    ids = [x["id"] for x in c.get("/api/resources?type=Funding").get_json()["resources"]]
    add("TC-09", "Filter resources by type Funding", "Resources 1 and 8", "Resources " + " and ".join(map(str, ids)), ids == [1, 8])
    rec = fresh()
    register(rec, "Cara Das", "cara@example.com")
    rec.post("/api/ideas", json={"title": "Test", "sector": "Technology", "stage": "Idea", "support": "Mentorship"})
    ranked = rec.get("/api/recommendations").get_json()["recommendations"]
    order, scores = [x["id"] for x in ranked], [x["score"] for x in ranked]
    add("TC-10", "Rank resources for a Technology / Idea / Mentorship idea", "Order 1, 2, 3, 6, 4, 7, 8, 5; scores 12, 12, 12, 12, 10, 10, 10, 6",
        f"Order {', '.join(map(str, order))}; scores {', '.join(map(str, scores))}", order == [1, 2, 3, 6, 4, 7, 8, 5] and scores == [12, 12, 12, 12, 10, 10, 10, 6])
    path = rec.get("/api/network?from=You&to=Investor").get_json()["path"]
    add("TC-11", "BFS path from You to Investor", "You -> Incubator -> Investor (2 steps)", " -> ".join(path), path == ["You", "Incubator", "Investor"])
    r = rec.get("/api/network?from=Stranger&to=Investor")
    add("TC-12", "BFS from a role that is not in the network", "Empty path, no crash (HTTP 200)", f"HTTP {r.status_code}; path {r.get_json()['path']}", r.status_code == 200 and r.get_json()["path"] == [])
    r = venturely.app.test_client().get("/api/ideas")
    add("TC-13", "Open the ideas API without signing in", "Refused (HTTP 401)", f"HTTP {r.status_code}", r.status_code == 401)
    return rows


def benchmark(n=200):
    c = fresh()
    register(c, "Dev Test", "dev@example.com")
    c.post("/api/ideas", json={"title": "Bench", "sector": "Technology", "stage": "Idea"})
    out = {}
    for name, url in [("recommendations", "/api/recommendations"), ("network", "/api/network?from=You&to=Investor")]:
        t = time.perf_counter()
        for _ in range(n):
            c.get(url)
        out[name] = (time.perf_counter() - t) * 1000 / n
    return out


if __name__ == "__main__":
    res = run_all()
    for r in res:
        print(f"{r['id']}  {'PASS' if r['ok'] else 'FAIL'}  {r['scenario']}\n        expected: {r['expected']}\n        actual:   {r['actual']}")
    print(f"{sum(r['ok'] for r in res)}/{len(res)} test cases passed")
    for k, v in benchmark().items():
        print(f"average time per request, {k}: {v:.2f} ms")
