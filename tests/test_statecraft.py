"""V5 contracts/people/resources: boundary fixtures and complete command chains."""
from copy import deepcopy
import pytest
from campaign.engine import RuleError,relation_key
from campaign.ruler import diplomacy as dip,knowledge as know,civil,statecraft
from campaign.ruler.engine import new_campaign,apply_command as act,validate,view
from campaign.ruler.models import RulerState
from campaign.ruler.core import count

def realm(seed=11):return new_campaign(seed,extended=True,living=True)
def treaty(s,a,b,kind,**kw):
    o=dip.propose(s,a,b,kind,**kw);dip.agree(s,o);return o

def advance(s,days):
    end=s.day+days
    while s.day<end and not s.ending and s.people[s.ruler_id].status!='dead':
        s=act(s,'advance',{'days':min(90,end-s.day),'until_event':False})
    return s

def test_legacy_optin_does_not_reset_and_projection_is_read_only():
    s=new_campaign(11,extended=True);before=s.to_dict();n=act(s,'statecraft_enable',{})
    assert s.to_dict()==before and n.rules_version==5 and n.gold==s.gold and n.day==s.day
    assert n.armies['ottoman-1']==s.armies['ottoman-1'] and n.places['sogut']==s.places['sogut']
    assert n.armies['byzantine-frontier'].cohorts==s.armies['byzantine-frontier'].cohorts
    before=n.to_dict();v=view(n);assert n.to_dict()==before
    assert RulerState.from_dict(n.to_dict()).to_dict()==before
    assert not {'polities','intelligence','loyalty','chance','answer'}&v['statecraft'].keys()
    assert view(s)['statecraft'] is None

def test_peace_payment_waits_for_return_then_refund_or_transfer_once():
    s=realm();r=s.polities['byzantine'];r.doctrine='trade';before=r.gold
    n=act(s,'negotiate',{'target':'byzantine','proposal':'peace','payment':40});o=next(iter(dip.data(n)['offers'].values()))
    assert n.gold==s.gold-40 and n.polities['byzantine'].gold==before
    n.day=o['ready'];dip.tick(n);assert o['status']=='returning' and o['payment']==40
    n.day=o['ready'];dip.tick(n);assert o['status']=='accepted' and o['payment']==0
    assert n.polities['byzantine'].gold==before+40
    dip.tick(n);assert n.polities['byzantine'].gold==before+40
    reject=realm();reject=act(reject,'negotiate',{'target':'germiyan','proposal':'alliance','payment':30})
    o=next(iter(dip.data(reject)['offers'].values()));o.update(status='returning',answer=False,ready=1);reject.day=1
    dip.tick(reject);assert reject.gold==s.gold and o['status']=='rejected'
    dip.tick(reject);assert reject.gold==s.gold

def test_incoming_offer_is_unknown_until_arrival_and_answer_is_not_agreement():
    s=realm();o=dip.propose(s,'germiyan','ottoman','trade')
    assert not view(s)['statecraft']['offers']
    with pytest.raises(RuleError):act(s,'treaty_reply',{'offer':o['id'],'accept':True})
    s.day=o['ready'];dip.tick(s);assert o['status']=='arrived'
    n=act(s,'treaty_reply',{'offer':o['id'],'accept':True});assert not dip.active(n,'ottoman','germiyan','trade')
    n.day=dip.data(n)['offers'][o['id']]['ready'];dip.tick(n)
    assert dip.active(n,'ottoman','germiyan','trade')
    assert 'answer' not in view(n)['statecraft']['offers'][0]

@pytest.mark.parametrize('value',[None,'',-1,False,10.5,501])
def test_invalid_payment_never_changes_save(value):
    s=realm();before=s.to_dict()
    with pytest.raises(RuleError):act(s,'negotiate',{'target':'germiyan','proposal':'trade','payment':value})
    assert s.to_dict()==before

