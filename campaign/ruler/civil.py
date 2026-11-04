from __future__ import annotations

from dataclasses import asdict
from math import ceil
from campaign.content import PLACE_INDEX, TROOPS
from campaign.engine import require, relation_key
from campaign.ruler.models import Cohort, RulerState
from campaign.ruler.core import *
from campaign.ruler import world, knowledge

INSTITUTIONS={
 'scribes':{'name':'Служба писцов','cost':70,'days':60,'upkeep':3,'requires':[]},
 'land_register':{'name':'Земельный учёт','cost':100,'days':90,'upkeep':4,'requires':['scribes']},
 'builders':{'name':'Строительная служба','cost':90,'days':90,'upkeep':3,'requires':['land_register']},
 'shipping':{'name':'Организация перевозок','cost':100,'days':90,'upkeep':4,'requires':['scribes']},
}


def institution_help(s, iid):
    """Public prerequisites and command validation share the same explanation."""
    item=INSTITUTIONS[iid];missing=[x for x in (item['requires'] if not(s.rules_version>=5 and iid=='builders') else []) if s.institutions.get(x,{}).get('status')!='active']
    reasons=[]
    for x in missing:
        current=s.institutions.get(x)
        reasons.append(f'Дождитесь готовности службы «{INSTITUTIONS[x]["name"]}»: осталось {max(0,current["ready"]-s.day)} дней. Нажмите «Продолжить время».' if current else f'Сначала учредите «{INSTITUTIONS[x]["name"]}» в этом разделе и дождитесь завершения подготовки.')
    if not any(p.faction=='ottoman' and p.status=='active' and p.location==s.capital and not p.travel and p.skills['stewardship']>=35 for p in s.people.values()):
        candidates=[p.name for p in s.people.values() if p.faction=='ottoman' and p.status=='active' and p.skills['stewardship']>=35]
        reasons.append(f'В столице {name(s.capital)} нужен опытный распорядитель. Подойдут: {", ".join(candidates)}. Верните одного из них в столицу и дождитесь прибытия.' if candidates else 'Среди действующих служителей сейчас нет подходящего распорядителя. Дождитесь возвращения опытного человека на службу; без исполнителя учреждение не начнёт работу.')
    if s.gold<item['cost']:reasons.append(f'Нужно {item["cost"]} монет; в казне {s.gold}. Не хватает {item["cost"]-s.gold}. Проверьте счета и ожидаемые поступления.')
    return {'reasons':reasons,'requires':[] if s.rules_version>=5 and iid=='builders' else list(item['requires']),'next_institution':missing[0] if missing and missing[0] not in s.institutions else None}


def construction_options(s,p,include_pending=True):
    result=[]
    for kind,title,cost,days in [('granary','Зернохранилище',60,60),('fortress','Новая крепость',250,360),('repair','Ремонт стен',(p.max_walls-p.walls)*2,60)]:
        reasons=[]
        if include_pending and any(e['kind']=='construction' and e['province']==p.id for e in s.edicts):
            reasons.append('Строительное распоряжение уже в пути. Средства выделены. Продолжите время и дождитесь прибытия гонца; повторно платить не нужно.')
        if p.owner!='ottoman':reasons.append('Сначала решите на совете вопрос об управлении завоёванным владением.')
        if p.id in s.sieges:reasons.append('Владение в осаде. Сначала снимите осаду; начать работы сейчас нельзя.')
        if p.construction:reasons.append(f'Здесь уже идут работы: осталось {p.construction["work"]} дней при наличии работников. Продолжите время и дождитесь донесения.')
        if kind=='granary' and 'granary' in p.buildings:reasons.append('Зернохранилище уже построено. Выберите другое владение.')
        if kind=='repair' and (not p.fortress_level or p.walls>=p.max_walls):reasons.append('Повреждённых крепостных стен здесь нет. Ремонт не требуется.')
        if kind=='fortress':
            if p.fortress_level:reasons.append('В этом владении крепость уже есть. Для новой выберите неукреплённое поселение.')
            if s.institutions.get('builders',{}).get('status')!='active' and not (s.rules_version>=5 and knowledge.available(s,'ottoman',p.id,'stonework')):reasons.append('Пригласите мастера каменного строительства в это поселение через «Дела правления → Мастера» или учредите строительную службу.' if s.rules_version>=5 else 'Нужна действующая строительная служба. Порядок подготовки: Служба писцов → Земельный учёт → Строительная служба. Каждая должна завершить подготовку.')
            if s.rules_version>=5 and s.institutions.get('builders',{}).get('status')!='active' and knowledge.available(s,'ottoman',p.id,'stonework') and all(knowledge.busy(s,m.id) for m in knowledge.available(s,'ottoman',p.id,'stonework')):reasons.append('Прибывшие каменщики заняты. Завершите или отмените прежнюю работу.')
            if p.reserve<20:reasons.append(f'Нужны 20 свободных работников; здесь доступно {p.reserve}. Выберите другое поселение или верните людей из военной службы.')
        if s.gold<cost:reasons.append(f'Нужно {cost} монет; в казне {s.gold}. Не хватает {cost-s.gold}.')
        result.append({'id':kind,'name':title,'cost':cost,'days':days,'reasons':reasons})
    return result



def _construction_tick(s,p,fed):
    if not p.construction or p.owner!=p.controller:return
    master=s.people.get(p.construction.get('master'))
    if s.rules_version>=5 and (not fed or master and (master.status!='active' or master.location!=p.id or master.travel)):
        if not p.construction.get('paused'):record(s,name(p.id)+': строительству недостаёт продовольствия или мастера.','obstruction')
        p.construction['paused']=True;return
    p.construction.pop('paused',None);p.construction['work']-=1
    if p.construction['work']>0:return
    building=p.construction['building'];p.reserve+=p.construction['workers']
    if building=='fortress':p.fortress_level=1;p.walls=p.max_walls=60;p.buildings.append('new_fortress')
    elif building=='repair':p.walls=p.max_walls
    else:p.buildings.append(building)
    p.construction=None
    if p.controller=='ottoman':record(s,f'{name(p.id)}: строительные работы завершены.','building')


