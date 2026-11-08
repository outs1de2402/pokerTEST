"""Рушій техаського холдему: стіл, раунди торгів, сайд-поти, боти. Усе рахує сервер."""
import asyncio, itertools, random, time
from types import SimpleNamespace as NS

SPEED = 1.0  # множник пауз (у тестах 0)
HN = ['Старша карта','Пара','Дві пари','Трійка','Стріт','Флеш','Фул-хаус','Каре','Стріт-флеш']
BOTS = ['Олег','Марта','Іван','Софія','Тарас','Надія','Богдан','Ліна']
def sleep(x): return asyncio.sleep(x * SPEED)

def ev5(c):
    r = sorted((x[0] for x in c), reverse=True); fl = len({x[1] for x in c}) == 1; st = 0
    if len(set(r)) == 5:
        if r[0] - r[4] == 4: st = r[0]
        elif r[:2] == [14, 5]: st = 5
    g = sorted(((r.count(k), k) for k in set(r)), reverse=True); k = [x[1] for x in g]
    if st and fl: return (8, st)
    if g[0][0] == 4: return (7, *k)
    if g[0][0] == 3 and g[1][0] == 2: return (6, *k)
    if fl: return (5, *r)
    if st: return (4, st)
    if g[0][0] == 3: return (3, *k)
    if g[0][0] == 2 and g[1][0] == 2: return (2, *k)
    if g[0][0] == 2: return (1, *k)
    return (0, *r)

def best(cards): return max(ev5(c) for c in itertools.combinations(cards, 5))

def player(name, user=None, ws=None):
    return NS(name=name, user=user, ws=ws, chips=0, hand=[], bet=0, total=0, folded=False, allin=False,
              acted=False, inn=False, last='', show=False, win=False, agg=random.uniform(.5, 2), ev=None)

