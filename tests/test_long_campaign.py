from copy import deepcopy
import pytest
from campaign.engine import RuleError, relation_key
from campaign.ruler import world, chronicle, civil
from campaign.ruler.engine import new_campaign, apply_command, validate, view
from campaign.ruler.models import RulerState
from campaign.ruler.core import count


def test_enable_preserves_old_state_and_old_rules_until_explicit_command():
    old=new_campaign(17);before=old.to_dict()
    new=apply_command(old,'continue_campaign',{})
    assert old.to_dict()==before and new.rules_version==4
    assert new.gold==old.gold and new.places==old.places and new.armies==old.armies
    assert RulerState.from_dict(new.to_dict()).to_dict()==new.to_dict()
    public=view(new)
    assert not {'polities','foreign_cargo','intelligence','plan'}.intersection(public)


def test_first_chapter_resolution_continues_in_long_mode():
    s=new_campaign(3,extended=True);s.day=730
    s.flags.update(crisis_resolved='settlement',resolution_day=720)
    from campaign.ruler.story import schedule
    schedule(s)
    assert s.ending is None and view(s)['chapter']['number']==2
    old=new_campaign(3);old.day=730;old.flags.update(crisis_resolved='settlement',resolution_day=720)
    schedule(old);assert old.ending
    continued=apply_command(old,'continue_campaign',{})
    assert continued.ending is None and view(continued)['chapter']['number']==2


def test_defeat_cannot_be_reopened_as_a_campaign():
    s=new_campaign(5);s.ending='Поражение'
    with pytest.raises(RuleError):apply_command(s,'continue_campaign',{})


def test_foreign_training_debits_real_people_money_and_completes_once():
    s=new_campaign(5,extended=True);r=s.polities['byzantine'];r.gold=500
    people=sum(count(p.garrison)+p.reserve for p in s.places.values())+sum(a.size for a in s.armies.values())
    s.day=30;world.tick(s)
    trained=sum(t['count'] for p in s.places.values() for t in p.training)
    assert trained>0
    after=sum(count(p.garrison)+p.reserve for p in s.places.values())+sum(a.size for a in s.armies.values())+trained
    assert after==people
    local_training=sum(t['count'] for p in s.places.values() if p.controller=='byzantine' for t in p.training)
    assert r.gold==500+r.income-r.expense-local_training*2
    s.day=44;civil.tick(s);validate(s)
    assert not any(p.training for p in s.places.values() if p.controller!='ottoman')


def test_unobserved_remote_army_cannot_change_opponent_plan():
    a=new_campaign(31,extended=True);a.day=7;world.tick(a)
    b=deepcopy(a);b.armies['ottoman-1'].location='lisbon'
    # Intelligence does not refresh when arbitrary remote state changes.
    r1=a.polities['byzantine'];r2=b.polities['byzantine']
    places=[p for p in a.places.values() if p.controller=='byzantine']
    aa=[x for x in a.armies.values() if x.faction=='byzantine']
    world._plan(a,'byzantine',r1,places,aa);world._plan(b,'byzantine',r2,places,aa)
    assert (r1.plan,r1.target,r1.rally)==(r2.plan,r2.target,r2.rally)


def test_peace_can_be_rejected_and_reserved_payment_is_refunded_once():
    s=new_campaign(6,extended=True)
    s=apply_command(s,'diplomacy',{'target':'byzantine','proposal':'peace'})
    gold=s.gold;s.day=14;civil.tick(s)
    assert s.relations[relation_key('ottoman','byzantine')]['status']=='war'
    assert s.gold==gold+40 and not any(x['kind']=='diplomacy' for x in s.couriers)
    civil.tick(s);assert s.gold==gold+40


def test_tribute_is_escrow_until_reply_then_becomes_real_peace():
    s=new_campaign(6,extended=True);r=s.polities['byzantine'];bank=r.gold
    chronicle.decide(s,'war_pressure',{'faction':'byzantine'},'tribute')
    assert s.gold==130 and r.gold==bank
    s.day=14;civil.tick(s)
    assert r.gold==bank+100 and s.relations[relation_key('ottoman','byzantine')]['status']=='peace'


def test_petitions_have_real_conditions_and_no_monthly_duplicate():
    s=new_campaign(19,extended=True);s.flags['chapter']=2;s.day=900
    chronicle.tick(s);assert not any(x['scene']=='pay_dispute' for x in s.agendas)
    s.arrears=40;chronicle.tick(s)
    assert sum(x['scene']=='pay_dispute' for x in s.agendas)==1
    chronicle.tick(s);assert sum(x['scene']=='pay_dispute' for x in s.agendas)==1
    assert len(s.agendas)<=3


def test_courses_need_actual_time_and_cancel_on_departure():
    s=new_campaign(9,extended=True);s.people['orhan'].location=s.capital
    before=s.people['orhan'].skills['stewardship']
    chronicle.decide(s,'heir_school',{'person':'orhan'},'teach')
    assert s.people['orhan'].skills['stewardship']==before
    s.day=179;chronicle.tick(s);assert s.people['orhan'].skills['stewardship']==before
    s.day=180;chronicle.tick(s);assert s.people['orhan'].skills['stewardship']==before+8
    chronicle.decide(s,'heir_school',{'person':'orhan'},'teach')
    s.people['orhan'].location='domanic';s.day=181;chronicle.tick(s)
    assert not s.flags['courses'] and s.people['orhan'].skills['stewardship']==before+8


