from copy import deepcopy

import pytest
from hypothesis import given, strategies as st
from campaign.engine import RuleError
from campaign.ruler.engine import apply_command, new_campaign, validate, view
from campaign.ruler.models import RulerState
from campaign.ruler.core import all_cohorts, count, troops


def start(seed=11):
    s=new_campaign(seed)
    return apply_command(s,'decide',{'agenda':s.agendas[0]['id'],'choice':'stewardship'})


def headcount(s):
    return sum(c.count for c in all_cohorts(s))+sum(p.reserve+sum(t['count'] for t in p.training)+(p.construction.get('workers',0) if p.construction else 0) for p in s.places.values())


def food(s):
    return sum(p.grain for p in s.places.values())+sum(a.grain for a in s.armies.values())+sum(c['grain'] for c in s.transports.values())+s.merchant['grain']+sum(s.merchant['warehouses'].values())


def advance_to(s,day):
    while s.day<day and not s.ending and s.people[s.ruler_id].status!='dead':
        s=apply_command(s,'advance',{'days':min(90,day-s.day),'until_event':False})
    return s


@given(st.integers(1,79))
def test_split_merge_preserves_people_lineage_food_and_funds(n):
    s=start();before=(headcount(s),food(s),s.gold)
    s=apply_command(s,'split_army',{'army':'ottoman-1','commander':'turgut','troops':{'militia':min(n,59)}})
    second=next(a for a in s.armies.values() if a.faction=='ottoman' and a.id!='ottoman-1')
    assert (headcount(s),food(s),s.gold)==before
    assert all(c.origin=='sogut' for c in second.cohorts)
    s=apply_command(s,'merge_armies',{'army':'ottoman-1','other':second.id})
    assert (headcount(s),food(s),s.gold)==before
    assert troops(s.armies['ottoman-1'].cohorts)=={'militia':60,'archers':20,'cavalry':0}
    validate(s)


def test_zero_garrison_is_allowed_and_not_invisible():
    s=start();before=headcount(s)
    s=apply_command(s,'transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':45}})
    assert count(s.places['sogut'].garrison)==0 and s.armies['ottoman-1'].size==125
    assert headcount(s)==before
    assert any('гарнизоне 0' in r['text'] for r in s.reports)


def test_form_army_has_no_free_provisions():
    s=start();before=food(s);people=headcount(s)
    s=apply_command(s,'form_army',{'province':'sogut','commander':'orhan','troops':{'militia':10}})
    assert food(s)==before and headcount(s)==people
    army=next(a for a in s.armies.values() if a.commander=='orhan')
    assert army.grain==200 and army.location=='sogut'


@pytest.mark.parametrize('payload',[{'days':'x'},{'days':True},{'days':0},{'allow_assault':'false'},{'allow_requisition':1},{'funds':True},{'area':'bilecik'}])
def test_bad_mandates_reject_atomically(payload):
    s=start();before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'mission',{'army':'ottoman-1','target':'bilecik','purpose':'conquer',**payload})
    assert s.to_dict()==before


def test_training_is_local_delayed_and_consumes_reserve_once():
    s=start();n=headcount(s);gold=s.gold;guards=count(s.places['sogut'].garrison)
    s=apply_command(s,'raise',{'province':'sogut','troop':'archers','count':10})
    assert s.gold==gold-40 and headcount(s)==n and count(s.places['sogut'].garrison)==guards
    s=advance_to(s,29);assert count(s.places['sogut'].garrison)==guards
    s=advance_to(s,30);assert s.places['sogut'].garrison[-1].troop=='archers' and s.places['sogut'].garrison[-1].count==10
    assert headcount(s)==n


def test_appointed_officer_arrives_before_taking_office():
    s=start();before=s.places['domanic'].governor
    s=apply_command(s,'appoint',{'person':'orhan','role':'governor','province':'domanic'})
    assert s.places['domanic'].governor==before and s.people['orhan'].travel
    s=advance_to(s,15)
    assert s.places['domanic'].governor=='orhan' and s.people['orhan'].location=='domanic'
    assert not s.people['orhan'].travel


def test_report_projection_hides_private_state_and_preserves_unknowns():
    s=start();data=view(s)
    forbidden={'seed','trust','ambition','health','skills','loyalty','prosperity','flags','outbox'}
    def check(v):
        if isinstance(v,dict):
            assert not forbidden.intersection(v)
            for x in v.values():check(x)
        elif isinstance(v,list):
            for x in v:check(x)
    check(data)
    assert data['provinces']['lisbon']['garrison'] is None
    assert data['provinces']['lisbon']['grain'] is None
    assert data['council']['speeches']
    assert all('hint' not in c for c in data['council']['choices'])


