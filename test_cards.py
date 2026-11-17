"""Тести оцінки комбінацій, колоди та башмака. Запуск: python test_cards.py"""
from collections import Counter
from cards import ev5, best, hand_name, new_deck, shuffle, Shoe, card_str

def H(s):
    f = {'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    return [(f.get(x[:-1]) or int(x[:-1]), 'SHDC'.index(x[-1])) for x in s.split()]

HANDS = [  # від найсильнішої до найслабшої
    ('AS KS QS JS 10S', 'Роял-флеш'), ('9H 8H 7H 6H 5H', 'Стріт-флеш'), ('AH AD AC AS KD', 'Каре'),
    ('KH KD KC 2S 2D', 'Фул-хаус'), ('AH JH 9H 5H 3H', 'Флеш'), ('10S 9D 8C 7H 6S', 'Стріт'),
    ('QH QD QC 9S 4D', 'Трійка'), ('JH JD 4C 4S AD', 'Дві пари'), ('10H 10D AC 8S 3D', 'Пара'), ('AH JD 9C 5S 3D', 'Старша карта')]

def test_categories_and_order():
    ev = [ev5(H(h)) for h, _ in HANDS]
    for e, (_, name) in zip(ev, HANDS): assert hand_name(e) == name, (e, name)
    assert ev == sorted(ev, reverse=True) and len(set(ev)) == len(ev)

def test_wheel_straight():
    assert ev5(H('AS 2D 3C 4H 5S')) == (4, 5)
    assert ev5(H('2D 3C 4H 5S 6S')) > ev5(H('AS 2D 3C 4H 5S'))     # 6-high стріт старший за колесо
    assert ev5(H('AH 2H 3H 4H 5H')) == (8, 5) and ev5(H('AH KD QC JH 10S')) == (4, 14)

def test_not_a_straight():
    assert ev5(H('QS KS AS 2D 3C'))[0] == 0                          # немає «обертання» через туз

def test_kickers():
    assert ev5(H('AH AD KC 5S 3D')) > ev5(H('AC AS QC 5H 3H'))        # пара тузів: кікер K проти Q
    assert ev5(H('AH AD KC 5S 3D')) > ev5(H('AC AS KD 4H 3H'))        # другий кікер
    assert ev5(H('KH KD 4C 4S AD')) > ev5(H('KC KS 4D 4H QD'))        # дві пари: кікер
    assert ev5(H('KH KD 3C 3S AD')) < ev5(H('KC KS 4D 4H 2D'))        # дві пари: старша пара вирішує
    assert ev5(H('KH KD KC 2S 2D')) > ev5(H('QH QD QC AS AD'))        # фул-хаус: трійка вирішує
    assert ev5(H('AH 9H 8H 5H 3H')) > ev5(H('KH QH JH 9H 7H'))        # флеш: старша карта
    assert ev5(H('AH 9H 8H 5H 3H')) == ev5(H('AD 9D 8D 5D 3D'))       # масті не впливають

def test_best_of_seven():
    assert best(H('2C 3D') + H('AS KS QS JS 10S')) == (8, 14)          # грає борд
    assert hand_name(best(H('AH AD') + H('AC KD KS 2C 7D'))) == 'Фул-хаус'
    assert best(H('9H 9D') + H('2C 3D 4H 5S 6C'))[0] == 4              # стріт з борду бʼє пару
    assert best(H('AS 2S') + H('3S 4S 5S 9C KH')) == (8, 5)            # колесо-стріт-флеш

def test_deck_and_shoe():
    d = new_deck(); assert len(d) == 52 and len(set(d)) == 52
    s = Shoe(6); assert len(s.cards) == 312 and all(v == 24 for v in Counter(c[0] for c in s.cards).values())
    seen = [s.draw() for _ in range(80)]; assert len(s.cards) == 232 and not s.need_shuffle()
    while not s.need_shuffle(): s.draw()
    s.fill(); assert len(s.cards) == 312
    a = list(range(10)); shuffle(a); assert sorted(a) == list(range(10))

if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('ok', k)
