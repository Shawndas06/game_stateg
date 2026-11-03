"""Cross-system regressions for the expanded campaign, not historical assertions."""
from copy import deepcopy

import pytest

from campaign.content import ADJACENCY, CAPITALS, DYNASTY, FACTIONS, PLACES, PLACE_INDEX, ROADS
from campaign.engine import RuleError, _occupy, apply_command, army_power, budget, new_campaign, relation, supplied, validate
from campaign.models import Siege, State


def start():
    return apply_command(new_campaign(42), 'choose', {'choice': 'stewardship'})


def turn(s):
    while s.pending_event:
        s = apply_command(s, 'choose', {'choice': 'oath' if s.pending_event in ['succession'] or s.pending_event.startswith('accession_') else 'charter'})
    return apply_command(s, 'end_turn', {})


def legacy(s):
    data = s.to_dict()
    original = {'sogut','karacahisar','bilecik','yarhisar','inegol','yenishehir','koyunhisar','bursa','nicaea','mudanya','cius','nicomedia','kutahya'}
    data.update(schema_version=1, rules_version=1, content_version='bithynia-1')
    data.pop('ruler_id');data.pop('ruler_rank')
    data['provinces'] = {k:v for k,v in data['provinces'].items() if k in original}
    for p in data['provinces'].values():p.pop('fortress_level');p.pop('max_walls')
    data['factions'] = {k:v for k,v in data['factions'].items() if k in ['ottoman','byzantine','germiyan']}
    for f in data['factions'].values():f.pop('administrative_base')
    data['armies'] = {k:v for k,v in data['armies'].items() if v['faction'] in data['factions']}
    data['treaties'] = {k:v for k,v in data['treaties'].items() if all(fid in data['factions'] for fid in k.split(':'))}
    return data


def test_gazetteer_routes_and_initial_economies():
    assert len(PLACES) == 162 and len(FACTIONS) == 39
    assert all(a in PLACE_INDEX and b in PLACE_INDEX and a != b for a,b in ROADS)
    seen={'sogut'}
    while (expanded:=seen | {n for p in seen for n in ADJACENCY[p]}) != seen:seen=expanded
    assert seen == set(PLACE_INDEX)
    s=start()
    assert all(budget(s,fid)['net'] >= 0 for fid in FACTIONS)
    assert all(s.provinces[p].owner==fid for fid,p in CAPITALS.items())
    assert supplied(s,s.armies['byzantine-1'])


def test_old_save_preserves_occupation_units_and_story_and_reopens_chapter():
    s=start();s.turn=108;s.ruler='Орхан';s.shown_events+=['succession'];s.flags['succession_done']=True
    s.provinces['inegol'].controller='ottoman';s.provinces['inegol'].walls=7
    s.armies['ottoman-1'].troops={'archers':23,'cavalry':11}
    data=legacy(s);data['ending']='Первая глава завершена: бейлик сохранился, но Бурса осталась за его пределами.'
    restored=State.from_dict(data)
    assert restored.ending is None and restored.ruler_rank==2
    assert restored.provinces['inegol'].owner=='byzantine' and restored.provinces['inegol'].controller=='ottoman'
    assert restored.provinces['inegol'].walls==7 and restored.provinces['inegol'].max_walls==40
    assert restored.armies['ottoman-1'].troops==s.armies['ottoman-1'].troops
    assert restored.flags==s.flags and len(restored.provinces)==162
    assert State.from_dict(restored.to_dict()).to_dict()==restored.to_dict()
    validate(restored)


def test_complete_dynasty_can_reach_1453_and_save_load():
    s=start();relation(s,'ottoman','byzantine')['status']='peace'
    rulers=[]
    for _ in range(619):
        while s.pending_event:
            s=apply_command(s,'choose',{'choice':'oath'})
            rulers.append(s.ruler_id)
        assert s.ending is None
        s=apply_command(s,'end_turn',{})
        if s.turn in [100,252,360,456,488,608]:s=State.from_dict(s.to_dict())
    assert rulers == [r['id'] for r in DYNASTY[1:]]
    assert s.turn==619 and s.ending and s.ruler_id=='mehmed_2'


