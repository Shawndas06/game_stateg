"""Legal seeded V5 playthroughs, every reached choice, replayable action traces."""
import json
from pathlib import Path
from campaign.engine import RuleError
from campaign.ruler.engine import new_campaign,apply_command,view,validate
from campaign.ruler.models import RulerState
from campaign.ruler.story import choices
from ruler_scenarios import PREFERRED


def run(seed,style,horizon=1095):
    s=new_campaign(seed,extended=True,living=True);trace=[];prefixes={};rejections=[]
    def act(kind,payload):
        nonlocal s
        before=s.to_dict()
        try:s=apply_command(s,kind,payload)
        except RuleError as error:
            assert s.to_dict()==before;rejections.append({'day':s.day,'kind':kind,'reason':str(error)});return False
        validate(s);s=RulerState.from_dict(s.to_dict());trace.append({'day':s.day,'kind':kind,'payload':payload});return True
    act('begin_reign',{})
    master=view(s)['statecraft']['masters'][0]['id']
    if style=='craft':act('hire_master',{'person':master,'province':'sogut'})
    if style=='vassal':act('negotiate',{'target':'germiyan','proposal':'submit','tribute':5,'levy':20})
    elif style!='war':act('negotiate',{'target':'germiyan','proposal':'trade','payment':0})
    trained=False;planned=False
    for _ in range(2000):
        if s.ending or s.day>=horizon:break
        for agenda in list(s.agendas):
            prefixes.setdefault(agenda['scene'],s.to_dict())
            preferred=PREFERRED.get(agenda['scene']);variants=[c for c,_ in choices(s,agenda['scene'])]
            if preferred in variants:variants.remove(preferred);variants.insert(0,preferred)
            if style=='war' and agenda['scene']=='frontier_letter':variants=['refuse']+[c for c in variants if c!='refuse']
            for choice in variants:
                if act('decide',{'agenda':agenda['id'],'choice':choice}):break
        for offer in view(s)['statecraft']['offers']:
            if offer['b']=='ottoman' and offer['status']=='arrived':act('treaty_reply',{'offer':offer['id'],'accept':style!='war'})
        if style=='craft' and not trained and s.people[master].location=='sogut' and not s.people[master].travel and s.gold>=35:
            trained=act('learn_craft',{'province':'sogut','person':master,'tech':'carpentry'})
        if not planned and s.day>=30 and s.armies['ottoman-1'].size and not s.armies['ottoman-1'].travel:
            target='bilecik' if style=='war' else s.capital
            if act('plan_order',{'army':'ottoman-1','target':target,'purpose':'conquer' if style=='war' else 'cover','funds':0,'allow_assault':style=='war'}):planned=act('execute_plan',{})
        if s.people[s.ruler_id].status=='dead':
            assert any(a['scene']=='succession' for a in s.agendas);continue
        assert act('advance',{'days':90}),rejections[-1:]
    assert s.day>=horizon or s.ending,(seed,style,s.day)
    branches=[]
    for scene,prefix in prefixes.items():
        p=RulerState.from_dict(prefix);agenda=next(a for a in p.agendas if a['scene']==scene)
        for choice,_ in choices(p,scene):
            before=p.to_dict()
            try:n=apply_command(p,'decide',{'agenda':agenda['id'],'choice':choice});validate(n);outcome='executed'
            except RuleError as error:outcome='refused: '+str(error)
            assert p.to_dict()==before
            branches.append({'scene':scene,'choice':choice,'outcome':outcome,'day':p.day})
    return {'seed':seed,'style':style,'day':s.day,'ending':s.ending,'trace':trace,'rejections':rejections,'branches':branches,'snapshot':s.to_dict()}

if __name__=='__main__':
    results=[]
    for seed in [11,29,73]:
        for style in ['craft','diplomatic','war','vassal']:
            result=run(seed,style);results.append(result)
            print('PASS V5',seed,style,'day',result['day'],'ending',bool(result['ending']),'branches',len(result['branches']),flush=True)
    Path('/tmp/statecraft-acceptance.json').write_text(json.dumps({'games':results},ensure_ascii=False))