def obligation(s: RulerState,kind: str,who: str,due: int,amount: int=0,province: str | None=None,scope: str='state') -> str:
    require(kind in ['debt','reward','protection','charter'],'Неизвестный вид обязательства')
    require(kind in ['debt','reward'] or province in s.places,'Для этого обязательства нужно владение')
    ident=uid(s,'obligation')
    s.obligations[ident]={'id':ident,'kind':kind,'creditor':who,'due':due,'amount':amount,'province':province,'scope':scope,'status':'open','created':s.day}
    return ident


def settle(s: RulerState,oid: str) -> None:
    require(oid in s.obligations,'Обязательство не найдено')
    o=s.obligations[oid];require(o['status'] in ['open','broken'],'Это обязательство уже исполнено')
    if o['kind'] in ['debt','reward']:
        spend(s,o['amount'])
        if o['creditor']=='merchants':s.merchant['gold']+=o['amount']
        elif o['creditor'] in s.people:s.people[o['creditor']].wealth+=o['amount']
    elif o['kind']=='protection':
        p=s.places[o['province']]
        require(p.controller=='ottoman' and count(p.garrison)+sum(a.size for a in s.armies.values() if a.faction=='ottoman' and a.location==p.id and not a.travel)>=20 and p.id not in s.hazards,'У дороги ещё нет достаточной охраны или остаётся разбойный отряд')
    elif o['kind']=='charter':
        require(s.places[o['province']].tax!='extraordinary','Чрезвычайный сбор противоречит выданной грамоте')
    o['status']='fulfilled';o['fulfilled']=s.day
    if s.rules_version>=4 and o['creditor'] in s.people and o['kind'] in ['debt','reward']:
        from campaign.ruler.court import remember
        remember(s,o['creditor'],'payment:'+o['id'],s.people[o['creditor']].name+' получил '+str(o['amount'])+' монет по записанному обязательству.')
    if o['creditor'] in s.people:s.people[o['creditor']].trust=min(90,s.people[o['creditor']].trust+8)
    record(s,f'Исполнено обязательство: {obligation_text(s,o)}.','promise')


def obligation_text(s: RulerState,o: dict) -> str:
    who=s.people[o['creditor']].name if o['creditor'] in s.people else 'купцам'
    if o['kind'] in ['debt','reward']:return f'выплатить {o["amount"]} — {who}'
    if o['kind']=='protection':return f'обеспечить охрану дороги у {name(o["province"])}'
    return f'сохранить выданные права в {name(o["province"])}'


def budget(s: RulerState) -> dict:
    own=[p for p in s.places.values() if p.controller=='ottoman']
    gross=grants=local=0
    for p in own:
        factor={'relief':.65,'customary':1,'extraordinary':1.35}[p.tax]
        tax=int((8 if not p.fortress_level else 16)*p.prosperity/65*factor*(.5 if p.owner!='ottoman' else 1))
        tax=max(0,tax)
        grant=tax//4 if p.grant and p.grant['beneficiary'] in s.people and s.people[p.grant['beneficiary']].status!='dead' else 0
        gross+=tax;grants+=grant;local+=3
    # Count payroll from actual Ottoman containers, not present ownership of origins.
    total=sum(c.count*TROOPS[c.troop]['upkeep'] for p in own for c in p.garrison)+sum(c.count*TROOPS[c.troop]['upkeep'] for a in s.armies.values() if a.faction=='ottoman' for c in a.cohorts)+sum(x['count']*TROOPS[x['troop']]['upkeep'] for c in s.transports.values() for x in c.get('escorts',[]))
    fortress_upkeep=sum(3 for p in own if 'new_fortress' in p.buildings)
    institutions=sum(INSTITUTIONS[k]['upkeep'] for k,v in s.institutions.items() if k in INSTITUTIONS and v['status']=='active')
    wages=ceil(total/10)
    extra=0
    if s.rules_version>=5:
        from campaign.ruler.diplomacy import data
        d=data(s);extra=sum(m['wage'] for pid,m in d['specialists'].items() if m['employer']=='ottoman' and s.people[pid].status=='active')+sum(c['tribute']+c['arrears'] for f,c in d['subjects'].items() if f=='ottoman')
    pending=sum(o['payment'] for o in s.flags.get('statecraft',{}).get('offers',{}).values())
    return {'gross':gross,'grants':grants,'income':gross-grants,'wages':wages,'administration':local,'institutions':institutions,'statecraft_due':extra,'expense':wages+local+institutions+fortress_upkeep+extra,'net':gross-grants-wages-local-institutions-fortress_upkeep-extra,'period_days':30,'reserved':pending+sum(e['escrow'] for e in s.edicts)+sum(a.funds for a in s.armies.values() if a.faction=='ottoman')+sum(c['mandate']['funds'] for c in s.couriers if c['kind']=='order')}