def test_council_facts_change_with_funds_and_do_not_read_future():
    s=start();before=view(s)['council']['speeches']
    s=apply_command(s,'raise',{'province':'sogut','troop':'archers','count':10})
    after=view(s)['council']['speeches']
    assert next(x['text'] for x in before if x['person']=='hasan')!=next(x['text'] for x in after if x['person']=='hasan')
    s=apply_command(s,'consult',{'topic':'military','army':'ottoman-1'})
    assert view(s)['council']['title']=='Военный совет'
    assert any(r['kind']=='speech' for r in s.outbox)


def test_trade_moves_real_cargo_escort_and_money():
    s=start();n=headcount(s);grain=food(s);gold=s.gold;merchant=s.merchant['gold']
    s=apply_command(s,'trade',{'mode':'purchase','province':'sogut','amount':400,'escort':10,'escort_province':'sogut'})
    assert headcount(s)==n and food(s)==grain
    assert s.gold==gold-40 and s.merchant['gold']==merchant+40
    assert count(s.places['sogut'].garrison)==35
    c=next(iter(s.transports.values()));assert c['status']=='assembling' and c['location']=='kutahya' and c['escort_location']=='sogut'
    s=advance_to(s,20);c=s.transports[c['id']]
    assert c['status']=='completed' and c['grain']==0 and c['escorts']==[]
    assert count(s.places['sogut'].garrison)==45
    assert headcount(s)==n


def test_provision_subtracts_source_and_never_teleports():
    s=start();before=food(s);source=s.places['karacahisar'].grain;bag=s.armies['ottoman-1'].grain
    s=apply_command(s,'provision',{'province':'karacahisar','army':'ottoman-1','amount':300})
    assert s.places['karacahisar'].grain==source-300 and s.armies['ottoman-1'].grain==bag
    assert food(s)==before
    s=advance_to(s,10)
    assert next(iter(s.transports.values()))['status']=='completed'


def test_gift_with_bad_decision_and_repeated_scene_is_atomic():
    s=start();s=advance_to(s,30);ag=next(x for x in s.agendas if x['scene']=='frontier_letter');before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'decide',{'agenda':ag['id'],'choice':'accept','treatment':'execute'})
    assert s.to_dict()==before
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'refuse','treatment':'execute'})
    before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'decide',{'agenda':ag['id'],'choice':'refuse','treatment':'execute'})
    assert s.to_dict()==before


def test_succession_preserves_all_nonpersonal_property():
    s=start();s.people['osman'].status='dead'
    # Boundary fixture for death; battle-driven cases are exercised in scenario runs.
    from campaign.ruler.story import schedule
    schedule(s);ag=next(x for x in s.agendas if x['scene']=='succession')
    old=(headcount(s),food(s),s.gold,deepcopy(s.obligations),deepcopy(s.relations))
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'orhan'})
    assert s.ruler_id=='orhan' and (headcount(s),food(s),s.gold,s.obligations,s.relations)==old
    validate(s)


def test_wounded_commander_transfers_command_not_soldiers():
    s=start();old=s.armies['ottoman-1'].size
    s.people['osman'].status='wounded';s.people['osman'].wounded_until=60;s.people['osman'].health=30
    s=apply_command(s,'advance',{'days':1})
    assert s.armies['ottoman-1'].commander=='turgut' and s.armies['ottoman-1'].size==old
    assert s.ruler_id=='osman'


def test_delivered_mandate_is_bounded_and_executes_real_movement():
    s=start();s=apply_command(s,'mission',{'army':'ottoman-1','purpose':'cover','target':'domanic','funds':20})
    s=advance_to(s,20);a=s.armies['ottoman-1']
    assert a.location=='domanic' and s.people['osman'].location=='domanic'
    s=apply_command(s,'recall',{'army':a.id});s=advance_to(s,40)
    assert s.armies[a.id].location=='sogut'


def test_same_day_commands_do_not_age_people_or_resolve_queues():
    s=start();birth=s.people['turgut'].born;day=s.day
    for _ in range(6):s=apply_command(s,'consult',{'topic':'military','army':'ottoman-1'})
    assert s.day==day and s.people['turgut'].born==birth


def test_snapshot_roundtrip_has_identical_continuation():
    s=start();s=apply_command(s,'trade',{'mode':'purchase','province':'sogut','amount':400})
    s=apply_command(s,'mission',{'army':'ottoman-1','target':'domanic','purpose':'cover','funds':10})
    copy=RulerState.from_dict(s.to_dict())
    for _ in range(5):
        s=apply_command(s,'advance',{'days':7});copy=apply_command(copy,'advance',{'days':7})
        assert s.to_dict()==copy.to_dict()


