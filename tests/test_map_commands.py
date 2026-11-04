"""Map commands use the same physical orders and calendar as the campaign."""
from copy import deepcopy
import pytest
from campaign.engine import RuleError
from campaign.ruler.engine import new_campaign,apply_command,view,validate
from campaign.ruler.models import RulerState
from campaign.ruler import civil,diplomacy

@pytest.mark.parametrize('mode',[3,4,5])
def test_march_to_own_city_arrives_and_completes_without_teleport(mode):
    s=new_campaign(11,extended=mode>=4,living=mode==5);before=deepcopy(s.armies['ottoman-1'].cohorts)
    s=apply_command(s,'mission',{'army':'ottoman-1','purpose':'march','target':'domanic','funds':0})
    assert s.armies['ottoman-1'].location=='sogut' and not s.armies['ottoman-1'].travel
    assert s.armies['ottoman-1'].cohorts==before
    for _ in range(30):
        s=apply_command(s,'advance',{'days':1});s=RulerState.from_dict(s.to_dict())
        if s.armies['ottoman-1'].mission['status']=='completed':break
    assert s.armies['ottoman-1'].location=='domanic' and s.armies['ottoman-1'].mission['status']=='completed'
    validate(s)

@pytest.mark.parametrize('mode',[3,4,5])
@pytest.mark.parametrize('target',['kutahya','bilecik'])
def test_march_cannot_bypass_neutral_passage_or_attack_permission(mode,target):
    s=new_campaign(11,extended=mode>=4,living=mode==5);before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'mission',{'army':'ottoman-1','purpose':'march','target':target,'funds':20})
    assert s.to_dict()==before

def test_real_negotiated_passage_allows_march_and_returned_order_stops_on_breach():
    s=new_campaign(11,extended=True,living=True)
    s=apply_command(s,'negotiate',{'target':'germiyan','proposal':'access'})
    for _ in range(30):
        s=apply_command(s,'advance',{'days':1})
        if diplomacy.active(s,'ottoman','germiyan','access'):break
    assert diplomacy.active(s,'ottoman','germiyan','access')
    s=apply_command(s,'plan_order',{'army':'ottoman-1','purpose':'march','target':'kutahya','funds':0})
    draft=view(s)['statecraft']['draft'];assert draft['route'][-1]=='kutahya'
    s=apply_command(s,'execute_plan',{})
    s=apply_command(s,'break_treaty',{'target':'germiyan'});location=s.armies['ottoman-1'].location
    s=apply_command(s,'advance',{'days':1})
    assert s.armies['ottoman-1'].location==location and s.armies['ottoman-1'].mission['status']=='awaiting'
    assert any(r['kind']=='obstruction' for r in s.reports)


def test_local_tax_assessment_matches_budget_and_withholds_foreign_accounts():
    s=new_campaign(11,extended=True,living=True)
    s=apply_command(s,'grant',{'province':'sogut','person':'ahmed'})
    s=apply_command(s,'policy',{'province':'sogut','tax':'extraordinary'})
    before=s.to_dict();v=view(s);assert s.to_dict()==before
    rows=[p['assessment'] for p in v['provinces'].values() if p['controlled']]
    for field,aggregate in [('gross','gross'),('granted','grants'),('treasury','income')]:assert sum(x[field] for x in rows)==v['budget'][aggregate]
    assert all(p['assessment'] is None for p in v['provinces'].values() if not p['controlled'])


def test_calendar_not_number_of_map_wait_buttons_controls_income_and_work():
    s=new_campaign(29,extended=True,living=True)
    s=apply_command(s,'raise',{'province':'sogut','troop':'militia','count':3})
    daily=deepcopy(s);weekly=deepcopy(s)
    while daily.day<35:daily=apply_command(daily,'advance',{'days':1,'until_event':False})
    while weekly.day<35:weekly=apply_command(weekly,'advance',{'days':min(7,35-weekly.day),'until_event':False})
    assert daily.gold==weekly.gold and daily.arrears==weekly.arrears
    assert daily.places==weekly.places
    assert daily.armies==weekly.armies

@pytest.mark.parametrize('modern',[False,True])
def test_peaceful_march_never_carries_assault_authority(modern):
    s=new_campaign(11,extended=True,living=modern);before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'mission',{'army':'ottoman-1','purpose':'march','target':'domanic','allow_assault':True})
    assert s.to_dict()==before