def test_subjects_share_wars_but_no_cycles_and_tribute_is_real():
    s=realm();treaty(s,'germiyan','ottoman','submit',tribute=10)
    assert dip.root(s,'germiyan')=='ottoman'
    from campaign.ruler.core import war
    assert war(s,'germiyan','byzantine')
    with pytest.raises(RuleError):dip.propose(s,'ottoman','germiyan','submit')
    before=s.gold;bank=s.polities['germiyan'].gold;s.day=30;dip.tick(s)
    assert s.gold==before+10 and s.polities['germiyan'].gold==bank-10
    dip.tick(s);assert s.gold==before+10
    s=act(s,'break_treaty',{'target':'germiyan'});assert dip.root(s,'germiyan')=='germiyan'

def test_levy_is_actual_garrison_then_actual_return_with_same_origin():
    s=realm();treaty(s,'germiyan','ottoman','submit');pid=dip.capital(s,'germiyan');p=s.places[pid];before=count(p.garrison)
    s=act(s,'vassal_levy',{'target':'germiyan','count':10});loan=next(iter(dip.data(s)['loans'].values()));assert count(s.places[pid].garrison)==before
    s.day=loan['ready'];dip.tick(s);a=s.armies[loan['army']]
    assert count(s.places[pid].garrison)==before-10 and a.size==10 and a.cohorts[0].origin==pid
    validate(s);s=RulerState.from_dict(s.to_dict());loan=dip.data(s)['loans'][loan['id']];a=s.armies[loan['army']]
    # Return while the contingent is still at muster; no simulated route fixture needed.
    a.travel=None;s=act(s,'levy_return',{'loan':loan['id']});s.day+=1;dip.tick(s)
    assert count(s.places[pid].garrison)==before and not s.armies[a.id].size
    validate(s)

def test_bot_calls_real_subjects_and_human_is_asked_first():
    s=realm();treaty(s,'ottoman','germiyan','submit');dip.declare(s,'germiyan','byzantine',defensive=True)
    before=count(s.places['sogut'].garrison);s.day=90;dip.tick(s)
    offers=[o for o in dip.data(s)['offers'].values() if o['kind']=='levy' and o['b']=='ottoman']
    assert offers and not dip.data(s)['loans'] and count(s.places['sogut'].garrison)==before

def test_master_hire_arrival_training_apprentice_engine_and_workers():
    s=realm();m=view(s)['statecraft']['masters'][0];before=s.places['sogut'].reserve
    s=act(s,'hire_master',{'person':m['id'],'province':'sogut'})
    assert s.people[m['id']].travel
    with pytest.raises(RuleError):act(s,'learn_craft',{'person':m['id'],'province':'sogut','tech':'carpentry'})
    s=advance(s,15);assert s.people[m['id']].location=='sogut' and not s.people[m['id']].travel
    s=act(s,'learn_craft',{'person':m['id'],'province':'sogut','tech':'carpentry'})
    assert s.places['sogut'].reserve==before-3
    with pytest.raises(RuleError):act(s,'move_master',{'person':m['id'],'province':'domanic'})
    s=advance(s,60);assert 'carpentry' in dip.data(s)['skills']['ottoman']
    assert any(p.role=='master' and p.id!=m['id'] and p.faction=='ottoman' for p in s.people.values())
    assert s.places['sogut'].reserve>=before
    # These are boundary-state supplies, not a claim of a fully legal campaign prefix.
    s.gold=400;s.places['sogut'].grain=10000;s.armies['ottoman-1'].location='sogut';s.armies['ottoman-1'].travel=None
    treaty(s,'ottoman','byzantine','peace',payment=40)
    reserve=s.places['sogut'].reserve;troops=s.armies['ottoman-1'].size
    s=act(s,'commission_engine',{'person':m['id'],'province':'sogut','army':'ottoman-1','engine':'ram'})
    assert s.places['sogut'].reserve==reserve-5
    s=advance(s,30);assert s.armies['ottoman-1'].engines==1
    assert s.armies['ottoman-1'].size<=troops+5
    assert any(c.service=='engine_crew' and c.count==5 for c in s.armies['ottoman-1'].cohorts)
    validate(s)

def test_ignored_specialist_can_join_rival_for_real_fee():
    s=realm();m=view(s)['statecraft']['masters'][0];pid=m['id'];before={f:r.gold for f,r in s.polities.items()}
    s.day=121;know.tick(s);employer=dip.data(s)['specialists'][pid]['employer']
    assert employer in s.polities and s.polities[employer].gold<=before[employer]-m['fee']
    with pytest.raises(RuleError):act(s,'hire_master',{'person':pid})

