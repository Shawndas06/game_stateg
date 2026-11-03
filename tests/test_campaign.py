from copy import deepcopy
import json

import pytest
from hypothesis import given, strategies as st

from campaign.content import BUILDINGS, EVENTS, TECHNOLOGIES, TROOPS
from campaign.engine import RuleError, apply_command, budget, new_campaign, relation, remove_troops, validate
from campaign.models import Siege, State


def start(seed=1, choice="stewardship"):
    return apply_command(new_campaign(seed), "choose", {"choice": choice})


def answer(s):
    while s.pending_event:
        choices = EVENTS[s.pending_event]["choices"]
        # Explicitly preserve promised rights; choose the affordable non-payment fallback otherwise.
        preferred = {"first_city": "charter", "military_claim": "centralize", "local_petition": "honour", "bursa": "capital", "merchant_debt": "privileges", "succession": "authority"}
        s = apply_command(s, "choose", {"choice": preferred.get(s.pending_event, choices[-1]["id"])})
    return s


@given(st.dictionaries(st.sampled_from(list(TROOPS)), st.integers(0, 500), min_size=1), st.integers(0, 2000))
def test_losses_conserve_every_survivor(troops, loss):
    old = dict(troops)
    recorded = remove_troops(troops, loss)
    assert sum(old.values()) - sum(troops.values()) == min(loss, sum(old.values()))
    assert sum(recorded.values()) == min(loss, sum(old.values()))
    assert all(0 <= troops[t] <= old[t] for t in troops)


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "10", 501, None])
def test_invalid_mobilization_is_atomic(bad):
    s = start(); before = s.to_dict()
    with pytest.raises(RuleError):
        apply_command(s, "mobilize", {"army": "ottoman-1", "troop": "militia", "count": bad})
    assert s.to_dict() == before


def test_initial_capital_mobilization_and_recruitment_work():
    s = start(); initial = budget(s, "ottoman")["troops"]
    s = apply_command(s, "mobilize", {"army": "ottoman-1", "troop": "militia", "count": 25})
    assert budget(s, "ottoman")["troops"] == initial
    s = apply_command(s, "recruit", {"province": "sogut", "troop": "archers", "count": 10})
    assert budget(s, "ottoman")["troops"] == initial + 10


def test_route_checks_actual_corridor_and_treaty():
    s = start()
    for target in ("bursa", "kutahya"):
        with pytest.raises(RuleError): apply_command(s, "move", {"army": "ottoman-1", "target": target})
    s = apply_command(s, "move", {"army": "ottoman-1", "target": "inegol"})
    assert s.armies["ottoman-1"].location == "sogut"
    s = apply_command(s, "end_turn", {})
    assert s.armies["ottoman-1"].location == "inegol" and "inegol" in s.sieges


def besieging(seed=1):
    s = start(seed)
    s = apply_command(s, "move", {"army": "ottoman-1", "target": "inegol"})
    return apply_command(s, "end_turn", {})


def test_siege_troops_keep_their_composition_and_upkeep():
    before = start(); after = besieging()
    assert before.armies["ottoman-1"].troops == after.armies["ottoman-1"].troops
    assert budget(before, "ottoman")["expense"] == budget(after, "ottoman")["expense"]
    assert after.provinces["inegol"].controller == "byzantine"


def test_next_season_forecast_matches_actual_winter_boundary():
    s = start()
    for _ in range(5):
        f = s.factions['ottoman']; old_food = f.food
        forecast = budget(s, 'ottoman')
        s = apply_command(s, 'end_turn', {})
        assert s.factions['ottoman'].food - old_food == forecast['food_income'] - forecast['food_expense']


@pytest.mark.parametrize("seed", range(12))
def test_assault_never_discards_survivors(seed):
    s = besieging(seed)
    a = s.armies["ottoman-1"]
    total = a.size
    s = apply_command(s, "siege_mode", {"army": a.id, "mode": "assault"})
    result = apply_command(s, "end_turn", {})
    expected_losses = __import__('math').ceil(total * (.20 if result.provinces['inegol'].controller == 'ottoman' else .32))
    remaining = result.armies[a.id].size
    if result.provinces['inegol'].controller == 'ottoman': remaining += sum(result.provinces['inegol'].garrison.values())
    assert total - remaining == expected_losses
    validate(result)


