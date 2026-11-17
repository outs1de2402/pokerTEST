"""Тести рушія Blackjack. Запуск: python test_blackjack.py"""
import random
from blackjack import Blackjack, RuleError, RULES, value, MIN_BET, MAX_BET
from test_cards import H

class Stack:
    """Башмак із наперед заданим порядком карт: гравець, відкрита дилера, гравець, закрита дилера, далі добір."""
    def __init__(s, cards): s.cards = list(cards)[::-1]; s.total = 999
    def draw(s): return s.cards.pop()
    def need_shuffle(s): return False
    def fill(s): pass
def game(txt, balance=1000): return Blackjack(balance, Stack(H(txt)))
def raises(f, *a):
    try: f(*a)
    except RuleError: return True
    return False

# ---------- значення карт ----------
def test_hand_values():
    assert value(H('AS KH')) == (21, True) and value(H('AS AH')) == (12, True) and value(H('AS 9H 5D')) == (15, False)
    assert value(H('AS 6H')) == (17, True) and value(H('AS 6H 10D')) == (17, False)          # туз як 1, якщо 11 дає перебір
    assert value(H('AS AH 9D')) == (21, True) and value(H('10S 10H 5D')) == (25, False) and value(H('KS QH')) == (20, False)

def test_rules_config():
    assert RULES['decks'] == 6 and RULES['blackjack_pays'] == '3:2' and RULES['dealer_peek'] and RULES['double_after_split']
    assert not (RULES['surrender'] or RULES['insurance'] or RULES['even_money'] or RULES['split_21_is_blackjack'])
    g = Blackjack(); assert len(g.shoe.cards) == 312

# ---------- Blackjack і ставки ----------
def test_blackjack_pays_3_to_2():
    g = game('AS 9H KS 7D'); g.deal(100); assert g.phase == 'done' and g.hands[0].result == 'blackjack' and g.balance == 1150
def test_both_blackjack_is_push():
    g = game('AS AH KS KH'); g.deal(100); assert g.hands[0].result == 'push' and g.balance == 1000
def test_dealer_blackjack_peek_ace_and_ten():
    g = game('10S AH 10H KD'); g.deal(100); assert g.phase == 'done' and g.hands[0].result == 'lose' and g.balance == 900 and not g.legal_actions() - {'deal'}
    g = game('9S KH 9H AD'); g.deal(100); assert g.phase == 'done' and g.balance == 900                       # 10 + туз
def test_no_peek_when_upcard_is_not_ace_or_ten():
    g = game('10S 9H 9D 10C'); g.deal(100); assert g.phase == 'player'                                        # у дилера 19, перевірки не було
    g = game('10S AH 9D 5C'); g.deal(100); assert g.phase == 'player'                                         # туз, але Blackjack немає
def test_blackjack_beats_three_card_21():
    g = game('AS 5H KS 6D'); g.deal(100); assert g.balance == 1150 and len(g.dealer) == 2                      # дилер не добирає проти Blackjack
def test_three_card_21_pushes_dealer_21():
    g = game('7S 5H 7D 6C 7H 10D'); g.deal(100); g.hit()                                                      # гравець 7-7-7=21, дилер 5-6-10=21
    assert g.phase == 'done' and g.hands[0].result == 'push' and g.balance == 1000 and not g.hands[0].natural

# ---------- результати ----------
def test_push_returns_bet():
    g = game('KS 10H 8S 8D'); g.deal(100); g.stand(); assert g.hands[0].result == 'push' and g.balance == 1000
def test_bust_loses_and_dealer_does_not_draw():
    g = game('KS 9H 6S 8D KH'); g.deal(100); g.hit(); assert g.hands[0].result == 'bust' and g.balance == 900 and len(g.dealer) == 2
def test_dealer_bust_pays_1_to_1():
    g = game('KS 6H 9S 10D KH'); g.deal(100); g.stand(); assert g.dealer and len(g.dealer) == 3 and g.hands[0].result == 'win' and g.balance == 1100
