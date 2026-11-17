import os, tempfile
os.environ['POKER_DB'] = tempfile.mktemp()
from fastapi.testclient import TestClient
import server
def login(c, n): return c.post('/api/register', json={'name': n, 'password': 'secret1'}).json()['token']
def recv_bj(ws):
    while True:
        m = ws.receive_json()
        if m['t'] == 'bj': return m
with TestClient(server.app) as c:
    tok = login(c, 'anna')
    with c.websocket_connect('/ws') as ws:
        ws.send_json({'t': 'auth', 'token': tok}); assert ws.receive_json()['t'] == 'authok'
        ws.send_json({'t': 'bj_state'}); m = recv_bj(ws); v = m['view']
        assert v['phase'] == 'bet' and v['balance'] == 1000 and v['actions'] == ['deal'] and m['rules']
        ws.send_json({'t': 'bj_deal', 'bet': 7}); assert ws.receive_json()['t'] == 'err'; assert recv_bj(ws)['view']['balance'] == 1000   # некоректна ставка
        ws.send_json({'t': 'bj_deal', 'bet': 100}); m = recv_bj(ws); v = m['view']
        holes = [e for e in m['events'] if e['e'] == 'card' and e.get('hole')]
        assert len(m['events']) >= 4 and holes and holes[0]['card'] is None            # закрита карта не передається
        if v['phase'] == 'player':
            assert v['dealer']['cards'][1] is None and v['balance'] == 900
            ws.send_json({'t': 'bj_deal', 'bet': 100}); assert ws.receive_json()['t'] == 'err'; recv_bj(ws)   # подвійний Deal
            while v['phase'] == 'player': ws.send_json({'t': 'bj_act', 'a': 'stand'}); v = recv_bj(ws)['view']
        assert v['phase'] == 'done' and all(v['dealer']['cards']); bal = v['balance']
    with c.websocket_connect('/ws') as ws:                                                      # перезавантаження сторінки
        ws.send_json({'t': 'auth', 'token': tok}); ws.receive_json(); ws.send_json({'t': 'bj_state'}); v = recv_bj(ws)['view']
        assert v['balance'] == bal and v['phase'] == 'done' and len(v['history']) == 1
        ws.send_json({'t': 'bj_new'}); v = recv_bj(ws)['view']; assert v['balance'] == 1000 and v['phase'] == 'bet' and not v['history']
print('SMOKE BJ OK')
