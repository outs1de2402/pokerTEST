import os,tempfile,time
os.environ['POKER_DB']=tempfile.mktemp()
import engine; engine.SPEED=0.02
from fastapi.testclient import TestClient
import server
with TestClient(server.app) as c:
    A=c.post('/api/register',json={'name':'anna','password':'secret1'}).json()
    B=c.post('/api/register',json={'name':'bohdan','password':'secret2'}).json()
    assert c.post('/api/register',json={'name':'ANNA','password':'secret1'}).status_code==409
    assert c.post('/api/login',json={'name':'anna','password':'bad'}).status_code==401
    with c.websocket_connect('/ws') as a, c.websocket_connect('/ws') as b:
        a.send_json({'t':'auth','token':A['token']});assert a.receive_json()['t']=='authok'
        b.send_json({'t':'auth','token':B['token']});assert b.receive_json()['t']=='authok'
        a.send_json({'t':'create','bots':1,'stack':500});m=a.receive_json();code=m['code'];assert m['t']=='lobby'
        assert c.get('/api/tables').json()[0]['code']==code
        b.send_json({'t':'join','code':code.lower()})
        a.send_json({'t':'start'})
        seen={'a':False,'b':False};hole=[]
        for who,ws in (('a',a),('b',b)):
            for _ in range(80):
                m=ws.receive_json()
                if m['t']=='state':
                    mine=[p for p in m['pl'] if p['me']][0];others=[p for p in m['pl'] if not p['me'] and p['h']]
                    assert all(x is None for p in others for x in p['h']) and all(mine['h'])
                    if m['act']: ws.send_json({'t':'act','tk':m['tk'],'a':'c'});seen[who]=True;break
        assert seen['a'] and seen['b'],seen
    print('SMOKE OK')
