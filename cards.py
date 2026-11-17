"""Колода, шу (Fisher–Yates) і оцінка покерних комбінацій. Спільний модуль для покеру та блекджека."""
import itertools, random

_rng = random.SystemRandom()          # криптостійке джерело випадковості
HN = ['Старша карта', 'Пара', 'Дві пари', 'Трійка', 'Стріт', 'Флеш', 'Фул-хаус', 'Каре', 'Стріт-флеш']
FACES = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
SUITS = '♠♥♦♣'

def card_str(c): return FACES.get(c[0], str(c[0])) + SUITS[c[1]]

def shuffle(a):
    for i in range(len(a) - 1, 0, -1):
        j = _rng.randrange(i + 1); a[i], a[j] = a[j], a[i]
    return a

def new_deck(): return shuffle([(r, s) for r in range(2, 15) for s in range(4)])

class Shoe:
    """Башмак з кількох колод (для блекджека). Перетасовка між роздачами: need_shuffle() -> fill()."""
    def __init__(s, decks=6, cut=.25): s.decks, s.cut = decks, cut; s.fill()
    def fill(s):
        s.cards = shuffle([(r, u) for _ in range(s.decks) for r in range(2, 15) for u in range(4)]); s.total = len(s.cards)
    def need_shuffle(s): return len(s.cards) < s.total * s.cut
    def draw(s):
        if not s.cards: s.fill()
        return s.cards.pop()

def ev5(c):
    """Оцінка рівно 5 карт -> кортеж (категорія, розв'язувачі...); кортежі порівнюються напряму."""
    r = sorted((x[0] for x in c), reverse=True); fl = len({x[1] for x in c}) == 1; st = 0
    if len(set(r)) == 5:
        if r[0] - r[4] == 4: st = r[0]
        elif r[:2] == [14, 5]: st = 5          # «колесо» A-2-3-4-5
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

def hand_name(ev): return 'Роял-флеш' if ev[:2] == (8, 14) else HN[ev[0]]

def best_cards(cards):
    """Повертає (оцінка, п'ять карт найкращої комбінації) — для підсвічування переможної руки."""
    return max(((ev5(c), c) for c in itertools.combinations(cards, 5)), key=lambda x: x[0])
