"""Reach offensive and defensive sieges legally; no injected soldiers or scenes."""
import json
from pathlib import Path
from campaign.ruler.engine import new_campaign,apply_command,validate,view
from campaign.ruler.models import RulerState


def offensive(prepared=True):
    s=new_campaign(19,extended=True,living=True);trace=[]
    def act(kind,payload):
        nonlocal s
        s=apply_command(s,kind,payload);validate(s);s=RulerState.from_dict(s.to_dict());trace.append({'day':s.day,'kind':kind,'payload':payload})
    act('begin_reign',{});a=s.agendas[0];act('decide',{'agenda':a['id'],'choice':'stewardship'})
    master=next(m['id'] for m in view(s)['statecraft']['masters'] if 'mining' in m['knows'])
    act('hire_master',{'person':master,'province':'sogut'})
    if prepared:
        act('raise',{'province':'sogut','troop':'archers','count':20})
        while s.places['sogut'].training:act('advance',{'days':1})
        act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35,'archers':20}})
    act('mission',{'army':'ottoman-1','purpose':'conquer','target':'inegol','funds':20})
    for _ in range(90):
        act('advance',{'days':1})
        if 'inegol' in s.sieges and not s.people[master].travel:break
    assert 'inegol' in s.sieges and s.armies['ottoman-1'].location=='inegol'
    act('move_master',{'person':master,'province':'inegol'})
    while s.people[master].travel:act('advance',{'days':1})
    prefix=s.to_dict();results=[]
    for operation in ['search','tunnel']:
        s=RulerState.from_dict(prefix);owner=s.places['inegol'].controller;walls=s.places['inegol'].walls
        act('siege_operation',{'province':'inegol','person':master,'operation':operation})
        for _ in range(45):
            act('advance',{'days':1})
            w=list(s.flags['statecraft']['siege_work'].values())[-1]
            if w['status']!='active':break
        assert s.places['inegol'].controller==owner
        if prepared or operation=='search':
            assert w['status']=='completed',w
            if operation=='search':assert type(s.sieges['inegol']['passage_found']) is bool
            else:assert s.places['inegol'].walls<=max(0,walls-12)
        else:
            assert w['status']=='failed' and w['reason']=='siege_ended',w
            assert s.day<w['ready'] and 'inegol' not in s.sieges
            assert not any('подкоп повредил' in r['text'] for r in s.reports)
        results.append({'operation':operation,'day':s.day,'state':s.to_dict()})
    return {'seed':19,'trace':trace,'results':results,'prefix':prefix}


def defensive():
    s=new_campaign(11,extended=True,living=True);trace=[]
    def act(kind,payload):
        nonlocal s
        s=apply_command(s,kind,payload);validate(s);trace.append({'day':s.day,'kind':kind,'payload':payload})
    act('begin_reign',{});act('decide',{'agenda':s.agendas[0]['id'],'choice':'stewardship'})
    act('mission',{'army':'ottoman-1','purpose':'cover','target':'domanic','funds':0})
    for _ in range(360):
        act('advance',{'days':1})
        targets=[p for p,sg in s.sieges.items() if sg['faction']!='ottoman' and s.places[p].controller=='ottoman']
        if targets:break
        assert not s.ending and s.people[s.ruler_id].status!='dead'
    assert targets
    site=targets[0];before=sum(c.count for c in s.places[site].garrison)
    act('siege_operation',{'province':site,'operation':'sortie','count':min(10,before)})
    assert sum(c.count for c in s.places[site].garrison)<before
    return {'seed':11,'day':s.day,'trace':trace,'snapshot':s.to_dict()}


if __name__=='__main__':
    results={'offensive':offensive(),'interrupted':offensive(False),'defensive':defensive()}
    Path('/tmp/statecraft-sieges.json').write_text(json.dumps(results,ensure_ascii=False))
    print('PASS legal V5 siege chains: trained reinforcements sustain search/tunnel; defeated unprepared army interrupts work; defender reaches actual attack and sorties',flush=True)