def test_routine_supply_sustains_stationary_capital_without_phantom_grain():
    s=start();s=apply_command(s,'raise',{'province':'domanic','troop':'militia','count':8});s=advance_to(s,30)
    ag=next(a for a in s.agendas if a['scene']=='frontier_letter')
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'accept'})
    s=advance_to(s,270)
    road=next(a for a in s.agendas if a['scene']=='road_warning')
    s=apply_command(s,'decide',{'agenda':road['id'],'choice':'local'})
    s=advance_to(s,700)
    assert s.armies['ottoman-1'].size==80
    assert count(s.places['sogut'].garrison)==45
    assert any(c['kind']=='local_supply' and c['status']=='completed' for c in s.transports.values())
    assert s.armies['ottoman-1'].grain>0


def test_demobilization_returns_local_people_without_troop_creation():
    s=start();before=headcount(s);reserve=s.places['sogut'].reserve
    s=apply_command(s,'demobilize',{'province':'sogut','troops':{'militia':20}})
    assert headcount(s)==before and s.places['sogut'].reserve==reserve+20
    assert count(s.places['sogut'].garrison)==25


def test_payroll_escrow_and_split_rounding_never_pay_twice():
    from campaign.ruler.civil import _month,budget
    s=start();s=apply_command(s,'split_army',{'army':'ottoman-1','commander':'turgut','troops':{'militia':17}})
    for a in s.armies.values():
        if a.faction=='ottoman':
            s.gold-=20;a.funds=20
    wealth=lambda x:x.gold+sum(p.wealth for p in x.people.values())+sum(a.funds for a in x.armies.values() if a.faction=='ottoman')
    before=wealth(s);b=budget(s);_month(s)
    assert wealth(s)-before==b['gross']-b['expense']


def test_detained_and_executed_envoys_have_distinct_lifecycles():
    s=start();s=advance_to(s,30);ag=next(a for a in s.agendas if a['scene']=='frontier_letter');pid=ag['context']['envoy']
    detained=apply_command(s,'decide',{'agenda':ag['id'],'choice':'refuse','treatment':'detain'})
    assert detained.people[pid].status=='detained'
    released=apply_command(detained,'release_envoy',{'person':pid})
    assert released.people[pid].status=='leaving' and released.people[pid].travel
    killed=apply_command(s,'decide',{'agenda':ag['id'],'choice':'refuse','treatment':'execute'})
    assert killed.people[pid].status=='dead'
    with pytest.raises(RuleError):apply_command(killed,'release_envoy',{'person':pid})


def test_calendar_chunking_cannot_farm_income_or_food():
    original=start();a=advance_to(original,25);b=original
    for _ in range(25):b=apply_command(b,'advance',{'days':1,'until_event':False})
    assert a.day==b.day and a.gold==b.gold and headcount(a)==headcount(b) and food(a)==food(b)
    assert {p:p1.grain for p,p1 in a.places.items()}=={p:p1.grain for p,p1 in b.places.items()}


def test_ruler_public_api_replay_archive_and_old_campaigns(tmp_path):
    from fastapi.testclient import TestClient
    from server.app import create_app,Settings
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/ruler-api.db'))
    with TestClient(app) as c:
        c.post('/api/auth/demo');legacy=c.post('/api/campaigns').json();save=c.post('/api/campaigns',json={'scenario':'ruler_v1'}).json()
        assert save['state']['scenario']=='ruler_v1'
        ag=save['state']['agendas'][0]
        payload={'command_id':'ruler-start-request','revision':0,'kind':'decide','payload':{'agenda':ag['id'],'choice':'stewardship'}}
        first=c.post(f'/api/campaigns/{save["id"]}/commands',json=payload)
        assert first.status_code==200
        assert c.post(f'/api/campaigns/{save["id"]}/commands',json=payload).json()==first.json()
        archive=c.get(f'/api/campaigns/{save["id"]}/archive?limit=2').json()
        assert len(archive['items'])==2
        nxt=c.get(f'/api/campaigns/{save["id"]}/archive?after={archive["next"]}').json()
        assert nxt['items'] and all(x['seq']>archive['next'] for x in nxt['items'])
        assert c.get(f'/api/campaigns/{legacy["id"]}').json()==legacy
        campaigns=c.get('/api/campaigns').json();assert {x['id'] for x in campaigns}=={save['id'],legacy['id']}
        c.cookies.clear();c.post('/api/auth/demo')
        assert c.get('/api/campaigns').json()==[]
        assert c.get(f'/api/campaigns/{save["id"]}/archive').status_code==404
    app.state.store.engine.dispose()


