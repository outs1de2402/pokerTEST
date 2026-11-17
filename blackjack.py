"""Рушій Blackjack (21). Чиста логіка без мережі та інтерфейсу: детермінована, перевіряється тестами.
Правила (див. RULES): 6 колод, дилер стоїть на всіх 17 (S17), закрита карта + перевірка на Blackjack,
виплата 3:2, Double на перших двох картах (DAS), Split до 4 рук, розділені тузи — по одній карті, без Surrender/Insurance."""
from cards import Shoe

RULES = {'decks': 6, 'dealer_stands_on': 'усі 17, включно з soft 17 (S17)', 'blackjack_pays': '3:2', 'dealer_peek': True,
         'double': 'на перших двох картах руки', 'double_after_split': True, 'split': 'дві карти однакового номіналу, до 4 рук',
         'split_aces': 'по одній карті на кожен туз, повторний split тузів заборонений', 'split_21_is_blackjack': False,
         'surrender': False, 'insurance': False, 'even_money': False}
RULES_TEXT = ['6 стандартних колод по 52 карти, башмак перетасовується приблизно після 75% карт.',
    'Дилер отримує одну відкриту й одну закриту карту; при відкритому тузі або карті вартістю 10 одразу перевіряє Blackjack.',
    'Дилер стоїть на всіх 17, включно з Soft 17 (S17).', 'Натуральний Blackjack (туз + карта вартістю 10 на перших двох картах) платить 3:2, звичайна перемога 1:1.',
    'Blackjack бʼє звичайні 21. Якщо Blackjack в обох — Push (ставка повертається). 21 після Split не є Blackjack.',
    'Double Down: на перших двох картах (також після Split) — подвоєння ставки і рівно одна карта.',
    'Split: дві карти однакового номіналу, до 4 рук. Розділені тузи отримують по одній карті, повторно тузи не розділяються.',
    'Surrender, Insurance та Even Money вимкнені. Ставки кратні 10, від 10 до 1000 віртуальних фішок.']
CHIPS = [10, 50, 100, 500, 1000]; MIN_BET, MAX_BET, START = 10, 1000, 1000; MAX_HANDS = 4

class RuleError(ValueError): pass

def value(cards):
    """(сума, soft?) — туз = 11, якщо це не призводить до перебору."""
    t = sum(1 if r == 14 else 10 if r >= 10 else r for r, _ in cards); aces = any(r == 14 for r, _ in cards)
    return (t + 10, True) if aces and t + 10 <= 21 else (t, False)

class Hand:
    def __init__(s, cards=None, bet=0, split=False, aces=False):
        s.cards = cards or []; s.bet = bet; s.from_split = split; s.split_aces = aces; s.done = False; s.doubled = False; s.result = None; s.net = 0
    total = property(lambda s: value(s.cards)[0]); soft = property(lambda s: value(s.cards)[1])
    bust = property(lambda s: s.total > 21)
    natural = property(lambda s: len(s.cards) == 2 and s.total == 21 and not s.from_split)

