"""Paused field engagements. Units reference real cohorts, never copied soldiers."""
from math import ceil
from campaign.content import TROOPS
from campaign.engine import require
from campaign.ruler.core import effective_power, losses, name, record, route, duration, uid

LANES = ('left', 'center', 'right', 'reserve')
ORDERS = ('hold', 'advance', 'left', 'center', 'right', 'reserve')


def begin(s, province, attackers, defenders):
    if not s.flags.get('tactical_mode'): return False
    factions={a.faction for a in defenders}
    present=[a for a in s.armies.values() if a.location==province and a.size and not(a.travel and a.travel.get('retreat'))]
    attackers=[a for a in present if a.faction==attackers[0].faction]
    defenders=[a for a in present if a.faction in factions]
    if not any(a.commander==s.ruler_id and a.faction=='ottoman' for a in attackers+defenders): return False
    if s.people[s.ruler_id].status!='active' or s.people[s.ruler_id].location!=province: return False
    units=[]
    for side,group in [('attack',attackers),('defend',defenders)]:
        for a in group:
            for troop in sorted({c.troop for c in a.cohorts}):
                units.append({'id':a.id+':'+troop,'army':a.id,'troop':troop,'side':side,
                              'lane':'right' if troop=='cavalry' else 'center','order':'hold',
                              'initial':sum(c.count for c in a.cohorts if c.troop==troop)})
    terrain=('plain','woods','hill')[sum(province.encode())%3]
    s.flags['battle']={'id':uid(s,'battle'),'province':province,'round':0,'phase':'deploy',
                       'player_side':'attack' if any(a.faction=='ottoman' for a in attackers) else 'defend',
                       'terrain':terrain,'units':units,'log':['Войска встретились. Расставьте отряды или передайте бой командующему.']}
    record(s,f'У {name(province)} предстоит полевое сражение. Правитель принимает командование; календарь остановлен.','battle')
    return True


def count(s,u):
    return sum(c.count for c in s.armies[u['army']].cohorts if c.troop==u['troop'])


def public(s):
    b=s.flags.get('battle')
    if not b:return None
    return {k:v for k,v in b.items() if k!='units'} | {'units':[
        {k:v for k,v in u.items() if k!='order'} | {'count':count(s,u),
         'order':u['order'] if u['side']==b['player_side'] else None,
         'commander':s.people[s.armies[u['army']].commander].name if s.armies[u['army']].commander in s.people else 'Походный отряд',
         'name':TROOPS[u['troop']]['name']} for u in b['units']]}


def power(s,u,b):
    a=s.armies[u['army']]
    weight=sum(c.count*TROOPS[c.troop]['power'] for c in a.cohorts)
    result=effective_power(s,a)*count(s,u)*TROOPS[u['troop']]['power']/max(1,weight)
    if u['troop']=='cavalry' and b['terrain']=='woods':result*=.65
    if u['side']=='defend' and b['terrain']=='hill' and u['order']=='hold':result*=1.2
    return result


def aftermath(s,b,won):
    """Field victory is not fortress capture. Rejoin the existing siege system."""
    from campaign.ruler import military
    pid=b['province'];p=s.places[pid]
    winners=[s.armies[i] for i in dict.fromkeys(u['army'] for u in b['units'] if u['side']==won)]
    winners=[a for a in winners if a.size and not (a.travel and a.travel.get('retreat'))]
    if not winners:return
    actor=winners[0].faction
    if p.controller==actor:return
    from campaign.ruler.core import war
    if not war(s,actor,p.controller):return
    if not p.walls and sum(effective_power(s,a) for a in winners)>sum(c.count*TROOPS[c.troop]['power'] for c in p.garrison)*1.5:
        military.occupy(s,pid,winners)
    else:
        sg=s.sieges.setdefault(pid,{'province':pid,'faction':actor,'armies':[],'supplies':max(1,p.grain),'morale':90,'started':s.day})
        if sg['faction']==actor:
            for a in winners:
                a.travel=None
                if a.id not in sg['armies']:sg['armies'].append(a.id)


def finish(s,won):
    from campaign.ruler import military
    b=s.flags.pop('battle')
    if s.rules_version>=5:
        from campaign.ruler.diplomacy import field_result
        field_result(s,[s.armies[aid] for aid in dict.fromkeys(u['army'] for u in b['units'] if u['side']!=won)])
    for aid in dict.fromkeys(u['army'] for u in b['units']):
        a=s.armies[aid];side=next(u['side'] for u in b['units'] if u['army']==aid)
        military._risk(s,a,1,'field')
        if a.commander in s.people:
            person=s.people[a.commander];person.experience['battle']=person.experience.get('battle',0)+1
            person.skills['command']=min(90,person.skills['command']+1)
        if side==won:continue
        a.morale=max(10,a.morale-15);a.travel=None
        paths=[path for p in s.places.values() if p.controller==a.faction and p.id!=a.location
               if (path:=route(s,a.location,p.id,a.faction,hostile_end=False))]
        if a.size and paths:
            path=min(paths,key=lambda p:(len(p),p));a.travel={'path':path,'left':duration(a.location,path[0]),'retreat':True}
        elif a.size:
            losses(a.cohorts,a.size)
            record(s,'Отступающие не нашли пути отхода; оставшиеся воины выбыли из армии.','battle')
        if a.mission:a.mission['status']='awaiting'
    aftermath(s,b,won)
    record(s,f'Сражение у {name(b["province"])} завершено: '+('ваши войска удержали поле.' if won==b['player_side'] else 'ваши войска отступили.')+' Потери внесены в походные ведомости.','battle')