def test_conditional_scenes_do_not_fire_without_their_cause():
    s=start();s=advance_to(s,250)
    scenes={a['scene'] for a in s.agendas}|set(s.shown)
    assert not {'charter_return','promise_broken','campaign_return','delayed_supply','rival_letters','accusation'}.intersection(scenes)


def test_capital_capture_relocates_court_and_recovery_releases_captives():
    from campaign.ruler.military import occupy
    s=start();s=apply_command(s,'mission',{'army':'ottoman-1','purpose':'cover','target':'domanic','funds':10})
    s=advance_to(s,10);enemy=s.armies['byzantine-frontier'];enemy.location='sogut'
    # Boundary fixture: the normal battle path is separately exercised in legal walks.
    before=s.gold;occupy(s,'sogut',[enemy])
    assert s.capital=='karacahisar' and s.people['hasan'].status=='captured'
    assert s.gold+ s.places['sogut'].seized_gold==before
    a=s.armies['ottoman-1'];a.location='sogut';s.people[s.ruler_id].location='sogut'
    occupy(s,'sogut',[a])
    assert s.people['hasan'].status=='wounded' and s.places['sogut'].seized_gold==0 and s.gold==before
    validate(s)


def test_service_grant_returns_to_treasury_on_death_without_changing_owner():
    s=start();s=apply_command(s,'grant',{'province':'karacahisar','person':'konur'})
    s.people['konur'].status='dead';s=apply_command(s,'advance',{'days':1})
    assert s.places['karacahisar'].grant is None and s.places['karacahisar'].owner=='ottoman'


def test_executed_merchant_envoy_changes_actual_access_to_trade():
    s=start();s=advance_to(s,60);ag=next(a for a in s.agendas if a['scene']=='grain_offer')
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'decline','treatment':'execute'})
    assert not view(s)['trade_access']['available']
    with pytest.raises(RuleError):apply_command(s,'trade',{'mode':'purchase','province':'sogut','amount':100})
    s=apply_command(s,'trade_reparation',{});assert not view(s)['trade_access']['available']
    s=advance_to(s,s.day+30);assert view(s)['trade_access']['available']


def test_stale_observations_do_not_overwrite_a_newer_report():
    from campaign.ruler.core import observation
    s=start();observation(s,'karacahisar','Ранняя ведомость')
    s=advance_to(s,1);s.knowledge['karacahisar']['day']=1;s.knowledge['karacahisar']['grain']=1234
    s=advance_to(s,10)
    assert s.knowledge['karacahisar']['day']==1 and s.knowledge['karacahisar']['grain']==1234


def test_splitting_does_not_shift_an_extra_wage_into_campaign_escrow():
    from campaign.ruler.civil import _month
    whole=start();split=start()
    split=apply_command(split,'split_army',{'army':'ottoman-1','commander':'turgut','troops':{'militia':17}})
    whole.gold-=40;whole.armies['ottoman-1'].funds=40
    for a in split.armies.values():
        if a.faction=='ottoman':split.gold-=20;a.funds=20
    _month(whole);_month(split)
    assert whole.gold==split.gold
    assert whole.armies['ottoman-1'].funds==sum(a.funds for a in split.armies.values() if a.faction=='ottoman')


def test_two_armies_share_a_siege_and_one_can_leave_without_erasing_the_other():
    s=start();s=apply_command(s,'transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':45}})
    s=apply_command(s,'split_army',{'army':'ottoman-1','commander':'turgut','troops':{'militia':60}})
    secondary=next(a.id for a in s.armies.values() if a.faction=='ottoman' and a.id!='ottoman-1')
    for aid in ['ottoman-1',secondary]:s=apply_command(s,'mission',{'army':aid,'target':'inegol','purpose':'conquer','funds':20})
    s=advance_to(s,5)
    assert set(s.sieges['inegol']['armies'])=={'ottoman-1',secondary}
    total_before=headcount(s)
    s=apply_command(s,'recall',{'army':secondary});s=advance_to(s,12)
    assert s.armies[secondary].location=='sogut'
    assert s.sieges['inegol']['armies']==['ottoman-1']
    assert headcount(s)==total_before


