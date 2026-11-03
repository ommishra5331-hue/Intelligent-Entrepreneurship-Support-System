from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, heapq, re
from collections import deque
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = os.environ.get('IES_SECRET', 'ies-local-development-key-change-before-deployment')
DB = os.path.join(os.path.dirname(__file__), 'entrepreneurship.db')

RESOURCES = [
 {"id":1,"title":"Startup India Seed Fund Scheme","type":"Funding","stage":"Idea / Early","sector":"All sectors","description":"Explore early-stage funding support through eligible incubators.","url":"https://www.startupindia.gov.in/"},
 {"id":2,"title":"Startup India Learning Program","type":"Learning","stage":"Idea / Early","sector":"All sectors","description":"Learn the fundamentals of building and managing a startup.","url":"https://www.startupindia.gov.in/"},
 {"id":3,"title":"MVP Validation Checklist","type":"Guide","stage":"Idea","sector":"All sectors","description":"A practical checklist to validate a problem before building a product.","url":"https://www.ycombinator.com/library"},
 {"id":4,"title":"Digital Marketing Basics","type":"Learning","stage":"Growth","sector":"All sectors","description":"Understand channels, positioning and customer acquisition.","url":"https://skillshop.withgoogle.com/"},
 {"id":5,"title":"MSME Development Resources","type":"Support","stage":"Early / Growth","sector":"Manufacturing / Services","description":"Government information and support for MSMEs.","url":"https://msme.gov.in/"},
 {"id":6,"title":"Business Model Canvas","type":"Guide","stage":"Idea / Early","sector":"All sectors","description":"Map customers, value proposition, channels and revenue streams.","url":"https://www.strategyzer.com/library/the-business-model-canvas"},
 {"id":7,"title":"Intellectual Property India","type":"Support","stage":"Early / Growth","sector":"All sectors","description":"Official information about trademarks, patents and IP services.","url":"https://ipindia.gov.in/"},
 {"id":8,"title":"Startup Fundraising Guide","type":"Funding","stage":"Early / Growth","sector":"All sectors","description":"Understand funding stages, investor readiness and pitch preparation.","url":"https://www.startupindia.gov.in/"}
]
PEOPLE = {"You":["Incubator","Mentor","Founder"],"Incubator":["You","Investor","Mentor"],"Mentor":["You","Incubator","Founder"],"Founder":["You","Mentor","Investor"],"Investor":["Incubator","Founder"]}

@contextmanager
def db():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        con.execute('''CREATE TABLE IF NOT EXISTS ideas(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,title TEXT NOT NULL,sector TEXT NOT NULL,stage TEXT NOT NULL,problem TEXT DEFAULT '',description TEXT DEFAULT '',support TEXT DEFAULT 'Mentorship',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id))''')

def current_user():
    if 'user_id' not in session: return None
    with db() as con: return con.execute('SELECT id,name,email FROM users WHERE id=?',(session['user_id'],)).fetchone()

def api_login_required():
    return current_user() is not None

@app.route('/')
def home():
    if current_user(): return render_template('index.html', user=dict(current_user()))
    return render_template('auth.html')

@app.post('/auth/register')
def register():
    data=request.get_json() or {}; name=(data.get('name') or '').strip(); email=(data.get('email') or '').strip().lower(); password=data.get('password') or ''
    if len(name)<2 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$',email) or len(password)<6:
        return jsonify(ok=False,message='Enter a valid name, email and password (at least 6 characters).'),400
    try:
        with db() as con: cur=con.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name,email,generate_password_hash(password))); uid=cur.lastrowid
        session['user_id']=uid
        return jsonify(ok=True)
    except sqlite3.IntegrityError: return jsonify(ok=False,message='This email is already registered. Please log in.'),409

@app.post('/auth/login')
def login():
    data=request.get_json() or {}; email=(data.get('email') or '').strip().lower(); password=data.get('password') or ''
    with db() as con: user=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not user or not check_password_hash(user['password'],password): return jsonify(ok=False,message='Incorrect email or password.'),401
    session.clear(); session['user_id']=user['id']; return jsonify(ok=True)

@app.post('/auth/logout')
def logout(): session.clear(); return jsonify(ok=True)

def require_user():
    user=current_user()
    if not user: return None
    return user

@app.get('/api/me')
def me():
    u=require_user()
    if not u: return jsonify(ok=False),401
    return jsonify(user=dict(u))