def test_unsupplied_attacker_loses_troops():
    s = besieging()
    s.provinces['sogut'].controller = 'germiyan'
    s.provinces['karacahisar'].controller = 'germiyan'
    s.provinces['domanic'].controller = 'germiyan'
    s.provinces['inonu'].controller = 'germiyan'
    # Give the player an isolated rear area so the campaign itself remains alive.
    s.provinces['mudanya'].owner = s.provinces['mudanya'].controller = 'ottoman'
    a = s.armies['ottoman-1']; a.supply = 0
    before = a.size
    s = apply_command(s, 'end_turn', {})
    assert s.armies[a.id].size < before


def test_peace_closes_operations_trade_stops_on_war_and_dead_factions_cannot_trade():
    s = besieging()
    p = s.provinces['yarhisar']; p.controller = 'ottoman'
    s = apply_command(s, 'diplomacy', {'target':'byzantine','proposal':'peace'})
    assert not s.sieges
    assert s.provinces['yarhisar'].owner == 'ottoman'
    assert s.provinces[s.armies['ottoman-1'].location].controller == 'ottoman'
    for _ in range(4): s = answer(apply_command(s, 'end_turn', {}))
    s = apply_command(s,'diplomacy',{'target':'byzantine','proposal':'trade'})
    assert budget(s,'ottoman')['trade'] == 12
    s = answer(apply_command(s,'end_turn',{}))
    s = apply_command(s,'diplomacy',{'target':'byzantine','proposal':'war'})
    assert budget(s,'ottoman')['trade'] == 0
    for p in s.provinces.values():
        if p.controller=='germiyan': p.controller='byzantine'
    with pytest.raises(RuleError): apply_command(s,'diplomacy',{'target':'germiyan','proposal':'trade'})


def test_paid_story_choice_cannot_be_bought_with_no_money():
    s = new_campaign(1); s.factions['ottoman'].gold = 0
    before = s.to_dict()
    with pytest.raises(RuleError): apply_command(s,'choose',{'choice':'frontier'})
    assert s.to_dict() == before


STORY_COSTS = {('founding','frontier'):30, ('founding','stewardship'):25, ('merchant_debt','repay'):90, ('first_city','charter'):25, ('bursa','capital'):60, ('succession','oath'):40}


@pytest.mark.parametrize('event,choice',[(eid,c['id']) for eid,event in EVENTS.items() for c in event['choices']])
def test_every_story_choice_roundtrips_and_paid_choices_respect_boundaries(event,choice):
    s=start();s.pending_event=event;s.shown_events=[]
    if event=='bursa':s.provinces['bursa'].controller='ottoman'
    cost=STORY_COSTS.get((event,choice),0)
    if cost:
        s.factions['ottoman'].gold=cost-1
        before=s.to_dict()
        with pytest.raises(RuleError):apply_command(s,'choose',{'choice':choice})
        assert before==s.to_dict()
    s.factions['ottoman'].gold=max(cost,100)
    result=apply_command(s,'choose',{'choice':choice})
    assert result.flags[event]==choice
    assert event in result.shown_events
    assert State.from_dict(json.loads(json.dumps(result.to_dict()))).to_dict()==result.to_dict()


def test_political_support_changes_actual_economy_and_forces():
    s = start()
    s = apply_command(s, 'diplomacy', {'target': 'germiyan', 'proposal': 'trade'})
    assert budget(s, 'ottoman')['trade'] == 12
    s.factions['ottoman'].groups['merchants'] = 39
    assert budget(s, 'ottoman')['trade'] == 0
    s.factions['ottoman'].groups['military'] = 29
    before = s.armies['ottoman-1'].size
    s = apply_command(s, 'end_turn', {})
    assert s.armies['ottoman-1'].size < before