class Blackjack:
    def __init__(s, balance=START, shoe=None):
        s.shoe = shoe or Shoe(RULES['decks']); s.start = s.balance = balance; s.hands = []; s.dealer = []
        s.phase = 'bet'; s.active = 0; s.reveal = False; s.round = 0; s.history = []; s.events = []

    # ---------- службове ----------
    def _ev(s, e, **kw): s.events.append({'e': e, **kw})
    def _clear(s): s.hands, s.dealer, s.phase, s.active, s.reveal = [], [], 'bet', 0, False
    def _to_hand(s, h):
        c = s.shoe.draw(); h.cards.append(c); s._ev('card', to='player', hand=s.hands.index(h), card=c)
    def _to_dealer(s, hole=False):
        c = s.shoe.draw(); s.dealer.append(c); s._ev('card', to='dealer', hole=hole, card=c)
    def _dealer_bj(s): return len(s.dealer) == 2 and value(s.dealer)[0] == 21
    def _cur(s):
        if s.phase != 'player': raise RuleError('Зараз немає ходу гравця')
        return s.hands[s.active]
    def _advance(s):
        while s.active < len(s.hands) and s.hands[s.active].done: s.active += 1
        return s._finish() if s.active >= len(s.hands) else s.events

    # ---------- дії ----------
    def legal_actions(s):
        if s.phase in ('bet', 'done'): return {'deal'} if s.balance >= MIN_BET else set()
        h = s.hands[s.active]; a = {'hit', 'stand'}
        if len(h.cards) == 2 and s.balance >= h.bet: a.add('double')
        if len(h.cards) == 2 and h.cards[0][0] == h.cards[1][0] and len(s.hands) < MAX_HANDS and s.balance >= h.bet and not h.split_aces: a.add('split')
        return a
    def _need(s, a):
        if a not in s.legal_actions(): raise RuleError(f'Дія недоступна: {a}')
    def deal(s, bet):
        if s.phase == 'done': s._clear()
        if s.phase != 'bet': raise RuleError('Раунд уже триває')
        if type(bet) is not int or bet < MIN_BET or bet > MAX_BET or bet % 10: raise RuleError(f'Ставка: від {MIN_BET} до {MAX_BET}, кратна 10')
        if bet > s.balance: raise RuleError('Недостатньо фішок')
        s.events = []
        if s.shoe.need_shuffle(): s.shoe.fill(); s._ev('shuffle')
        s.balance -= bet; s.round += 1; h = Hand(bet=bet); s.hands = [h]; s.active = 0; s.reveal = False
        s._to_hand(h); s._to_dealer(); s._to_hand(h); s._to_dealer(hole=True)
        up = s.dealer[0][0]
        if (up == 14 or 10 <= up <= 13) and s._dealer_bj() or h.natural: return s._finish()      # перевірка Blackjack дилера / натуральний Blackjack
        s.phase = 'player'; return s.events
    def hit(s):
        s._need('hit'); s.events = []; h = s._cur(); s._to_hand(h)
        if h.bust or h.total == 21: h.done = True
        return s._advance()
    def stand(s):
        s._need('stand'); s.events = []; s._cur().done = True; return s._advance()
    def double(s):
        s._need('double'); s.events = []; h = s._cur(); s.balance -= h.bet; h.bet *= 2; h.doubled = True
        s._to_hand(h); h.done = True; return s._advance()
    def split(s):
        s._need('split'); s.events = []; h = s._cur(); s.balance -= h.bet; aces = h.cards[0][0] == 14
        h2 = Hand([h.cards.pop()], h.bet, True, aces); h.from_split = True; h.split_aces = aces; s.hands.insert(s.active + 1, h2)
        s._to_hand(h); s._to_hand(h2)
        for x in (h, h2):
            if aces or x.total == 21: x.done = True
        return s._advance()

    # ---------- дилер і розрахунок ----------
    def _finish(s):
        s.reveal = True; s._ev('reveal')
        if not s._dealer_bj() and any(not h.bust and not h.natural for h in s.hands):
            while value(s.dealer)[0] < 17: s._to_dealer()                     # S17: soft 17 дилер не добирає
        s._settle(); return s.events
    def _settle(s):
        if s.phase == 'done': return                                          # захист від подвійного нарахування
        dt, dbj = value(s.dealer)[0], s._dealer_bj()
        for h in s.hands:
            t = h.total
            res = ('push' if dbj else 'blackjack') if h.natural else 'lose' if dbj else 'bust' if h.bust else 'win' if dt > 21 or t > dt else 'push' if t == dt else 'lose'
            h.result = res; h.net = {'blackjack': h.bet * 3 // 2, 'win': h.bet, 'push': 0, 'lose': -h.bet, 'bust': -h.bet}[res]
            s.balance += h.bet + h.net; s._ev('result', hand=s.hands.index(h), result=res, net=h.net)
        s.phase = 'done'
        s.history = (s.history + [{'n': s.round, 'bet': sum(h.bet for h in s.hands), 'net': sum(h.net for h in s.hands),
                                   'dealer': [list(c) for c in s.dealer], 'hands': [{'cards': [list(c) for c in h.cards], 'result': h.result, 'net': h.net} for h in s.hands]}])[-50:]
    def new_game(s, balance=START):
        s.shoe.fill(); s.start = s.balance = balance; s._clear(); s.history = []; s.round = 0; s.events = []

    # ---------- представлення та збереження ----------
    def view(s):
        card = lambda c: {'r': c[0], 's': c[1]}
        shown = s.dealer if s.reveal else s.dealer[:1]
        return {'phase': s.phase, 'balance': s.balance, 'active': s.active if s.phase == 'player' else -1, 'round': s.round,
                'hands': [{'cards': [card(c) for c in h.cards], 'bet': h.bet, 'total': h.total, 'soft': h.soft, 'done': h.done, 'doubled': h.doubled,
                           'bj': h.natural, 'bust': h.bust, 'result': h.result, 'net': h.net} for h in s.hands],
                'dealer': {'cards': [card(c) for c in shown] + ([None] if s.dealer and not s.reveal else []), 'total': value(shown)[0], 'soft': value(shown)[1], 'bj': s.reveal and s._dealer_bj()},
                'actions': sorted(s.legal_actions()), 'min_bet': MIN_BET, 'max_bet': MAX_BET, 'chips': CHIPS, 'broke': s.balance < MIN_BET and s.phase != 'player', 'history': s.history[-20:]}
    def to_dict(s):
        return {'balance': s.balance, 'start': s.start, 'phase': s.phase, 'active': s.active, 'reveal': s.reveal, 'round': s.round, 'history': s.history,
                'dealer': [list(c) for c in s.dealer], 'shoe': {'cards': [list(c) for c in s.shoe.cards], 'total': s.shoe.total, 'decks': getattr(s.shoe, 'decks', RULES['decks'])},
                'hands': [{'cards': [list(c) for c in h.cards], 'bet': h.bet, 'split': h.from_split, 'aces': h.split_aces, 'done': h.done, 'doubled': h.doubled, 'result': h.result, 'net': h.net} for h in s.hands]}
    @classmethod
    def from_dict(cls, d, shoe=None):
        g = cls(d['balance'], shoe or Shoe(d['shoe']['decks'])); g.shoe.cards = [tuple(c) for c in d['shoe']['cards']]; g.shoe.total = d['shoe']['total']
        g.start, g.phase, g.active, g.reveal, g.round, g.history = d['start'], d['phase'], d['active'], d['reveal'], d['round'], d['history']
        g.dealer = [tuple(c) for c in d['dealer']]
        for x in d['hands']:
            h = Hand([tuple(c) for c in x['cards']], x['bet'], x['split'], x['aces']); h.done, h.doubled, h.result, h.net = x['done'], x['doubled'], x['result'], x['net']; g.hands.append(h)
        return g