@app.get('/api/dashboard')
def dashboard():
    u=require_user()
    if not u: return jsonify(ok=False),401
    with db() as con:
        ideas=[dict(x) for x in con.execute('SELECT * FROM ideas WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall()]
    return jsonify(ideas=ideas,stats={"ideas":len(ideas),"resources":len(RESOURCES),"recommendations":len(RESOURCES),"connections":len(PEOPLE)-1},recent=ideas[:4])

@app.route('/api/ideas',methods=['GET','POST'])
def ideas_api():
    u=require_user()
    if not u: return jsonify(ok=False),401
    if request.method=='GET':
        q=(request.args.get('q') or '').strip().lower()
        with db() as con: rows=[dict(x) for x in con.execute('SELECT * FROM ideas WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall()]
        if q: rows=[x for x in rows if q in x['title'].lower() or q in x['sector'].lower() or q in x['description'].lower()]
        return jsonify(ideas=rows)
    d=request.get_json() or {}; title=(d.get('title') or '').strip()
    if not title: return jsonify(ok=False,message='Idea title is required.'),400
    with db() as con: cur=con.execute('INSERT INTO ideas(user_id,title,sector,stage,problem,description,support) VALUES(?,?,?,?,?,?,?)',(u['id'],title,d.get('sector','Technology'),d.get('stage','Idea'),d.get('problem',''),d.get('description',''),d.get('support','Mentorship'))); iid=cur.lastrowid
    return jsonify(ok=True,id=iid)

@app.route('/api/ideas/<int:iid>',methods=['PUT','DELETE'])
def idea_detail(iid):
    u=require_user()
    if not u: return jsonify(ok=False),401
    with db() as con:
        found=con.execute('SELECT id FROM ideas WHERE id=? AND user_id=?',(iid,u['id'])).fetchone()
        if not found: return jsonify(ok=False,message='Idea not found.'),404
        if request.method=='DELETE': con.execute('DELETE FROM ideas WHERE id=? AND user_id=?',(iid,u['id'])); return jsonify(ok=True)
        d=request.get_json() or {}; title=(d.get('title') or '').strip()
        if not title: return jsonify(ok=False,message='Idea title is required.'),400
        con.execute('UPDATE ideas SET title=?,sector=?,stage=?,problem=?,description=?,support=? WHERE id=? AND user_id=?',(title,d.get('sector','Technology'),d.get('stage','Idea'),d.get('problem',''),d.get('description',''),d.get('support','Mentorship'),iid,u['id']))
    return jsonify(ok=True)

@app.get('/api/resources')
def resources():
    if not api_login_required(): return jsonify(ok=False),401
    q=(request.args.get('q') or '').lower(); typ=request.args.get('type','All')
    rows=[r for r in RESOURCES if (typ=='All' or r['type']==typ) and (not q or q in (r['title']+' '+r['description']+' '+r['sector']).lower())]
    return jsonify(resources=rows)

@app.get('/api/recommendations')
def recommendations():
    u=require_user()
    if not u: return jsonify(ok=False),401
    with db() as con: ideas=[dict(x) for x in con.execute('SELECT * FROM ideas WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall()]
    idea=ideas[0] if ideas else {"sector":"Technology","stage":"Idea","support":"Mentorship"}
    heap=[]
    for r in RESOURCES:
        score=4 if idea['sector'].lower() in r['sector'].lower() or r['sector']=='All sectors' else 0
        score+=3 if idea['stage'].lower() in r['stage'].lower() or 'Idea / Early' in r['stage'] else 1
        score+=5 if idea['support'].lower() in r['type'].lower() or idea['support']=='Mentorship' else 1
        heapq.heappush(heap,(-score,r['id'],r))
    ranked=[]
    while heap:
        score,_,r=heapq.heappop(heap); ranked.append({**r,'score':-score})
    return jsonify(recommendations=ranked,context=idea['title'] if ideas else 'Add an idea to personalize these matches')

@app.get('/api/network')
def network():
    if not api_login_required(): return jsonify(ok=False),401
    start=request.args.get('from','You'); end=request.args.get('to','Investor')
    queue=deque([(start,[start])]); seen={start}; path=[]
    while queue:
        node,p=queue.popleft()
        if node==end: path=p; break
        for nxt in PEOPLE.get(node,[]):
            if nxt not in seen: seen.add(nxt); queue.append((nxt,p+[nxt]))
    return jsonify(people=list(PEOPLE.keys()),edges=PEOPLE,path=path)

if __name__=='__main__':
    init_db(); app.run(host='127.0.0.1',port=5000,debug=False)