def test_port_can_receive_food_while_landlocked_fortress_cannot():
    s = start()
    a = s.armies['ottoman-1'];a.location = 'mudanya';a.troops = {'militia': 300}
    s.sieges['mudanya'] = Siege('mudanya', a.id)
    s = apply_command(s, 'end_turn', {})
    assert s.sieges['mudanya'].supplies == 100
    a = s.armies['ottoman-1'];a.location = 'inegol'
    s.sieges.clear();s.sieges['inegol'] = Siege('inegol', a.id)
    s = apply_command(s, 'end_turn', {})
    assert s.sieges['inegol'].supplies < 100


def test_past_choice_creates_a_different_future_and_cost():
    a = start(choice='merchants'); b = start(choice='stewardship')
    for _ in range(8):
        a = apply_command(a,'end_turn',{}); b = apply_command(b,'end_turn',{})
    assert a.pending_event == 'merchant_debt' and b.pending_event is None
    a = apply_command(a,'choose',{'choice':'privileges'})
    assert a.flags['merchant_privileges']
    clean = deepcopy(a);clean.flags.pop('merchant_privileges')
    assert budget(clean,'ottoman')['net']-budget(a,'ottoman')['net']==8


def test_research_pause_roundtrip_and_dependencies():
    s = start()
    with pytest.raises(RuleError): apply_command(s,'research',{'technology':'trebuchets'})
    s = apply_command(s,'research',{'technology':'siege_camp'})
    for _ in range(2): s=apply_command(s,'end_turn',{})
    progress=s.factions['ottoman'].research['progress']
    s=apply_command(s,'pause_research',{})
    s=State.from_dict(json.loads(json.dumps(s.to_dict())))
    s=apply_command(s,'research',{'technology':'siege_camp'})
    assert s.factions['ottoman'].research['progress']==progress
    for _ in range(8):s=answer(apply_command(s,'end_turn',{}))
    assert 'siege_camp' in s.factions['ottoman'].technologies


@pytest.mark.parametrize('building',list(BUILDINGS))
def test_every_building_completes_once_and_can_be_restored(building):
    s=start();s.factions['ottoman'].gold=1000;s.factions['ottoman'].technologies=['siege_camp']
    s=apply_command(s,'build',{'province':'sogut','building':building})
    s=State.from_dict(json.loads(json.dumps(s.to_dict())))
    for _ in range(BUILDINGS[building]['turns']):s=apply_command(s,'end_turn',{})
    assert s.provinces['sogut'].buildings.count(building)==1
    with pytest.raises(RuleError):apply_command(s,'build',{'province':'sogut','building':building})


def test_save_load_preserves_identical_future():
    s=besieging(13)
    restored=State.from_dict(json.loads(json.dumps(s.to_dict())))
    for _ in range(12):
        s=answer(apply_command(s,'end_turn',{}))
        restored=answer(apply_command(restored,'end_turn',{}))
        assert s.to_dict()==restored.to_dict()


def test_entire_chapter_from_real_start_without_forcing_a_capture():
    s=start(42,'frontier')
    s=apply_command(s,'mobilize',{'army':'ottoman-1','troop':'militia','count':30})
    s=apply_command(s,'recruit',{'province':'sogut','troop':'militia','count':40})
    s=apply_command(s,'mobilize',{'army':'ottoman-1','troop':'militia','count':40})
    for target in ('inegol','bursa'):
        s=apply_command(s,'move',{'army':'ottoman-1','target':target})
        for _ in range(30):
            s=answer(apply_command(s,'end_turn',{}))
            if s.provinces[target].controller=='ottoman':break
        assert s.provinces[target].controller=='ottoman'
    assert s.flags['chapter_complete'] and s.capital=='bursa'
    assert 'first_city' in s.shown_events and 'military_claim' in s.shown_events
    s=apply_command(s,'diplomacy',{'target':'byzantine','proposal':'peace'})
    assert s.provinces['bursa'].owner=='ottoman'
    assert s.ending is None


@pytest.mark.parametrize('seed',range(8))
def test_long_season_sequences_preserve_invariants(seed):
    s=start(seed)
    for _ in range(110):
        s=answer(s)
        if s.ending:break
        s=apply_command(s,'end_turn',{})
        validate(s)
    assert s.ruler=='Орхан' and s.ending is None
