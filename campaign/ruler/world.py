"""Opponent budgets, local reconnaissance and bounded military plans.

The planner sees dated observations, not the player's remote armies or treasury.
All formations come from existing garrisons; training consumes local reserves.
"""
from math import ceil
from campaign.content import FACTIONS, TROOPS, ADJACENCY, PLACE_INDEX
from campaign.engine import relation_key, route_kind
from campaign.ruler.models import Army, Cohort, Person, Polity
from campaign.ruler.core import calendar, count, duration, effective_power, name, record, roll, route, take, troops, uid, war


def enable(s):
    s.schema_version=s.rules_version=4
    s.content_version='ruler-campaign-2'
    for fid in FACTIONS:
        places=[p for p in s.places.values() if p.controller==fid]
        if fid!='ottoman' and places:
            s.polities.setdefault(fid,Polity(doctrine='trade' if fid in ['venice','genoa','pisa'] else 'expansion' if sum(fid.encode())%3==0 else 'defense',shipping=sum(PLACE_INDEX[p.id][7] for p in places)>=2))


def harvest(s,p):
    capacity=max(1600,PLACE_INDEX[p.id][5]*32) if p.fortress_level else 2400
    return int(capacity*p.prosperity/65*max(.3,min(1,p.reserve/(80 if p.fortress_level else 60))))


def contacts(s):
    return sorted({'byzantine','germiyan'}|{s.places[n].controller for p in s.places.values() if p.controller=='ottoman' for n in ADJACENCY[p.id]}-{'ottoman'})


def _scout(s,fid,realm,places,armies):
    visible={p.id for p in places}|{a.location for a in armies}
    visible|={n for pid in list(visible) for n in ADJACENCY[pid] if route_kind(pid,n)=='land'}
    for pid in visible:
        p=s.places[pid]
        field=sum(effective_power(s,a) for a in s.armies.values() if a.size and a.location==pid and a.faction!=fid)
        realm.intelligence[pid]={'day':s.day,'controller':p.controller,'guards':count(p.garrison),'defense':sum(c.count*TROOPS[c.troop]['power'] for c in p.garrison),'walls':p.walls,'field':round(field)}


