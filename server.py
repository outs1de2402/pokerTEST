"""Сервер: акаунти (SQLite), WebSocket-столи, роздача статичного фронтенду."""
import asyncio, hashlib, os, random, re, secrets, sqlite3, string, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine import Table

DB = os.environ.get('POKER_DB', 'poker.db')
TABLES: dict = {}; SEAT: dict = {}   # код -> стіл; імʼя -> стіл, за яким сидить гравець

def q(sql, *a):
    c = sqlite3.connect(DB)
    try: r = c.execute(sql, a).fetchall(); c.commit(); return r
    finally: c.close()
def hp(pw, salt): return hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 200_000)

def drop(t):
    if t.task: t.task.cancel()
    TABLES.pop(t.code, None)
    for p in t.P:
        if SEAT.get(p.user) is t: SEAT.pop(p.user, None)

async def sweeper():
    while True:
        await asyncio.sleep(30)
        for t in list(TABLES.values()):
            if t.over or (t.idle and time.time() - t.idle > 300): drop(t)

@asynccontextmanager
async def lifespan(app):
    q('create table if not exists users(name text primary key, salt blob, hash blob)')
    q('create table if not exists sessions(token text primary key, name text)')
    task = asyncio.create_task(sweeper()); yield; task.cancel()

app = FastAPI(lifespan=lifespan)

class Cred(BaseModel):
    name: str
    password: str

def session(name):
    t = secrets.token_urlsafe(32); q('insert into sessions values(?,?)', t, name); return {'token': t, 'name': name}

@app.post('/api/register')
def register(c: Cred):
    n = c.name.strip()
    if not re.fullmatch(r'[\w-]{3,16}', n): raise HTTPException(400, 'Імʼя: 3–16 символів (літери, цифри, _ -)')
    if len(c.password) < 6: raise HTTPException(400, 'Пароль: мінімум 6 символів')
    if q('select 1 from users where lower(name)=lower(?)', n): raise HTTPException(409, 'Таке імʼя вже зайняте')
    salt = os.urandom(16); q('insert into users values(?,?,?)', n, salt, hp(c.password, salt)); return session(n)

@app.post('/api/login')
def login(c: Cred):
    r = q('select name,salt,hash from users where lower(name)=lower(?)', c.name.strip())
    if not r or not secrets.compare_digest(r[0][2], hp(c.password, r[0][1])): raise HTTPException(401, 'Невірне імʼя або пароль')
    return session(r[0][0])

@app.get('/api/tables')
def tables():
    return [{'code': t.code, 'host': t.host, 'n': len(t.P), 'bots': t.nbots} for t in TABLES.values() if not t.started and len(t.P) + t.nbots <= 9]

@app.websocket('/ws')
async def ws_ep(ws: WebSocket):
    await ws.accept(); name = None
    try:
        m = await ws.receive_json()
        r = q('select name from sessions where token=?', str(m.get('token'))) if m.get('t') == 'auth' else None
        if not r: await ws.send_json({'t': 'autherr'}); await ws.close(); return
        name = r[0][0]; await ws.send_json({'t': 'authok', 'name': name})
        if SEAT.get(name): await SEAT[name].attach(name, ws)
        while True:
            m = await ws.receive_json(); k = m.get('t'); t = SEAT.get(name)
            if k == 'create' and not t:
                code = next(c for c in iter(lambda: ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)), None) if c not in TABLES)
                bots = max(0, min(8, int(m.get('bots') or 0))); stack = m.get('stack') if m.get('stack') in (500, 1000, 2000) else 1000
                if m.get('solo'): bots = max(1, bots)
                t = TABLES[code] = Table(code, name, stack, bots); SEAT[name] = t; await t.join(name, ws)
                if m.get('solo'): await t.start()
            elif k == 'join' and not t:
                t = TABLES.get(str(m.get('code', '')).strip().upper())
                if not t or t.started or len(t.P) + t.nbots >= 9: await ws.send_json({'t': 'err', 'm': 'Стіл не знайдено, він повний або гра вже йде'}); continue
                SEAT[name] = t; await t.join(name, ws)
            elif k == 'start' and t and t.host == name and not t.started:
                if len(t.P) + t.nbots < 2: await ws.send_json({'t': 'err', 'm': 'Потрібно мінімум 2 гравці — додайте ботів'}); continue
                await t.start()
            elif k == 'act' and t: t.recv(name, m)
            elif k == 'leave' and t:
                SEAT.pop(name, None); await t.leave(name)
                if t.host == name and not t.started: await t.cast({'t': 'left'}); drop(t)
                await ws.send_json({'t': 'left'})
    except (WebSocketDisconnect, RuntimeError): pass
    finally:
        t = SEAT.get(name) if name else None
        if t: await t.detach(name)

app.mount('/', StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'), html=True))
