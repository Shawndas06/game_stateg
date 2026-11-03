"""Real legal careers and post-campaign letters, with replayable prefixes."""
import json
from pathlib import Path
from campaign.engine import RuleError
from campaign.ruler import court
from campaign.ruler.engine import new_campaign,apply_command,validate
from campaign.ruler.models import RulerState
from campaign.ruler.story import SCENES
from ruler_scenarios import PREFERRED


def run(seed,career,war=False):
    s=new_campaign(seed,extended=True);trace=[];prefixes={}
    def act(kind,payload):
        nonlocal s
        before=s.to_dict()
        try:s=apply_command(s,kind,payload)
        except RuleError:
            assert s.to_dict()==before
            return False
        trace.append({'day':s.day,'kind':kind,'payload':payload});validate(s)
        return True
    if war:
        act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35}})
        act('appoint_commander',{'army':'ottoman-1','commander':'turgut'})
        act('mission',{'army':'ottoman-1','purpose':'conquer','target':'bilecik','funds':40,'allow_assault':True})
    preference={**PREFERRED,'orhan_trial':career,'orhan_account':'recognize','konur_word':'honour','konur_reply':'settle','turgut_men':'reward','turgut_reply':'hear'}
    if war:preference.update(frontier_letter='refuse',border_proposal='prepare',turgut_men='rest')
    for step in range(300):
        if s.ending or s.day>=450:break
        for agenda in list(s.agendas):
            scene=agenda['scene'];prefixes.setdefault(scene,s.to_dict())
            ids=[c for c,_ in SCENES[scene][2]];wanted=preference.get(scene)
            if wanted in ids:ids.remove(wanted);ids.insert(0,wanted)
            for choice in ids:
                if act('decide',{'agenda':agenda['id'],'choice':choice}):break
        if s.people[s.ruler_id].status=='dead' or not act('advance',{'days':30}):break
        if step%7==0:s=RulerState.from_dict(s.to_dict())
    return {'seed':seed,'career':career,'war':war,'day':s.day,'ending':s.ending,'trace':trace,'people':{pid:s.people[pid].history for pid in ['konur','orhan','turgut']},'deeds':s.flags.get('accomplishments',[])},prefixes


def main():
    runs=[];prefixes={}
    for seed in [11,29,73]:
        for career in ['govern','field','study']:
            r,p=run(seed,career);runs.append(r)
            for scene,s in p.items():prefixes.setdefault(scene,[]).append(s)
            print('PASS career',seed,career,'day',r['day'],'ending',bool(r['ending']),flush=True)
        r,p=run(seed,'govern',war=True);runs.append(r)
        for scene,s in p.items():prefixes.setdefault(scene,[]).append(s)
        print('PASS campaign return',seed,'day',r['day'],'ending',bool(r['ending']),flush=True)
    branches=[];missing=[]
    for scene,(_,_,choices) in court.SCENES.items():
        for choice,_ in choices:
            for snap in prefixes.get(scene,[]):
                s=RulerState.from_dict(snap);a=next(a for a in s.agendas if a['scene']==scene)
                try:after=apply_command(s,'decide',{'agenda':a['id'],'choice':choice})
                except RuleError:continue
                validate(after);RulerState.from_dict(after.to_dict())
                branches.append({'scene':scene,'choice':choice,'prefix_snapshot':snap});break
            else:missing.append(scene+'/'+choice)
    result={'runs':runs,'branches':branches,'unreached':missing}
    Path('/tmp/court-acceptance.json').write_text(json.dumps(result,ensure_ascii=False))
    print('Personal branches',len(branches),'/',sum(len(v[2]) for v in court.SCENES.values()),'; unreached',missing,flush=True)
    assert not missing,missing
    base=Path('/tmp/ruler-acceptance.json')
    if base.exists():
        combined=json.loads(base.read_text());combined['branches']+=branches
        Path('/tmp/court-browser-acceptance.json').write_text(json.dumps(combined,ensure_ascii=False))


if __name__=='__main__':main()