@pytest.mark.parametrize('rank', [1,2])
def test_cannot_bypass_murad_by_building_walls(rank):
    s=start();s.ruler_rank=rank;s.factions['ottoman'].gold=1000
    before=s.to_dict()
    for kind,payload in [('found_fortress',{'province':'domanic'}),('build',{'province':'domanic','building':'walls'})]:
        with pytest.raises(RuleError):apply_command(s,kind,payload)
        assert s.to_dict()==before


def test_murad_accession_and_paid_fortress_through_storage_roundtrip():
    s=start();s.factions['ottoman'].gold=1000;s.turn=251;s.ruler='Орхан';s.ruler_id='orhan';s.ruler_rank=2;s.shown_events.append('succession')
    s=apply_command(s,'end_turn',{})
    assert s.pending_event=='accession_murad_1'
    s=apply_command(s,'choose',{'choice':'oath'})
    f=s.factions['ottoman']; gold,people=f.gold,f.manpower
    s=apply_command(s,'found_fortress',{'province':'domanic'})
    assert s.factions['ottoman'].gold==gold-250 and s.factions['ottoman'].manpower==people-20
    s=State.from_dict(s.to_dict())
    for _ in range(3):s=apply_command(s,'end_turn',{})
    assert s.provinces['domanic'].fortress_level==0
    before=budget(s,'ottoman')['expense'];s=apply_command(s,'end_turn',{})
    p=s.provinces['domanic']
    assert p.fortress_level==1 and p.walls==p.max_walls==60 and p.construction is None
    assert budget(s,'ottoman')['expense']==before+3
    with pytest.raises(RuleError):apply_command(s,'found_fortress',{'province':'domanic'})
    p.walls=20;s=apply_command(s,'repair_walls',{'province':'domanic'})
    for _ in range(2):s=apply_command(s,'end_turn',{})
    assert s.provinces['domanic'].walls==60
    assert s.provinces['domanic'].buildings.count('new_fortress')==1


@pytest.mark.parametrize('constraint', ['gold','manpower','siege','occupied','busy'])
def test_fortress_rejections_are_atomic(constraint):
    s=start();s.ruler_rank=3;s.factions['ottoman'].gold=1000
    if constraint=='gold':s.factions['ottoman'].gold=249
    if constraint=='manpower':s.factions['ottoman'].manpower=19
    if constraint=='siege':
        a=s.armies['byzantine-1'];a.location='domanic';s.sieges['domanic']=Siege('domanic',a.id)
    if constraint=='occupied':s.provinces['domanic'].owner='byzantine'
    if constraint=='busy':s.provinces['domanic'].construction={'building':'market','left':2}
    before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'found_fortress',{'province':'domanic'})
    assert s.to_dict()==before


def test_crossing_requires_knowledge_and_is_paid_only_when_resolved():
    s=start();a=s.armies['ottoman-1'];a.location='chrysopolis'
    s.provinces['chrysopolis'].owner=s.provinces['chrysopolis'].controller='ottoman'
    with pytest.raises(RuleError):apply_command(s,'move',{'army':a.id,'target':'constantinople'})
    s.factions['ottoman'].technologies=['ferries']
    gold=s.factions['ottoman'].gold
    s=apply_command(s,'move',{'army':a.id,'target':'constantinople'})
    s=apply_command(s,'move',{'army':a.id,'target':'constantinople'})
    assert s.factions['ottoman'].gold==gold
    expected=budget(s,'ottoman')['net']
    s=apply_command(s,'end_turn',{})
    assert s.armies[a.id].location=='constantinople'
    assert s.factions['ottoman'].gold==gold+expected-10


def test_isolated_owned_port_requires_convoy_supply():
    s=start();a=s.armies['ottoman-1'];a.location='famagusta';s.capital='alexandria'
    for pid in ['famagusta','alexandria']:s.provinces[pid].owner=s.provinces[pid].controller='ottoman'
    s.factions['ottoman'].technologies=['ferries']
    assert not supplied(s,a)
    s.factions['ottoman'].technologies.append('convoys')
    assert supplied(s,a)