def test_zero_army_surviving_court_members_return_physically():
    s=start();a=s.armies['ottoman-1'];a.location='inegol';a.cohorts=[]
    for person in ['osman','turgut']:s.people[person].location='inegol'
    s=apply_command(s,'advance',{'days':1})
    assert s.people['osman'].travel and s.people['osman'].location=='inegol'
    s=advance_to(s,10)
    assert s.people['osman'].location==s.capital and not s.people['osman'].travel
    assert not s.armies['ottoman-1'].cohorts


def test_village_promise_does_not_withdraw_an_unrelated_beys_force():
    s=new_campaign(11);s=apply_command(s,'decide',{'agenda':s.agendas[0]['id'],'choice':'frontier'})
    s=advance_to(s,120);ag=next(a for a in s.agendas if a['scene']=='village_petition')
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'guard'})
    promise=next(o for o in s.obligations.values() if o['kind']=='protection')
    assert promise['creditor']=='community:domanic'
    konur=next(a.id for a in s.armies.values() if a.commander=='konur');size=s.armies[konur].size
    s=advance_to(s,215)
    assert s.obligations[promise['id']]['status']=='broken'
    assert s.armies[konur].size==size and not s.armies[konur].service_return


def test_actual_guard_duty_fulfils_the_promise_without_a_confirmation_button():
    s=start();s=apply_command(s,'raise',{'province':'domanic','troop':'militia','count':8})
    s=advance_to(s,120);ag=next(a for a in s.agendas if a['scene']=='village_petition')
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'guard'})
    oid=next(o['id'] for o in s.obligations.values() if o['kind']=='protection')
    s=advance_to(s,211)
    assert s.obligations[oid]['status']=='fulfilled'


def test_delivered_repeal_of_promised_rights_creates_a_recorded_breach():
    s=start();s=advance_to(s,120);ag=next(a for a in s.agendas if a['scene']=='village_petition')
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'charter'})
    s=apply_command(s,'policy',{'province':'domanic','tax':'extraordinary'})
    assert s.edicts and next(o for o in s.obligations.values() if o['kind']=='charter')['status']=='open'
    s=advance_to(s,125)
    assert next(o for o in s.obligations.values() if o['kind']=='charter')['status']=='broken'
    assert any(a['scene']=='promise_broken' for a in s.agendas)


def test_extension_is_a_request_until_the_counterparty_answers():
    s=new_campaign(11);s=apply_command(s,'decide',{'agenda':s.agendas[0]['id'],'choice':'merchants'})
    s=advance_to(s,181);ag=next(a for a in s.agendas if a['scene']=='promise_broken')
    oid=ag['context']['obligation'];due=s.obligations[oid]['due']
    s=apply_command(s,'decide',{'agenda':ag['id'],'choice':'negotiate'})
    assert s.obligations[oid]['status']=='broken' and s.obligations[oid]['due']==due
    s=advance_to(s,195)
    assert s.obligations[oid]['status']=='open' and s.obligations[oid]['due']==285


def test_remote_orders_reserve_money_but_begin_only_after_delivery():
    s=start();reserve=s.places['domanic'].reserve;money=s.gold
    s=apply_command(s,'raise',{'province':'domanic','troop':'militia','count':10})
    assert s.edicts and s.edicts[0]['escrow']==20 and s.gold==money-20
    assert s.places['domanic'].reserve==reserve and not s.places['domanic'].training
    s=advance_to(s,5)
    assert not s.edicts and s.places['domanic'].reserve==reserve-10
    assert s.places['domanic'].training[0]['ready']>14


def test_player_cannot_bypass_order_delivery_with_internal_flags():
    s=start();before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'raise',{'province':'domanic','troop':'militia','count':10,'_delivered':True})
    assert s.to_dict()==before


def test_accession_media_marks_actual_transfer_and_preserves_old_save_behavior():
    from campaign.ruler.story import schedule
    for extended in [False,True]:
        s=new_campaign(11,extended=extended)
        assert view(s)['accession'] is None
        s.people['osman'].status='dead';schedule(s)
        assert view(s)['accession'] is None,'Death alone is not recognition of a successor'
        ag=next(x for x in s.agendas if x['scene']=='succession')
        before=(s.day,s.gold,headcount(s),food(s),deepcopy(s.obligations),deepcopy(s.relations))
        result=apply_command(s,'decide',{'agenda':ag['id'],'choice':'orhan'})
        assert result.ruler_id=='orhan'
        assert (result.day,result.gold,headcount(result),food(result),result.obligations,result.relations)==before
        expected={'from':'osman','to':'orhan','day':s.day} if extended else None
        assert view(result)['accession']==expected
        assert view(RulerState.from_dict(result.to_dict()))['accession']==expected
        assert view(s)['accession'] is None,'Input state was mutated'
