"""Seeded legal campaign walks and continuations of reached new petitions."""
import json
from pathlib import Path
from campaign.engine import RuleError
from campaign.ruler.engine import new_campaign, apply_command, validate
from campaign.ruler.models import RulerState
from campaign.ruler.story import SCENES, choices as available_choices
from campaign.ruler.chronicle import SCENES as NEW_SCENES
from ruler_scenarios import PREFERRED


def run(seed,style,days=3650):
    s=new_campaign(seed,extended=True);trace=[];prefixes={}
    def act(kind,payload):
        nonlocal s
        try:s=apply_command(s,kind,payload)
        except RuleError:return False
        trace.append({'day':s.day,'kind':kind,'payload':payload});validate(s)
        return True
    for pid in ['domanic','inonu']:
        if style!='idle':act('raise',{'province':pid,'troop':'militia','count':20})
    if style=='war':act('raise',{'province':'sogut','troop':'militia','count':40})
    acted=False;access=False
    for step in range(max(2000,days*2)):
        if s.ending or s.day>=days:break
        for agenda in list(s.agendas):
            scene=agenda['scene'];prefixes.setdefault(scene,s.to_dict())
            if style=='idle' and scene!='succession':continue
            preferred=PREFERRED.get(scene)
            if style=='war' and scene in ['frontier_letter','border_proposal']:preferred='refuse' if scene=='frontier_letter' else 'prepare'
            choices=[c for c,_ in available_choices(s,scene)]
            if preferred in choices:choices.remove(preferred);choices.insert(0,preferred)
            for c in choices:
                if act('decide',{'agenda':agenda['id'],'choice':c}):break
        if style=='diplomatic':
            from campaign.ruler.civil import INSTITUTIONS
            for iid in ['scribes','land_register','builders']:
                item=INSTITUTIONS[iid]
                if iid not in s.institutions and s.gold>=item['cost'] and all(s.institutions.get(k,{}).get('status')=='active' for k in item['requires']):act('institution',{'institution':iid});break
        if style=='diplomatic' and s.day>=31 and s.gold>=30 and s.relations['byzantine:ottoman'].get('access_until',0)<s.day+90 and not any(c['kind']=='access' for c in s.couriers):
            access=act('diplomacy',{'target':'byzantine','proposal':'access'})
        if s.day>=65 and style=='diplomatic' and (not s.armies['ottoman-1'].mission or s.armies['ottoman-1'].mission['status']!='active') and not any(c['kind']=='order' for c in s.couriers) and s.relations['byzantine:ottoman'].get('access_until',0)>s.day:
            acted=act('mission',{'army':'ottoman-1','purpose':'cover','target':'domanic','funds':0})
        if not acted and style=='war' and s.day>=35:
            acted=act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':40}})
        if s.people[s.ruler_id].status=='dead':break
        if not act('advance',{'days':90}):break
        if step%19==0:s=RulerState.from_dict(s.to_dict())
    assert s.day>=days or s.ending,(seed,style,s.day,'stalled')
    return {'seed':seed,'style':style,'day':s.day,'chapter':s.flags.get('chapter',1),'ending':s.ending,'holdings':sum(p.controller=='ottoman' for p in s.places.values()),'trace':trace,'snapshot':s.to_dict()},prefixes


def main():
    results=[];prefixes={}
    for seed in [11,29,73]:
        for style in ['diplomatic','war','idle']:
            result,reached=run(seed,style);results.append(result);prefixes.update({k:v for k,v in reached.items() if k not in prefixes})
            print('PASS',seed,style,'day',result['day'],'chapter',result['chapter'],'holdings',result['holdings'],'ending',bool(result['ending']),flush=True)
    result,reached=run(11,'diplomatic',7300);results.append(result)
    assert result['day']>=7300 and result['ending'] is None and result['chapter']>=3, 'Viable diplomatic continuation regressed'
    assert sum(r['ending'] is not None for r in results if r['style']=='idle')>=2, 'Unattended frontier no longer produces a consequence'
    prefixes.update({k:v for k,v in reached.items() if k not in prefixes})
    print('PASS extended horizon',result['day'],'chapter',result['chapter'],'ending',bool(result['ending']),flush=True)
    branches=[]
    for scene,prefix in prefixes.items():
        if scene not in NEW_SCENES:continue
        for choice,_ in NEW_SCENES[scene][2]:
            s=RulerState.from_dict(prefix);agenda=next(a for a in s.agendas if a['scene']==scene);before=s.to_dict()
            try:
                after=apply_command(s,'decide',{'agenda':agenda['id'],'choice':choice})
                validate(after);RulerState.from_dict(after.to_dict());outcome='executed'
            except RuleError as e:
                assert s.to_dict()==before;outcome='rejected: '+str(e)
            branches.append({'scene':scene,'choice':choice,'seed':s.seed,'day':s.day,'outcome':outcome,'prefix_snapshot':prefix})
    data={'games':results,'new_branches':branches,'unreached':sorted(set(NEW_SCENES)-set(prefixes))}
    Path('/tmp/long-campaign-acceptance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print('Reached new scenes:',sorted(set(prefixes)&set(NEW_SCENES)),'unreached:',data['unreached'],flush=True)
    base=Path('/tmp/ruler-acceptance.json')
    if base.exists():
        combined=json.loads(base.read_text())
        combined['branches'] += [b for b in branches if b['outcome']=='executed']
        Path('/tmp/ruler-combined-acceptance.json').write_text(json.dumps(combined,ensure_ascii=False))


if __name__=='__main__':main()