def _pay(s,fid,realm,places,armies):
    realm.income=sum(int((16 if p.fortress_level else 8)*p.prosperity/65*(1 if p.owner==fid else .5)) for p in places if p.id not in s.sieges)
    wages=sum(c.count*TROOPS[c.troop]['upkeep'] for p in places for c in p.garrison)+sum(c.count*TROOPS[c.troop]['upkeep'] for a in armies for c in a.cohorts)
    realm.expense=ceil(wages/10)+3*len(places)
    due=realm.expense+realm.arrears
    paid=min(realm.gold+realm.income,due)
    realm.gold+=realm.income-paid;realm.arrears=due-paid
    for a in armies:
        if realm.arrears:a.morale=max(10,a.morale-8)
    for p in places:
        if p.id not in s.sieges:p.grain+=int(harvest(s,p)*(.65 if calendar(s)['season']=='Зима' else 1))
    # Recruitment is a local queue, paid before its manpower leaves the reserve.
    frontier=[p for p in places if any(s.places[n].controller!=fid for n in ADJACENCY[p.id]) and p.id not in s.sieges]
    if frontier and realm.gold>=40 and not realm.arrears:
        p=min(frontier,key=lambda p:(count(p.garrison),p.id))
        limit=60 if any(war(s,fid,s.places[n].controller) for n in ADJACENCY[p.id]) else 40
        n=min(20,p.reserve,max(0,limit-count(p.garrison)-sum(t['count'] for t in p.training)))
        if p.grain<(count(p.garrison)+n)*30:n=0
        if n:
            realm.gold-=n*2;p.reserve-=n
            p.training.append({'id':uid(s,'cohort'),'troop':'militia','count':n,'origin':p.id,'ready':s.day+14})
    if len(armies)>=(min(8,max(2,len(places)//4)) if any(war(s,fid,p.controller) for p in s.places.values()) else 1) or realm.gold<realm.expense or realm.arrears:return
    for p in sorted(frontier,key=lambda p:-count(p.garrison)):
        n=min(troops(p.garrison)['militia'],50,max(0,count(p.garrison)-max(20,PLACE_INDEX[p.id][5]//2)))
        if n<15:continue
        units=take(s,p.garrison,{'militia':min(n,troops(p.garrison)['militia'])})
        ident=uid(s,'army');person=uid(s,'captain')
        skill=35+int(roll(s,'captain:'+fid)*20)
        s.people[person]=Person(person,'Командующий '+FACTIONS[fid],1299+s.day//365-35,p.id,'commander',skills={'command':skill,'stewardship':30,'siege':35,'logistics':40},faction=fid)
        s.armies[ident]=Army(ident,fid,p.id,units,person,grain=0)
        break


def _plan(s,fid,r,places,armies):
    fresh={pid:k for pid,k in r.intelligence.items() if s.day-k['day']<=45}
    threatened=[p for p in places if p.id in s.sieges and s.sieges[p.id]['faction']!=fid]
    if threatened:
        r.target=min(threatened,key=lambda p:p.id).id;r.rally=r.target;r.plan='relieve';return
    targets=[(pid,k) for pid,k in fresh.items() if war(s,fid,k['controller']) and any(s.places[n].controller==fid for n in ADJACENCY[pid])]
    own=sum(effective_power(s,a) for a in armies)
    possible=[(pid,k) for pid,k in targets if own>(k['defense']*(1+k['walls']/50)+k['field'])*(1.4 if r.doctrine=='defense' else 1.15)]
    if possible and not r.arrears and s.day>=90:
        pid,k=min(possible,key=lambda item:(item[1]['defense']*(1+item[1]['walls']/50)+item[1]['field'],-PLACE_INDEX[item[0]][5],item[0]))
        r.target=pid
        bases=[p for p in places if p.id in ADJACENCY[pid] and p.id not in s.sieges]
        r.rally=max(bases,key=lambda p:(p.grain,p.id)).id if bases else None;r.plan='attack'
    else:
        r.plan='guard';r.target=None
        fronts=[p for p in places if any(war(s,fid,s.places[n].controller) for n in ADJACENCY[p.id])]
        r.rally=max(fronts or places,key=lambda p:(p.grain,p.id)).id if places else None


def _politics(s,fid,r,places,armies):
    if s.day<365 or s.day-r.last_war<720 or r.arrears or not armies:return
    neighbors={s.places[n].controller for p in places for n in ADJACENCY[p.id]}-{fid}
    if any(war(s,fid,n) for n in neighbors):return
    power=sum(effective_power(s,a) for a in armies)
    for other in sorted(neighbors):
        rel=s.relations[relation_key(fid,other)]
        known=[k for k in r.intelligence.values() if k['controller']==other and s.day-k['day']<=45]
        resistance=min((k['defense']*(1+k['walls']/50)+k['field'] for k in known),default=float('inf'))
        if s.day>=rel.get('truce_until',0) and power>resistance*1.5 and roll(s,'opportunity:'+fid+':'+other)<(.08 if r.doctrine=='trade' else .22 if r.doctrine=='expansion' else .12):
            rel['status']='war';r.last_war=s.day
            if other=='ottoman':record(s,f'{FACTIONS[fid]} объявляет войну. Пограничные распорядители требуют сил для обороны.','diplomacy')
            break


def tick(s):
    if s.rules_version<4:return
    # Couriers carry foreign grain physically; capture transfers it to the place.
    for c in list(s.foreign_cargo):
        c['left']-=1
        if c['left']>0:continue
        if c['path']:c['location']=c['path'].pop(0)
        p=s.places[c['location']]
        if (p.controller!=c['faction'] and not any(a.faction==c['faction'] and a.size and a.location==p.id for a in s.armies.values())) or any(a.size and a.location==p.id and war(s,a.faction,c['faction']) for a in s.armies.values()):
            p.grain+=c['grain'];s.foreign_cargo.remove(c);continue
        if c['path']:c['left']=duration(p.id,c['path'][0]);continue
        a=s.armies.get(c['army'])
        if a and a.location==p.id and a.faction==c['faction']:a.grain+=c['grain']
        else:p.grain+=c['grain']
        s.foreign_cargo.remove(c)
    for p in s.places.values():
        if p.controller!='ottoman' and p.id not in s.sieges:
            needed=count(p.garrison);used=min(needed,p.grain);p.grain-=used
            if used<needed and s.day%14==0:
                from campaign.ruler.core import losses
                losses(p.garrison,max(1,needed//40))
        if s.day%90==0 and p.id not in s.sieges:
            p.reserve=min(100,p.reserve+1)
            # Granaries slow spoilage; hoarding cannot eliminate logistics forever.
            cap=max(6000,harvest(s,p)*4)
            if p.grain>cap:p.grain-=ceil((p.grain-cap)*(.01 if 'granary' in p.buildings else .03))
    for fid,r in s.polities.items():
        places=[p for p in s.places.values() if p.controller==fid]
        armies=[a for a in s.armies.values() if a.faction==fid and a.size]
        if not places:continue
        if s.day%7==0:_scout(s,fid,r,places,armies);_plan(s,fid,r,places,armies)
        if s.day%30==0:_pay(s,fid,r,places,armies)
        if s.day%180==0:_politics(s,fid,r,places,armies)


def order(s,a):
    r=s.polities[a.faction]
    if not a.size or a.travel:return
    here=s.places[a.location]
    known=r.intelligence.get(a.location,{})
    exhausted=a.grain<a.size*5 or a.morale<45 or known.get('field',0)>effective_power(s,a)*1.6
    if a.location in s.sieges and not exhausted:
        sg=s.sieges[a.location]
        force=sum(effective_power(s,b) for b in s.armies.values() if b.id in sg['armies'])
        if a.mission and force>known.get('defense',800)*(1+known.get('walls',100)/50)*1.3:a.mission['status']='active'
        return
    dest=r.rally
    if r.plan=='relieve':dest=r.target
    elif r.plan=='attack' and not exhausted:
        assembled=[b for b in s.armies.values() if b.faction==a.faction and b.size and b.location==a.location and not b.travel]
        k=r.intelligence.get(r.target,{})
        defense=k.get('defense',800)*(1+k.get('walls',100)/50)+k.get('field',0)
        if sum(effective_power(s,b) for b in assembled)>defense*1.15 and a.grain>=a.size*14:dest=r.target
    if exhausted:
        homes=[(route(s,a.location,p.id,a.faction,military=True),p.id) for p in s.places.values() if p.controller==a.faction and p.id not in s.sieges and p.grain>(count(p.garrison)+a.size)*14]
        homes=[(path,pid) for path,pid in homes if path is not None]
        dest=min(homes,key=lambda x:(len(x[0]),x[1]))[1] if homes else None
    if dest and dest!=a.location:
        path=route(s,a.location,dest,a.faction,military=True)
        if path:
            fee=(0 if route_kind(a.location,path[0])=='land' else (10 if route_kind(a.location,path[0])=='ferry' else 20)*ceil(a.size/100))
            if r.gold<fee:return
            r.gold-=fee;a.travel={'path':[path[0]],'left':duration(a.location,path[0])}
            a.mission={'purpose':'conquer' if dest==r.target and r.plan=='attack' else 'return','target':dest,'status':'active','deadline':s.day+180,'allow_assault':r.plan=='attack','spent':0}
    if a.grain<a.size*14 and not any(c['army']==a.id for c in s.foreign_cargo) and r.gold>=5:
        sources=[p for p in s.places.values() if p.controller==a.faction and p.grain>(count(p.garrison)+a.size)*30 and p.id not in s.sieges]
        for p in sorted(sources,key=lambda p:p.id):
            path=route(s,p.id,a.location,a.faction,military=True)
            if path is None or any(s.places[n].controller!=a.faction for n in path[:-1]):continue
            n=min(a.size*30,p.grain-count(p.garrison)*30);p.grain-=n;r.gold-=5
            s.foreign_cargo.append({'faction':a.faction,'army':a.id,'location':p.id,'grain':n,'path':path,'left':duration(p.id,path[0]) if path else 1})
            break


def accept_peace(s,fid,payment):
    r=s.polities[fid]
    known=sum(k['field'] for k in r.intelligence.values() if k['controller']=='ottoman' and s.day-k['day']<=45)
    own=sum(effective_power(s,a) for a in s.armies.values() if a.faction==fid and a.size)
    lost=sum(p.owner==fid and p.controller=='ottoman' for p in s.places.values())
    return r.arrears>0 or own<known*.8 or lost>=2 or payment>=max(40,ceil(own/2))