def command(s: RulerState,kind: str,d: dict) -> bool:
    if kind in ['policy','grant','revoke_grant','audit','construction'] and not d.get('_delivered') and dispatch_regional(s,kind,d):return True
    if kind=='appoint':
        pid=str(d.get('person',''));role=str(d.get('role',''));target=str(d.get('province',s.capital))
        require(pid in s.people and s.people[pid].faction=='ottoman' and s.people[pid].status=='active' and not s.people[pid].travel,'Этот человек сейчас не может принять назначение')
        require(role in ['governor','treasurer','judge','regent'],'Неизвестная должность')
        require(pid!=s.ruler_id and not any(pid in [a.commander,a.deputy] for a in s.armies.values()),'Человек уже находится при войске или является правителем')
        if s.rules_version>=5:require(not knowledge.busy(s,pid),'Этот человек ведёт работы. Сначала завершите или отмените их')
        if role=='governor':owned(s,target,True)
        else:target=s.capital
        require(not any(a['person']==pid or a['role']==role and a['province']==target for a in s.appointments),'Назначение на эту должность уже в пути')
        path=route(s,s.people[pid].location,target,hostile_end=False);require(path is not None,'Назначенец не может добраться до места службы')
        s.appointments.append({'id':uid(s,'appointment'),'person':pid,'role':role,'province':target,'location':s.people[pid].location,'path':path,'left':0})
        s.people[pid].travel={'purpose':'appointment','target':target}
        record(s,f'{s.people[pid].name} получил назначение; принятие дел состоится после прибытия в {name(target)}.','appointment')
    elif kind=='summon':
        person=s.people.get(str(d.get('person','')))
        require(person is not None and person.faction=='ottoman' and person.id!=s.ruler_id and person.status=='active' and not person.travel,'Этот человек не может сейчас прибыть ко двору')
        require(not any(person.id in [a.commander,a.deputy] and a.size for a in s.armies.values()),'Военачальник должен вернуться вместе со своим отрядом')
        target=ruler_location(s);path=route(s,person.location,target,hostile_end=True)
        require(path is not None,'Нет доступного пути ко двору')
        for place in s.places.values():
            if place.governor==person.id:place.governor=None
        person.travel={'id':uid(s,'summons'),'purpose':'summons','target':target,'path':path,'left':0,'location':person.location}
        record(s,person.name+' вызван ко двору. Ему ещё предстоит прибыть.','appointment')
    elif kind=='policy':
        p=owned(s,str(d.get('province','')),s.rules_version<4);tax=str(d.get('tax',''))
        require(tax in ['relief','customary','extraordinary'],'Неизвестный порядок сборов')
        p.tax=tax;record(s,f'{name(p.id)}: установлен порядок сборов — '+{'relief':'временное облегчение','customary':'обычные сборы','extraordinary':'чрезвычайный сбор'}[tax]+'.','policy')
    elif kind=='grant':
        p=owned(s,str(d.get('province','')),True);pid=str(d.get('person',''))
        require(pid in s.people and s.people[pid].faction=='ottoman' and s.people[pid].status=='active','Получатель недоступен')
        require(p.grant is None,'Доход этого владения уже пожалован; сначала пересмотрите пожалование')
        p.grant={'beneficiary':pid,'share':.25,'service':'military','since':s.day};s.people[pid].memories.append(f'grant:{p.id}')
        record(s,f'Четверть сборов {name(p.id)} пожалована {s.people[pid].name} за службу. Право собственности не изменилось.','grant')
    elif kind=='revoke_grant':
        p=owned(s,str(d.get('province','')),True);require(p.grant is not None,'В этом владении нет пожалования')
        pid=p.grant['beneficiary'];s.people[pid].memories.append(f'grant_revoked:{p.id}');s.people[pid].trust-=15;p.grant=None
        record(s,f'Пожалование доходов {name(p.id)} отозвано. Получатель потребовал рассмотреть основания отзыва.','grant')
    elif kind=='audit':
        p=owned(s,str(d.get('province','')),True);require(p.audit is None,'Проверка уже проводится')
        spend(s,15);p.audit={'ready':s.day+14,'governor':p.governor}
        record(s,f'Назначена проверка сборов и расходов в {name(p.id)}. Писец сопоставит счета через четырнадцать дней.','audit')
    elif kind=='fulfil':settle(s,str(d.get('obligation','')))
    elif kind=='trade_reparation':
        require(s.flags.get('merchants_offended') and not s.flags.get('reconciliation_ready'),'Нет открытых переговоров о возмещении')
        spend(s,60);s.merchant['gold']+=60;s.flags['reconciliation_ready']=s.day+30
        record(s,'Купцам переданы шестьдесят монет возмещения и гарантия безопасного проезда. Ответ об открытии новых сделок ожидается через месяц.','diplomacy')
    elif kind=='trade':
        require(not s.flags.get('merchants_offended'),'После казни представителя купцы приостановили новые сделки. Требуется возмещение и гарантия проезда.')
        mode=str(d.get('mode',''));require(mode in ['purchase','transit'],'Выберите вид сделки')
        require(not any(c['kind'] in ['purchase','transit'] and c['status'] not in ['completed','cancelled','seized'] for c in s.transports.values()),'Сначала завершите действующую торговую сделку')
        target=str(d.get('province',s.capital));owned(s,target,True)
        source=s.merchant['location'];end=target if mode=='purchase' else 'eskisehir'
        path=route(s,source,end,hostile_end=False);require(path is not None,'Нет мирного пути для этой сделки')
        if mode=='transit':
            first=route(s,source,target,hostile_end=False);second=route(s,target,end,hostile_end=False)
            require(first is not None and second is not None,'Нет пути через ваши владения');path=first+second
        amount=d.get('amount',400 if mode=='purchase' else 300)
        require(type(amount) is int and 100<=amount<=2000 and amount%100==0,'Груз: от 100 до 2000 пайков, сотнями')
        require(s.merchant['grain']>=amount,'У купцов нет такого запаса зерна')
        escorts=[];esc=str(d.get('escort_province',target));n=d.get('escort',0)
        require(type(n) is int and 0<=n<=30,'Охрана: от 0 до 30 человек')
        if n:
            p=owned(s,esc);require(p.id not in s.sieges,'Гарнизон отрезан осадой')
            escorts=take(s,p.garrison,{'militia':n})
        cost=amount//10 if mode=='purchase' else 0
        spend(s,cost);s.merchant['gold']+=cost;s.merchant['grain']-=amount
        ident=uid(s,'caravan');convoy={'id':ident,'kind':mode,'location':source,'origin':source,'target':end,'via':target,'path':path,'left':0,'grain':amount,'escorts':[asdict(x) for x in escorts],'status':'moving','created':s.day,'fee':12,'escort_origin':esc,'escort_join':[]}
        if escorts:
            # Escort travels to the merchant before cargo departure; no teleportation.
            join=route(s,esc,source,hostile_end=False);require(join is not None,'Охрана не может добраться до купца')
            convoy['escort_location']=esc;convoy['escort_join']=join;convoy['status']='assembling'
        s.transports[ident]=convoy
        record(s,f'Согласована сделка: '+(f'поставка {amount} пайков за {cost}.' if mode=='purchase' else 'проезд каравана с пошлиной после доставки.')+(' Охрана направлена к месту сбора.' if escorts else ' Караван отправляется без военной охраны.'),'trade')
    elif kind=='transport_order':
        cid=str(d.get('transport',''));require(cid in s.transports,'Обоз не найден');c=s.transports[cid]
        require(c['status'] in ['held','moving','assembling'],'Этот обоз уже завершил путь')
        action=d.get('action');require(action in ['resume','return'],'Неизвестное распоряжение обозу')
        target=c['target'] if action=='resume' else c.get('escort_origin',s.capital)
        if action=='resume' and c['kind']=='supply' and c.get('army') in s.armies:target=s.armies[c['army']].location
        c['target']=target
        path=route(s,c['location'],target,hostile_end=c['kind']=='supply' and action=='resume');require(path is not None,'Нет разрешённого пути')
        c['path']=path;c['left']=0;c['status']='moving';c['returning']=action=='return';c['release_authorized']=True
        if c['returning']:c['target']=target
    elif kind=='institution':
        iid=str(d.get('institution',''));require(iid in INSTITUTIONS,'Неизвестное учреждение')
        require(iid not in s.institutions,'Учреждение уже создаётся или действует')
        item=INSTITUTIONS[iid]
        help=institution_help(s,iid)
        require(not help['reasons'],' '.join(help['reasons']))
        spend(s,item['cost']);s.institutions[iid]={'status':'preparing','ready':s.day+item['days']}
        record(s,f'Начато учреждение: {item["name"]}. Выделены средства, готовятся люди и учёт.','institution')
    elif kind=='construction':
        p=owned(s,str(d.get('province','')),True);kind=d.get('building')
        require(kind in ['granary','fortress','repair'],'Неизвестная работа')
        option=next(x for x in construction_options(s,p,include_pending=not d.get('_delivered')) if x['id']==kind)
        require(not option['reasons'],' '.join(option['reasons']))
        if kind=='fortress':
            require(not p.fortress_level and (s.institutions.get('builders',{}).get('status')=='active' or s.rules_version>=5 and knowledge.available(s,'ottoman',p.id,'stonework')),'Нужны неукреплённое поселение и действующая строительная служба')
            require(p.reserve>=20,'Нужны двадцать свободных работников');spend(s,250);p.reserve-=20
            p.construction={'building':kind,'work':360,'workers':20}
            if s.rules_version>=5 and s.institutions.get('builders',{}).get('status')!='active':
                masters=[m for m in knowledge.available(s,'ottoman',p.id,'stonework') if not knowledge.busy(s,m.id)]
                require(masters,'Мастер занят: освободите его от другой работы');p.construction['master']=masters[0].id
        elif kind=='repair':
            require(p.fortress_level and p.walls<p.max_walls,'Стены не нуждаются в ремонте');spend(s,(p.max_walls-p.walls)*2);p.construction={'building':kind,'work':60,'workers':0}
        else:
            require('granary' not in p.buildings,'Зернохранилище уже есть');spend(s,60);p.construction={'building':kind,'work':60,'workers':0}
        record(s,f'{name(p.id)}: выделены средства на строительные работы.','building')
    elif kind=='diplomacy':
        if s.rules_version>=5:
            from campaign.ruler.diplomacy import command as diplomacy_command
            return diplomacy_command(s,'negotiate',d)
        target=str(d.get('target',''));proposal=d.get('proposal');key=relation_key('ottoman',target)
        require(key in s.relations and target!='ottoman','Нет дипломатического адресата')
        require(target in (world.contacts(s) if s.rules_version>=4 else ['byzantine','germiyan']),'В этой главе установлены связи с Византией и Гермияном')
        require(not any(x['kind']=='diplomacy' and x['target']==target for x in s.couriers),'Послание уже находится в пути')
        if proposal=='access' and s.rules_version>=4:
            require(s.relations[key]['status']=='peace','Во время войны договориться о проходе нельзя')
            spend(s,30);s.couriers.append({'id':uid(s,'access'),'kind':'access','target':target,'ready':s.day+14,'payment':30})
            record(s,'Посол отправлен договариваться о праве прохода на два года. Тридцать монет зарезервированы.','diplomacy')
        elif proposal=='war':
            require(s.day>=s.relations[key].get('truce_until',0),'Действует данное слово о перемирии');s.relations[key]['status']='war'
            record(s,'Отправлено извещение об объявлении войны.','diplomacy')
        elif proposal=='peace':
            require(s.relations[key]['status']=='war','Война не идёт')
            occupied=[p for p in s.places.values() if p.owner==target and p.controller=='ottoman']
            require(occupied or s.gold>=40,'Нужно предложить платёж или иметь военный результат')
            spend(s,0 if occupied else 40)
            s.couriers.append({'id':uid(s,'peace'),'kind':'diplomacy','target':target,'ready':s.day+14,'payment':0 if occupied else 40})
            record(s,'Посол отправлен с предложением мира. Ответ ожидается через четырнадцать дней.','diplomacy')
        else:require(False,'Выберите войну или предложение мира')
    elif kind=='release_envoy':
        person=s.people.get(str(d.get('person','')))
        require(person is not None and person.status=='detained','Этот посланник не находится под стражей')
        release_envoy(s,person)
    elif kind=='ransom':
        pid=str(d.get('person',''));require(pid in s.people and s.people[pid].status=='captured' and s.people[pid].faction=='ottoman','Этот человек не находится в плену')
        spend(s,60);s.people[pid].status='wounded';s.people[pid].health=40;s.people[pid].wounded_until=s.day+30
        # Release is followed by travel, not instant restoration of command.
        p=s.people[pid];path=route(s,p.location,s.capital,hostile_end=False)
        if path is not None:
            p.travel={'purpose':'recovery','target':s.capital,'path':path,'left':0}
        record(s,f'Выкуп за {p.name} передан. После освобождения ему требуется лечение и возвращение.','ransom')
    else:return False
    return True


