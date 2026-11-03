"""Lawful 1299 -> Murad walk and every choice from naturally reached scenes."""
import json
from pathlib import Path
from long_scenarios import run
from campaign.ruler import dynasty, story
from campaign.ruler.engine import apply_command, view
from campaign.ruler.models import RulerState


def verify(prefixes):
    checked=[]
    for scene,options in dynasty.SCENES.items():
        assert scene in prefixes,('unreached',scene)
        for choice,_ in options[2]:
            s=RulerState.from_dict(prefixes[scene])
            agenda=next(a for a in s.agendas if a['scene']==scene)
            cost=50 if scene=='murad_education' and choice!='defer' else 60 if scene=='murad_council' and choice in ['accounts','service'] else 0
            for _ in range(11):
                if s.gold>=cost:break
                s=apply_command(s,'advance',{'days':30,'until_event':False})
            result=apply_command(s,'decide',{'agenda':agenda['id'],'choice':choice})
            view(result)  # Validate public text, not just internal mutation.
            if scene=='murad_council' and choice=='service':
                oid=result.flags['murad_service'];before=result.gold
                result=apply_command(result,'fulfil',{'obligation':oid})
                assert result.gold==before-60 and result.obligations[oid]['status']=='fulfilled'
            if scene=='orhan_handover':assert result.ruler_id==('murad' if choice=='handover' else 'orhan')
            checked.append({'scene':scene,'choice':choice,'day':s.day})
    return checked


def main():
    result,prefixes=run(11,'diplomatic',27000)
    assert result['snapshot']['ruler_id']=='murad',result['ending']
    Path('/tmp/dynasty-prefixes.json').write_text(json.dumps(prefixes,ensure_ascii=False))
    Path('/tmp/dynasty-walk.json').write_text(json.dumps(result,ensure_ascii=False))
    checked=verify(prefixes)
    Path('/tmp/dynasty-acceptance.json').write_text(json.dumps({'walk':result,'branches':checked,'prefixes':{k:v for k,v in prefixes.items() if k in dynasty.SCENES}},ensure_ascii=False))
    print('PASS dynasty: lawful seed11 diplomatic walk, day',result['day'],'ruler Murad;',len(checked),'choices from reached scenes',flush=True)


if __name__=='__main__':main()