def test_plan_is_nonspending_atomic_stale_aware_and_confirmed_once():
    s=realm();before=s.gold;g=count(s.places['sogut'].garrison)
    d={'army':'ottoman-1','purpose':'cover','target':'sogut','funds':20,'troops':{'militia':10}}
    n=act(s,'plan_order',d);assert n.gold==before and count(n.places['sogut'].garrison)==g
    assert view(n)['statecraft']['draft']['garrison']['militia']==g-10
    stale=act(n,'consult',{})
    with pytest.raises(RuleError):act(stale,'execute_plan',{})
    done=act(n,'execute_plan',{});assert done.gold==before-20 and count(done.places['sogut'].garrison)==g-10
    with pytest.raises(RuleError):act(done,'execute_plan',{})
    validate(done)

def test_delegation_spends_cap_once_preserves_across_edits_and_pauses():
    s=realm();p=s.places['sogut'];p.garrison=p.garrison[:1];p.walls-=5
    s=act(s,'governance_policy',{'province':'sogut','budget':10,'repair':True})
    before=s.gold;s.day=1;statecraft._policy(s);assert s.gold==before-10
    assert dip.data(s)['policies']['sogut']['spent']==10 and s.places['sogut'].construction
    s=act(s,'governance_policy',{'province':'sogut','budget':20,'repair':True})
    assert dip.data(s)['policies']['sogut']['spent']==10
    s.people['hasan'].status='ill';statecraft._policy(s);assert dip.data(s)['policies']['sogut']['status']=='paused'

def test_training_wait_does_not_advance_past_completion_and_reload_retains_tasks():
    s=realm();s=act(s,'raise',{'province':'sogut','troop':'militia','count':2});s=RulerState.from_dict(s.to_dict())
    for _ in range(30):
        if not s.places['sogut'].training:break
        s=act(s,'advance',{'days':90,'wait_for':{'kind':'training','id':'sogut'}})
    assert s.day==14 and not s.places['sogut'].training
    assert not any(t['kind']=='training' for t in view(s)['statecraft']['tasks'])

def test_unknown_commands_are_rule_errors_not_internal_errors():
    s=realm()
    for kind,payload in [('commission_engine',{'province':'missing'}),('intrigue',{}),('siege_operation',{}),('execute_plan',{})]:
        with pytest.raises(RuleError):act(s,kind,payload)


def test_store_receipts_and_owner_isolation_for_new_contracts(tmp_path):
    from server.storage import Store,MissingCampaign
    store=Store(f'sqlite:///{tmp_path}/realm.db');save=store.create('one',11,'ruler_v1','realm')
    result=store.command(save['id'],'one','embassy-1',0,'negotiate',{'target':'germiyan','proposal':'trade','payment':20})
    assert store.command(save['id'],'one','embassy-1',0,'negotiate',{'target':'germiyan','proposal':'trade','payment':20})==result
    store.engine.dispose();store=Store(f'sqlite:///{tmp_path}/realm.db')
    assert store.get(save['id'],'one')==result
    with pytest.raises(MissingCampaign):store.command(save['id'],'two','steal',1,'break_treaty',{'target':'germiyan'})
    assert store.get(save['id'],'one')==result
    store.engine.dispose()

@pytest.mark.parametrize('side,operation',[('attack','search'),('attack','tunnel'),('attack','infiltrate'),('defend','sortie')])
def test_siege_actions_change_real_state_without_instant_capture(side,operation):
    s=realm(29);site='bilecik' if side=='attack' else 'sogut';p=s.places[site]
    a=s.armies['ottoman-1' if side=='attack' else 'byzantine-frontier'];a.location=site;a.travel=None
    s.sieges[site]={'province':site,'faction':a.faction,'armies':[a.id],'started':s.day,'supplies':p.grain,'morale':90,'passage_found':True}
    master=next(pid for pid,m in dip.data(s)['specialists'].items() if 'mining' in m['knows'])
    dip.data(s)['specialists'][master]['employer']='ottoman';s.people[master].location=site;s.people[master].faction='ottoman'
    s=act(s,'siege_operation',{'province':site,'operation':operation,'person':master,'count':10})
    old_controller=s.places[site].controller;walls=s.places[site].walls
    if operation=='sortie':
        assert count(s.places[site].garrison)<count(p.garrison) and s.armies[a.id].size<a.size
        with pytest.raises(RuleError):act(s,'siege_operation',{'province':site,'operation':operation,'count':10})
    else:
        w=next(iter(dip.data(s)['siege_work'].values()));s.day=w['ready'];know.tick(s)
        assert w['status']=='completed'
        if operation=='tunnel':assert s.places[site].walls==max(0,walls-12)
        if operation=='infiltrate':assert s.sieges[site]['passage_used']
    assert s.places[site].controller==old_controller
    validate(s)