def tick(s: RulerState) -> None:
    from campaign.ruler.military import deliver_order
    deliver_edicts(s)
    if s.flags.get('reconciliation_ready') and s.day>=s.flags['reconciliation_ready']:
        s.flags['merchants_offended']=False;s.flags['reconciliation_ready']=None
        record(s,'Получен ответ купцов: возмещение принято, новые договоры снова рассматриваются.','diplomacy')
    for item in list(s.couriers):
        if item['kind']=='extension':
            if s.day<item['ready']:continue
            o=s.obligations.get(item['obligation'])
            if o and o['status'] in ['open','broken']:
                acceptable=o.get('extensions',0)<1 and not(o['kind']=='charter' and s.places[o['province']].tax=='extraordinary') and not(o['creditor']=='merchants' and s.flags.get('merchants_offended'))
                if acceptable:
                    o['status']='open';o['due']=s.day+90;o['extensions']=o.get('extensions',0)+1
                    record(s,'Получатель согласился на однократную отсрочку на девяносто дней. Новые условия записаны.','agreement')
                else:record(s,'В отсрочке отказано: получатель настаивает на первоначальном обязательстве.','negotiation')
            s.couriers.remove(item);continue
        if item['kind']=='access':
            if s.day<item['ready']:continue
            if war(s,'ottoman',item['target']):
                s.gold+=item['payment'];record(s,'Из-за войны договор о проходе сорван; платёж возвращён.','diplomacy')
            else:
                s.relations[relation_key('ottoman',item['target'])]['access_until']=s.day+720;s.polities[item['target']].gold+=item['payment']
                record(s,'Получено право прохода через владения '+item['target']+' на два года.','agreement')
            s.couriers.remove(item);continue
        if item['kind']=='diplomacy':
            if s.day<item['ready']:continue
            if s.rules_version>=4:
                from campaign.ruler.world import accept_peace
                if not item.get('guaranteed') and not accept_peace(s,item['target'],item['payment']):
                    s.gold+=item['payment'];s.couriers.remove(item);record(s,'Предложение мира отклонено. Выделенный платёж возвращён в свободную казну.','diplomacy');continue
                s.polities[item['target']].gold+=item['payment']
            key=relation_key('ottoman',item['target']);s.relations[key].update(status='peace',truce_until=s.day+item.get('truce',180))
            for p in s.places.values():
                if {p.owner,p.controller}=={'ottoman',item['target']}:p.owner=p.controller
            for pid,sg in list(s.sieges.items()):
                if {sg['faction'],s.places[pid].controller}=={'ottoman',item['target']}:del s.sieges[pid]
            for army in s.armies.values():
                if army.faction in ['ottoman',item['target']] and s.places[army.location].controller!=army.faction:
                    homes=[p for p in s.places.values() if p.controller==army.faction]
                    routes=[(route(s,army.location,p.id,army.faction,hostile_end=False),p.id) for p in homes]
                    routes=[(path,pid) for path,pid in routes if path is not None]
                    if routes:
                        path,pid=min(routes,key=lambda x:(len(x[0]),x[1]));army.travel={'path':path,'left':duration(army.location,path[0]),'retreat':True,'civilian':True} if path else None
                    if army.mission:army.mission['status']='awaiting'
            record(s,'Получено согласие на мир; удерживаемые земли признаны за сторонами.','diplomacy');s.couriers.remove(item);continue
        if not _journey(s,item,courier=True,hostile_end=item['kind']=='order'):
            continue
        s.couriers.remove(item)
        if item['kind']=='order':
            a=s.armies.get(item['army'])
            if a and a.size:
                if a.location!=item['location']:
                    path=route(s,item['location'],a.location,hostile_end=True)
                    if path is not None:item['path']=path;item['left']=0;s.couriers.append(item);continue
                    s.gold+=item['mandate']['funds'];record(s,'Гонец не нашёл доступного пути к переместившемуся войску. Приказ возвращён.','obstruction')
                else:deliver_order(s,a,item['mandate'])
            else:s.gold+=item['mandate']['funds'];record(s,'Приказ вернулся: назначенное войско больше не существует.','obstruction')
        else:
            snapshot=item['snapshot'];old=s.knowledge.get(item['province'])
            if old is None or snapshot['day']>=old['day']:
                s.knowledge[item['province']]=snapshot
                record(s,f'Получена ведомость {name(item["province"])}; наблюдения сделаны в день {snapshot["day"]}.','report',snapshot['source'],snapshot['day'])
    for ap in list(s.appointments):
        person=s.people[ap['person']]
        if person.status not in ['active','wounded'] or s.places[ap['province']].controller!='ottoman':
            person.travel=None;s.appointments.remove(ap);record(s,'Назначение прервано: человек или место службы недоступны.','appointment');continue
        if _journey(s,ap,courier=True):
            person.location=ap['province'];person.travel=None
            for p in s.places.values():
                if p.governor==person.id:p.governor=None
            if ap['role']=='governor':
                s.places[ap['province']].governor=person.id;s.flags['governor_started:'+person.id]=s.day
            elif ap['role']=='regent':s.regent=person.id
            else:
                for p in s.people.values():
                    if p.role==ap['role']:p.role='officer'
            person.role=ap['role'];s.appointments.remove(ap)
            record(s,f'{person.name} прибыл в {name(person.location)} и принял дела.','appointment')
    for person in s.people.values():
        if person.travel and person.travel.get('purpose') in ['recovery','retreat','diplomatic_return','summons']:
            tr=person.travel;tr.setdefault('location',person.location)
            arrived=_journey(s,tr,courier=True,hostile_end=tr.get('purpose')=='summons',safe_conduct=tr.get('purpose')=='diplomatic_return');person.location=tr['location']
            if arrived:
                person.location=tr['target']
                if tr.get('purpose')=='diplomatic_return':person.status='departed'
                if tr.get('purpose')=='summons':
                    from campaign.ruler.court import remember
                    remember(s,person.id,'summons:'+tr['id'],person.name+' прибыл в '+name(person.location)+' по приглашению правителя.')
                person.travel=None
        if person.status in ['wounded','ill'] and s.day>=person.wounded_until:
            person.status='active';person.health=min(90,person.health+30)
            if person.faction=='ottoman':record(s,f'{person.name} снова способен нести службу.','recovery')
        if s.day%180==0 and person.status=='active' and person.faction=='ottoman' and calendar(s)['year']-person.born>=45 and roll(s,'illness:'+person.id)<.025:
            person.status='ill';person.health=max(30,person.health-20);person.wounded_until=s.day+30
            record(s,f'{person.name} заболел и временно оставил обычную службу.','illness')
        if s.day%365==0 and person.status=='active':
            age=calendar(s)['year']-person.born
            if age>55:
                person.health=max(0,person.health-int((age-50)/4))
                if roll(s,'age:'+person.id)<max(0,(age-60)/600)+(1-person.health/100)*.02:
                    person.status='dead'
                    if person.faction=='ottoman':record(s,f'{person.name} скончался. Его должность и обязанности требуют решения.','death')
    for p in s.places.values():
        if p.grant and s.people[p.grant['beneficiary']].status=='dead':
            p.grant=None
            if p.controller=='ottoman':record(s,f'Служебное пожалование {name(p.id)} вернулось в распоряжение казны после смерти получателя.','grant')
        if p.controller=='ottoman':
            for a in s.armies.values():
                if a.faction=='ottoman' and a.location==p.id and not a.travel and p.grain<count(p.garrison)*7:
                    n=min(max(0,count(p.garrison)*14-p.grain),max(0,a.grain-a.size*7));a.grain-=n;p.grain+=n
            consumed=(0 if p.id in s.sieges else count(p.garrison))+sum(x['count'] for x in p.training)+(p.construction.get('workers',0) if p.construction else 0)
            received=min(p.grain,consumed);p.grain-=received
            if received<consumed and s.day%14==0:
                losses(p.garrison,max(1,ceil(count(p.garrison)*.02)));p.unrest+=2
        if p.id not in s.sieges:
            for tr in list(p.training):
                if s.day>=tr['ready']:
                    p.garrison.append(Cohort(tr['id'],tr['troop'],tr['count'],tr['origin'],training=10));p.training.remove(tr)
                    if p.controller=='ottoman':record(s,f'{name(p.id)}: подготовлены {tr["count"]} воинов. Они находятся в гарнизоне.','recruitment')
            _construction_tick(s,p,p.controller!='ottoman' or received>=consumed)
        if p.audit and s.day>=p.audit['ready']:
            if s.flags.get('sabotage_transport') and p.id=='karacahisar':
                s.flags['sabotage_proven']=True
                record(s,'Писец сопоставил накладную и опросил охрану: обоз удержан распоряжением Конура после отметки об отправке.','audit')
            gov=s.people.get(p.audit['governor']);diverted=s.flags.get('diverted:'+p.id,0)
            if diverted:
                record(s,f'Проверка {name(p.id)} обнаружила расхождение в {diverted} монет. Ответственный: {gov.name if gov else "местный сборщик"}.','audit')
                s.flags['evidence:'+p.id]={'person':gov.id if gov else None,'amount':diverted}
            else:record(s,f'Проверка {name(p.id)}: ведомости и поступления совпадают. Оснований для обвинения не найдено.','audit')
            p.audit=None;s.flags['audit_done']=True
    for iid,item in s.institutions.items():
        if item['status']=='preparing' and s.day>=item['ready']:
            item['status']='active';record(s,f'{INSTITUTIONS[iid]["name"]} приступила к работе.','institution')
    for o in s.obligations.values():
        if o['status']=='open' and s.day>o['due']:
            if o['kind']=='protection' and protection_met(s,o['province']):
                o['status']='fulfilled';o['fulfilled']=s.day;record(s,f'Ведомость подтвердила выставленную охрану у {name(o["province"])}. Обязательство исполнено.','promise');continue
            if o['kind']=='charter' and s.places[o['province']].tax!='extraordinary':
                o['status']='fulfilled';record(s,'Срок грамоты прошёл без нарушения оговорённых условий.','promise');continue
            o['status']='broken';_withdraw_service(s,o);s.flags['broken_promises']=s.flags.get('broken_promises',0)+1
            if o['creditor'] in s.people:s.people[o['creditor']].trust-=15;s.people[o['creditor']].memories.append('broken:'+o['id'])
            record(s,f'Срок истёк: {obligation_text(s,o)}. Получатель требует ответа.','broken_promise')
    _routine_supply(s)
    _transports(s)
    if s.day%30==0:_month(s)
    if s.day%90==0:
        for p in s.places.values():
            if p.controller=='ottoman':observation(s,p.id,'Местная ведомость')