def test_insufficient_means_reject_new_choice_atomically():
    s=new_campaign(4,extended=True);s.gold=10
    chronicle.petition(s,'war_pressure',{'faction':'byzantine'})
    agenda=next(x for x in s.agendas if x['scene']=='war_pressure');before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'decide',{'agenda':agenda['id'],'choice':'tribute'})
    assert s.to_dict()==before


def test_access_requires_delivery_expires_and_is_void_during_war():
    from campaign.ruler.core import route
    s=new_campaign(23,extended=True);s.relations['byzantine:ottoman']['status']='peace'
    s=apply_command(s,'diplomacy',{'target':'byzantine','proposal':'access'})
    assert not s.relations['byzantine:ottoman'].get('access_until')
    s.day=14;civil.tick(s)
    assert s.relations['byzantine:ottoman']['access_until']==734
    assert route(s,'sogut','bilecik',military=True,hostile_end=False) is not None
    s.day=735;assert route(s,'sogut','bilecik',military=True,hostile_end=False) is None


def test_losing_territory_does_not_complete_border_chapter():
    s=new_campaign(23,extended=True);s.flags.update(chapter=2,chapter_started=700);s.day=1500
    s.places['inonu'].controller='byzantine'
    chronicle.progress(s);assert s.flags['chapter']==2


def test_foreign_cargo_is_captured_into_real_local_stock():
    s=new_campaign(3,extended=True);p=s.places['sogut'];before=p.grain
    s.foreign_cargo.append({'faction':'byzantine','army':'byzantine-frontier','location':'sogut','path':[],'left':1,'grain':400})
    s.day=1;world.tick(s)
    assert not s.foreign_cargo and p.grain==before+400


def test_subsidy_changes_actual_neighbor_war_and_treasury():
    s=new_campaign(3,extended=True);s.day=800
    before=s.polities['germiyan'].gold
    chronicle.decide(s,'alliance_offer',{'faction':'germiyan','enemy':'byzantine'},'subsidy')
    assert s.gold==170 and s.polities['germiyan'].gold==before+60
    assert s.relations['byzantine:germiyan']['status']=='war'


@pytest.mark.parametrize('scene,choice',[(scene,c) for scene,(_,_,choices) in chronicle.SCENES.items() for c,_ in choices])
def test_new_choice_boundary_executes_saves_and_removes_its_agenda(scene,choice):
    # Explicit boundary fixtures, not substitutes for legal campaign walks.
    s=new_campaign(41,extended=True);s.gold=1000;s.arrears=50
    if scene in ['scarcity','occupation']:context={'province':'sogut'}
    elif scene in ['war_pressure','alliance_offer']:context={'faction':'byzantine' if scene=='war_pressure' else 'germiyan','enemy':'byzantine'}
    elif scene in ['siege_school','heir_school']:context={'person':'orhan'}
    else:context={'army':'ottoman-1','province':'sogut'}
    if scene=='occupation':s.places['sogut'].owner='byzantine'
    if scene=='scarcity':s.relations['byzantine:ottoman']['status']='peace'
    chronicle.petition(s,scene,context);agenda=next(a for a in s.agendas if a['scene']==scene)
    after=apply_command(s,'decide',{'agenda':agenda['id'],'choice':choice})
    assert not any(a['id']==agenda['id'] for a in after.agendas)
    validate(after);assert RulerState.from_dict(after.to_dict()).to_dict()==after.to_dict()


def test_long_mode_api_persists_private_world_and_replays_public_receipt(tmp_path):
    from fastapi.testclient import TestClient
    from server.app import create_app,Settings
    from server.storage import CampaignRow
    app=create_app(Settings(mode='test',database_url='sqlite:///'+str(tmp_path/'long.db')))
    try:
        with TestClient(app) as client:
            assert client.post('/api/auth/demo',json={}).status_code==200
            created=client.post('/api/campaigns',json={'scenario':'ruler_v1','campaign_mode':'long'}).json()
            assert created['state']['rules_version']==4 and created['state']['campaign_mode']=='long'
            command={'command_id':'long-replay-0001','revision':0,'kind':'advance','payload':{'days':7}}
            first=client.post(f'/api/campaigns/{created["id"]}/commands',json=command)
            assert first.status_code==200,first.text
            assert client.post(f'/api/campaigns/{created["id"]}/commands',json=command).json()==first.json()
            assert client.get(f'/api/campaigns/{created["id"]}').json()==first.json()
            assert 'polities' not in first.json()['state']
            with app.state.store.session() as db:
                saved=db.get(CampaignRow,created['id']).snapshot
                assert saved['polities'] and saved['rules_version']==4
    finally:app.state.store.engine.dispose()