def test_search_is_fixed_and_interrupted_siege_work_does_not_damage_new_siege():
    s=realm();a=s.armies['ottoman-1'];a.location='bilecik';p=s.places['bilecik'];a.travel=None
    s.sieges[p.id]={'province':p.id,'faction':'ottoman','armies':[a.id],'started':0,'supplies':p.grain,'morale':90}
    master=next(pid for pid,m in dip.data(s)['specialists'].items() if 'mining' in m['knows'])
    dip.data(s)['specialists'][master]['employer']='ottoman';s.people[master].location=p.id;s.people[master].faction='ottoman'
    s=act(s,'siege_operation',{'province':p.id,'operation':'search','person':master});s.day=14;know.tick(s)
    first=s.sieges[p.id]['passage_found']
    s=act(s,'siege_operation',{'province':p.id,'operation':'search','person':master});s.day=28;know.tick(s)
    assert s.sieges[p.id]['passage_found']==first
    s=act(s,'siege_operation',{'province':p.id,'operation':'tunnel','person':master});s.sieges[p.id]['started']=29
    walls=s.places[p.id].walls;s.day=58;know.tick(s);assert s.places[p.id].walls==walls
    assert list(dip.data(s)['siege_work'].values())[-1]['status']=='failed'

def test_throne_installation_requires_vassal_and_physical_candidate_arrival():
    s=realm();s=act(s,'support_claim',{'person':'ahmed','target':'germiyan'});s.day=90
    with pytest.raises(RuleError):act(s,'negotiate',{'target':'germiyan','proposal':'dynasty','candidate':'ahmed','payment':40})
    treaty(s,'germiyan','ottoman','submit');o=dip.propose(s,'ottoman','germiyan','dynasty',candidate='ahmed',payment=40)
    old=dip.data(s)['rulers']['germiyan'];units=deepcopy(s.armies);dip.agree(s,o)
    assert dip.data(s)['rulers']['germiyan']==old and s.people['ahmed'].travel and s.armies==units
    for _ in range(90):
        s.day+=1;know.tick(s);dip.tick(s)
        if dip.data(s)['claims']['ahmed']['status']=='installed':break
    assert dip.data(s)['rulers']['germiyan']=='ahmed'
    assert s.people['ahmed'].location==dip.capital(s,'germiyan') and s.armies==units

def test_multiple_governors_do_not_reuse_stale_policy_after_first_spend():
    s=realm();s.people['konur'].skills['stewardship']=65
    for pid in ['sogut','karacahisar']:
        s.places[pid].walls-=3
        s=act(s,'governance_policy',{'province':pid,'budget':10,'repair':True})
    before=s.gold;statecraft._policy(s)
    assert s.gold==before-12
    assert all(dip.data(s)['policies'][p]['spent']==6 for p in ['sogut','karacahisar'])
    statecraft._policy(s);assert s.gold==before-12

def test_paused_construction_does_not_suppress_due_audit():
    s=realm();p=s.places['sogut'];p.grain=0;p.construction={'building':'fortress','work':10,'workers':20,'master':'hasan'}
    s.people['hasan'].status='ill';s.people['hasan'].wounded_until=30;p.audit={'ready':1,'governor':'hasan'};s.day=1
    civil.tick(s)
    assert p.construction['work']==10 and p.construction['paused'] and p.audit is None

