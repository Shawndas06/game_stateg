from copy import deepcopy
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from campaign.engine import RuleError
from campaign.ruler.engine import apply_command, new_campaign, view
from server.app import Settings,create_app
from server.storage import DiagnosticRow
from tactical_scenarios import encounter


def test_regular_council_calendar_and_repeat_open():
    s=new_campaign(11,extended=True,living=True)
    s=apply_command(s,'begin_reign',{})
    for _ in range(21):
        s=apply_command(s,'advance',{'days':1,'strategic':True,'until_event':False})
    assert s.day==21 and s.flags['advance_result']['reason']=='council'
    assert view(s)['council_schedule']['next_day']==42
    rows=[r for r in s.reports if r['kind']=='council_due'];assert len(rows)==1
    payload={'agenda':s.agendas[0]['id']} if s.agendas else {}
    s=apply_command(s,'consult',payload);seq=s.archive_seq;gold=s.gold
    s=apply_command(s,'consult',payload)
    assert s.archive_seq==seq and s.gold==gold and s.day==21


def test_day_week_accounting_and_no_ui_commands():
    base=apply_command(new_campaign(29,extended=True,living=True),'begin_reign',{})
    daily=base;weekly=base
    for _ in range(28):daily=apply_command(daily,'advance',{'days':1,'strategic':True,'until_event':False})
    while weekly.day<28:weekly=apply_command(weekly,'advance',{'days':min(7,28-weekly.day),'strategic':True,'until_event':False})
    assert daily.day==weekly.day==28
    assert daily.gold==weekly.gold and daily.places==weekly.places and daily.armies==weekly.armies


@pytest.mark.parametrize('bad',[None,{},[{'unit':'missing','lane':'center'}],[{'unit':'own','lane':'ocean'}],'invalid'])
def test_invalid_batch_is_atomic(bad):
    s,_=encounter();before=deepcopy(s.to_dict());b=s.flags['battle'];own=next(u for u in b['units'] if u['side']==b['player_side'])
    if isinstance(bad,list):bad=[{**x,'unit':own['id'] if x.get('unit')=='own' else x.get('unit')} for x in bad]
    with pytest.raises(RuleError):apply_command(s,'battle_step',{'battle':b['id'],'orders':bad})
    assert s.to_dict()==before


def test_batch_matches_explicit_preparation_and_rejects_duplicates():
    s,_=encounter();b=s.flags['battle'];units=[u for u in b['units'] if u['side']==b['player_side']]
    orders=[{'unit':u['id'],'lane':'left' if i%2 else 'reserve'} for i,u in enumerate(units)]
    prepared=s
    for order in orders:prepared=apply_command(prepared,'battle_deploy',{'battle':b['id'],**order})
    explicit=apply_command(prepared,'battle_step',{'battle':b['id']})
    batch=apply_command(s,'battle_step',{'battle':b['id'],'orders':orders})
    assert batch.armies==explicit.armies and batch.flags['battle']==explicit.flags['battle']
    with pytest.raises(RuleError):apply_command(s,'battle_step',{'battle':b['id'],'orders':[orders[0],orders[0]]})
    enemy=next(u for u in b['units'] if u['side']!=b['player_side'])
    with pytest.raises(RuleError):apply_command(s,'battle_step',{'battle':b['id'],'orders':[{'unit':enemy['id'],'lane':'left'}]})


def test_diagnostics_privacy_bounds_rate_and_retention(tmp_path):
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/diag.db',session_secret='test'))
    body={'build':'abc123','quality':'low','width':390,'height':844,'events':[{'kind':'map_frame','duration_ms':25}]}
    with TestClient(app) as c:
        assert c.post('/api/diagnostics',json=body).status_code==401
        c.post('/api/auth/demo')
        with app.state.store.session.begin() as db:db.add(DiagnosticRow(id='expired',created_at=int(time.time())-31*86400,report={}))
        assert c.post('/api/diagnostics',json=body).status_code==202
        for invalid in [{**body,'token':'secret'},{**body,'events':[{'kind':'manual','duration_ms':0,'text':'private'}]},{**body,'width':0},{**body,'events':body['events']*21}]:
            assert c.post('/api/diagnostics',json=invalid).status_code==422
        with app.state.store.session() as db:
            rows=list(db.scalars(select(DiagnosticRow)));assert len(rows)==1 and rows[0].report==body
        for _ in range(19):assert c.post('/api/diagnostics',json=body).status_code==202
        assert c.post('/api/diagnostics',json=body).status_code==429
        assert c.get('/api/release').status_code==200
    app.state.store.engine.dispose()