def test_dealer_stands_on_soft_17():
    g = game('KS AH 9S 6D'); g.deal(100); g.stand(); assert len(g.dealer) == 2 and g.hands[0].result == 'win'      # A+6 = soft 17, добору немає
def test_dealer_hits_16_and_stands_on_hard_17():
    g = game('KS 10H 8S 6D AH'); g.deal(100); g.stand(); assert len(g.dealer) == 3 and value(g.dealer) == (17, False) and g.hands[0].result == 'win'
def test_dealer_hits_soft_16_to_18_and_stands():
    g = game('KS AH 9S 5D 2C'); g.deal(100); g.stand(); assert value(g.dealer) == (18, True) and g.hands[0].result == 'win'  # 19 проти 18
def test_hit_to_21_auto_stands():
    g = game('5S KH 6S 7D KC'); g.deal(100); g.hit(); assert g.phase == 'done' and g.hands[0].total == 21

# ---------- Double ----------
def test_double_once_one_card():
    g = game('5S KH 6S 7D KC'); g.deal(100); g.double()
    assert g.hands[0].bet == 200 and len(g.hands[0].cards) == 3 and g.phase == 'done' and g.balance == 1200
    assert raises(g.double) and g.balance == 1200
def test_double_blocked_by_balance_and_after_hit():
    g = game('5S KH 6S 7D', balance=150); g.deal(100); assert 'double' not in g.legal_actions() and raises(g.double)
    g = game('2S KH 3S 7D 2D', balance=1000); g.deal(100); g.hit(); assert 'double' not in g.legal_actions()
def test_double_loss_costs_double():
    g = game('5S KH 6S 10D 2C'); g.deal(100); g.double(); assert g.hands[0].result == 'lose' and g.balance == 800

# ---------- Split ----------
def test_split_creates_independent_hands():
    g = game('8S 6H 8H 10D 3S 10S KC'); g.deal(100); g.split()
    assert len(g.hands) == 2 and g.balance == 800 and [h.bet for h in g.hands] == [100, 100] and g.active == 0
    g.hit(); assert len(g.hands[0].cards) == 3 and len(g.hands[1].cards) == 2                               # рука 2 не змінилась
    assert g.hands[0].total == 21 and g.hands[1].total == 18 and g.active == 1                              # 21 — рука завершена автоматично
def test_double_after_split():
    g = game('8S 6H 8H 10D 3S 5C 10C'); g.deal(100); g.split(); assert 'double' in g.legal_actions(); g.double()
    assert g.hands[0].bet == 200 and g.hands[1].bet == 100 and g.active == 1
def test_split_needs_same_rank_and_funds():
    g = game('KS 6H QS 9D'); g.deal(100); assert 'split' not in g.legal_actions() and raises(g.split)             # K-Q: різний номінал
    g = game('KS 6H KH 9D', balance=150); g.deal(100); assert 'split' not in g.legal_actions()                  # не вистачає на другу ставку
    g = game('KS 6H KH 9D'); g.deal(100); assert 'split' in g.legal_actions()
def test_split_aces_one_card_no_resplit_and_21_not_blackjack():
    g = game('AS 9H AH 8D AC KD'); g.deal(100); g.split()                                                      # туз+туз, добір: туз і король
    assert g.phase == 'done' and [len(h.cards) for h in g.hands] == [2, 2]
    assert g.hands[0].cards[1][0] == 14
    assert g.hands[1].total == 21 and not g.hands[1].natural and g.hands[1].result == 'win' and g.hands[1].net == 100   # 1:1, а не 3:2
    assert g.hands[0].result == 'lose'                                                                           # 12 проти 17
def test_max_four_hands():
    g = game('8S 6H 8H 10D' + ' 8C' * 12); g.deal(100)
    while 'split' in g.legal_actions(): g.split()
    assert len(g.hands) == 4 and 'split' not in g.legal_actions() and raises(g.split) and g.balance == 600