def test_attrition_removes_last_soldier_and_active_siege():
    for cause in ['politics','food','arrears']:
        s=start();a=s.armies['ottoman-1'];a.location='inegol';a.troops={'militia':1}
        s.sieges['inegol']=Siege('inegol',a.id)
        f=s.factions['ottoman']
        if cause=='politics':f.groups['military']=0
        elif cause=='arrears':f.arrears=100000
        else:
            f.gold=100000;f.food=0
            for p in s.provinces.values():
                if p.controller=='ottoman':p.garrison={'militia':10000}
        s=apply_command(s,'end_turn',{})
        assert not s.sieges and s.armies[a.id].size==0
        assert s.provinces[s.armies[a.id].location].controller=='ottoman'
        s=apply_command(s,'mobilize',{'army':a.id,'troop':'militia','count':1})
        assert s.armies[a.id].size==1
        validate(s)


def test_relief_army_can_defeat_friendly_city_besieger():
    s=start();enemy=s.armies['byzantine-1'];enemy.location='sogut';enemy.troops={'militia':3}
    s.sieges['sogut']=Siege('sogut',enemy.id)
    a=s.armies['ottoman-1'];a.location='karacahisar'
    s=apply_command(s,'move',{'army':a.id,'target':'sogut'})
    s=apply_command(s,'end_turn',{})
    assert s.armies[a.id].location=='sogut' and 'sogut' not in s.sieges
    assert s.provinces['sogut'].controller=='ottoman'


def test_besieged_recruitment_is_rejected_atomically():
    s=start();enemy=s.armies['byzantine-1'];enemy.location='sogut';s.sieges['sogut']=Siege('sogut',enemy.id)
    before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'recruit',{'province':'sogut','troop':'militia','count':10})
    assert s.to_dict()==before


def test_last_province_annexation_resolves_all_operations():
    s=start();a=s.armies['ottoman-1'];a.location='kutahya'
    _occupy(s,Siege('kutahya',a.id))
    # Germiyan has additional new holdings, take them through the same capture transition.
    for p in list(s.provinces.values()):
        if p.controller=='germiyan':
            a.location=p.id;a.troops={'militia':100};_occupy(s,Siege(p.id,a.id))
    assert all(p.owner!='germiyan' for p in s.provinces.values())
    assert relation(s,'ottoman','germiyan')['status']=='peace'
    assert s.armies['germiyan-1'].size==0
    validate(s)


def test_supply_and_morale_change_actual_field_battle():
    outcomes=[]
    for condition in [100,30]:
        s=start();a=s.armies['ottoman-1'];a.troops={'militia':100};a.supply=a.morale=condition
        other=s.armies['byzantine-1'];other.location='inegol';other.troops={'militia':40}
        s=apply_command(s,'move',{'army':a.id,'target':'inegol'})
        s=apply_command(s,'end_turn',{})
        outcomes.append(s.armies[a.id].location)
    assert outcomes==['inegol','sogut']


def test_old_snapshot_and_command_receipt_migrate_without_duplicate_action(tmp_path):
    from server.storage import Store, CampaignRow, CommandRow
    from sqlalchemy import select
    store=Store(f'sqlite:///{tmp_path}/legacy.db')
    created=store.create('owner',42)
    response=store.command(created['id'],'owner','original-request',0,'choose',{'choice':'stewardship'})
    old=legacy(State.from_dict(response['state']))
    with store.session.begin() as db:
        row=db.get(CampaignRow,created['id']);row.snapshot=deepcopy(old)
        receipt=db.scalar(select(CommandRow).where(CommandRow.campaign==row.id))
        receipt.response={'id':row.id,'state':deepcopy(old)}
    resumed=store.get(created['id'],'owner')
    replay=store.command(created['id'],'owner','original-request',0,'choose',{'choice':'stewardship'})
    assert replay==resumed and len(replay['state']['provinces'])==162
    assert replay['state']['revision']==1
    assert replay['state']['factions']['ottoman']['gold']==response['state']['factions']['ottoman']['gold']
    later=store.command(created['id'],'owner','next-request',1,'end_turn',{})
    assert later['state']['revision']==2 and later['state']['turn']==1
    store.engine.dispose()


