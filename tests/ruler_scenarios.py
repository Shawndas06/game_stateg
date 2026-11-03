"""Executable acceptance walks. Real legal commands; no injected pending events.

Run: PYTHONPATH=. .venv/bin/python tests/ruler_scenarios.py --out /tmp/ruler-acceptance.json
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import json
from pathlib import Path

from campaign.engine import RuleError
from campaign.ruler.engine import apply_command, new_campaign, validate, view
from campaign.ruler.models import RulerState
from campaign.ruler.story import CHAPTER_SCENES as SCENES

SEEDS=[11,29,73]
PROFILES=['military','diplomatic','mixed','honour','break_promises','execute_envoys','delay','overspend','recovery']
PREFERRED={'founding':'stewardship','frontier_letter':'accept','grain_offer':'buy','service_terms':'reward','village_petition':'charter','quarter_accounts':'audit','road_warning':'patrol','merchant_due':'settle','governor_accounts':'audit','border_proposal':'peace','assembly_claim':'confirm','crisis':'settlement','charter_return':'honour','promise_broken':'repair','campaign_return':'review','casualty_hearing':'deputy','delayed_supply':'wait','accusation':'recover','rival_letters':'investigate','succession':'orhan'}


class Walk:
    def __init__(self,seed=11,profile='diplomatic'):
        self.state=new_campaign(seed);self.profile=profile;self.trace=[];self.rejections=[];self.coverage=set();self.prefixes={};self.snapshots=[]

    def act(self,kind,payload=None,optional=False):
        before=self.state.to_dict()
        try:self.state=apply_command(self.state,kind,payload or {})
        except RuleError as e:
            assert before==self.state.to_dict()
            self.rejections.append({'day':self.state.day,'kind':kind,'payload':payload or {},'reason':str(e)})
            if not optional:raise
            return False
        validate(self.state)
        self.trace.append({'day':self.state.day,'kind':kind,'payload':payload or {},'revision':self.state.revision})
        if self.state.revision%9==0:
            restored=RulerState.from_dict(self.state.to_dict());assert restored.to_dict()==self.state.to_dict();self.state=restored
        return True

    def choice(self,agenda,cid,treatment='receive',optional=False):
        self.prefixes.setdefault(agenda['scene'],deepcopy(self.state))
        ok=self.act('decide',{'agenda':agenda['id'],'choice':cid,'treatment':treatment},optional)
        if ok:self.coverage.add((agenda['scene'],cid))
        return ok

    def answer(self,skip=()):
        for ag in list(self.state.agendas):
            if ag['scene'] in skip:continue
            cid=PREFERRED[ag['scene']];treatment='receive'
            if self.profile in ['military','mixed'] and ag['scene']=='founding':cid='frontier'
            if self.profile=='military' and ag['scene']=='frontier_letter':cid='refuse'
            if self.profile=='diplomatic' and ag['scene']=='founding':cid='merchants'
            if self.profile=='honour' and ag['scene']=='service_terms':cid='grant'
            if self.profile=='honour' and ag['scene']=='road_warning':cid='local'
            if self.profile=='break_promises':
                if ag['scene']=='founding':cid='merchants'
                if ag['scene']=='promise_broken':cid='refuse'
                if ag['scene']=='charter_return':cid='revoke'
                if ag['scene']=='assembly_claim':cid='centralize'
            if self.profile=='execute_envoys' and ag['scene'] in ['frontier_letter','border_proposal','grain_offer','merchant_due']:
                cid={'frontier_letter':'refuse','border_proposal':'prepare','grain_offer':'decline','merchant_due':'refuse'}[ag['scene']];treatment='execute'
            if self.profile=='delay' and ag['scene']!='succession':continue
            if not self.choice(ag,cid,treatment,optional=True):
                for alt,_ in SCENES[ag['scene']][2]:
                    if self.choice(ag,alt,optional=True):break

    def until(self,day,skip=()):
        while self.state.day<day and not self.state.ending:
            self.answer(skip)
            if self.state.people[self.state.ruler_id].status=='dead':
                self.answer()
                if self.state.people[self.state.ruler_id].status=='dead':break
            self.act('advance',{'days':min(90,day-self.state.day)})

    def run(self):
        self.answer()
        if self.profile in ['military','mixed','recovery']:
            self.act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35}})
            self.act('appoint_commander',{'army':'ottoman-1','commander':'turgut'})
            self.act('mission',{'army':'ottoman-1','target':'bilecik','purpose':'conquer','funds':40,'allow_assault':True})
        if self.profile=='honour':
            self.act('raise',{'province':'domanic','troop':'militia','count':10})
        if self.profile=='overspend':
            for p in ['sogut','karacahisar','domanic','inonu']:
                self.act('raise',{'province':p,'troop':'cavalry','count':30},optional=True)
        for step in range(240):
            if self.state.ending:break
            self.answer()
            if self.state.people[self.state.ruler_id].status=='dead':self.answer()
            if self.state.ending:break
            if self.profile in ['honour','mixed']:
                for o in list(self.state.obligations.values()):
                    if o['status'] in ['open','broken'] and o['kind'] in ['debt','reward']:self.act('fulfil',{'obligation':o['id']},optional=True)
            if self.profile=='recovery' and step==10:
                self.act('recall',{'army':'ottoman-1'},optional=True)
            self.act('advance',{'days':90})
            if self.state.day>=64*90:raise AssertionError('No chapter result within64 seasons')
        assert self.state.ending, (self.profile,self.state.day)
        data=view(self.state)
        assert data['ending'] and not any('hint' in c for c in data['council']['choices'])
        return {'seed':self.state.seed,'profile':self.profile,'day':self.state.day,'commands':len(self.trace),'result':self.state.ending,'rejections':self.rejections,'trace':self.trace,'reports':self.state.reports}


def supplemental():
    walks=[]
    # Actual enemy counterattack, loss of the capital and subsequent recovery.
    w=Walk(39,'military');w.answer()
    w.act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':45}})
    w.act('mission',{'army':'ottoman-1','purpose':'cover','target':'domanic','funds':20})
    w.until(310)
    assert w.state.capital=='karacahisar' and w.state.places['sogut'].controller=='byzantine'
    w.act('mission',{'army':'ottoman-1','purpose':'conquer','target':'sogut','funds':30,'allow_assault':True,'allow_requisition':True})
    w.until(400)
    assert w.state.places['sogut'].controller=='ottoman'
    assert w.state.places['sogut'].seized_gold==0
    walks.append(w)
    # A cargo reaches an abandoned siege location: genuine delayed-supply branch.
    w=Walk(19,'military');w.answer();w.act('mission',{'army':'ottoman-1','target':'inegol','purpose':'conquer','funds':30})
    while w.state.armies['ottoman-1'].location!='inegol':w.act('advance',{'days':1})
    w.act('provision',{'army':'ottoman-1','province':'karacahisar','amount':400})
    w.act('recall',{'army':'ottoman-1'})
    for _ in range(20):
        w.act('advance',{'days':1})
        if any(a['scene']=='delayed_supply' for a in w.state.agendas):break
    assert any(a['scene']=='delayed_supply' for a in w.state.agendas),'Delayed supply not reached'
    walks.append(w)
    # A legal unpaid service promise motivates an actual supply obstruction.
    w=Walk(23,'break_promises');w.answer()
    w.until(90);w.answer()
    w.until(272,skip=['promise_broken'])
    w.act('appoint_commander',{'army':'ottoman-1','commander':'turgut'})
    w.act('provision',{'army':'ottoman-1','province':'karacahisar','amount':400})
    w.act('advance',{'days':1})
    assert any(a['scene']=='rival_letters' for a in w.state.agendas),'Intrigue branch not reached'
    w.prefixes['rival_letters']=deepcopy(w.state)
    w.act('audit',{'province':'karacahisar'})
    w.until(w.state.day+25,skip=['rival_letters','delayed_supply','promise_broken'])
    assert w.state.flags.get('sabotage_proven')
    walks.append(w)
    # Combat seeds are searched deterministically, with actual battles and no
    # alteration of person status, to reach ransom and death/heir situations.
    found_capture=found_succession=False
    for seed in range(1,101):
        if found_capture and found_succession:break
        w=Walk(seed,'military');w.answer()
        w.act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35}})
        w.act('lead',{'army':'ottoman-1','posture':'assault','regent':'hasan'})
        w.act('mission',{'army':'ottoman-1','target':'bursa','purpose':'conquer','funds':30,'allow_assault':True,'allow_requisition':True,'area':['sogut','inegol','bursa']})
        for _ in range(85):
            if w.state.ending:break
            w.act('advance',{'days':1})
            if any(p.status=='captured' for p in w.state.people.values()) and not found_capture:
                for ag in w.state.agendas:
                    if ag['scene']=='casualty_hearing' and w.state.people[ag['context']['person']].status=='captured':
                        w.prefixes['casualty_hearing']=deepcopy(w.state);walks.append(w);found_capture=True;break
            if any(ag['scene']=='succession' for ag in w.state.agendas) and not found_succession:
                w.prefixes['succession']=deepcopy(w.state);walks.append(w);found_succession=True;break
            if w.state.people[w.state.ruler_id].status=='dead':break
    assert found_capture,'No combat capture seed found'
    assert found_succession,'No combat succession seed found'
    return walks


def acceptance():
    results=[];walks=[];coverage=set();prefixes={}
    for profile in PROFILES:
        for seed in SEEDS:
            w=Walk(seed,profile);result=w.run();results.append(result);walks.append(w)
            print(f'PASS {profile} seed{seed}: day{w.state.day}, {len(w.trace)} commands',flush=True)
    walks+=supplemental()
    for w in walks:
        coverage|=w.coverage
        for scene,state in w.prefixes.items():
            prefixes.setdefault(scene,[]).append(state)
        for ag in w.state.agendas:prefixes.setdefault(ag['scene'],[]).append(deepcopy(w.state))
    branches=[]
    for scene,(_,_,choices) in SCENES.items():
        for cid,_ in choices:
            errors=[];passed=False
            for state in prefixes.get(scene,[]):
                ag=next((a for a in state.agendas if a['scene']==scene),None)
                if not ag:continue
                try:after=apply_command(state,'decide',{'agenda':ag['id'],'choice':cid})
                except RuleError as e:errors.append(str(e));continue
                validate(after)
                continuation=Walk(state.seed,'branch');continuation.state=after
                result=continuation.run()
                assert result['result']
                assert scene in after.shown and not any(x['id']==ag['id'] for x in after.agendas)
                branches.append({'scene':scene,'choice':cid,'seed':state.seed,'day':state.day,'outcome_reports':after.outbox,'prefix_snapshot':state.to_dict(),'continuation':{'day':result['day'],'result':result['result'],'trace':result['trace']}})
                coverage.add((scene,cid));passed=True;break
            assert passed,(scene,cid,'No legal reached prefix accepts this choice',errors)
    envoy_variants=[]
    for scene in ['frontier_letter','border_proposal','grain_offer','merchant_due']:
        for cid,_ in SCENES[scene][2]:
            for treatment in ['receive','gift','detain','execute']:
                forbidden=treatment in ['detain','execute'] and cid not in ['refuse','prepare','decline']
                found=False
                for state in prefixes.get(scene,[]):
                    ag=next((a for a in state.agendas if a['scene']==scene),None)
                    if not ag:continue
                    before=state.to_dict()
                    try:after=apply_command(state,'decide',{'agenda':ag['id'],'choice':cid,'treatment':treatment})
                    except RuleError as e:
                        assert state.to_dict()==before
                        if forbidden:envoy_variants.append({'scene':scene,'choice':cid,'treatment':treatment,'result':'rejected atomically'});found=True;break
                        continue
                    assert not forbidden,(scene,cid,treatment)
                    envoy=ag['context']['envoy'];person=after.people[envoy]
                    assert person.status==('dead' if treatment=='execute' else 'detained' if treatment=='detain' else 'leaving')
                    validate(after);envoy_variants.append({'scene':scene,'choice':cid,'treatment':treatment,'result':person.status});found=True;break
                assert found,(scene,cid,treatment,'No covered legal or expected-rejection case')
    return {'envoy_variants':envoy_variants,'profiles':results,'branches':branches,'coverage_count':len(coverage),'expected_choices':sum(len(x[2]) for x in SCENES.values()),'supplemental_walks':[{'seed':w.state.seed,'trace':w.trace,'reports':w.state.reports} for w in walks[len(PROFILES)*len(SEEDS):]],'limits':['Finite authored branch coverage, not all possible state combinations.','Browser and human review recorded separately.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='/private/tmp/ruler-acceptance.json');args=parser.parse_args()
    data=acceptance();Path(args.out).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(f'PASS {len(data["profiles"])} full games; {data["coverage_count"]}/{data["expected_choices"]} authored choices; saved {args.out}')
