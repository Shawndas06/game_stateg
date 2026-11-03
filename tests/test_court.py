from copy import deepcopy
import pytest
from campaign.engine import RuleError
from campaign.ruler import court,civil
from campaign.ruler.core import count
from campaign.ruler.models import RulerState
from campaign.ruler.engine import new_campaign,apply_command,view,validate


def answer(s,scene,choice):
    a=next(a for a in s.agendas if a['scene']==scene)
    return apply_command(s,'decide',{'agenda':a['id'],'choice':choice})


def advance(s,day):
    routine={'frontier_letter':'accept','grain_offer':'decline','service_terms':'reward','village_petition':'charter','quarter_accounts':'accept','charter_return':'honour','road_warning':'ignore'}
    while s.day<day and not s.ending:
        for agenda in list(s.agendas):
            if agenda['scene'] in routine:s=answer(s,agenda['scene'],routine[agenda['scene']])
        s=apply_command(s,'advance',{'days':min(90,day-s.day)})
    return s


def test_governor_story_needs_arrival_and_ninety_days_of_work():
    s=new_campaign(11,extended=True);s=answer(s,'founding','stewardship');s=advance(s,90)
    s=answer(s,'orhan_trial','govern')
    assert s.places['domanic'].governor is None and s.people['orhan'].travel
    assert not court.work_evidence(s)
    s=advance(s,110);assert s.places['domanic'].governor=='orhan'
    assert not court.work_evidence(s)
    s=advance(s,210);assert court.work_evidence(s)
    assert view(s)['people']['orhan']['history']


def test_study_choice_spends_stated_price_and_returns_with_real_result():
    s=new_campaign(11,extended=True);s=answer(s,'founding','stewardship');s=advance(s,90)
    gold=s.gold;s=answer(s,'orhan_trial','study')
    assert s.gold==gold-50 and not court.work_evidence(s)
    s=advance(s,300)
    assert court.work_evidence(s)
    s=answer(s,'orhan_account','recognize')
    assert any(d['id']=='heir_duty' for d in view(s)['accomplishments'])
    restored=RulerState.from_dict(s.to_dict());assert restored.to_dict()==s.to_dict()


def test_existing_commander_gets_a_report_not_a_second_incompatible_job():
    s=new_campaign(11,extended=True);s=answer(s,'founding','stewardship')
    s=apply_command(s,'split_army',{'army':'ottoman-1','commander':'orhan','troops':{'militia':10}})
    s=advance(s,90)
    assert not any(a['scene']=='orhan_trial' for a in s.agendas)
    assert s.flags['personal_threads']['orhan']['choice']=='field'


def test_payment_history_is_exact_and_idempotent():
    from campaign.ruler.civil import obligation
    s=new_campaign(11,extended=True);oid=obligation(s,'reward','konur',0,40)
    before=s.people['konur'].wealth;s=apply_command(s,'fulfil',{'obligation':oid})
    assert s.people['konur'].wealth==before+40
    assert sum(h['key']=='payment:'+oid for h in s.people['konur'].history)==1
    before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'fulfil',{'obligation':oid})
    assert s.to_dict()==before


def test_three_actual_balanced_ledgers_award_once_without_new_money():
    s=new_campaign(1,extended=True)
    for day in [30,60,90]:
        s.day=day;s.flags['last_accounts']={'day':day,'income':60,'expense':30};court.tick(s)
    gold=s.gold;court.tick(s)
    assert sum(a['id']=='accounts' for a in s.flags['accomplishments'])==1 and s.gold==gold


def test_no_supply_achievement_until_cargo_really_arrives():
    s=new_campaign(1,extended=True)
    s.transports['fixture']={'kind':'purchase','status':'moving','target':'sogut'}
    court.tick(s);assert not any(a['id']=='supplies' for a in s.flags.get('accomplishments',[]))
    s.transports['fixture']['status']='completed';court.tick(s)
    assert any(d['id']=='supplies' for d in s.flags['accomplishments'])


@pytest.mark.parametrize('scene,choice',[(scene,c) for scene,(_,_,choices) in court.SCENES.items() for c,_ in choices])
def test_personal_choice_boundary_is_reproducible_and_conserves_people(scene,choice):
    s=new_campaign(11,extended=True);s.gold=1000;s.day=400
    pid='orhan' if scene.startswith('orhan') else 'konur' if scene.startswith('konur') else 'turgut'
    s.flags['personal_threads']={pid:{'stage':'opened','day':0,'choice':'study'}}
    if scene=='orhan_account':s.people['orhan'].history.append({'key':'course:200stewardship','day':200,'date':'1299-09-17','text':'Курс завершён','ruler':'osman'})
    court.open_case(s,scene,{'person':pid})
    before=sum(count(p.garrison)+p.reserve+sum(t['count'] for t in p.training) for p in s.places.values())+sum(a.size for a in s.armies.values())
    s=answer(s,scene,choice);validate(s)
    after=sum(count(p.garrison)+p.reserve+sum(t['count'] for t in p.training) for p in s.places.values())+sum(a.size for a in s.armies.values())
    assert before==after
    assert RulerState.from_dict(s.to_dict()).to_dict()==s.to_dict()
    assert s.people[pid].history


def test_hidden_attitudes_are_not_exposed_by_personal_history():
    s=new_campaign(11,extended=True);court.remember(s,'konur','known','Условие службы записано.')
    p=view(s)['people']['konur'];assert p['history'][0]['text']=='Условие службы записано.'
    assert not {'trust','ambition','memories','health'}.intersection(p)


def test_ignored_personal_letter_closes_without_fake_fulfilment():
    s=new_campaign(11,extended=True);s=answer(s,'founding','stewardship');s=advance(s,90)
    a=next(a for a in s.agendas if a['scene']=='orhan_trial')
    s=advance(s,a['deadline']+1)
    assert s.flags['personal_threads']['orhan']['stage']=='closed'
    assert any(h['key']=='silence:orhan_trial' for h in s.people['orhan'].history)
    assert not any(d['id']=='heir_duty' for d in s.flags.get('accomplishments',[]))


def test_platform_url_is_derived_without_overriding_custom_domain(monkeypatch):
    from server.app import Settings
    monkeypatch.delenv('PUBLIC_URL',raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_URL','https://example.onrender.com')
    assert Settings.environment().public_url=='https://example.onrender.com'
    monkeypatch.setenv('PUBLIC_URL','https://custom.example')
    assert Settings.environment().public_url=='https://custom.example'


def test_accession_closes_a_former_heirs_personal_petition():
    s=new_campaign(11,extended=True);s=answer(s,'founding','stewardship');s=advance(s,90)
    assert any(a['scene']=='orhan_trial' for a in s.agendas)
    # Succession boundary fixture; the real death/recognition path has its own walks.
    s.ruler_id='orhan';court.tick(s)
    assert not any(a['scene']=='orhan_trial' for a in s.agendas)
    assert s.flags['personal_threads']['orhan']['stage']=='closed'


def test_summons_travels_and_stops_the_clock_on_actual_arrival():
    s=new_campaign(11,extended=True);s.people['orhan'].location='domanic'
    s.places['domanic'].governor='orhan'
    s=apply_command(s,'summon',{'person':'orhan'})
    assert s.people['orhan'].location=='domanic' and s.people['orhan'].travel
    assert s.places['domanic'].governor is None
    s=apply_command(s,'advance',{'days':90})
    assert s.day<30 and s.people['orhan'].location==s.capital and not s.people['orhan'].travel
    assert any(h['key'].startswith('summons:') for h in s.people['orhan'].history)