def _journey(s: RulerState,obj: dict,courier: bool=False,hostile_end: bool=False,safe_conduct: bool=False) -> bool:
    if not obj['path']:return True
    dest=obj['path'][0]
    if not safe_conduct and war(s,'ottoman',s.places[dest].controller) and not(hostile_end and len(obj['path'])==1):
        if not obj.get('held'):
            obj['held']=True;record(s,f'Движение у {name(obj["location"])} задержано: дорога к {name(dest)} закрыта войной.','obstruction')
        return False
    obj['held']=False
    if obj['left']==0:obj['left']=duration(obj['location'],dest,courier)
    obj['left']-=1
    if obj['left']<=0:obj['location']=obj['path'].pop(0)
    return not obj['path']


def _transports(s: RulerState) -> None:
    for c in s.transports.values():
        if c['status'] not in ['moving','assembling']:continue
        a=s.armies.get(c.get('army'))
        if c['kind']=='supply' and c['location']=='karacahisar' and s.places['karacahisar'].governor=='konur' and s.people['konur'].trust<45 and a and a.commander=='turgut' and not c.get('release_authorized') and not s.flags.get('sabotage_transport'):
            c['status']='held';s.flags['sabotage_transport']=c['id']
            record(s,'Накладная обоза помечена отправленной, но охрана ещё находится в Караджахисаре. Командующий не подтвердил получение. Требуется проверка.','contradiction');continue
        if c['status']=='assembling':
            obj={'location':c.get('escort_location',c['location']),'path':c['escort_join'],'left':c['left']}
            done=_journey(s,obj);c['escort_location']=obj['location'];c['left']=obj['left'];c['escort_join']=obj['path']
            if done:c['status']='moving';c['left']=0
            continue
        if c['location'] in s.hazards and not c.get('ambushed'):
            c['ambushed']=True;force=sum(x['count'] for x in c['escorts']);hazard=s.hazards[c['location']]
            if force<hazard:
                # Cargo remains a real stock, seized into the local settlement.
                s.places[c['location']].grain+=c['grain'];c['grain']=0;c['status']='seized'
                _return_escort(s,c);record(s,f'Караван у {name(c["location"])} потерял груз: охрана не удержала дорогу.','trade_loss');continue
            units=[Cohort(**x) for x in c['escorts']];losses(units,ceil(hazard/3));c['escorts']=[asdict(x) for x in units]
            record(s,f'Охрана отбила нападение у {name(c["location"])}; есть потери.','battle')
        if not _journey(s,c,hostile_end=c['kind']=='supply'):
            if c.get('held'):c['status']='held'
            continue
        if c.get('returning'):
            s.places[c['location']].grain+=c['grain'];c['grain']=0;c['status']='cancelled';_return_escort(s,c);record(s,'Обоз возвратился; неиспользованный груз принят на местный склад.','transport');continue
        if c['kind']=='supply':
            a=s.armies.get(c['army'])
            if a and a.location==c['location'] and a.faction=='ottoman':a.grain+=c['grain'];c['grain']=0
            elif s.places[c['location']].controller=='ottoman':s.places[c['location']].grain+=c['grain'];c['grain']=0
            else:c['status']='held';record(s,'Обоз достиг указанного места, но армия ушла. Требуется новый маршрут.','obstruction');continue
        elif c['kind'] in ['purchase','local_supply']:
            s.places[c['location']].grain+=c['grain'];c['grain']=0
            if c['kind']=='purchase':s.flags['trade_delivered']=True
        else:
            s.merchant['warehouses'][c['location']]=s.merchant['warehouses'].get(c['location'],0)+c['grain'];c['grain']=0
            fee=min(s.merchant['gold'],c['fee']);s.merchant['gold']-=fee;s.gold+=fee;s.flags['trade_delivered']=True
        c['status']='completed';_return_escort(s,c)
        if c['kind']=='local_supply':continue
        record(s,f'Обоз прибыл в {name(c["location"])}. Груз и расчёты приняты по назначению.','delivery')


