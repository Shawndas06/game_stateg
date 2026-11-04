from __future__ import annotations

from math import ceil
from dataclasses import asdict
from campaign.content import ADJACENCY, PLACE_INDEX, TROOPS
from campaign.engine import require, route_kind
from campaign.ruler.models import Army, Cohort, RulerState
from campaign.ruler.core import *


def command(s: RulerState, kind: str, d: dict) -> bool:
    if kind in ['raise','demobilize'] and not d.get('_delivered'):
        from campaign.ruler.civil import dispatch_regional
        if dispatch_regional(s,kind,d):return True
    if kind=='raise':
        p=owned(s,str(d.get('province','')),True)
        require(p.id not in s.sieges,'Из осаждённого владения нельзя собрать новые силы')
        tid=d.get('troop');n=d.get('count')
        require(tid in TROOPS and type(n) is int and 1<=n<=40,'Набор: от 1 до 40 воинов известного рода')
        require(p.reserve>=n and not p.training,'Нет свободных людей или подготовка уже идёт')
        spend(s,n*TROOPS[tid]['cost']);p.reserve-=n
        p.training.append({'id':uid(s,'training'),'troop':tid,'count':n,'ready':s.day+{'militia':14,'archers':30,'cavalry':60}[tid],'origin':p.id})
        record(s,f'{name(p.id)}: начата подготовка {n} воинов. До окончания они остаются в учебном отряде.','recruitment')
    elif kind=='form_army':
        p=owned(s,str(d.get('province','')))
        require(p.id not in s.sieges,'В осаждённой крепости нельзя формировать походную армию')
        require(p.id==ruler_location(s),'Новый отряд формируют в присутствии правителя; удалённым армиям можно отправлять поручения')
        commander=str(d.get('commander',''));free_officer(s,commander,p.id)
        selected=selection(d.get('troops'));units=take(s,p.garrison,selected)
        aid=uid(s,'army');a=Army(aid,'ottoman',p.id,units,commander,grain=0,deputy_officer=f'Старший десятник отряда {aid}')
        s.armies[aid]=a
        if p.governor==commander:p.governor=None
        s.people[commander].role='commander'
        _load(s,a,p.id,min(p.grain,a.size*20))
        record(s,f'{s.people[commander].name} принял {a.size} воинов в {name(p.id)}. В гарнизоне осталось {count(p.garrison)}.','military')
    elif kind=='demobilize':
        p=owned(s,str(d.get('province','')),True)
        require(p.id not in s.sieges,'Нельзя распускать осаждённый гарнизон')
        units=take(s,p.garrison,selection(d.get('troops')))
        require(all(c.origin==p.id for c in units),'Эти люди должны вернуться в своё владение; сначала отправьте их домой')
        n=count(units);p.reserve+=n
        record(s,f'{name(p.id)}: {n} местных воинов отпущены со службы и вернулись к хозяйству.','demobilization')
    elif kind in ['transfer','split_army','merge_armies','lead','appoint_commander']:
        a=own_army(s,str(d.get('army','')))
        require(not a.travel and a.location==ruler_location(s),'Распределение войск и личное принятие командования требуют встречи с армией')
        require(a.location not in s.sieges,'Сначала закончите осаду или отведите войска')
        if kind=='transfer':
            p=owned(s,a.location);direction=d.get('direction')
            require(direction in ['to_army','to_garrison'],'Укажите направление передачи')
            target,source=(a.cohorts,p.garrison) if direction=='to_army' else (p.garrison,a.cohorts)
            moved=take(s,source,selection(d.get('troops')));target.extend(moved)
            record(s,f'{name(p.id)}: распределение сил изменено. В армии {a.size}, в гарнизоне {count(p.garrison)}.','military')
        elif kind=='split_army':
            commander=str(d.get('commander',''))
            require(commander!=a.commander,'Для отдельной армии нужен другой командующий')
            if a.deputy==commander:a.deputy=None
            free_officer(s,commander,a.location,a.id)
            selected=selection(d.get('troops'));before=a.size
            require(sum(selected.values())<before,'В исходной армии должен остаться хотя бы один воин; для полной передачи смените командующего')
            units=take(s,a.cohorts,selected);grain=a.grain*count(units)//before;a.grain-=grain
            aid=uid(s,'army');s.armies[aid]=Army(aid,a.faction,a.location,units,commander,grain=grain,deputy_officer=f'Старший десятник отряда {aid}')
            record(s,f'Армия разделена: {s.people[commander].name} получил {count(units)} воинов и часть обоза.','military')
        elif kind=='merge_armies':
            b=own_army(s,str(d.get('other','')))
            require(b.id!=a.id and not b.travel and b.location==a.location,'Армии должны встретиться для соединения')
            require(not any(x.get('army')==b.id and x['kind']=='order' for x in s.couriers),'Сначала отзовите приказ, находящийся в пути к присоединяемой армии')
            a.cohorts.extend(b.cohorts);a.grain+=b.grain;a.funds+=b.funds
            if b.commander in s.people:s.people[b.commander].role='officer'
            b.cohorts=[];del s.armies[b.id]
            record(s,f'Армии соединены в {name(a.location)}: {a.size} воинов.','military')
        else:
            commander=s.ruler_id if kind=='lead' else str(d.get('commander',''))
            p=s.people.get(commander)
            require(p is not None,'Выберите человека')
            # Release the chosen deputy slot before promotion, never another army.
            if a.deputy==commander:a.deputy=None
            free_officer(s,commander,a.location,a.id)
            old=a.commander;a.commander=commander
            if old in s.people and old!=commander:s.people[old].role='officer' if old!=s.ruler_id else 'ruler'
            p.role='ruler' if commander==s.ruler_id else 'commander'
            deputy=d.get('deputy')
            if deputy:
                require(deputy!=commander,'Командующий и заместитель должны быть разными людьми')
                free_officer(s,str(deputy),a.location,a.id);a.deputy=str(deputy)
            if kind=='lead':
                regent=str(d.get('regent',s.regent or ''))
                require(regent in s.people and s.people[regent].status=='active' and regent!=s.ruler_id and s.people[regent].location==s.capital,'Назначьте живого заместителя, находящегося в столице')
                s.regent=regent;a.posture=str(d.get('posture','rear'))
                require(a.posture in ['rear','field','assault'],'Неизвестное положение правителя')
            record(s,f'{p.name} принял командование армией {a.id}.','appointment')
    elif kind in ['mission','recall']:
        a=own_army(s,str(d.get('army','')))
        require(a.size>0,'В армии нет воинов')
        target=str(d.get('target',s.capital if kind=='recall' else ''))
        require(target in s.places,'Выберите существующую цель')
        purpose='return' if kind=='recall' else str(d.get('purpose','defend'))
        require(purpose in ['conquer','defend','relieve','cover','intercept','return'],'Неизвестная задача')
        area=d.get('area',[])
        require(isinstance(area,list) and all(isinstance(x,str) and x in s.places for x in area),'Укажите допустимые владения района')
        if not area:
            path=route(s,a.location,target,a.faction,military=True)
            require(path is not None,'Нет доступного маршрута; необходимы право прохода или перевозка')
            area=list(dict.fromkeys([a.location]+path+[n for p in path for n in ADJACENCY[p] if s.places[n].controller==a.faction]))
        require(a.location in area and target in area,'Армия и цель должны находиться в разрешённом районе')
        if purpose=='conquer':require(war(s,a.faction,s.places[target].controller),'Правитель должен сначала разрешить войну с владельцем цели')
        require(purpose not in ['defend','cover','return'] or s.places[target].controller==a.faction,'Для этой задачи нужно своё владение')
        days=d.get('days',180)
        require(type(days) is int and 30<=days<=720,'Срок поручения: от 30 до 720 дней')
        require(all(type(d.get(k,False)) is bool for k in ['allow_assault','allow_requisition']),'Разрешения должны быть логическими значениями')
        money=d.get('funds',0);require(type(money) is int and 0<=money<=5000,'Укажите допустимую сумму походной казны')
        spend(s,money)
        mandate={'id':uid(s,'mandate'),'purpose':purpose,'target':target,'area':area,'allow_assault':bool(d.get('allow_assault',False)),'allow_requisition':bool(d.get('allow_requisition',False)),'status':'issued','issued':s.day,'spent':0,'deadline':s.day+days,'funds':money}
        start=ruler_location(s);path=route(s,start,a.location,hostile_end=True)
        require(path is not None,'Гонец не может добраться до армии')
        # A later mandate supersedes undelivered orders and refunds their escrow.
        for item in list(s.couriers):
            if item['kind']=='order' and item['army']==a.id:
                s.gold+=item['mandate']['funds'];s.couriers.remove(item)
        if not path:deliver_order(s,a,mandate)
        else:s.couriers.append({'id':uid(s,'courier'),'kind':'order','army':a.id,'mandate':mandate,'location':start,'path':path,'left':0})
        record(s,f'Приказ: {purpose_label(purpose)} у {name(target)}. '+('Передан на месте.' if not path else 'Гонец отправлен к армии.'),'order')
    elif kind=='provision':
        a=own_army(s,str(d.get('army','')));p=owned(s,str(d.get('province','')))
        n=d.get('amount');require(type(n) is int and 1<=n<=10000 and p.grain>=n,'Недостаточно местного продовольствия')
        require(p.id not in s.sieges,'Осада прервала отправку обоза')
        path=route(s,p.id,a.location,hostile_end=True);require(path is not None,'Нет доступного пути для обоза')
        spend(s,5);p.grain-=n
        ident=uid(s,'transport');s.transports[ident]={'id':ident,'kind':'supply','location':p.id,'origin':p.id,'target':a.location,'army':a.id,'path':path,'left':0,'grain':n,'escorts':[],'status':'moving','created':s.day}
        record(s,f'{name(p.id)}: отправлен обоз с {n} пайками для армии.','supply')
    elif kind=='requisition':
        a=own_army(s,str(d.get('army','')))
        require(a.commander==s.ruler_id or a.mission and a.mission.get('allow_requisition'),'Реквизиция не разрешена поручением')
        p=s.places[a.location];n=d.get('amount')
        require(type(n) is int and 1<=n<=p.grain,'В поселении нет такого количества зерна')
        p.grain-=n;a.grain+=n;p.prosperity=max(0,p.prosperity-10);p.unrest+=10
        record(s,f'{name(p.id)}: в обоз изъято {n} пайков; жители подали жалобу на изъятие.','requisition')
    else:return False
    return True