# ---------- ставки та стан ----------
def test_bet_validation_leaves_state_intact():
    g = game('KS 9H 9S 8D')
    for bad in (0, 5, 15, -10, MAX_BET + 10, 2000, 10.5, True, '10'): assert raises(g.deal, bad), bad
    assert g.balance == 1000 and g.phase == 'bet'
    g.deal(100); assert raises(g.deal, 100) and g.balance == 900                                              # подвійний Deal не знімає ставку вдруге
def test_no_double_settlement():
    g = game('KS 6H 9S 10D KH'); g.deal(100); g.stand(); b = g.balance
    assert raises(g.stand) and raises(g.hit) and g.balance == b and len(g.history) == 1
def test_next_round_without_reload():
    g = game('KS 6H 9S 10D KH 10S 9H 8S 8D'); g.deal(100); g.stand(); assert g.phase == 'done'
    g.deal(50); assert g.phase == 'player' and g.round == 2 and len(g.hands) == 1 and len(g.dealer) == 2 and g.balance == 1100 - 50
def test_hole_card_hidden_until_dealer_turn():
    g = game('KS 9H 6S 8D KH'); g.deal(100); v = g.view()
    assert v['dealer']['cards'][1] is None and v['dealer']['total'] == 9 and v['actions'] == ['double', 'hit', 'stand']
    g.stand(); v = g.view(); assert all(v['dealer']['cards']) and v['phase'] == 'done'
def test_new_game_resets():
    g = game('KS 6H 9S 10D KH'); g.deal(100); g.stand(); g.new_game(); assert g.balance == 1000 and g.phase == 'bet' and not g.history and not g.hands
def test_broke_player_cannot_deal():
    g = game('KS 9H 9S 8D', balance=5); assert not g.legal_actions() and g.view()['broke'] and raises(g.deal, 10)
def test_shoe_reshuffles_between_rounds():
    g = Blackjack(); g.shoe.cards = g.shoe.cards[:50]; ev = g.deal(10); assert any(e['e'] == 'shuffle' for e in ev) and len(g.shoe.cards) > 250
def test_save_and_restore_mid_round():
    g = Blackjack(); g.deal(100)
    while g.phase == 'player' and g.hands[0].total < 12: g.hit()
    d = g.to_dict(); r = Blackjack.from_dict(d)
    assert r.view() == g.view() and r.shoe.cards == g.shoe.cards
    if g.phase == 'player': g.stand(); r.stand(); assert r.view() == g.view()

# ---------- симуляції ----------
def play_round(g, rnd):
    g.deal(rnd.choice([b for b in (10, 50, 100) if b <= g.balance]))
    while g.phase == 'player':
        a = sorted(g.legal_actions()); g.__getattribute__(rnd.choice(a))()
def test_random_play_invariants():
    rnd = random.Random(7); g = Blackjack(); rounds = 0
    for _ in range(4000):
        if g.balance < MIN_BET: g.new_game()
        before = g.balance; play_round(g, rnd); rounds += 1
        assert g.phase == 'done' and 1 <= len(g.hands) <= 4 and g.balance >= 0
        assert g.balance == before + sum(h.net for h in g.hands) and all(h.result and h.bet % 10 == 0 for h in g.hands)
        assert len(g.shoe.cards) + len(g.dealer) + sum(len(h.cards) for h in g.hands) <= 312

def test_house_edge_with_dealer_mimic_strategy():
    """Стратегія «як дилер» має програшне очікування ≈ −5%: перевіряє виплати 3:2/1:1 та правила дилера."""
    g = Blackjack(balance=10**9); net = bet = 0
    for _ in range(30000):
        g.deal(10)
        while g.phase == 'player':
            g.hit() if g.hands[g.active].total < 17 else g.stand()
        net += sum(h.net for h in g.hands); bet += sum(h.bet for h in g.hands)
    assert -.10 < net / bet < -.01, net / bet

if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('ok', k)