def test_command_directory_covers_every_public_command():
    import json
    from pathlib import Path
    from typing import get_args
    from server.app import Command
    directory=json.loads(Path('docs/command-directory.json').read_text())
    assert set(directory)==set(get_args(Command.model_fields['kind'].annotation))
    assert all(row['entry'] and row['condition'] and row['verification'] for row in directory.values())


def gather_request():
    return {'target':'sogut','armies':[{'army':'ottoman-1','funds':5,'food':100,'warehouse':'sogut'}],'sources':[{'province':'karacahisar','commander':'konur','troops':{'militia':10},'funds':7,'ration_days':20}]}


def test_remote_gather_no_teleport_and_real_resource_accounting():
    s=apply_command(new_campaign(11,extended=True,living=True),'begin_reign',{})
    gold=s.gold;guards=sum(c.count for c in s.places['karacahisar'].garrison)
    total=lambda st:sum(a.size for a in st.armies.values() if a.faction=='ottoman')+sum(sum(c.count for c in p.garrison) for p in st.places.values() if p.controller=='ottoman')
    grain=lambda st:sum(a.grain for a in st.armies.values() if a.faction=='ottoman')+sum(p.grain for p in st.places.values() if p.controller=='ottoman')+sum(c['grain'] for c in st.transports.values())
    men=total(s);food=grain(s);army_ids=set(s.armies)
    prepared=apply_command(s,'plan_gather',gather_request())
    assert prepared.gold==gold and total(prepared)==men and grain(prepared)==food and not prepared.edicts
    assert view(prepared)['statecraft']['gather_draft']['funds']==17
    s=apply_command(prepared,'execute_gather',{})
    assert s.gold==gold-17 and set(s.armies)==army_ids and total(s)==men and grain(s)==food
    assert sum(c.count for c in s.places['karacahisar'].garrison)==guards
    assert any(e['kind']=='form_army' and e['escrow']==7 for e in s.edicts)
    appeared=None
    for _ in range(30):
        s=apply_command(s,'advance',{'days':1,'until_event':False})
        appeared=next((a for a in s.armies.values() if a.commander=='konur'),None)
        if appeared:break
    assert appeared and s.day>0
    assert appeared.location=='karacahisar' and sum(c.count for c in s.places['karacahisar'].garrison)==guards-10
    assert all(c.origin=='karacahisar' for c in appeared.cohorts)
    for _ in range(30):
        if appeared.location=='sogut' and not appeared.travel:break
        s=apply_command(s,'advance',{'days':1,'until_event':False});appeared=s.armies[appeared.id]
    assert appeared.location=='sogut' and appeared.mission['status']=='completed'


@pytest.mark.parametrize('change',[
    {'armies':[{'army':{},'funds':0}]},
    {'sources':[{'province':{},'troops':{}}]},
    {'sources':[{'province':'karacahisar','commander':'konur','troops':{'militia':99999}}]},
    {'sources':[{'province':'karacahisar','commander':'orhan','troops':{'militia':5}}]},
    {'target':'bursa'},
    {'armies':[{'army':'ottoman-1','funds':5000}]},
    {'personal':True,'regent':'konur'},
])
def test_gather_rejections_are_atomic(change):
    s=new_campaign(11,extended=True,living=True);before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'plan_gather',{**gather_request(),**change})
    assert s.to_dict()==before


def test_stale_gather_draft_cannot_execute():
    s=apply_command(new_campaign(11,extended=True,living=True),'plan_gather',gather_request())
    s=apply_command(s,'consult',{});before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'execute_gather',{})
    assert s.to_dict()==before