def purpose_label(kind: str) -> str:
    return {'conquer':'завоевание','defend':'оборона','cover':'охрана дороги','relieve':'помощь осаждённым','intercept':'перехват','return':'возвращение'}[kind]


def deliver_order(s: RulerState,a: Army,m: dict) -> None:
    if a.mission and a.mission['status'] not in ['completed','failed','recalled']:a.mission['status']='recalled'
    s.gold+=a.funds;a.funds=m.pop('funds');a.mission=m;m['status']='active'
    record(s,f'{s.people[a.commander].name if a.commander else a.deputy_officer} получил приказ: {purpose_label(m["purpose"])} у {name(m["target"])}.','acknowledgement')


def _load(s: RulerState,a: Army,pid: str,n: int) -> None:
    p=s.places[pid];n=min(n,max(0,p.grain-count(p.garrison)*14));p.grain-=n;a.grain+=n


def repair_leadership(s: RulerState) -> None:
    from campaign.ruler.models import Person
    for a in s.armies.values():
        if not a.size:continue
        p=s.people.get(a.commander)
        if a.deputy in s.people and s.people[a.deputy].status not in ['active','wounded']:a.deputy=None
        if p and p.status=='active' and p.health>30:continue
        old=p.name if p else a.deputy_officer
        deputy=s.people.get(a.deputy)
        if deputy and deputy.status=='active' and deputy.location==a.location and deputy.health>30:
            a.commander=deputy.id;a.deputy=None;deputy.role='commander'
        else:
            ident=uid(s,'acting-officer')
            officer=Person(ident,a.deputy_officer or 'Старший походного отряда',calendar(s)['year']-30,a.location,'commander',skills={'command':15,'stewardship':15,'siege':10,'logistics':20},faction=a.faction)
            s.people[ident]=officer;a.commander=ident
        a.morale=max(10,a.morale-10)
        if a.faction=='ottoman':record(s,f'{old} выбыл. Войско сохранилось; управление принял {s.people[a.commander].name}.','command_change')


