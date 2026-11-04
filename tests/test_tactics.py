from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from campaign.engine import RuleError
from campaign.ruler import tactics
from campaign.ruler.engine import apply_command, view
from campaign.ruler.models import RulerState
from server.app import Settings, create_app
from server.auth import read_session
from tactical_scenarios import encounter, resolve


@pytest.fixture
def pending():
    return encounter()[0]


def test_pause_orders_and_no_created_troops(pending):
    s=pending;b=view(s)['battle'];own=next(u for u in b['units'] if u['side']==b['player_side'])
    before=deepcopy(s.to_dict())
    for kind,payload in [('advance',{'days':1}),('raise',{'count':1}),('continue_campaign',{}),('tactical_mode',{'enabled':False})]:
        with pytest.raises(RuleError):apply_command(s,kind,payload)
        assert s.to_dict()==before
    for lane in tactics.LANES:
        s=apply_command(s,'battle_deploy',{'battle':b['id'],'unit':own['id'],'lane':lane})
        assert s.to_dict()['armies']==before['armies']
        assert s.day==before['day'] and s.gold==before['gold']
    s=apply_command(s,'battle_step',{'battle':b['id']})
    assert sum(a.size for a in s.armies.values())<sum(a.size for a in pending.armies.values())
    assert s.day==before['day']
    assert RulerState.from_dict(s.to_dict()).to_dict()==s.to_dict()
    b=view(s)['battle'];u=next(u for u in b['units'] if u['side']==b['player_side'] and u['count'])
    moved=apply_command(s,'battle_deploy',{'battle':b['id'],'unit':u['id'],'order':'left'})
    assert next(x for x in view(moved)['battle']['units'] if x['id']==u['id'])['lane']==u['lane']
    assert all(u['order'] is None for u in view(moved)['battle']['units'] if u['side']!=b['player_side'])


@pytest.mark.parametrize('payload',[{'battle':'old','unit':'fake','lane':'center'},{'lane':[]},{'lane':'ocean'},{'order':'teleport'}])
def test_invalid_orders_are_atomic(pending,payload):
    b=view(pending)['battle'];unit=next(u for u in b['units'] if u['side']==b['player_side'])
    before=pending.to_dict()
    with pytest.raises(RuleError):apply_command(pending,'battle_deploy',{'battle':b['id'],'unit':unit['id'],**payload})
    assert pending.to_dict()==before


@pytest.mark.parametrize('mode',['hold','maneuver','delegate','retreat'])
def test_all_exits_preserve_resources_and_return_to_campaign(pending,mode):
    s,_=resolve(pending,mode)
    assert s.gold<=pending.gold
    assert s.day==pending.day and not view(s)['battle']
    assert all(a.size<=pending.armies[aid].size for aid,a in s.armies.items())
    assert sum(a.grain for a in s.armies.values())<=sum(a.grain for a in pending.armies.values())


def test_allied_armies_join_and_terrain_changes_strength():
    s,_=encounter(29,split=True);b=s.flags['battle']
    assert len({u['army'] for u in b['units'] if u['side']==b['player_side']})==2
    u=next(u for u in b['units'] if u['side']=='defend')
    u['order']='hold';b['terrain']='plain';flat=tactics.power(s,u,b)
    b['terrain']='hill';assert tactics.power(s,u,b)>flat


def test_api_receipts_ownership_and_restart(tmp_path):
    cfg=Settings(mode='test',database_url=f'sqlite:///{tmp_path}/tactics.db',session_secret='tactical-api-test')
    app=create_app(cfg)
    with TestClient(app) as c:
        token=c.post('/api/auth/demo').json()['session_token'];headers={'Authorization':'Bearer '+token}
        owner=read_session(token,cfg.session_secret)
        save=app.state.store.create(owner,11,'ruler_v1','long')
        _,trace=encounter()
        for i,step in enumerate(trace):
            body={'command_id':f'legal-step-{i:04}','revision':save['state']['revision'],**step}
            r=c.post(f'/api/campaigns/{save["id"]}/commands',json=body,headers=headers)
            assert r.status_code==200,r.text
            save=r.json()
        b=save['state']['battle'];assert b
        body={'command_id':'battle-round-0001','revision':save['state']['revision'],'kind':'battle_step','payload':{'battle':b['id']}}
        url=f'/api/campaigns/{save["id"]}/commands'
        first=c.post(url,json=body,headers=headers);assert first.status_code==200
        assert c.post(url,json=body,headers=headers).json()==first.json()
        assert c.post(url,json={**body,'command_id':'different-request'},headers=headers).status_code==409
        c.cookies.clear();c.post('/api/auth/demo')
        assert c.get(f'/api/campaigns/{save["id"]}').status_code==404
    app.state.store.engine.dispose()
    app=create_app(cfg)
    with TestClient(app) as c:
        restored=c.get(f'/api/campaigns/{save["id"]}',headers=headers).json()
        assert restored==first.json()
    app.state.store.engine.dispose()


def test_reserves_cannot_win_without_taking_the_field(pending):
    b=view(pending)['battle'];s=pending
    for u in b['units']:
        if u['side']==b['player_side']:
            s=apply_command(s,'battle_deploy',{'battle':b['id'],'unit':u['id'],'lane':'reserve'})
    s,_=resolve(s,'hold')
    assert any('ваши войска отступили' in r['text'] for r in s.reports)


def test_enemy_cannot_be_repositioned(pending):
    b=view(pending)['battle'];u=next(u for u in b['units'] if u['side']!=b['player_side'])
    with pytest.raises(RuleError):apply_command(pending,'battle_deploy',{'battle':b['id'],'unit':u['id'],'lane':'reserve'})


def test_unreachable_retreat_does_not_leave_an_active_enemy(pending,monkeypatch):
    from campaign.ruler import military
    s=deepcopy(pending);b=s.flags.pop('battle')
    groups=[[s.armies[i] for i in dict.fromkeys(u['army'] for u in b['units'] if u['side']==side)] for side in ['attack','defend']]
    monkeypatch.setattr(military,'route',lambda *args,**kwargs:None)
    won=military._battle(s,b['province'],*groups,automatic=True)
    assert all(a.size==0 for a in groups[1 if won else 0])


def test_stationed_besieger_without_mission_survives_next_tick(pending):
    from campaign.ruler import military
    s=deepcopy(pending);b=s.flags['battle'];pid=b['province']
    # Boundary fixture: a victorious army whose assignment has been cleared.
    tactics.finish(s,b['player_side'])
    assert pid in s.sieges
    aid=s.sieges[pid]['armies'][0];a=s.armies[aid];a.mission=None
    military.tick(s)
    assert aid in s.sieges[pid]['armies'] and a.location==pid
