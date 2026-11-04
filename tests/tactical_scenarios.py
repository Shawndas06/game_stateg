"""Reach field battles through legal movement, then exercise every battle exit."""
import json
from pathlib import Path
from campaign.ruler.engine import new_campaign, apply_command, view
from campaign.ruler.models import RulerState


def encounter(seed=11,target='bilecik',split=False):
    s=new_campaign(seed,extended=True);trace=[]
    def act(kind,payload=None):
        nonlocal s
        payload=payload or {};s=apply_command(s,kind,payload);trace.append({'kind':kind,'payload':payload})
    act('begin_reign');act('tactical_mode',{'enabled':True})
    act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35}})
    if split:
        act('split_army',{'army':'ottoman-1','commander':'orhan','troops':{'militia':20}})
    for a in list(s.armies.values()):
        if a.faction=='ottoman':act('mission',{'army':a.id,'target':target,'purpose':'conquer','funds':15,'allow_assault':True,'allow_requisition':True})
    for _ in range(160):
        if s.flags.get('battle'):return s,trace
        assert not s.ending and s.people[s.ruler_id].status=='active'
        act('advance',{'days':1})
    raise AssertionError('No legal battle reached')


def resolve(s,mode):
    start=s.day;trace=[]
    for _ in range(9):
        b=s.flags.get('battle')
        if not b:break
        kind={'delegate':'battle_delegate','retreat':'battle_retreat'}.get(mode,'battle_step')
        payload={'battle':b['id']}
        if mode=='maneuver':
            u=next(u for u in view(s)['battle']['units'] if u['side']==b['player_side'] and u['count'])
            order={'unit':u['id'],'battle':b['id'],**({'lane':'reserve'} if b['phase']=='deploy' else {'order':'advance' if u['lane']=='reserve' else 'left'})}
            s=apply_command(s,'battle_deploy',order);trace.append({'kind':'battle_deploy','payload':order})
        s=apply_command(s,kind,payload);trace.append({'kind':kind,'payload':payload})
        s=RulerState.from_dict(s.to_dict());assert s.day==start
    assert not s.flags.get('battle')
    return s,trace


def main():
    results=[]
    for seed,target,split in [(11,'bilecik',False),(11,'bursa',False),(29,'bilecik',True)]:
        prefix,path=encounter(seed,target,split)
        for mode in ['hold','maneuver','delegate','retreat']:
            s,trace=resolve(prefix,mode)
            if s.people[s.ruler_id].status=='dead':
                agenda=next(a for a in s.agendas if a['scene']=='succession')
                s=apply_command(s,'decide',{'agenda':agenda['id'],'choice':view(s)['council']['choices'][0]['id']})
            s=apply_command(s,'tactical_mode',{'enabled':False})
            if not s.ending:s=apply_command(s,'advance',{'days':7})
            results.append({'seed':seed,'target':target,'split':split,'mode':mode,'prefix':prefix.to_dict(),'trace':path+trace,'after':s.to_dict()})
    Path('/tmp/tactical-acceptance.json').write_text(json.dumps(results,ensure_ascii=False))
    print(f'PASS {len(results)} lawful field battle walks: two locations, allied armies, hold/maneuver/delegate/retreat, reload and campaign continuation')


if __name__=='__main__':main()
