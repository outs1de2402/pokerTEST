"""Штучний інтелект ботів. Не залежить від рушія: отримує знімок ситуації (dict), повертає рішення.
Рішення: {'t': 'f'|'c'|'r', 'to': сума_до_якої_підвищити}."""
import random
from cards import best

STYLES = {   # raise_at — поріг сили для рейзу, margin — запас над шансами банку для колу, bluff — частота блефу
    'cautious':   dict(raise_at=.80, margin=.18, bluff=.02, size=(.4, .6), loose=0.0),
    'balanced':   dict(raise_at=.72, margin=.12, bluff=.05, size=(.5, .8), loose=.05),
    'aggressive': dict(raise_at=.62, margin=.06, bluff=.12, size=(.6, 1.0), loose=.12),
}

def preflop_strength(hand):
    a, b = sorted((c[0] for c in hand), reverse=True)
    v = .5 + a / 28 if a == b else (a + b) / 40 + (.05 if a > 10 else 0)
    if hand[0][1] == hand[1][1]: v += .06
    if a != b and a - b <= 2: v += .04
    return min(v, 1)

def draw_bonus(hand, board):
    """Бонус за незавершені флеш- і стріт-дро (лише на флопі та терні)."""
    if len(board) >= 5: return 0
    cards = hand + board; b = 0
    if any(sum(c[1] == s for c in cards) == 4 and any(h[1] == s for h in hand) for s in range(4)): b += .15
    rs = {c[0] for c in cards} | ({1} if any(c[0] == 14 for c in cards) else set())
    hr = {h[0] for h in hand} | ({1} if any(h[0] == 14 for h in hand) else set())
    if any(all(x + i in rs for i in range(4)) and any(x + i in hr for i in range(4)) for x in range(1, 12)): b += .10
    return min(b, .22)

def strength(hand, board):
    if not board: return preflop_strength(hand)
    e = best(hand + board); k = e[0]
    if k == 1: made = .4 + .1 * (e[1] - 2) / 12 if any(c[0] == e[1] for c in hand) else .25
    else: made = [.15, 0, .65, .75, .85, .88, .95, .99, 1][k]
    return made + (1 - made) * draw_bonus(hand, board) if k < 4 else made

def decide(style, v):
    """v: hand, board, pot, to_call, chips, cur, min_raise_to, big_blind, opponents, raises, can_raise."""
    P = STYLES.get(style, STYLES['balanced']); bb = v['big_blind']
    s = strength(v['hand'], v['board']) - .02 * (max(1, v['opponents']) - 1) + random.uniform(-.07, .07)
    tc, pot = v['to_call'], v['pot']; odds = tc / ((pot + tc) or 1)
    if v['can_raise'] and v['chips'] > tc and v['raises'] < 4 and (s > P['raise_at'] or (random.random() < P['bluff'] and s > .25)):
        size = max(v['min_raise_to'] - v['cur'], round(pot * random.uniform(*P['size']) / bb) * bb)
        return {'t': 'r', 'to': v['cur'] + size}
    if tc == 0: return {'t': 'c'}
    if s > odds + P['margin'] or (s > .45 - P['loose'] and tc <= bb * 2): return {'t': 'c'}
    return {'t': 'f'}