def test_api_build_replay_reload_and_geography(tmp_path):
    from fastapi.testclient import TestClient
    from server.app import Settings, create_app
    from server.storage import CampaignRow
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/world-api.db',session_secret='test-session-secret'))
    with TestClient(app) as c:
        c.post('/api/auth/demo');save=c.post('/api/campaigns').json()
        with app.state.store.session.begin() as db:
            row=db.get(CampaignRow,save['id']);s=State.from_dict(row.snapshot)
            s.pending_event=None;s.ruler='Мурад I';s.ruler_id='murad_1';s.ruler_rank=3;s.turn=252;s.factions['ottoman'].gold=1000
            row.snapshot=s.to_dict()
        url=f"/api/campaigns/{save['id']}/commands"
        command={'command_id':'world-fortress-request','revision':0,'kind':'found_fortress','payload':{'province':'domanic'}}
        response=c.post(url,json=command)
        assert response.status_code==200
        assert c.post(url,json=command).json()==response.json()
        assert response.json()['state']['factions']['ottoman']['gold']==750
        reloaded=c.get(f"/api/campaigns/{save['id']}").json()
        assert reloaded==response.json()
        assert reloaded['state']['provinces']['domanic']['construction']=={'building':'new_fortress','left':4}
        geo=c.get('/mediterranean-geography.json')
        assert geo.status_code==200
        data=geo.json();assert data['land'] and data['lakes']
        for polygons in data.values():
            for polygon in polygons:
                for ring in polygon:
                    assert ring[0]==ring[-1]
                    assert all(-11<=x<=44.5 and 22<=y<=50.5 for x,y in ring)
    app.state.store.engine.dispose()


def test_unwalled_settlement_capture_is_not_a_fortress_siege():
    s=start();a=s.armies['ottoman-1'];a.location='domanic'
    s=apply_command(s,'move',{'army':a.id,'target':'pazaryeri'})
    s=apply_command(s,'end_turn',{})
    assert s.provinces['pazaryeri'].controller=='ottoman'
    assert s.provinces['pazaryeri'].owner=='byzantine'
    assert 'pazaryeri' not in s.sieges and s.provinces['pazaryeri'].walls==0
    assert s.pending_event=='first_city'


def test_siege_pauses_construction_and_capture_cancels_it():
    s=start();s.ruler_rank=3;s.factions['ottoman'].gold=1000
    s=apply_command(s,'found_fortress',{'province':'domanic'})
    a=s.armies['byzantine-1'];a.location='domanic';s.sieges['domanic']=Siege('domanic',a.id)
    s=apply_command(s,'end_turn',{})
    assert s.provinces['domanic'].construction['left']==4
    _occupy(s,s.sieges['domanic'])
    assert s.provinces['domanic'].construction is None
    assert s.provinces['domanic'].fortress_level==0
    validate(s)


def test_frontier_choice_moves_people_from_reserve_atomically():
    for reserve in [14,15,90]:
        s=new_campaign(42);s.factions['ottoman'].manpower=reserve
        before=s.to_dict();troops=budget(s,'ottoman')['troops'];gold=s.factions['ottoman'].gold
        if reserve<15:
            with pytest.raises(RuleError):apply_command(s,'choose',{'choice':'frontier'})
            assert s.to_dict()==before
        else:
            s=apply_command(s,'choose',{'choice':'frontier'})
            assert s.factions['ottoman'].manpower==reserve-15
            assert budget(s,'ottoman')['troops']==troops+15
            assert s.factions['ottoman'].gold==gold-30


def test_failed_retreat_keeps_original_siege_until_army_actually_leaves():
    s=start();a=s.armies['ottoman-1'];a.location='inegol';a.troops={'militia':40}
    s.sieges['inegol']=Siege('inegol',a.id)
    other=s.armies['byzantine-1'];other.location='sogut';other.troops={'militia':1000}
    s=apply_command(s,'retreat',{'army':a.id,'target':'sogut'})
    s=apply_command(s,'end_turn',{})
    assert s.armies[a.id].location=='inegol' and s.armies[a.id].size>0
    assert s.sieges['inegol'].army_id==a.id
    assert s.armies[a.id].order is None
    validate(s)