def test_treaty_does_not_appear_if_war_started_during_journey():
    s=realm();s=act(s,'negotiate',{'target':'germiyan','proposal':'trade','payment':20})
    o=next(iter(dip.data(s)['offers'].values()));o.update(status='returning',answer=True,ready=1)
    dip.declare(s,'germiyan','ottoman');s.day=1;dip.tick(s)
    assert o['status']=='rejected' and not dip.active(s,'ottoman','germiyan','trade')
    assert s.gold==230

def test_ai_can_choose_subordination_from_actual_defeat_and_dated_threat():
    from campaign.ruler import military,world
    s=realm(73);s.armies['ottoman-1'].location='nicomedia';s.armies['ottoman-1'].grain=10000
    # Combat boundary fixture, then normal defeat bookkeeping and observations.
    enemy=s.armies['byzantine-frontier'];enemy.cohorts[0].count=1
    military._battle(s,'nicomedia',[s.armies['ottoman-1']],[enemy])
    assert dip.data(s)['defeats'].get('byzantine')
    s.day=90;r=s.polities['byzantine'];places=[p for p in s.places.values() if p.controller=='byzantine']
    world._scout(s,'byzantine',r,places,[a for a in s.armies.values() if a.faction=='byzantine'])
    dip.tick(s)
    assert any(o['kind']=='submit' and o['a']=='byzantine' for o in dip.data(s)['offers'].values())

@pytest.mark.parametrize('kind,key',[('negotiate','proposal'),('learn_craft','tech'),('commission_engine','engine'),('commission_engine','army')])
@pytest.mark.parametrize('bad',[None,[],{},12,True])
def test_malformed_nested_fields_are_controlled_refusals(kind,key,bad):
    s=realm();before=s.to_dict()
    payload={'target':'germiyan','proposal':'trade','province':'sogut','tech':'carpentry','engine':'ram','army':'ottoman-1',key:bad}
    with pytest.raises(RuleError):act(s,kind,payload)
    assert s.to_dict()==before

def test_pending_legacy_paid_letter_is_migrated_without_second_payment():
    s=new_campaign(11,extended=True);s=act(s,'diplomacy',{'target':'byzantine','proposal':'peace'})
    bank=s.gold;letter=next(c for c in s.couriers if c['kind']=='diplomacy')
    s=act(s,'statecraft_enable',{});assert s.gold==bank and not any(c['kind']=='diplomacy' for c in s.couriers)
    offer=dip.data(s)['offers'][letter['id']];assert offer['payment']==40 and offer['ready']==letter['ready']
    s.day=letter['ready'];dip.tick(s);assert s.gold in [bank,bank+40]
    gold=s.gold;dip.tick(s);assert s.gold==gold

def test_craft_payroll_forecast_and_actual_account_debit_once():
    s=realm();pid=view(s)['statecraft']['masters'][0]['id'];s=act(s,'hire_master',{'person':pid,'province':'sogut'})
    s.day=30;before=s.gold
    civil._month(s);base=s.gold;know.tick(s)
    assert s.gold==base-3 and civil.budget(s)['statecraft_due']==3
    assert s.flags['last_accounts']['expense']>=3
    # Direct tick is intentionally not repeated: calendar, rather than ticks, owns payroll.

def test_wait_interruption_commits_obstruction_instead_of_rolling_back_time():
    s=realm();m=view(s)['statecraft']['masters'][0]['id']
    s=act(s,'hire_master',{'person':m,'province':'sogut'});s=advance(s,15)
    s=act(s,'learn_craft',{'person':m,'province':'sogut','tech':'carpentry'})
    project=next(iter(dip.data(s)['projects'].values()));s.people[m].status='ill';s.people[m].wounded_until=100
    before=s.day;n=act(s,'advance',{'days':90,'wait_for':{'kind':'workshop','id':project['id']}})
    assert n.day==before+1 and dip.data(n)['projects'][project['id']]['status']=='awaiting'
    assert any(r['kind']=='obstruction' for r in n.reports)
    # Ownership loss during an already authorised wait is an interruption, not an exception.
    s.places['sogut'].controller='byzantine'
    assert statecraft.waiting(s,{'kind':'construction','id':'sogut'})
    with pytest.raises(RuleError):statecraft.waiting(s,{'kind':'construction','id':'sogut'},initial=True)