def _return_escort(s: RulerState,c: dict) -> None:
    # Escort remains where it physically ended its journey; no home teleport.
    units=[Cohort(**x) for x in c['escorts']];c['escorts']=[]
    if not units:return
    if s.places[c['location']].controller=='ottoman':s.places[c['location']].garrison.extend(units)
    else:
        from campaign.ruler.models import Army
        ident=uid(s,'escort');a=Army(ident,'ottoman',c['location'],units,None,grain=0,deputy_officer='Старший охраны каравана')
        s.armies[ident]=a
        path=route(s,a.location,c.get('escort_origin',s.capital))
        if path:a.travel={'path':path,'left':duration(a.location,path[0]),'retreat':True,'civilian':True}


def _month(s: RulerState) -> None:
    b=budget(s);income=0
    for p in s.places.values():
        if p.controller!='ottoman':continue
        levy=sum(c.count for c in all_cohorts(s) if c.origin==p.id and c.service=='levy')+sum(t['count'] for t in p.training)
        harvest=(2400 if not p.fortress_level else 700)+(300 if 'granary' in p.buildings else 0)
        if s.rules_version>=4:
            from campaign.ruler.world import harvest as local_harvest
            harvest=local_harvest(s,p)
        harvest=int(harvest*max(.3,1-levy/200)) if s.rules_version>=4 else int(harvest*p.prosperity/65*max(.3,1-levy/200)*max(.3,min(1,p.reserve/(80 if p.fortress_level else 60))))
        if calendar(s)['season']=='Зима':harvest=int(harvest*.65)
        if p.id not in s.sieges:p.grain+=harvest
        factor={'relief':.65,'customary':1,'extraordinary':1.35}[p.tax]
        tax=max(0,int((8 if not p.fortress_level else 16)*p.prosperity/65*factor*(.5 if p.owner!='ottoman' else 1)))
        if p.grant:
            recipient=s.people[p.grant['beneficiary']]
            if recipient.status!='dead':part=tax//4;tax-=part;recipient.wealth+=part
        gov=s.people.get(p.governor)
        if gov and gov.status=='active' and gov.location==p.id and not gov.travel:
            if gov.skills['stewardship']<35 and gov.ambition>50:
                amount=min(5,tax);tax-=amount;gov.wealth+=amount;s.flags['diverted:'+p.id]=s.flags.get('diverted:'+p.id,0)+amount
            if gov.skills['stewardship']>=45 and p.tax!='extraordinary' and p.grain>count(p.garrison)*15:p.prosperity=min(90,p.prosperity+1)
        if p.tax=='extraordinary':p.unrest+=3;p.prosperity=max(15,p.prosperity-2)
        elif p.tax=='relief':p.unrest=max(0,p.unrest-2)
        if p.owner!=p.controller and p.unrest<20 and p.tax!='extraordinary':p.loyalty=min(75,p.loyalty+1)
        income+=tax
    weights={}
    for p in s.places.values():
        if p.grant and s.people[p.grant['beneficiary']].status=='dead':
            p.grant=None
            if p.controller=='ottoman':record(s,f'Служебное пожалование {name(p.id)} вернулось в распоряжение казны после смерти получателя.','grant')
        if p.controller=='ottoman':weights['garrison:'+p.id]=sum(c.count*TROOPS[c.troop]['upkeep'] for c in p.garrison)
    for a in s.armies.values():
        if a.faction=='ottoman':weights['army:'+a.id]=sum(c.count*TROOPS[c.troop]['upkeep'] for c in a.cohorts)
    for c in s.transports.values():weights['transport:'+c['id']]=sum(x['count']*TROOPS[x['troop']]['upkeep'] for x in c.get('escorts',[]))
    allocation={k:v//10 for k,v in weights.items()}
    remaining=b['wages']-sum(allocation.values())
    for key in sorted(weights,key=lambda k:(-(weights[k]%10),k)):
        if remaining:allocation[key]+=1;remaining-=1
    funded=0
    for a in s.armies.values():
        if a.faction=='ottoman':
            used=min(a.funds,allocation.get('army:'+a.id,0));a.funds-=used;funded+=used
            if a.mission:a.mission['spent']+=used
    available=s.gold+income;expense=max(0,b['expense']-b.get('statecraft_due',0)-funded);s.gold=max(0,available-expense);s.arrears+=max(0,expense-available)
    paid=min(s.gold,s.arrears);s.gold-=paid;s.arrears-=paid
    if s.arrears:
        for a in s.armies.values():
            if a.faction=='ottoman':a.morale=max(10,a.morale-5)
    s.flags['last_accounts']={'day':s.day,'income':income,'expense':b['expense']-b.get('statecraft_due',0)}
    record(s,f'Месячная ведомость: поступило {income}, из общей казны израсходовано {expense}, из походных средств {funded}, свободно {s.gold}, задолженность {s.arrears}.','accounts','Хранитель казны')


def _withdraw_service(s: RulerState,o: dict) -> None:
    if o['creditor']!='konur' or o['kind'] not in ['reward','debt']:return
    from campaign.ruler.models import Army
    for a in list(s.armies.values()):
        if a.faction!='ottoman' or not a.size:continue
        units=[c for c in a.cohorts if c.sponsor=='konur']
        if not units:continue
        before=a.size;n=count(units);a.cohorts=[c for c in a.cohorts if c.sponsor!='konur']
        grain=a.grain*n//before;a.grain-=grain
        ident=uid(s,'returning-service')
        ret=Army(ident,'ottoman',a.location,units,None,grain=grain,deputy_officer='Старший людей Конура',service_return=True)
        s.armies[ident]=ret
        if a.commander=='konur':a.commander=None;ret.commander='konur'
        path=route(s,a.location,'karacahisar',military=True)
        if path:ret.travel={'path':path,'left':duration(a.location,path[0]),'retreat':True}
        else:
            s.places[a.location].garrison.extend(units);ret.cohorts=[];s.places[a.location].grain+=ret.grain;ret.grain=0
        record(s,'После нарушения условий службы люди Конура отделились от походного войска и потребовали возвращения. Их фактический путь отмечен в ведомости.','service')


def release_envoy(s,person):
    target='nicomedia' if person.faction=='byzantine' else 'kutahya'
    path=route(s,person.location,target,person.faction,hostile_end=True)
    person.status='leaving'
    if path is not None:person.travel={'purpose':'diplomatic_return','target':target,'location':person.location,'path':path,'left':0}
    record(s,f'{person.name} отпущен и получил возможность вернуться с ответом.','envoy')


def _routine_supply(s: RulerState) -> None:
    """Routine administration dispatches existing local stocks, never creates grain."""
    for p in s.places.values():
        if p.controller!='ottoman' or p.id in s.sieges:continue
        local_armies=[a for a in s.armies.values() if a.faction=='ottoman' and a.location==p.id and not a.travel]
        mouths=count(p.garrison)+sum(a.size for a in local_armies)+sum(t['count'] for t in p.training)
        if not mouths:continue
        available=p.grain+sum(a.grain for a in local_armies)
        if available>=mouths*21:continue
        if any(c['kind']=='local_supply' and c['target']==p.id and c['status'] in ['moving','held'] for c in s.transports.values()):continue
        candidates=[]
        for q in s.places.values():
            if q.id==p.id or q.controller!='ottoman' or q.id in s.sieges:continue
            own_armies=[a for a in s.armies.values() if a.faction=='ottoman' and a.location==q.id]
            spare=q.grain-(count(q.garrison)+sum(a.size for a in own_armies))*30
            if spare<100:continue
            path=route(s,q.id,p.id,hostile_end=False)
            if path is not None and not any(x in s.hazards for x in [q.id]+path) and all(s.places[x].controller=='ottoman' for x in path):candidates.append((len(path),q.id,path,spare))
        if not candidates:
            if available<mouths*7 and not s.flags.get('supply_gap:'+p.id):
                s.flags['supply_gap:'+p.id]=True;record(s,f'Местный распорядитель {name(p.id)}: свободного подвоза по своим дорогам не найдено. Остался запас менее недели.','obstruction')
            continue
        _,source,path,spare=min(candidates)
        n=min(spare,mouths*30-available);s.places[source].grain-=n
        ident=uid(s,'local-supply');s.transports[ident]={'id':ident,'kind':'local_supply','location':source,'origin':source,'target':p.id,'path':path,'left':0,'grain':n,'escorts':[],'status':'moving','created':s.day}
        s.flags['supply_gap:'+p.id]=False


def reconcile_obligations(s: RulerState) -> None:
    for o in s.obligations.values():
        if o['status']=='open' and o['kind']=='charter' and s.places[o['province']].tax=='extraordinary':
            o['status']='broken';s.flags['broken_promises']=s.flags.get('broken_promises',0)+1
            record(s,f'Новое распоряжение о сборах нарушило записанные права {name(o["province"])}. Община потребовала ответа.','broken_promise')


def protection_met(s: RulerState,pid: str) -> bool:
    p=s.places[pid]
    return p.controller=='ottoman' and pid not in s.hazards and count(p.garrison)+sum(a.size for a in s.armies.values() if a.faction=='ottoman' and a.location==pid and not a.travel)>=20


def dispatch_regional(s: RulerState,kind: str,payload: dict) -> bool:
    pid=str(payload.get('province',''))
    owned(s,pid)
    if pid==ruler_location(s):return False
    path=route(s,ruler_location(s),pid,hostile_end=False)
    require(path is not None,'Распоряжение нельзя доставить во владение')
    require(not any(e['kind']==kind and e['province']==pid for e in s.edicts),'Такое распоряжение уже находится в пути')
    trial=deepcopy(s);trial.outbox=[]
    from campaign.ruler.military import command as military_command
    args=dict(payload,_delivered=True)
    handled=military_command(trial,kind,args) or command(trial,kind,args)
    require(handled,'Неизвестное местное распоряжение')
    cost=s.gold-trial.gold
    require(cost>=0,'Недопустимая смета распоряжения');spend(s,cost)
    s.edicts.append({'id':uid(s,'edict'),'kind':kind,'province':pid,'payload':dict(payload),'escrow':cost,'issued':s.day,'location':ruler_location(s),'path':path,'left':0})
    record(s,f'Распоряжение для {name(pid)} отправлено с гонцом; начало работ и расходование выделенных средств подтвердит местный исполнитель.','edict')
    return True


def deliver_edicts(s: RulerState) -> None:
    from campaign.ruler.military import command as military_command
    for ident in [e['id'] for e in s.edicts]:
        item=next(e for e in s.edicts if e['id']==ident)
        if s.places[item['province']].controller!='ottoman':
            s.gold+=item['escrow'];s.edicts=[e for e in s.edicts if e['id']!=ident]
            record(s,'Местное распоряжение отменено после потери владения; выделенные средства возвращены в казну.','obstruction');continue
        if not _journey(s,item,courier=True):continue
        trial=deepcopy(s);trial.gold+=item['escrow'];before=trial.gold
        args=dict(item['payload'],_delivered=True)
        try:
            handled=military_command(trial,item['kind'],args) or command(trial,item['kind'],args)
            require(handled,'Местный исполнитель не распознал распоряжение')
            require(before-trial.gold<=item['escrow'],'Изменившаяся стоимость требует нового распоряжения')
        except RuleError as e:
            s.gold+=item['escrow'];record(s,f'Распоряжение {name(item["province"])} не исполнено: {e}. Выделенные средства возвращены.','obstruction')
        else:
            s.__dict__.update(trial.__dict__)
            record(s,f'Гонец доставил распоряжение в {name(item["province"])}; исполнитель принял его к исполнению.','acknowledgement')
        s.edicts=[e for e in s.edicts if e['id']!=ident]
