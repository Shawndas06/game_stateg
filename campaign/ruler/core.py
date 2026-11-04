from __future__ import annotations

from collections import deque
from datetime import date, timedelta
from math import ceil, cos, hypot, radians
from copy import deepcopy
from typing import Any

from campaign.content import ADJACENCY, PLACE_INDEX, TROOPS
from campaign.engine import RuleError, require, rng as legacy_rng, route_kind
from campaign.ruler.models import Army, Cohort, RulerState

EPOCH = date(1299, 3, 1)


def calendar(s: RulerState) -> dict:
    d = EPOCH + timedelta(days=s.day)
    return {'date': d.isoformat(), 'year': d.year, 'month': d.month, 'day': d.day, 'season': ['Зима','Зима','Весна','Весна','Весна','Лето','Лето','Лето','Осень','Осень','Осень','Зима'][d.month-1]}


def uid(s: RulerState, prefix: str) -> str:
    s.counter += 1
    return f'{prefix}-{s.counter}'


def name(pid: str) -> str:
    return PLACE_INDEX[pid][1]


def count(cohorts: list[Cohort]) -> int:
    return sum(c.count for c in cohorts)


def troops(cohorts: list[Cohort]) -> dict[str, int]:
    return {t: sum(c.count for c in cohorts if c.troop == t) for t in TROOPS}


def selection(data: dict) -> dict[str, int]:
    require(isinstance(data, dict) and bool(data) and set(data) <= set(TROOPS), 'Укажите состав отряда')
    require(all(type(v) is int and 0 <= v <= 5000 for v in data.values()) and sum(data.values()) > 0, 'Укажите целое положительное число воинов')
    return data


def take(s: RulerState, source: list[Cohort], requested: dict[str, int]) -> list[Cohort]:
    selection(requested)
    require(all(troops(source).get(t, 0) >= n for t, n in requested.items()), 'В этом месте нет указанного числа воинов')
    result = []
    for tid, amount in requested.items():
        for c in list(source):
            if c.troop != tid or not amount: continue
            n = min(c.count, amount)
            if c.sponsor in s.people:
                require(not any(o['creditor']==c.sponsor and o['status'] in ['broken','repudiated'] for o in s.obligations.values()),'Люди предоставившего отряд бея требуют урегулировать условия службы')
            if n == c.count:
                source.remove(c); result.append(c)
            else:
                c.count -= n
                result.append(Cohort(uid(s,'cohort'), tid, n, c.origin, c.sponsor, c.service, c.training))
            amount -= n
    return result