def test_trade_contract_moves_actual_money_and_cargo_without_creating_grain():
    s=realm();treaty(s,'germiyan','ottoman','submit',tribute=0);treaty(s,'ottoman','germiyan','trade')
    for p in s.places.values():
        if p.controller=='ottoman':p.grain=0
        elif p.controller=='germiyan':p.grain=20000
    before=sum(p.grain for p in s.places.values());gold=s.gold;bank=s.polities['germiyan'].gold
    t=next(t for t in dip.data(s)['treaties'].values() if t['kind']=='trade')
    dip._commerce(s,t)
    cargo=[c for c in s.foreign_cargo if c.get('trade')==t['id']]
    assert cargo and sum(p.grain for p in s.places.values())+sum(c['grain'] for c in cargo)==before
    assert s.gold==gold-10 and s.polities['germiyan'].gold==bank+10
    dip._commerce(s,t);assert s.gold==gold-10 and len(s.foreign_cargo)==len(cargo)

@pytest.mark.parametrize('angry',[False,True])
def test_intrigue_follows_actual_vassal_conflict_and_never_spawns_armies(angry):
    s=realm();treaty(s,'germiyan','byzantine','submit');pid=dip.data(s)['rulers']['germiyan']
    if angry:dip.data(s)['subjects']['germiyan']['arrears']=10
    s=act(s,'intrigue',{'target':'germiyan','person':pid,'operation':'revolt'})
    units={k:deepcopy(a.cohorts) for k,a in s.armies.items()};plot=next(iter(dip.data(s)['plots'].values()));s.day=plot['ready'];statecraft._plots(s)
    assert {k:a.cohorts for k,a in s.armies.items()}==units
    assert (dip.root(s,'germiyan')=='germiyan')==angry
    assert plot['status']==('completed' if angry else 'failed')

def test_unresolved_subject_demand_gives_time_before_real_rebellion():
    s=realm();treaty(s,'germiyan','ottoman','submit');c=dip.data(s)['subjects']['germiyan'];c['arrears']=50
    units=deepcopy(s.armies);statecraft._cases(s);assert dip.root(s,'germiyan')=='ottoman' and c['demand_since']==0
    s.day=89;statecraft._cases(s);assert dip.root(s,'germiyan')=='ottoman'
    s.day=90;statecraft._cases(s);assert dip.root(s,'germiyan')=='germiyan' and s.armies==units
    from campaign.ruler.core import war
    assert war(s,'germiyan','ottoman')

def test_foreign_successor_preserves_state_contracts_and_real_forces():
    s=realm();treaty(s,'germiyan','ottoman','submit',tribute=7);old=dip.data(s)['rulers']['germiyan'];s.people[old].status='dead';s.day=1
    before=deepcopy(s.armies);bank=s.polities['germiyan'].gold;pledge=deepcopy(dip.data(s)['subjects']['germiyan'])
    dip.tick(s);successor=dip.data(s)['rulers']['germiyan']
    assert successor!=old and s.people[successor].status=='active'
    assert s.people[successor].location==dip.capital(s,'germiyan')
    assert s.armies==before and s.polities['germiyan'].gold==bank and dip.data(s)['subjects']['germiyan']==pledge

def test_peace_physically_withdraws_armies_instead_of_trapping_them():
    s=realm();a=s.armies['ottoman-1'];a.location='bursa';a.travel=None
    treaty(s,'ottoman','byzantine','peace',payment=40)
    assert a.travel and a.travel['civilian'] and a.travel['retreat']
    assert a.location=='bursa' and a.size>0
    validate(s)

@pytest.mark.parametrize('trust,expected',[(20,False),(55,True)])
def test_protection_intrigue_requires_trust_in_patron_and_actual_distress(trust,expected):
    s=realm();pid=dip.data(s)['rulers']['germiyan'];s.people[pid].trust=trust;s.polities['germiyan'].arrears=40
    s=act(s,'intrigue',{'target':'germiyan','person':pid,'operation':'defection'})
    plot=next(iter(dip.data(s)['plots'].values()));s.day=plot['ready'];units=deepcopy(s.armies);statecraft._plots(s)
    assert bool([o for o in dip.data(s)['offers'].values() if o['kind']=='submit' and o['a']=='germiyan'])==expected
    assert s.armies==units and plot['status']==('completed' if expected else 'failed')
