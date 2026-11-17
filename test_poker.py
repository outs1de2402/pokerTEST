"""Тести правил покеру: торги, мінімальні рейзи, неповний олл-ін, heads-up, сайд-поти, нічиї, боти.
Запуск: python test_poker.py"""
import asyncio, engine
from engine import Table, player
import bots
from test_cards import H
engine.SPEED = 0
run = asyncio.run

def mk(n=3, chips=1000):
    t = Table('T', 'h', chips, 0); t.P = [player(f'p{i}') for i in range(n)]
    for p in t.P: p.chips = chips; p.inn = True
    t.btn = 0; return t
def script(t, moves):
    it = iter(moves); t.bot = lambda p: next(it)
R = lambda to: {'t': 'r', 'to': to}; CALL = {'t': 'c'}; FOLD = {'t': 'f'}

# ---------- торги ----------
def test_min_bet_clamped():
    t = mk(); script(t, [R(5), FOLD, FOLD]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert t.cur == 20 and t.P[0].bet == 20

def test_min_reraise_clamped():
    t = mk(); script(t, [R(100), R(110), FOLD, CALL]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert t.cur == 200 and t.P[0].bet == t.P[1].bet == 200 and t.P[2].folded

def test_full_raise_reopens_action():
    t = mk(); script(t, [R(100), R(250), FOLD, R(400), CALL]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert t.cur == 400 and t.P[0].bet == t.P[1].bet == 400

def test_short_allin_does_not_reopen():
    t = mk(); t.P[1].chips = 130
    script(t, [R(100), R(999), CALL, R(500)]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert t.cur == 130 and [p.bet for p in t.P] == [130, 130, 130] and t.P[1].allin   # P0 не зміг рейзити

def test_allin_clamped_to_stack_and_total_tracked():
    t = mk(); t.P[0].chips = 50; script(t, [R(9999), CALL, CALL]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert t.P[0].allin and t.P[0].total == 50 and t.P[1].bet == 50

def test_everyone_folds_ends_round():
    t = mk(); script(t, [R(40), FOLD, FOLD]); t.cur, t.minr = 0, 20; run(t.betround(0))
    assert sum(not p.folded for p in t.P) == 1

def _order(n):
    t = mk(n); t.btn = -1; order = []
    def b(p): order.append((len(t.board), t.P.index(p))); return CALL
    t.bot = b; run(t.hand()); return t, order

def test_heads_up_order():
    t, o = _order(2)
    assert o[0] == (0, 0) and o[1] == (0, 1)        # дилер = малий блайнд ходить першим на префлопі
    assert o[2] == (3, 1)                            # постфлоп першим ходить великий блайнд
    assert t.SB == 10 and sum(p.chips for p in t.P) == 2000

def test_three_handed_order():
    t, o = _order(3)
    assert [x[1] for x in o[:3]] == [0, 1, 2] and o[3] == (3, 1)   # префлоп: після ВВ, постфлоп: з малого блайнда

def test_blinds_posted():
    t = mk(4); t.bot = lambda p: FOLD
    async def go():
        t.btn = -1; await t.hand()
    run(go()); assert sum(p.chips for p in t.P) == 4000

# ---------- банк ----------
BOARD = [(2, 0), (7, 1), (9, 2), (11, 3), (13, 0)]
def pay(t): t.board = list(BOARD); run(t.payout()); return [p.chips for p in t.P]
def setup(totals, hands, folded=()):
    t = mk(len(totals), 0); t.btn = 0
    for p, tot, h in zip(t.P, totals, hands): p.total = tot; p.hand = h
    for i in folded: t.P[i].folded = True
    return t

def test_side_pots():
    t = setup([100, 300, 300, 50], [[(13, 1), (13, 2)], [(11, 0), (11, 1)], [(9, 0), (9, 1)], [(3, 0), (4, 1)]], folded=[3])
    assert pay(t) == [350, 400, 0, 0]               # A бере основний + 1-й сайд, B — 2-й сайд; разом 750

def test_split_pot_odd_chip_goes_left_of_dealer():
    royal = [(14, 0), (13, 0), (12, 0), (11, 0), (10, 0)]
    t = setup([101, 101, 101], [[(2, 1), (3, 2)], [(2, 2), (3, 3)], [(4, 1), (5, 2)]], folded=[2])
    t.board = royal; run(t.payout())
    assert [p.chips for p in t.P] == [151, 152, 0]  # зайва фішка — гравцю ліворуч від дилера (P1)

def test_uncalled_bet_returned():
    t = setup([300, 100], [[(2, 1), (3, 2)], [(13, 1), (13, 2)]])
    assert pay(t) == [200, 200]                      # B (сильніша рука) бере 200, A повертається 200

def test_everyone_else_folded():
    t = setup([40, 20, 10], [[(2, 1), (3, 2)], [(4, 1), (5, 2)], [(6, 1), (7, 2)]], folded=[1, 2])
    assert pay(t) == [70, 0, 0]

def test_view_exposes_winning_five():
    t = setup([100, 100], [[(14, 1), (14, 2)], [(2, 1), (3, 2)]]); t.board = list(BOARD); t.btn = 0; run(t.payout())
    v = t.view(t.P[0]); w = v['pl'][0]
    assert w['w'] and len(w['b5']) == 5 and v['pl'][1]['b5'] is None and v['hno'] == 0
    assert all(x is None for x in t.view(t.P[1])['pl'][0]['h']) is False   # після вскриття карти переможця видно

def test_chip_conservation_simulation():
    for n in range(2, 10):
        t = Table('T', 'x', 1000, 0); t.P = [player(f'b{i}') for i in range(n)]
        for p in t.P: p.chips = 1000
        for h in range(80):
            if sum(p.chips > 0 for p in t.P) < 2: break
            run(t.hand()); assert sum(p.chips for p in t.P) == 1000 * n, (n, h)
            for p in t.P: p.total = 0

# ---------- боти ----------
def view(hand, board=(), to_call=0, pot=100, opp=2, chips=1000):
    return dict(hand=hand, board=list(board), pot=pot, to_call=to_call, chips=chips, cur=to_call, min_raise_to=to_call + 20,
                big_blind=20, opponents=opp, raises=0, can_raise=True)

def test_bots_never_fold_monster_and_fold_trash():
    aa = [(14, 0), (14, 1)]; trash = [(7, 0), (2, 1)]
    for st in bots.STYLES:
        assert all(bots.decide(st, view(aa, to_call=40))['t'] != 'f' for _ in range(300))
        folds = sum(bots.decide(st, view(trash, to_call=300))['t'] == 'f' for _ in range(300)); assert folds > 270, (st, folds)

def test_aggressive_raises_more_than_cautious():
    h = [(10, 1), (9, 1)]; rate = lambda st: sum(bots.decide(st, view(h))['t'] == 'r' for _ in range(3000)) / 3000
    assert rate('aggressive') > rate('balanced') > rate('cautious')

def test_bot_decisions_are_legal_in_game():
    t = mk(4); t.P[0].chips = 60
    for p in t.P: p.hand = [(2, 0), (3, 1)]
    d = t.bot(t.P[0]); assert d['t'] in 'fcr' and ('to' in d or d['t'] != 'r')

if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('ok', k)