def losses(cohorts: list[Cohort], amount: int) -> int:
    amount = min(count(cohorts), max(0, amount)); total = count(cohorts)
    allocation = {c.id: c.count * amount // max(1,total) for c in cohorts}
    remaining = amount-sum(allocation.values())
    for c in sorted(cohorts,key=lambda c: (-(c.count*amount % max(1,total)),c.id)):
        if remaining and allocation[c.id] < c.count: allocation[c.id] += 1; remaining -= 1
    for c in cohorts: c.count -= allocation[c.id]
    cohorts[:] = [c for c in cohorts if c.count]
    return amount


def roll(s: RulerState, key: str) -> float:
    import hashlib, random
    return random.Random(int.from_bytes(hashlib.sha256(f'{s.seed}:{s.day}:{key}'.encode()).digest()[:8],'big')).random()


def record(s: RulerState, text: str, kind: str = 'report', source: str = 'Писец', observed: int | None = None) -> None:
    s.archive_seq += 1
    item = {'seq':s.archive_seq,'day':s.day,'date':calendar(s)['date'],'kind':kind,'source':source,'text':text,'observed_day':s.day if observed is None else observed}
    s.outbox.append(item)
    s.reports.append(item)
    s.reports[:] = s.reports[-18:]


def spend(s: RulerState, gold: int) -> None:
    require(type(gold) is int and gold >= 0, 'Недопустимая сумма')
    require(s.gold >= gold, f'Казначей: требуется {gold}, свободно в казне {s.gold}.')
    s.gold -= gold


def owned(s: RulerState, pid: str, settled: bool = False):
    require(pid in s.places and s.places[pid].controller == 'ottoman', 'Это владение не под вашим контролем')
    p = s.places[pid]
    require(not settled or p.owner == 'ottoman', 'Сначала закрепите владение соглашением')
    return p


def own_army(s: RulerState, aid: str) -> Army:
    require(aid in s.armies and s.armies[aid].faction == 'ottoman', 'Армия не под вашим командованием')
    return s.armies[aid]


def ruler_location(s: RulerState) -> str:
    ruler=s.people[s.ruler_id]
    if ruler.status in ['captured','dead']:
        regent=s.people.get(s.regent)
        return regent.location if regent and regent.status=='active' else s.capital
    return ruler.location


def war(s: RulerState, a: str, b: str) -> bool:
    if s.rules_version>=5:
        from campaign.ruler.diplomacy import root
        a,b=root(s,a),root(s,b)
    return a != b and s.relations.get(':'.join(sorted([a,b])),{}).get('status') == 'war'


def route(s: RulerState, start: str, target: str, faction: str = 'ottoman', area: list[str] | None = None, hostile_end: bool = True, military: bool = False) -> list[str] | None:
    if start == target: return []
    queue=deque([(start,[])]);seen={start}
    for_current = s.institutions.get('shipping',{}).get('status') == 'active'
    if faction=='ottoman' and s.rules_version>=5:
        from campaign.ruler import maritime
        if for_current and s.institutions['shipping'].get('maritime'):
            for_current=any(p.controller=='ottoman' and maritime.harbour(s,p.id) for p in s.places.values())
    if faction!='ottoman' and s.rules_version>=4:for_current=s.polities.get(faction).shipping if faction in s.polities else False
    while queue:
        current, path = queue.popleft()
        for n in ADJACENCY[current]:
            if n in seen or area is not None and n not in area: continue
            kind=route_kind(current,n)
            if kind!='land' and not for_current and not(kind=='ferry' and faction=='ottoman' and s.rules_version>=5 and maritime.navigation(s)):continue
            controller=s.places[n].controller
            access=s.relations.get(':'.join(sorted([faction,controller])),{}).get('access_until',0)>s.day and not war(s,faction,controller)
            if s.rules_version>=5:
                from campaign.ruler.diplomacy import access as treaty_access
                access=access or treaty_access(s,faction,controller)
            allowed=controller==faction or access or (war(s,faction,controller) if military else not war(s,faction,controller))
            if n==target and hostile_end: allowed=True
            if not allowed: continue
            if n==target:return path+[n]
            seen.add(n);queue.append((n,path+[n]))
    return None


def duration(a: str, b: str, courier: bool = False) -> int:
    p,q=PLACE_INDEX[a],PLACE_INDEX[b]
    km=hypot((p[2]-q[2])*111*cos(radians((p[3]+q[3])/2)),(p[3]-q[3])*111)
    return max(1,ceil(km*(1.2 if route_kind(a,b)=='land' else 1)/(65 if courier else 22)))


def delivery_days(start: str, path: list[str], courier: bool = True) -> int:
    total=0
    for p in path:total+=duration(start,p,courier);start=p
    return total


def learn(s: RulerState, pid: str, source: str, at: int | None = None) -> None:
    p=s.places[pid]
    s.knowledge[pid]={'controller':p.controller,'owner':p.owner,'garrison':troops(p.garrison),'walls':p.walls,'grain':p.grain if p.controller=='ottoman' else None,'day':s.day if at is None else at,'source':source}


def observation(s: RulerState, pid: str, source: str = 'Донесение') -> None:
    # A dispatch carries the observation made at departure, not tomorrow's truth.
    p=s.places[pid]
    snapshot={'controller':p.controller,'owner':p.owner,'garrison':troops(p.garrison),'walls':p.walls,'grain':p.grain if p.controller=='ottoman' else None,'day':s.day,'source':source,'armies':[{'id':a.id,'size':a.size,'grain':a.grain,'commander':a.commander} for a in s.armies.values() if a.faction=='ottoman' and a.location==pid]}
    path=route(s,pid,ruler_location(s), hostile_end=False)
    if path is not None:
        s.couriers.append({'id':uid(s,'dispatch'),'kind':'observation','snapshot':snapshot,'province':pid,'location':pid,'path':path,'left':0})


def all_cohorts(s: RulerState):
    for p in s.places.values(): yield from p.garrison
    for a in s.armies.values(): yield from a.cohorts
    for c in s.transports.values():
        yield from [Cohort(**x) for x in c.get('escorts',[])]


def effective_power(s: RulerState, a: Army) -> float:
    skill=s.people[a.commander].skills['command'] if a.commander in s.people else 15
    return sum(c.count*TROOPS[c.troop]['power']*(1+c.training/500) for c in a.cohorts)*max(.25,a.morale/100)*(1+skill/200)*(1 if a.grain>0 else .45)


def free_officer(s: RulerState, pid: str, location: str, excluding: str | None = None) -> None:
    require(pid in s.people and s.people[pid].faction=='ottoman' and s.people[pid].status=='active' and s.people[pid].health>30,'Этот человек сейчас не может принять командование')
    require(s.people[pid].location==location and not s.people[pid].travel,'Командующий должен прибыть к войску')
    require(not any(a.id!=excluding and a.size and pid in [a.commander,a.deputy] for a in s.armies.values()),'Этот человек уже находится при другой армии')
    if s.rules_version>=5:
        from campaign.ruler.knowledge import busy
        require(not busy(s,pid),'Этот человек руководит работами; сначала освободите его от прежнего поручения')