def command(s,kind,d):
    if kind=='tactical_mode':
        require(type(d.get('enabled')) is bool,'Выберите способ управления боем')
        require(not s.flags.get('battle'),'Сначала завершите текущий бой')
        s.flags['tactical_mode']=d['enabled'];return True
    if not kind.startswith('battle_'):return False
    b=s.flags.get('battle');require(b is not None,'Сейчас нет полевого сражения')
    require(d.get('battle')==b['id'],'Это распоряжение относится к другому сражению')
    if kind=='battle_deploy':
        u=next((u for u in b['units'] if u['id']==d.get('unit')),None)
        require(u is not None and u['side']==b['player_side'] and count(s,u)>0,'Этот отряд недоступен')
        if b['phase']=='deploy':
            require(d.get('lane') in LANES,'Выберите участок поля');u['lane']=d['lane']
        else:
            require(d.get('order') in ORDERS,'Неизвестный приказ');u['order']=d['order']
    elif kind=='battle_retreat':
        for a in {u['army'] for u in b['units'] if u['side']==b['player_side']}:
            losses(s.armies[a].cohorts,ceil(s.armies[a].size*.08))
        finish(s,'defend' if b['player_side']=='attack' else 'attack')
    elif kind=='battle_delegate':
        from campaign.ruler.military import _battle
        groups=[[s.armies[i] for i in dict.fromkeys(u['army'] for u in b['units'] if u['side']==side)] for side in ['attack','defend']]
        s.flags.pop('battle');won='attack' if _battle(s,b['province'],*groups,automatic=True) else 'defend'
        aftermath(s,b,won)
    elif kind=='battle_step':
        orders=d.get('orders',[])
        require(isinstance(orders,list) and len(orders)<=len(b['units']),'Неверная ведомость приказов')
        seen=set();prepared=[]
        for item in orders:
            require(isinstance(item,dict),'Неверный приказ отряду')
            u=next((u for u in b['units'] if u['id']==item.get('unit')),None)
            require(u is not None and u['side']==b['player_side'] and count(s,u)>0 and u['id'] not in seen,'Отряд недоступен или указан дважды')
            key='lane' if b['phase']=='deploy' else 'order';value=item.get(key)
            require(value in (LANES if key=='lane' else ORDERS),'Неизвестное распоряжение отряду')
            seen.add(u['id']);prepared.append((u,key,value))
        for u,key,value in prepared:u[key]=value
        b['phase']='combat';b['round']+=1
        alive=[u for u in b['units'] if count(s,u)>0]
        # Enemy orders depend on visible deployment, not hidden future player choices.
        for u in alive:
            if u['side']!=b['player_side']:
                u['order']='advance'
                if u['troop']=='cavalry':
                    u['order']='hold' if b['terrain']=='woods' else min(('left','right'),key=lambda lane:sum(count(s,x) for x in alive if x['side']!=u['side'] and x['lane']==lane))
                elif u['lane']=='reserve':
                    u['order']=min(('left','center','right'),key=lambda lane:sum(count(s,x) for x in alive if x['side']==u['side'] and x['lane']==lane))
                elif u['side']=='defend' and b['terrain']=='hill':u['order']='hold'
        movements=[]
        for u in alive:
            prior=u['lane']
            if u['order'] in LANES:u['lane']=u['order']
            elif u['order']=='advance' and u['lane']=='reserve':u['lane']='center'
            if prior!=u['lane']:movements.append(TROOPS[u['troop']]['name']+' — '+{'left':'левый фланг','center':'центр','right':'правый фланг','reserve':'резерв'}[u['lane']])
        damage={u['id']:0.0 for u in alive}
        for u in alive:
            if u['lane']=='reserve':continue
            enemies=[x for x in alive if x['side']!=u['side']]
            if not enemies:continue
            targets=[x for x in enemies if x['lane']==u['lane']] or [x for x in enemies if x['lane']!='reserve'] or enemies
            strength=power(s,u,b)*(.85 if u['order']=='hold' else 1.1)
            if not any(x['lane']==u['lane'] for x in enemies):strength*=1.2
            for target in targets:damage[target['id']]+=strength*.1/len(targets)/max(1,TROOPS[target['troop']]['power'])
        fallen={side:0 for side in ['attack','defend']}
        for u in alive:
            a=s.armies[u['army']];cohorts=[c for c in a.cohorts if c.troop==u['troop']]
            n=losses(cohorts,min(count(s,u),ceil(damage[u['id']])));a.cohorts[:]=[c for c in a.cohorts if c.count]
            fallen[u['side']]+=n
        message=f'Этап {b["round"]}: ваши потери {fallen[b["player_side"]]}, потери противника {fallen["defend" if b["player_side"]=="attack" else "attack"]}.'
        if movements:message+=' Перемещения: '+ '; '.join(movements)+'.'
        if b['terrain']=='woods' and any(u['troop']=='cavalry' and u['lane']!='reserve' for u in alive):message+=' Лес ограничивал действия конницы.'
        if b['terrain']=='hill' and any(u['side']=='defend' and u['order']=='hold' and u['lane']!='reserve' for u in alive):message+=' Защитникам помогала позиция на высоте.'
        b['log'].append(message);record(s,message,'battle')
        remaining={side:sum(count(s,u) for u in b['units'] if u['side']==side) for side in ['attack','defend']}
        routed=[side for side in remaining if remaining[side]<=sum(u['initial'] for u in b['units'] if u['side']==side)*.4]
        if routed or b['round']>=8:
            strength={side:sum(power(s,u,b)*(0 if u['lane']=='reserve' else 1) for u in b['units'] if u['side']==side) for side in remaining}
            won=('defend' if routed[0]=='attack' else 'attack') if len(routed)==1 else ('attack' if strength['attack']>strength['defend'] else 'defend')
            finish(s,won)
    else:require(False,'Неизвестное распоряжение в бою')
    return True