def test_gather_api_replay_ownership_and_deferred_failure(tmp_path):
    from server.auth import read_session
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/gather.db',session_secret='gather-test'))
    with TestClient(app) as c:
        token=c.post('/api/auth/demo').json()['session_token'];owner=read_session(token,'gather-test');save=app.state.store.create(owner,11,'ruler_v1','realm')
        url=f'/api/campaigns/{save["id"]}/commands'
        request={'command_id':'prepare-gather-0001','revision':save['state']['revision'],'kind':'plan_gather','payload':gather_request()}
        prepared=c.post(url,json=request);assert prepared.status_code==200,prepared.text
        request={'command_id':'execute-gather-0001','revision':prepared.json()['state']['revision'],'kind':'execute_gather','payload':{}}
        first=c.post(url,json=request);assert first.status_code==200,first.text
        assert c.post(url,json=request).json()==first.json()
        assert len([e for e in first.json()['state']['pending_edicts'] if e['kind']=='form_army'])==1
        latest=first.json();response=c.post(url,json={'command_id':'forbidden-internal','revision':latest['state']['revision'],'kind':'form_army','payload':{'_delivered':True,'province':'karacahisar','commander':'konur','troops':{'militia':1}}})
        assert response.status_code==422
        # A legal summons makes the future executor unavailable before delivery.
        response=c.post(url,json={'command_id':'summon-future-leader','revision':latest['state']['revision'],'kind':'summon','payload':{'person':'konur'}});assert response.status_code==200,response.text;latest=response.json()
        for i in range(10):
            if not any(e['kind']=='form_army' for e in latest['state']['pending_edicts']):break
            response=c.post(url,json={'command_id':f'wait-obstruction-{i:03}','revision':latest['state']['revision'],'kind':'advance','payload':{'days':1}});assert response.status_code==200,response.text;latest=response.json()
        assert not any(e['kind']=='form_army' for e in latest['state']['pending_edicts'])
        assert not any(a['commander']=='konur' for a in latest['state']['armies'].values())
        assert any(r['kind']=='obstruction' for r in latest['state']['reports'])
        c.cookies.clear();c.post('/api/auth/demo');assert c.post(url,json=request).status_code==404
    app.state.store.engine.dispose()


def test_create_receipt_prevents_duplicate_new_game_with_existing_save(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from server.storage import Store,CampaignRow,VersionConflict
    store=Store(f'sqlite:///{tmp_path}/create.db');old=store.create('owner',1,'ruler_v1','long')
    def create(i):return store.create('owner',i+2,'ruler_v1','realm','same-creation-0001')
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(create,range(4)))
    assert len({x['id'] for x in results})==1 and results[0]['id']!=old['id']
    with store.session() as db:assert len(list(db.scalars(select(CampaignRow))))==2
    with pytest.raises(VersionConflict,match='Идентификатор создания'):store.create('owner',10,'ruler_v1','chapter','same-creation-0001')
    assert store.create('different-owner',1,'ruler_v1','realm','same-creation-0001')['id']!=results[0]['id']
    store.engine.dispose()


def test_text_compression_and_media_range_cache_contract(tmp_path):
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/headers.db',session_secret='test'))
    with TestClient(app) as c:
        data=c.get('/mediterranean-geography.json?v=test',headers={'Accept-Encoding':'gzip'})
        assert data.status_code==200 and data.headers['content-encoding']=='gzip'
        assert data.headers['cache-control']=='public, max-age=86400' and data.json()['land']
        plain=c.get('/mediterranean-geography.json');assert plain.headers['cache-control']=='no-cache'
        media=c.get('/media/succession.mp4',headers={'Range':'bytes=0-31','Accept-Encoding':'gzip'})
        assert media.status_code==206 and len(media.content)==32 and 'content-encoding' not in media.headers
        assert c.get('/api/catalog').headers['cache-control']=='no-store'
    app.state.store.engine.dispose()


def test_council_protocol_keeps_changed_facts_on_the_same_day():
    s=apply_command(new_campaign(11,extended=True,living=True),'consult',{})
    first=s.archive_seq;day=s.day
    s=apply_command(s,'consult',{});assert s.archive_seq==first
    s=apply_command(s,'raise',{'province':'sogut','troop':'militia','count':1})
    before=s.archive_seq;s=apply_command(s,'consult',{})
    assert s.day==day and s.archive_seq>before
    assert any(f'{s.gold} монет' in r['text'] for r in s.reports if r['kind']=='speech')