class Table:
    def __init__(s, code, host, stack, nbots):
        s.code, s.host, s.stack, s.nbots = code, host, stack, nbots
        s.P, s.board, s.logs = [], [], []
        s.started = s.over = False; s.idle = None; s.task = None; s.pend = None
        s.btn, s.cur, s.SB, s.BB, s.minr, s.hno, s.turn, s.rc, s.tk = -1, 0, 10, 20, 20, 0, -1, 0, 0

    # ---------- зв'язок ----------
    def humans(s): return [p for p in s.P if p.user]
    def pot(s): return sum(p.total for p in s.P)
    async def send(s, p, m):
        if p.ws:
            try: await p.ws.send_json(m)
            except Exception: p.ws = None
    async def cast(s, m):
        for p in s.humans(): await s.send(p, m)
    async def log(s, t, c=''):
        s.logs = (s.logs + [[t, c]])[-60:]; await s.cast({'t': 'log', 'm': t, 'c': c})
    def lobby(s):
        return {'t': 'lobby', 'code': s.code, 'host': s.host, 'players': [p.name for p in s.P], 'bots': s.nbots, 'stack': s.stack}
    async def sync(s):
        for p in s.humans(): await s.send(p, s.view(p))
    def view(s, me):
        a = s.pend[0] if s.pend else None; act = None
        if a is me:
            tc = min(s.cur - a.bet, a.chips); mx = a.bet + a.chips
            act = {'tc': tc, 'mn': min(s.cur + s.minr, mx), 'mx': mx, 'r': a.chips > tc, 'pt': s.pot(), 'cur': s.cur}
        card = lambda c: {'r': c[0], 's': c[1]}
        pl = [{'n': p.name, 'c': p.chips, 'b': p.bet, 'f': p.folded, 'w': p.win, 'me': p is me,
               'l': 'Вибув' if p.chips == 0 and not p.total else p.last,
               'h': [card(c) if (p is me or (p.show and not p.folded)) else None for c in p.hand]} for p in s.P]
        combo = HN[best(me.hand + s.board)[0]] if me.hand and len(s.board) >= 3 and not me.folded else ''
        return {'t': 'state', 'tk': s.tk, 'turn': s.turn, 'btn': s.btn, 'pot': s.pot(), 'wait': bool(a),
                'bd': [card(c) for c in s.board], 'act': act, 'pl': pl, 'combo': combo}
    async def join(s, name, ws):
        s.P.append(player(name, name, ws)); await s.cast(s.lobby())
    async def attach(s, name, ws):
        p = next(p for p in s.P if p.user == name); p.ws = ws; s.idle = None
        await s.send(p, s.lobby())
        for t, c in s.logs: await s.send(p, {'t': 'log', 'm': t, 'c': c})
        if s.started: await s.send(p, s.view(p))
    async def detach(s, name):
        p = next((p for p in s.P if p.user == name), None)
        if not p: return
        p.ws = None
        if s.pend and s.pend[0] is p and not s.pend[1].done(): s.pend[1].set_result(s.bot(p))
        if not any(h.ws for h in s.humans()): s.idle = time.time()
    async def leave(s, name):
        p = next((p for p in s.P if p.user == name), None)
        if not p: return
        if not s.started: s.P.remove(p); await s.cast(s.lobby()); return
        await s.detach(name); p.user = None; p.name += ' 🤖'
    def recv(s, name, m):
        if not s.pend: return
        p, f = s.pend
        if p.user != name or f.done() or m.get('tk') != s.tk or m.get('a') not in ('f', 'c', 'r'): return
        try: to = int(m.get('to') or 0)
        except (TypeError, ValueError): to = 0
        f.set_result({'t': m['a'], 'to': to})
    async def start(s):
        for i in range(min(s.nbots, 9 - len(s.P))): s.P.append(player(BOTS[i]))
        for p in s.P: p.chips = s.stack
        s.started = True; s.task = asyncio.create_task(s.run())

    # ---------- боти ----------
    def strength(s, p):
        if not s.board:
            a, b = sorted((c[0] for c in p.hand), reverse=True)
            v = .5 + a / 28 if a == b else (a + b) / 40 + (.05 if a > 10 else 0)
            if p.hand[0][1] == p.hand[1][1]: v += .06
            if a != b and a - b <= 2: v += .04
            return min(v, 1)
        e = best(p.hand + s.board); k = e[0]
        if k == 1: return .4 + .1 * (e[1] - 2) / 12 if any(c[0] == e[1] for c in p.hand) else .25
        return [.15, 0, .65, .75, .85, .88, .95, .99, 1][k]
    def bot(s, p):
        v = s.strength(p) + random.uniform(-.08, .08); tc = s.cur - p.bet; pt = s.pot(); odds = tc / ((pt + tc) or 1)
        if s.rc < 4 and p.chips > tc and (v > .72 or (random.random() < .05 * p.agg and v > .3)):
            size = max(s.minr, round(pt * random.uniform(.4, .9) / s.BB) * s.BB); return {'t': 'r', 'to': s.cur + size}
        if tc == 0: return {'t': 'c'}
        if v > odds + .12 or (v > .45 and tc <= s.BB * 2): return {'t': 'c'}
        return {'t': 'f'}

    # ---------- хід гри ----------
    def pay(s, p, a):
        a = min(a, p.chips); p.chips -= a; p.bet += a; p.total += a
        if not p.chips: p.allin = True
    def nxt(s, i):
        while True:
            i = (i + 1) % len(s.P)
            if s.P[i].inn: return i
    async def act(s, p):
        s.turn = s.P.index(p); tc = min(s.cur - p.bet, p.chips)
        if p.user and p.ws:
            s.tk += 1; fut = asyncio.get_running_loop().create_future(); s.pend = (p, fut); await s.sync()
            try: d = await asyncio.wait_for(fut, 45)
            except asyncio.TimeoutError:
                d = s.bot(p); await s.log(f'{p.name} не відповів — автоматичний хід', 'h')
            s.pend = None
        else:
            await s.sync(); await sleep(random.uniform(.6, 1.2)); d = s.bot(p)
        t = d['t']
        if t == 'r':
            mx = p.bet + p.chips; to = min(max(d.get('to', 0), s.cur + s.minr), mx)
            if to > s.cur:
                first = s.cur == 0; s.minr = max(s.minr, to - s.cur); s.cur = to; s.rc += 1
                for q in s.P: q.acted = False
                s.pay(p, to - p.bet)
                p.last = ('Олл-ін ' if p.allin else 'Бет ' if first else 'Рейз ') + str(to); await s.log(f'{p.name} — {p.last}')
            else: t = 'c'
        if t == 'f': p.folded = True; p.last = 'Фолд'; await s.log(f'{p.name} фолдить')
        elif t == 'c':
            s.pay(p, tc); p.last = f'Колл {tc}' if tc else 'Чек'; await s.log(f'{p.name} ' + (f'коллить {tc}' if tc else 'чекає'))
        p.acted = True; s.turn = -1; await s.sync()
    async def betround(s, i):
        while True:
            if sum(not p.folded for p in s.P) <= 1: return
            can = [p for p in s.P if not p.folded and not p.allin]
            if all(p.acted and p.bet == s.cur for p in can) or (len(can) <= 1 and (not can or can[0].bet >= s.cur)): return
            p = s.P[i % len(s.P)]; i += 1
            if p.folded or p.allin or (p.acted and p.bet == s.cur): continue
            await s.act(p)
    def reset(s):
        s.cur, s.minr, s.rc = 0, s.BB, 0
        for p in s.P: p.bet = 0; p.acted = False; p.last = 'Фолд' if p.folded else 'Олл-ін' if p.allin else ''
    async def hand(s):
        s.hno += 1
        if s.hno > 1 and (s.hno - 1) % 10 == 0: s.SB *= 2; s.BB *= 2; await s.log(f'Блайнди зросли: {s.SB}/{s.BB}', 'h')
        for p in s.P:
            p.inn = p.chips > 0; p.folded = not p.inn; p.allin = False; p.bet = p.total = 0
            p.acted = False; p.hand = []; p.show = False; p.win = False; p.last = ''
        s.board = []; deck = [(r, u) for r in range(2, 15) for u in range(4)]; random.shuffle(deck)
        s.btn = s.nxt(s.btn); hu = sum(p.inn for p in s.P) == 2
        sb = s.btn if hu else s.nxt(s.btn); bb = s.nxt(sb); pre = sb if hu else s.nxt(bb); post = bb if hu else s.nxt(s.btn)
        await s.log(f'── Роздача #{s.hno} · Дилер: {s.P[s.btn].name} ──', 'h')
        await s.log('🃏 Дилер тасує колоду та роздає по дві карти')
        for _ in range(2):
            for p in s.P:
                if p.inn: p.hand.append(deck.pop())
        s.pay(s.P[sb], s.SB); s.pay(s.P[bb], s.BB)
        s.P[sb].last = f'SB {s.P[sb].bet}'; s.P[bb].last = f'BB {s.P[bb].bet}'
        s.cur = max(p.bet for p in s.P); s.minr = s.BB; s.rc = 0
        await s.log(f'{s.P[sb].name} — малий блайнд {s.P[sb].bet}, {s.P[bb].name} — великий блайнд {s.P[bb].bet}')
        await s.sync(); await s.betround(pre)
        for nm, n in (('Флоп', 3), ('Тьорн', 1), ('Рівер', 1)):
            if sum(not p.folded for p in s.P) < 2: break
            s.reset(); deck.pop(); new = [deck.pop() for _ in range(n)]; s.board += new
            await s.log('🃏 Дилер: ' + nm + ' — ' + ' '.join({11: 'J', 12: 'Q', 13: 'K', 14: 'A'}.get(c[0], str(c[0])) + '♠♥♦♣'[c[1]] for c in new))
            await s.sync()
            if sum(not p.folded and not p.allin for p in s.P) >= 2: await s.betround(post)
            else: await sleep(.9)
        await s.payout()
    async def payout(s):
        al = [p for p in s.P if not p.folded]; multi = len(al) > 1; won = {}
        if multi:
            for p in al: p.show = True; p.ev = best(p.hand + s.board)
            await s.log('🃏 Дилер: вскриваємо карти', 'h')
        prev = 0
        for L in sorted({p.total for p in s.P if p.total > 0}):
            amt = sum(min(p.total, L) - min(p.total, prev) for p in s.P); prev = L
            el = [p for p in al if p.total >= L] or al; w = el
            if multi: m = max(p.ev for p in el); w = [p for p in el if p.ev == m]
            sh = amt // len(w)
            for p in w: won[s.P.index(p)] = won.get(s.P.index(p), 0) + sh
            won[s.P.index(w[0])] += amt - sh * len(w)
        for i, a in won.items():
            p = s.P[i]; p.chips += a; p.win = True
            await s.log(f'{p.name} виграє {a}' + (f' ({HN[p.ev[0]]})' if multi else ' — усі спасували'), 'w')
        s.turn = -1; await s.sync()
    async def run(s):
        try:
            while True:
                await s.hand(); await sleep(6)
                for p in s.P:
                    if p.chips == 0 and p.total > 0: await s.log(f'{p.name} вибуває зі столу', 'h')
                    p.total = 0
                left = [p for p in s.P if p.chips > 0]
                if len(left) < 2 or not any(p.user and p.chips > 0 for p in s.P):
                    await s.cast({'t': 'end', 'm': '🏆 Переможець: ' + left[0].name if len(left) == 1 else 'Гру завершено'})
                    s.over = True; return
        except asyncio.CancelledError: pass
