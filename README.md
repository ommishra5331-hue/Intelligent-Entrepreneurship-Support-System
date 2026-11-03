# Venturely — Intelligent Entrepreneurship Support System

A modern, responsive founder workspace built with Flask, SQLite, HTML, CSS and JavaScript. It can be run without VS Code.

## What's functional
- Sign up and sign in with hashed passwords; each account sees only its own ideas.
- Responsive sidebar, top navigation and mobile menu.
- Dashboard with live counts and recent ideas.
- Add, edit, search and delete business ideas; records persist in SQLite.
- Resource library with working external resource links, search and category filters.
- Personalized resource ranking using a max-priority queue (Python `heapq`).
- Mentor/support ecosystem path finder using an adjacency-list graph and BFS.
- Profile page and sign out.

## DSA concepts used
| DSA concept | Where it is used |
|---|---|
| Lists / arrays | Resource collection and idea results |
| Linear search | Search/filter over idea and resource records |
| Sorting / priority queue | Ranking recommendations with `heapq` |
| Graph (adjacency list) | Sample mentor/support network |
| BFS + queue | Shortest path between network roles, O(V + E) |
| Hashing | Password hashing via Werkzeug (security, not password storage in plain text) |

## Run on Windows without VS Code
1. Download and extract the ZIP file.
2. Open the extracted `Intelligent_Entrepreneurship_Support_System` folder.
3. Click the folder address bar, type `cmd`, and press Enter.
4. Run these commands one by one:

   ```bat
   python -m pip install -r requirements.txt
   python app.py
   ```
5. Keep the Command Prompt window open. Open Chrome and visit **http://127.0.0.1:5000**.
6. Create an account from the signup tab and start using your workspace.

If `python` is not recognized, install Python from https://www.python.org/downloads/ and select **Add Python to PATH** during installation.

## Data and limitations
- The SQLite database `entrepreneurship.db` is created automatically beside `app.py`.
- Accounts and ideas are stored locally on the computer running the app. This is a local academic prototype, not a production-hosted service.
- The network is illustrative; it does not make real mentor introductions.
- Resource links point to external organizations and may change. Recommendation scores are a simple transparent heuristic, not verified funding eligibility.
- For public deployment, set a strong `IES_SECRET`, use HTTPS, add CSRF/rate limiting and deploy behind a production WSGI server.
