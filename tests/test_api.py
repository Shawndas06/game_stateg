import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from time import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from server.app import Settings, create_app
from server.auth import read_session, session_token, telegram_user
from server.storage import Store, VersionConflict


@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/state.db',session_secret='test-session-secret'))
    with TestClient(app) as c:
        yield c
    app.state.store.engine.dispose()


def command(c,save,kind,payload=None,ident='command-00001'):
    return c.post(f"/api/campaigns/{save['id']}/commands",json={'command_id':ident,'revision':save['state']['revision'],'kind':kind,'payload':payload or {}})


def test_auth_ownership_and_replay(client):
    assert client.post('/api/campaigns').status_code==401
    client.post('/api/auth/demo')
    save=client.post('/api/campaigns').json()
    one=command(client,save,'choose',{'choice':'frontier'})
    assert one.status_code==200
    replay=command(client,save,'choose',{'choice':'frontier'})
    assert replay.json()==one.json()
    assert command(client,save,'choose',{'choice':'merchants'}).status_code==409
    assert command(client,save,'end_turn',ident='other-request').status_code==409
    client.cookies.clear();client.post('/api/auth/demo')
    assert client.get(f"/api/campaigns/{save['id']}").status_code==404


def test_rejection_does_not_save_partial_mutation(client):
    client.post('/api/auth/demo');save=client.post('/api/campaigns').json()
    bad=command(client,save,'choose',{'choice':'missing'})
    assert bad.status_code==422
    assert client.get(f"/api/campaigns/{save['id']}").json()==save


def test_restart_restores_owner_snapshot_and_saved_receipt(tmp_path):
    url=f'sqlite:///{tmp_path}/restart.db'
    first=Store(url);created=first.create('player',42)
    result=first.command(created['id'],'player','saved-command',0,'choose',{'choice':'frontier'})
    first.engine.dispose()
    second=Store(url)
    assert second.latest('player')==result
    assert second.command(created['id'],'player','saved-command',0,'choose',{'choice':'frontier'})==result
    second.engine.dispose()


def test_simultaneous_commands_apply_exactly_once(tmp_path):
    store=Store(f'sqlite:///{tmp_path}/race.db');save=store.create('player',1)
    def send(i):
        try:return store.command(save['id'],'player',f'request-{i}',0,'choose',{'choice':'frontier'})['state']['revision']
        except VersionConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,[1,2]))
    assert results.count(1)==1 and results.count('conflict')==1
    assert store.get(save['id'],'player')['state']['revision']==1
    store.engine.dispose()


def signed_telegram(token,auth_date,user=None):
    data={'auth_date':str(auth_date),'query_id':'abc','user':json.dumps(user or {'id':123})}
    secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
    data['hash']=hmac.new(secret,'\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode(data)


def test_telegram_signature_expiry_and_session_integrity():
    assert telegram_user(signed_telegram('token',1000),'token',1001)=='tg:123'
    for payload in [signed_telegram('token',1000),signed_telegram('token',2000)]:
        with pytest.raises(ValueError):telegram_user(payload,'wrong',1001)
    with pytest.raises(ValueError):telegram_user(signed_telegram('token',1000),'token',1301)
    with pytest.raises(ValueError):telegram_user(signed_telegram('token',1100),'token',1000)
    token=session_token('tg:123','secret',1000)
    assert read_session(token,'secret',1001)=='tg:123'
    with pytest.raises(ValueError):read_session(token+'x','secret',1001)
    with pytest.raises(ValueError):read_session(token,'secret',1000+86401)


def test_production_never_exposes_demo_login():
    with pytest.raises(RuntimeError):create_app(Settings(mode='production'))


def test_reject_cross_origin_mutation(client):
    assert client.post('/api/auth/demo',headers={'origin':'https://unknown.example'}).status_code==403


def test_chapter_geography_is_served_with_valid_rings(client):
    response=client.get('/bithynia-geography.json')
    assert response.status_code==200
    geometry=response.json()
    assert geometry['land'] and geometry['lakes']
    for polygon in geometry['land']+geometry['lakes']:
        for ring in polygon:
            assert len(ring)>=4 and ring[0]==ring[-1]
            assert all(27.3<=lon<=32 and 38<=lat<=42.6 for lon,lat in ring)


def test_prologue_command_survives_reload_and_replay_without_advancing(client):
    client.post('/api/auth/demo')
    save=client.post('/api/campaigns',json={'scenario':'ruler_v1','campaign_mode':'long'}).json()
    assert save['state']['prologue_pending']
    before=save['state']
    response=command(client,save,'begin_reign',ident='prologue-0001')
    assert response.status_code==200,response.text
    after=response.json()
    assert not after['state']['prologue_pending']
    for field in ['day','gold','armies','obligations','provinces','people','agendas']:
        assert after['state'][field]==before[field],field
    assert command(client,save,'begin_reign',ident='prologue-0001').json()==after
    assert client.get(f"/api/campaigns/{save['id']}").json()==after
    # Existing short games retain their original entry and reject this command.
    short=client.post('/api/campaigns',json={'scenario':'ruler_v1'}).json()
    assert not short['state']['prologue_pending']
    assert command(client,short,'begin_reign',ident='prologue-0002').status_code==422