def _risk(s: RulerState,a: Army,intensity: float, context: str) -> None:
    for pid in [a.commander,a.deputy]:
        if pid not in s.people:continue
        person=s.people[pid]
        if person.status!='active':continue
        exposure=({'rear':.15,'field':.65,'assault':1.4}[a.posture] if pid==s.ruler_id else .65)*intensity
        r=roll(s,f'person:{pid}:{context}')
        if r<.025*exposure:
            person.status='dead';person.health=0
            if a.faction=='ottoman':record(s,f'{person.name} погиб в бою.','death')
        elif r<.07*exposure:
            person.status='captured'
            if a.faction=='ottoman':record(s,f'{person.name} оказался в плену. Двор получил требование о выкупе.','capture')
        elif r<.20*exposure:
            person.status='wounded';person.health=max(20,person.health-35);person.wounded_until=s.day+60
            if a.faction=='ottoman':record(s,f'{person.name} ранен и временно не может командовать.','wound')


def occupy(s: RulerState,pid: str,forces: list[Army]) -> None:
    p=s.places[pid];actor=forces[0].faction;old=p.controller;p.controller=actor
    p.reserve+=count(p.garrison)
    p.garrison=[];remaining=min(15,sum(a.size for a in forces)//5)
    for a in sorted(forces,key=lambda a:a.id):
        for tid,n in troops(a.cohorts).items():
            amount=min(n,remaining)
            if amount:p.garrison.extend(take(s,a.cohorts,{tid:amount}));remaining-=amount
    p.loyalty=35;p.occupied_since=s.day
    p.reserve+=sum(t['count'] for t in p.training)+(p.construction.get('workers',0) if p.construction else 0)
    p.construction=None;p.training=[]
    # People still in training return to the displaced population, not the victor's army.
    p.governor=None;p.audit=None;s.sieges.pop(pid,None)
    departing={x for a in s.armies.values() if a.travel and a.travel.get('retreat') for x in [a.commander,a.deputy] if x}
    for person in s.people.values():
        if person.location!=pid or person.travel or person.id in departing:continue
        if person.status=='captured' and person.faction==actor:
            person.status='wounded';person.health=max(40,person.health);person.wounded_until=s.day+30
            if 'ottoman' in [person.faction,actor]:record(s,f'{person.name} освобождён после возвращения {name(pid)}.','release')
        elif person.faction==old and person.status in ['active','wounded']:
            person.status='captured';record(s,f'{person.name} оказался в плену при падении {name(pid)}.','capture')
    if old=='ottoman' and s.capital==pid:
        seized=s.gold//2;s.gold-=seized;p.seized_gold+=seized
        homes=[x for x in s.places.values() if x.controller=='ottoman']
        if homes:
            home=max(homes,key=lambda x:(x.owner=='ottoman',x.walls,x.id));s.capital=home.id
            candidates=[x for x in s.people.values() if x.faction=='ottoman' and x.status=='active' and x.location==home.id]
            s.regent=candidates[0].id if candidates else None
        record(s,f'Ставка в {name(pid)} потеряна; в захваченных сундуках осталось {seized} монет. Дела переносятся в {name(s.capital)}.','capital_loss')
    if old=='ottoman' and actor!='ottoman':record(s,f'{name(pid)} потерян. Оставшиеся войска и распоряжения требуют пересмотра.','capture')
    if actor=='ottoman' and p.seized_gold:
        s.gold+=p.seized_gold;record(s,f'В возвращённом владении найдены казённые сундуки: {p.seized_gold} монет.','treasury');p.seized_gold=0
    for a in forces:
        if a.mission and a.mission['target']==pid:
            a.mission['status']='completed';s.gold+=a.funds if actor=='ottoman' else 0;a.funds=0
        if a.commander in s.people:s.people[a.commander].experience['siege']=s.people[a.commander].experience.get('siege',0)+1
    if actor=='ottoman':
        s.flags.setdefault('first_capture',pid);s.flags['capture_day']=s.day;observation(s,pid,'Донесение о занятии')
        record(s,f'{name(pid)} занят. Гарнизон выделен из походных частей. До соглашения прежний владелец сохраняет притязания.','capture')
    if not any(x.controller==old for x in s.places.values()):
        for x in s.places.values():
            if x.owner==old:x.owner=x.controller
        for key,t in s.relations.items():
            if old in key.split(':'):t['status']='peace'
        for a in s.armies.values():
            if a.faction==old:
                s.places[a.location].reserve+=a.size;s.places[a.location].grain+=a.grain;a.grain=0;a.cohorts=[];a.travel=None;a.mission=None


def _battle(s: RulerState,pid: str,attackers: list[Army],defenders: list[Army],automatic: bool=False) -> bool | None:
    from campaign.ruler import tactics
    if not automatic and tactics.begin(s,pid,attackers,defenders):return None
    ap=sum(effective_power(s,a) for a in attackers);dp=sum(effective_power(s,a) for a in defenders)
    success=ap>=dp
    for group,rate in [(attackers,.15 if success else .30),(defenders,.35 if success else .12)]:
        for a in group:
            n=losses(a.cohorts,ceil(a.size*rate));a.morale=max(10,a.morale-(5 if group is attackers and success else 12));_risk(s,a,1,'field')
            if a.commander in s.people:
                p=s.people[a.commander];p.experience['battle']=p.experience.get('battle',0)+1;p.skills['command']=min(90,p.skills['command']+1)
    losers=defenders if success else attackers
    for a in losers:
        paths=[path for p in s.places.values() if p.controller==a.faction and p.id!=pid
               if (path:=route(s,pid,p.id,a.faction,hostile_end=False))]
        a.location=pid;a.travel=None
        if paths:
            path=min(paths,key=len);a.travel={'path':path,'left':duration(pid,path[0]),'retreat':True}
        else:losses(a.cohorts,a.size)
        if a.mission:a.mission['status']='awaiting'
    if any(a.faction=='ottoman' for a in attackers+defenders):record(s,f'Полевое сражение у {name(pid)}: '+('наступающие удержали поле.' if success else 'наступление остановлено.'),'battle')
    return success


def tick(s: RulerState) -> None:
    repair_leadership(s)
    arrivals: dict[str,list[Army]]={}
    if s.flags.get('tactical_mode'):
        # An interrupted tick must not lose simultaneous encounters elsewhere.
        for a in s.armies.values():
            if a.size and not (a.travel and a.travel.get('retreat')) and any(e.size and e.location==a.location and war(s,a.faction,e.faction) and not(e.travel and e.travel.get('retreat')) for e in s.armies.values()):
                arrivals.setdefault(a.location,[]).append(a)
    engaged={a.id for group in arrivals.values() for a in group}
    for a in list(s.armies.values()):
        if not a.size:continue
        if a.travel and a.id not in engaged:
            a.travel['left']-=1
            if a.travel['left']>0:continue
            dest=a.travel['path'][0]
            require(dest in ADJACENCY[a.location],'Повреждён маршрут армии')
            if s.places[dest].controller!=a.faction and not war(s,a.faction,s.places[dest].controller) and not a.travel.get('civilian') and s.relations.get(':'.join(sorted([a.faction,s.places[dest].controller])),{}).get('access_until',0)<=s.day:
                a.travel=None
                if a.mission:a.mission['status']='awaiting'
                if a.faction=='ottoman':record(s,f'Армия остановлена: нет права входа в {name(dest)}.','obstruction')
                continue
            a.location=dest
            for pid in [a.commander,a.deputy]:
                if pid in s.people:s.people[pid].location=dest
            a.travel['path'].pop(0)
            if not a.travel['path']:
                a.travel=None
                if a.commander in s.people:
                    p=s.people[a.commander]
                    if 'march:'+dest not in p.memories:
                        p.memories.append('march:'+dest);p.experience['march']=p.experience.get('march',0)+1;p.skills['logistics']=min(90,p.skills['logistics']+1)
            else:a.travel['left']=duration(dest,a.travel['path'][0])
            if a.service_return and a.location=='karacahisar' and not a.travel:
                s.places[a.location].garrison.extend(a.cohorts);s.places[a.location].grain+=a.grain;a.cohorts=[];a.grain=0
                record(s,'Люди бея вернулись в Караджахисар; их прежнее походное поручение прекращено.','service')
            arrivals.setdefault(dest,[]).append(a)
        p=s.places[a.location]
        if not a.travel and p.controller==a.faction and p.id not in s.sieges:
            target=a.size*25
            if a.grain<target:_load(s,a,p.id,min(a.size*10,target-a.grain))
        ration=min(a.grain,a.size);a.grain-=ration
        if ration<a.size:
            a.morale=max(10,a.morale-1)
            if s.day%7==0:
                losses(a.cohorts,max(1,ceil(a.size*.03)))
                if a.faction=='ottoman':record(s,f'Армия у {name(a.location)} несёт потери без достаточного обоза.','supply')
        elif s.day%7==0:a.morale=min(100,a.morale+1)
    for pid,incoming in arrivals.items():
        resolved=set()
        present=[a for a in s.armies.values() if a.location==pid and a.size and not(a.travel and a.travel.get('retreat'))]
        sides=sorted({a.faction for a in incoming})
        for actor in sides:
            attackers=[a for a in incoming if a.faction==actor and a.size and not(a.travel and a.travel.get('retreat'))]
            enemies=[a for a in present if war(s,actor,a.faction) and a not in attackers and not(a.travel and a.travel.get('retreat')) and tuple(sorted([actor,a.faction])) not in resolved]
            for e in enemies:resolved.add(tuple(sorted([actor,e.faction])))
            if attackers and enemies:
                success=_battle(s,pid,attackers,enemies)
                if success is None:return
                if not success:continue
            if not attackers or any(a.travel and a.travel.get('retreat') for a in attackers):continue
            p=s.places[pid]
            if p.controller!=actor and war(s,actor,p.controller):
                if not p.walls and sum(effective_power(s,a) for a in attackers)>sum(c.count*TROOPS[c.troop]['power'] for c in p.garrison)*1.5:
                    occupy(s,pid,attackers)
                else:
                    siege=s.sieges.setdefault(pid,{'province':pid,'faction':actor,'armies':[],'supplies':max(1,p.grain),'morale':90,'started':s.day})
                    if siege['faction']==actor:
                        for a in attackers:
                            if a.id not in siege['armies']:siege['armies'].append(a.id)
            if actor=='ottoman':observation(s,pid,'Походное донесение')
    for pid,sg in list(s.sieges.items()):
        p=s.places[pid]
        sg['armies']=[aid for aid in sg['armies'] if aid in s.armies and s.armies[aid].size and s.armies[aid].location==pid and not s.armies[aid].travel]
        forces=[s.armies[x] for x in sg['armies']]
        if not forces or not war(s,sg['faction'],p.controller):del s.sieges[pid];continue
        defending_fields=[a for a in s.armies.values() if a.location==pid and a.size and a.faction==p.controller and not a.travel]
        if defending_fields:
            if _battle(s,pid,forces,defending_fields) is None:return
            sg['armies']=[a.id for a in forces if a.size and not a.travel]
            forces=[s.armies[x] for x in sg['armies']]
            if not forces:del s.sieges[pid];continue
        besiegers=sum(a.size for a in forces);guards=count(p.garrison)
        # A port can receive sea supply until a naval blockade exists.
        if PLACE_INDEX[pid][7] and s.day%7==0:p.grain+=max(guards*7,100)
        p.grain=max(0,p.grain-guards)
        if p.grain==0 and s.day%7==0:sg['morale']=max(0,sg['morale']-12)
        if s.day%7==0 and any(a.grain>0 for a in forces):
            skill=sum(s.people[a.commander].skills['siege']//25 if a.commander in s.people else 0 for a in forces)
            p.walls=max(0,p.walls-2-skill-sum(a.engines*3 for a in forces))
        for a in forces:
            if a.mission and s.day>a.mission['deadline']:
                a.mission['status']='awaiting'
        assault=[a for a in forces if a.mission and a.mission.get('allow_assault') and a.mission['status']=='active']
        if assault and s.day%14==0:
            attack=sum(effective_power(s,a) for a in forces);defense=sum(c.count*TROOPS[c.troop]['power'] for c in p.garrison)*(1+p.walls/50)*max(.3,sg['morale']/100)
            success=roll(s,f'assault:{pid}')<max(.08,min(.92,attack/max(1,attack+defense)))
            for a in forces:losses(a.cohorts,ceil(a.size*(.18 if success else .30)));_risk(s,a,1.5,'assault')
            losses(p.garrison,ceil(guards*(.7 if success else .15)))
            if sg['faction']=='ottoman':record(s,f'{name(pid)}: '+('штурм удался.' if success else 'штурм отбит; командующие запросили дальнейшее решение.'),'battle')
            if success and any(a.size for a in forces):occupy(s,pid,[a for a in forces if a.size]);continue
            for a in forces:
                if a.mission:a.mission['status']='awaiting'
        if guards==0 or sg['morale']==0:
            alive=[a for a in forces if a.size]
            if alive:occupy(s,pid,alive)
    cleanup(s)
    for a in list(s.armies.values()):
        if not a.size or a.travel:continue
        if a.faction!='ottoman':_npc(s,a);continue
        if a.mission and a.mission['status']=='active':_resupply(s,a)
        if a.location in s.sieges and a.id in s.sieges[a.location]['armies'] and (not a.mission or a.mission.get('purpose')!='return'):continue
        m=a.mission
        if not m or m['status']!='active':continue
        if s.day>m['deadline']:
            m['status']='awaiting';record(s,f'Срок поручения у {name(a.location)} истёк. Командующий ждёт решения.','obstruction');continue
        target=m['target']
        if a.location==target:
            if m['purpose']=='conquer' and s.places[target].controller!=a.faction and target in s.sieges:continue
            if m['purpose'] in ['defend','cover','intercept']:
                if a.location in s.hazards:
                    losses(a.cohorts,min(a.size,ceil(s.hazards.pop(a.location)/3)))
                    record(s,f'Дорога у {name(a.location)} очищена от разбойного отряда.','security')
                continue
            if m['purpose']=='relieve' and target in s.sieges:continue
            m['status']='completed';s.gold+=a.funds;a.funds=0
            record(s,f'Поручение выполнено: {purpose_label(m["purpose"])} у {name(target)}.','mission_complete');continue
        if m['purpose']=='conquer' and not war(s,a.faction,s.places[target].controller):
            m['status']='awaiting';record(s,'Поход остановлен после изменения отношений; новая война не разрешена.','obstruction');continue
        path=route(s,a.location,target,a.faction,m['area'],military=True)
        if path is None:
            m['status']='awaiting';record(s,f'Армия не нашла разрешённого пути к {name(target)}.','obstruction');continue
        if path:
            fee=(10 if route_kind(a.location,path[0])=='ferry' else 20 if route_kind(a.location,path[0])=='sea' else 0)*ceil(a.size/100)
            if fee>a.funds:
                m['status']='awaiting';record(s,'Командующий запросил средства на перевозку; самовольно выйти за походную казну он не может.','obstruction');continue
            a.funds-=fee;m['spent']+=fee
            a.travel={'path':[path[0]],'left':duration(a.location,path[0])}


def _npc(s: RulerState,a: Army) -> None:
    if s.rules_version>=4:
        from campaign.ruler.world import order
        order(s,a);return
    if not a.size or a.location in s.sieges:return
    threats=[p.id for p in s.places.values() if p.owner==a.faction and (war(s,a.faction,p.controller) or p.id in s.sieges and s.sieges[p.id]['faction']!=a.faction)]
    if not threats and s.day>=270:
        threats=[p.id for p in s.places.values() if war(s,a.faction,p.controller) and any(s.places[n].controller==a.faction for n in ADJACENCY[p.id])]
    targets=[(route(s,a.location,t,a.faction),t) for t in threats]
    targets=[(p,t) for p,t in targets if p is not None and p]
    if targets:
        path,target=min(targets,key=lambda x:(len(x[0]),x[1]));p=s.places[target]
        if a.size>count(p.garrison)*1.2 or p.id in s.sieges:a.travel={'path':[path[0]],'left':duration(a.location,path[0])}


def cleanup(s: RulerState) -> None:
    for pid,sg in list(s.sieges.items()):
        sg['armies']=[x for x in sg['armies'] if x in s.armies and s.armies[x].size and s.armies[x].location==pid and not s.armies[x].travel]
        if not sg['armies'] or s.places[pid].controller==sg['faction'] or not war(s,sg['faction'],s.places[pid].controller):del s.sieges[pid]
    for a in s.armies.values():
        if not a.size:
            for pid in [a.commander,a.deputy]:
                person=s.people.get(pid)
                if person and person.status in ['active','wounded'] and person.location!=s.capital and not person.travel:
                    home=s.capital if a.faction=='ottoman' else next((p.id for p in s.places.values() if p.controller==a.faction),None)
                    path=route(s,person.location,home,a.faction,hostile_end=False) if home else None
                    if path is not None:person.travel={'purpose':'retreat','target':home,'path':path,'left':0,'location':person.location}
            a.commander=None;a.deputy=None
            a.travel=None
            if a.mission:a.mission['status']='failed'
            if a.faction=='ottoman':s.gold+=a.funds;a.funds=0


def _resupply(s: RulerState,a: Army) -> None:
    if a.grain>=a.size*10:return
    if any(c.get('army')==a.id and c['kind']=='supply' and c['status'] in ['moving','held','assembling'] for c in s.transports.values()):return
    local=s.places[a.location]
    if local.controller!='ottoman' and a.mission.get('allow_requisition') and local.grain:
        n=min(local.grain,a.size*14);local.grain-=n;a.grain+=n;local.prosperity=max(0,local.prosperity-5);local.unrest+=5
        record(s,f'Командующий использовал разрешение на реквизицию у {name(local.id)}: {n} пайков передано в обоз.','requisition');return
    candidates=[]
    for p in s.places.values():
        if p.controller!='ottoman' or p.id in s.sieges or p.grain<=count(p.garrison)*15:continue
        path=route(s,p.id,a.location)
        if path is not None:candidates.append((len(path),p.id,path))
    if candidates and a.funds>=5:
        _,pid,path=min(candidates);source=s.places[pid];n=min(a.size*21,source.grain-count(source.garrison)*15)
        if n>0:
            source.grain-=n;a.funds-=5;a.mission['spent']+=5;ident=uid(s,'supply')
            s.transports[ident]={'id':ident,'kind':'supply','location':pid,'origin':pid,'target':a.location,'army':a.id,'path':path,'left':0,'grain':n,'escorts':[],'status':'moving','created':s.day}
            record(s,f'По поручению командующего из {name(pid)} отправлено {n} пайков. Перевозка оплачена из походной казны.','supply');return
    if a.grain<a.size*3 and not a.mission.get('supply_warning'):
        a.mission['supply_warning']=True;a.mission['status']='awaiting'
        record(s,'Командующий остановил дальнейшее продвижение и просит обеспечить обоз: доступной поставки в пределах средств нет.','obstruction')
