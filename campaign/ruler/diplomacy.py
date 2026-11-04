"""Negotiated obligations, sovereigns and physical contingent loans (rules v5)."""
from collections import deque
from math import ceil
from campaign.content import FACTIONS, ADJACENCY
from campaign.engine import RuleError, require, relation_key
from campaign.ruler.core import calendar, count, delivery_days, duration, name, record, roll, route, ruler_location, take, uid
from campaign.ruler.models import Army, Person, Polity

KINDS={'peace':'Мир','nap':'Ненападение','trade':'Торговый договор','alliance':'Оборонительный союз','access':'Право прохода','submit':'Признать сюзеренитет','demand':'Предложить вассалитет','dynasty':'Признать претендента','aid':'Призыв союзника','levy':'Запрос вассального войска'}

def data(s):return s.flags.get('statecraft',{})
def root(s,fid):
    seen=set();subjects=data(s).get('subjects',{})
    while fid in subjects:
        require(fid not in seen,'Обнаружен круг вассальных обязательств');seen.add(fid);fid=subjects[fid]['lord']
    return fid
def treasury(s,fid):return s.gold if fid=='ottoman' else s.polities[fid].gold
def money(s,fid,delta):
    require(treasury(s,fid)+delta>=0,'Не хватает средств на обязательство')
    if fid=='ottoman':s.gold+=delta
    else:s.polities[fid].gold+=delta
def capital(s,fid):
    if fid=='ottoman':return s.capital
    fixed=data(s).get('capitals',{}).get(fid)
    if fixed and s.places[fixed].controller==fid:return fixed
    places=[p for p in s.places.values() if p.controller==fid]
    return max(places,key=lambda p:(p.walls,p.id)).id if places else None
def messenger(s,a,b):
    """Envoys hire transport; unlike an army, they need no state fleet."""
    start=ruler_location(s) if a=='ottoman' else capital(s,a);end=capital(s,b)
    require(start and end,'Одна из сторон больше не имеет действующей ставки')
    queue=deque([(start,[])]);seen={start}
    while queue:
        here,path=queue.popleft()
        if here==end:return max(1,delivery_days(start,path))
        for n in ADJACENCY[here]:
            if n not in seen:seen.add(n);queue.append((n,path+[n]))
    require(False,'Гонец не может добраться до другой стороны')
def active(s,a,b,kind):
    return any(t['status']=='active' and (t['until'] is None or t['until']>s.day) and t['kind']==kind and {t['a'],t['b']}=={a,b} for t in data(s).get('treaties',{}).values())
def access(s,a,b):return root(s,a)==root(s,b) or active(s,a,b,'alliance')

def enable(s):
    if data(s):return
    s.schema_version=s.rules_version=5;s.content_version='ruler-statecraft-1'
    s.flags['statecraft']={k:{} for k in ['treaties','offers','subjects','rulers','capitals','claims','loans','defeats','delegations','projects','skills','specialists','cases','plots','policies','last_ai']}
    for fid in s.polities:
        pid=capital(s,fid)
        if not pid:continue
        person=Person('sovereign-'+fid,'Правитель: '+FACTIONS[fid],calendar(s)['year']-39,pid,'ruler',faction=fid,ambition=40+sum(fid.encode())%35)
        s.people[person.id]=person;s.places[pid].governor=person.id;data(s)['rulers'][fid]=person.id;data(s)['capitals'][fid]=pid
    # Already paid legacy letters retain their escrow and remaining journey.
    from campaign.ruler.world import accept_peace
    for c in list(s.couriers):
        if c['kind'] not in ['access','diplomacy']:continue
        kind='access' if c['kind']=='access' else 'peace'
        answer=kind=='access' or c.get('guaranteed',False) or accept_peace(s,c['target'],c['payment'])
        data(s)['offers'][c['id']]={'id':c['id'],'a':'ottoman','b':c['target'],'kind':kind,'days':720 if kind=='access' else c.get('truce',180),'tribute':0,'levy':0,'payment':c['payment'],'candidate':None,'enemy':None,'status':'returning','answer':answer,'ready':c['ready'],'sent':s.day,'due':c['ready']+90,'travel_days':max(1,c['ready']-s.day)}
        s.couriers.remove(c)
    record(s,'Правление теперь учитывает договоры, вассальные обязательства, полномочия управителей и работу мастеров. Календарь и прежние владения сохранены.','institution')

def propose(s,a,b,kind,days=720,tribute=10,levy=30,payment=0,candidate=None,enemy=None):
    require(isinstance(kind,str) and kind in KINDS and a!=b and a in FACTIONS and b in FACTIONS,'Выберите сторону и вид соглашения')
    require(candidate is None or isinstance(candidate,str),'Укажите человека по имени в ведомости')
    require(enemy is None or isinstance(enemy,str),'Укажите сторону военного поручения')
    require(capital(s,a) and capital(s,b),'У стороны нет владений для исполнения договора')
    require(type(days) is int and 90<=days<=1825,'Срок: от 90 до 1825 дней')
    require(type(tribute) is int and 0<=tribute<=100 and type(levy) is int and 0<=levy<=50,'Проверьте дань и долю военной помощи')
    require(type(payment) is int and 0<=payment<=500,'Платёж: от 0 до 500 монет')
    require(not any(o['a']==a and o['b']==b and o['kind']==kind and o['status'] in ['travelling','arrived','returning'] for o in data(s)['offers'].values()),'Такое посольство уже в пути или ожидает ответа')
    from campaign.ruler.core import war
    if kind in ['trade','nap','alliance','access']:require(not war(s,a,b),'Сначала заключите мир')
    if kind in ['trade','nap','alliance','access']:require(not active(s,a,b,kind),'Это соглашение уже действует; дождитесь окончания срока или явно расторгните его')
    if kind=='peace':require(war(s,a,b),'Между сторонами нет войны')
    if kind in ['peace','alliance','dynasty']:require(root(s,a)==a,'Такие внешнеполитические условия определяет сюзерен; сначала добейтесь самостоятельности')
    if kind in ['submit','demand']:
        subject,lord=(a,b) if kind=='submit' else (b,a)
        require(subject not in data(s)['subjects'] and root(s,lord)!=subject,'Нельзя создать двойное подчинение или круг вассалитета')
        require(root(s,a)==a,'Внешние условия определяет ваш сюзерен; сначала добейтесь самостоятельности')
    if kind=='dynasty':
        require(candidate in s.people and data(s)['claims'].get(candidate,{}).get('target')==b,'Нужен подготовленный претендент с опорой среди местных сторонников')
        require(data(s)['claims'][candidate]['ready']<=s.day and s.people[candidate].status=='active','Претендент ещё не готов или не может принять власть')
        require(data(s)['subjects'].get(b,{}).get('lord')==a,'Для навязывания правителя сначала нужен признанный вассалитет')
    travel=messenger(s,a,b);money(s,a,-payment)
    ident=uid(s,'embassy');o={'id':ident,'a':a,'b':b,'kind':kind,'days':days,'tribute':tribute,'levy':levy,'payment':payment,'candidate':candidate,'enemy':enemy,'status':'travelling','sent':s.day,'ready':s.day+travel,'travel_days':travel,'due':s.day+travel+90}
    data(s)['offers'][ident]=o
    if 'ottoman' in [a,b] and a=='ottoman':record(s,f'Посольство: {KINDS[kind]}, адресат {FACTIONS[b]}. До прибытия гонца {travel} дней; согласия пока нет.','diplomacy')
    return o

def accept(s,o):
    """Own accounts plus dated reconnaissance; no opponent treasury/hidden loyalty."""
    a,b,k=o['a'],o['b'],o['kind'];r=s.polities[b]
    from campaign.ruler.core import effective_power,war
    own=sum(effective_power(s,x) for x in s.armies.values() if x.faction==b and x.size)
    observations=[x for x in r.intelligence.values() if x['controller']==a and s.day-x['day']<=45]
    threat=max((x.get('field_by',{}).get(a,x['field'] if x['controller']==a else 0) for x in r.intelligence.values() if s.day-x['day']<=45),default=0)
    lost=sum(p.owner==b and p.controller!=b for p in s.places.values())
    if data(s).get('grievances',{}).get(a,-1000)>s.day-180 and k in ['trade','alliance','nap']:return False
    if k=='submit':return root(s,b)==b
    if k=='demand':return (lost>0 or data(s)['defeats'].get(b,0)>0 and own<threat*.8) and o['tribute']<=max(10,r.income//2) and root(s,b)==b
    if k=='peace':return r.arrears>0 or lost>0 or own<threat or o['payment']>=40 or r.doctrine=='trade'
    if k=='dynasty':return data(s)['subjects'].get(b,{}).get('lord')==a and o['payment']>=40
    if k=='aid':return active(s,a,b,'alliance') and not r.arrears and o['enemy'] in FACTIONS
    if k=='trade':return not war(s,a,b) and not r.arrears
    if k=='alliance':return r.doctrine!='expansion' or bool({x['controller'] for x in r.intelligence.values() if war(s,b,x['controller'])}&{fid for fid in FACTIONS if war(s,a,fid)})
    return not war(s,a,b)

def peace(s,a,b):
    from campaign.ruler import military
    a,b=root(s,a),root(s,b)
    s.relations[relation_key(a,b)].update(status='peace')
    for p in s.places.values():
        if {root(s,p.owner),root(s,p.controller)}=={a,b}:p.owner=p.controller
    for army in s.armies.values():
        if not army.size or root(s,army.faction) not in [a,b] or root(s,s.places[army.location].controller)==root(s,army.faction):continue
        homes=[route(s,army.location,p.id,army.faction,hostile_end=False) for p in s.places.values() if p.controller==army.faction and p.id not in s.sieges]
        paths=[path for path in homes if path]
        if paths:
            path=min(paths,key=len);army.travel={'path':path,'left':duration(army.location,path[0]),'retreat':True,'civilian':True}
        if army.mission:army.mission['status']='awaiting'
    military.cleanup(s)

def agree(s,o):
    a,b,k=o['a'],o['b'],o['kind'];require(capital(s,a) and capital(s,b),'Одна сторона утратила государство')
    from campaign.ruler.core import war
    if k in ['trade','nap','alliance','access']:
        require(not war(s,a,b),'До возвращения гонца началась война; прежние условия утратили силу')
        require(not active(s,a,b,k),'Соглашение уже заключено другим посольством')
    if k in ['peace','alliance','dynasty']:
        require(root(s,a)==a and (k=='dynasty' or root(s,b)==b),'За время переговоров изменилось подчинение сторон')
    if k in ['submit','demand']:
        subject,lord=(a,b) if k=='submit' else (b,a)
        require(subject not in data(s)['subjects'] and root(s,lord)!=subject,'Обязательства сторон изменились; нужен новый договор')
        require(root(s,lord)==lord,'Сюзерен сам утратил самостоятельность')
        peace(s,a,b);data(s)['subjects'][subject]={'lord':lord,'tribute':o['tribute'],'levy':o['levy'],'arrears':0,'since':s.day,'last_paid':-1}
    elif k=='peace':peace(s,a,b)
    elif k=='dynasty':
        claim=data(s)['claims'][o['candidate']];person=s.people[o['candidate']]
        require(person.status=='active' and not person.travel and data(s)['subjects'].get(b,{}).get('lord')==a,'Претендент недоступен или вассальная присяга утратила силу')
        from campaign.ruler.knowledge import travel
        travel(s,person,capital(s,b),'installation');claim.update(status='travelling',ready=s.day)
    elif k=='aid':declare(s,b,o['enemy'],defensive=True)
    elif k=='levy':request_levy(s,a,b,o['levy'])
    if k in ['peace','nap','alliance','access','trade']:
        rel=s.relations[relation_key(a,b)]
        if k in ['peace','nap','alliance']:rel['truce_until']=max(rel.get('truce_until',0),s.day+o['days'])
        if k in ['alliance','access']:rel['access_until']=max(rel.get('access_until',0),s.day+o['days'])
    if k not in ['aid','levy']:
        ident=uid(s,'treaty');data(s)['treaties'][ident]={'id':ident,'a':a,'b':b,'kind':k,'since':s.day,'until':None if k in ['submit','demand'] else s.day+o['days'],'status':'active','tribute':o['tribute'] if k in ['submit','demand'] else 0}
    money(s,b,o['payment']);o['payment']=0;o['status']='accepted'
    if 'ottoman' in [a,b]:record(s,f'Подтверждено соглашение «{KINDS[k]}» между {FACTIONS[a]} и {FACTIONS[b]}. Условия внесены в дела державы.','agreement')

def declare(s,a,b,defensive=False):
    require(a in FACTIONS and b in FACTIONS and a!=b,'Укажите существующее государство')
    require(root(s,a)==a,'Сначала расторгните вассальную присягу')
    a,b=root(s,a),root(s,b);require(a!=b,'Война внутри своей присяги требует выхода из неё')
    rel=s.relations[relation_key(a,b)]
    require(defensive or s.day>=rel.get('truce_until',0),'Действует данное слово. Для войны сначала явно расторгните договор')
    rel['status']='war'
    for t in data(s)['treaties'].values():
        if {t['a'],t['b']}=={a,b} and t['status']=='active':t['status']='broken'
    record(s,f'{FACTIONS[a]} объявляет войну государству {FACTIONS[b]}.','diplomacy')
    if not defensive:
        for ally in FACTIONS:
            if ally not in [a,b] and active(s,b,ally,'alliance'):
                if not any(o['a']==b and o['b']==ally and o['kind']=='aid' and o['enemy']==a for o in data(s)['offers'].values()):propose(s,b,ally,'aid',enemy=a)

def field_result(s,losers):
    if not data(s):return
    for fid in {a.faction for a in losers}:
        data(s)['defeats'][fid]=data(s)['defeats'].get(fid,0)+1

def command(s,kind,d):
    if kind=='negotiate':
        target=str(d.get('target',''));require(target in contacts(s),'Сначала установите контакт с государством')
        proposal=d.get('proposal')
        if proposal=='war':declare(s,'ottoman',target)
        else:propose(s,'ottoman',target,proposal,d.get('days',720),d.get('tribute',10),d.get('levy',30),d.get('payment',0),d.get('candidate'))
    elif kind=='treaty_reply':
        o=data(s)['offers'].get(str(d.get('offer','')));require(o and o['b']=='ottoman' and o['status']=='arrived','Это послание ещё не пришло или уже получило ответ')
        require(type(d.get('accept')) is bool,'Выберите согласие или отказ')
        o['answer']=d['accept'];o['status']='returning';o['ready']=s.day+o['travel_days']
        record(s,'Ответ передан гонцу. Подтверждения соглашения ещё нет.','diplomacy')
    elif kind=='break_treaty':
        target=str(d.get('target',''));require(target in FACTIONS and target!='ottoman','Укажите сторону договора')
        if data(s)['subjects'].get('ottoman',{}).get('lord')==target:del data(s)['subjects']['ottoman']
        elif data(s)['subjects'].get(target,{}).get('lord')=='ottoman':del data(s)['subjects'][target]
        for t in data(s)['treaties'].values():
            if {t['a'],t['b']}=={'ottoman',target} and t['status']=='active':t['status']='broken'
        s.relations[relation_key('ottoman',target)].update(truce_until=0,access_until=0)
        data(s).setdefault('grievances',{})[target]=s.day
        record(s,'Данное слово государству '+FACTIONS[target]+' отозвано. Получатель вправе пересмотреть поддержку и отношения.','broken_promise')
    elif kind=='vassal_levy':request_levy(s,'ottoman',str(d.get('target','')),d.get('count',10))
    else:return False
    return True

def contacts(s):
    from campaign.ruler.world import contacts as neighbors
    return sorted(set(neighbors(s))|{fid for fid,v in data(s)['subjects'].items() if v['lord']=='ottoman'}|({data(s)['subjects']['ottoman']['lord']} if 'ottoman' in data(s)['subjects'] else set()))

def request_levy(s,lord,subject,n):
    contract=data(s)['subjects'].get(subject);require(contract and contract['lord']==lord,'Это государство не обязано вам военной помощью')
    require(type(n) is int and 1<=n<=200,'Укажите от 1 до 200 готовых воинов')
    require(not any(x['subject']==subject and x['status']!='returned' for x in data(s)['loans'].values()),'Контингент уже запрошен или ещё не вернулся')
    sources=[p for p in s.places.values() if p.controller==subject and p.id not in s.sieges]
    require(sources,'Нет безопасного места для сбора')
    p=max(sources,key=lambda p:count(p.garrison));available=sum(c.count for c in p.garrison if c.troop=='militia')*contract['levy']//100
    require(n<=available,f'По договору здесь доступно {available} ополченцев. Новые люди из ничего не появляются')
    ident=uid(s,'contingent');data(s)['loans'][ident]={'id':ident,'lord':lord,'subject':subject,'province':p.id,'count':n,'status':'requested','ready':s.day+messenger(s,lord,subject),'due':s.day+180,'army':None}
    if 'ottoman' in [lord,subject]:record(s,f'Запрошен контингент {n} воинов из {name(p.id)}. До прибытия приказа гарнизон остаётся на месте.','order')

def _loans(s):
    from campaign.ruler.core import troops
    for x in data(s)['loans'].values():
        if x['status']=='requested' and s.day>=x['ready']:
            p=s.places[x['province']];contract=data(s)['subjects'].get(x['subject'])
            if not contract or contract['lord']!=x['lord'] or p.controller!=x['subject'] or p.id in s.sieges or troops(p.garrison)['militia']*contract['levy']//100<x['count']:
                x['status']='returned';record(s,'Сбор контингента сорван: договор или доступные силы изменились.','obstruction');continue
            units=take(s,p.garrison,{'militia':x['count']});person=uid(s,'levy-captain')
            s.people[person]=Person(person,'Начальник контингента '+FACTIONS[x['subject']],1260+s.day//365,p.id,'commander',faction=x['subject'])
            aid=uid(s,'army');s.armies[aid]=Army(aid,x['lord'],p.id,units,person,grain=0)
            army=s.armies[aid];n=min(p.grain,army.size*20);p.grain-=n;army.grain+=n
            x.update(status='serving',army=aid)
            path=route(s,p.id,capital(s,x['lord']),x['lord'],hostile_end=False,military=True)
            if path:army.travel={'path':path,'left':duration(p.id,path[0])}
            record(s,f'Контингент из {name(p.id)} выступил. Гарнизон уменьшился на {x["count"]} воинов.','military')
        if x['status'] not in ['serving','returning']:continue
        a=s.armies.get(x['army'])
        if not a or not a.size:x['status']='returned';continue
        if s.day>=x['due'] or x['status']=='returning':
            x['status']='returning'
            homes=[p for p in s.places.values() if p.controller==x['subject'] and p.id not in s.sieges]
            if a.location in [p.id for p in homes] and not a.travel:
                p=s.places[a.location];p.garrison.extend(a.cohorts);a.cohorts=[];p.grain+=a.grain;a.grain=0
                money(s,x['lord'],a.funds);a.funds=0;a.mission=None;x['status']='returned';s.people[a.commander].role='officer'
                record(s,'Контингент вернулся: сохранившиеся люди и подготовка внесены в местный гарнизон.','military')
            elif not a.travel and homes:
                paths=[route(s,a.location,p.id,a.faction,military=True) for p in homes]
                paths=[p for p in paths if p]
                if paths:
                    path=min(paths,key=len);a.mission=None;a.travel={'path':path,'left':duration(a.location,path[0]),'retreat':True}

def _commerce(s,t):
    """A trade agreement permits actual paid cargo, not a passive gold generator."""
    for buyer,seller in [(t['a'],t['b']),(t['b'],t['a'])]:
        if treasury(s,buyer)<10 or any(c.get('trade')==t['id'] and c['faction']==buyer for c in s.foreign_cargo):continue
        dests=[p for p in s.places.values() if p.controller==buyer and p.id not in s.sieges and p.grain<max(1500,count(p.garrison)*45)]
        sources=[p for p in s.places.values() if p.controller==seller and p.id not in s.sieges and p.grain>count(p.garrison)*45+100]
        if not dests or not sources:continue
        p=min(dests,key=lambda p:p.grain);source=max(sources,key=lambda p:p.grain)
        path=route(s,source.id,p.id,buyer,hostile_end=False)
        if path is None:continue
        money(s,buyer,-10);money(s,seller,10);source.grain-=100
        s.foreign_cargo.append({'id':uid(s,'trade-cargo'),'trade':t['id'],'seller':seller,'faction':buyer,'army':None,'location':source.id,'target':p.id,'grain':100,'path':path,'left':duration(source.id,path[0]) if path else 1})
        if 'ottoman' in [buyer,seller]:record(s,f'По торговому договору оплачено 100 пайков: {name(source.id)} → {name(p.id)}. Груз ещё в пути.','trade')

def tick(s):
    if not data(s):return
    from campaign.ruler.core import effective_power,war
    for fid,ident in list(data(s)['rulers'].items()):
        previous=s.people[ident];site=capital(s,fid)
        if not site or previous.status not in ['dead','retired']:continue
        successor=uid(s,'sovereign');p=Person(successor,'Преемник двора: '+FACTIONS[fid],calendar(s)['year']-30,site,'ruler',faction=fid)
        s.people[successor]=p;data(s)['rulers'][fid]=successor;s.places[site].governor=successor
        if fid in contacts(s):record(s,p.name+' принял печать. Договоры, недоимки и существующие войска государства сохранены.','succession')
    for o in list(data(s)['offers'].values()):
        if o['status'] in ['accepted','rejected','expired']:continue
        if o['status']=='travelling' and s.day>=o['ready']:
            if o['b']=='ottoman':o['status']='arrived';record(s,FACTIONS[o['a']]+': доставлено предложение «'+KINDS[o['kind']]+'».','new_offer')
            else:o.update(status='returning',answer=accept(s,o),ready=s.day+o['travel_days'])
        if o['status']=='arrived' and s.day>o['due']:o.update(status='expired');money(s,o['a'],o['payment']);o['payment']=0
        if o['status']=='returning' and s.day>=o['ready']:
            try:
                require(o['answer'],'Предложение отклонено');agree(s,o)
            except RuleError as error:
                money(s,o['a'],o['payment']);o['payment']=0;o['status']='rejected'
                if 'ottoman' in [o['a'],o['b']]:record(s,f'Посольство завершилось без соглашения: {error}. Зарезервированный платёж возвращён.','diplomacy')
    for t in data(s)['treaties'].values():
        if t['status']=='active' and t['until'] is not None and s.day>=t['until']:
            t['status']='expired'
            if 'ottoman' in [t['a'],t['b']]:record(s,'Истёк срок соглашения «'+KINDS[t['kind']]+'».','agreement')
        if t['status']=='active' and t['kind']=='trade' and s.day%30==0:_commerce(s,t)
    for subject,c in list(data(s)['subjects'].items()):
        if s.day%30==0 and c['last_paid']!=s.day:
            c['last_paid']=s.day;due=c['tribute']+c['arrears'];paid=min(treasury(s,subject),due)
            money(s,subject,-paid);money(s,c['lord'],paid);c['arrears']=due-paid
            if 'ottoman' in [subject,c['lord']]:record(s,f'Вассальная выплата: {FACTIONS[subject]} передало {paid} монет. Недоимка {c["arrears"]}.','accounts')
            accounts=s.flags.get('last_accounts',{})
            if accounts.get('day')==s.day:
                if subject=='ottoman':accounts['expense']+=paid
                elif c['lord']=='ottoman':accounts['income']+=paid
    for candidate,c in data(s)['claims'].items():
        p=s.people[candidate]
        if c.get('status')=='travelling' and not p.travel:
            dest=capital(s,c['target'])
            if not dest or p.status!='active' or p.location!=dest or data(s)['subjects'].get(c['target'],{}).get('lord')!='ottoman':c['status']='failed';p.travel=None;continue
            old=s.people.get(data(s)['rulers'].get(c['target']));
            if old:old.status='retired'
            p.location=dest;p.travel=None;p.faction=c['target'];p.role='ruler';data(s)['rulers'][c['target']]=p.id;s.places[dest].governor=p.id;c['status']='installed'
            record(s,p.name+' прибыл в '+name(dest)+' и принял власть. Местные войска и обязательства сохранились.','appointment')
    _loans(s)
    if s.day%90:return
    for subject,c in list(data(s)['subjects'].items()):
        lord=c['lord']
        if lord=='ottoman' or not any(war(s,lord,f) for f in FACTIONS):continue
        if any(x['subject']==subject and x['status']!='returned' for x in data(s)['loans'].values()):continue
        sources=[p for p in s.places.values() if p.controller==subject and p.id not in s.sieges]
        n=min(50,max((sum(x.count for x in p.garrison if x.troop=='militia')*c['levy']//100 for p in sources),default=0))
        if n:
            if subject=='ottoman':
                if not any(o['a']==lord and o['b']==subject and o['kind']=='levy' and o['status'] in ['travelling','arrived','returning'] for o in data(s)['offers'].values()):propose(s,lord,subject,'levy',levy=n)
            else:request_levy(s,lord,subject,n)
    for fid,r in s.polities.items():
        if not capital(s,fid) or root(s,fid)!=fid:continue
        neighbors=sorted({root(s,s.places[n].controller) for p in s.places.values() if p.controller==fid for n in ADJACENCY[p.id]}-{fid})
        own=sum(effective_power(s,a) for a in s.armies.values() if a.faction==fid and a.size)
        for other in neighbors:
            if root(s,other)==fid:continue
            known=[k for k in r.intelligence.values() if k['controller']==other and s.day-k['day']<=45]
            threat=max((k.get('field_by',{}).get(other,k['field'] if k['controller']==other else 0) for k in r.intelligence.values() if s.day-k['day']<=45),default=0)
            lost=any(p.owner==fid and p.controller==other for p in s.places.values())
            if war(s,fid,other):
                if (lost or data(s)['defeats'].get(fid)) and own<threat*.7 and fid not in data(s)['subjects']:kind='submit'
                elif data(s)['defeats'].get(other,0)>0 and own>threat*1.5 and root(s,other)==other:kind='demand'
                elif r.arrears or r.doctrine=='trade' or own<threat:kind='peace'
                else:continue
            elif r.doctrine=='trade' and not active(s,fid,other,'trade'):kind='trade'
            elif threat>own and not active(s,fid,other,'nap'):kind='nap'
            elif any(war(s,fid,x) and war(s,other,x) for x in FACTIONS) and not active(s,fid,other,'alliance'):kind='alliance'
            elif known and s.day>=365 and s.day-r.last_war>=720 and not r.arrears and own>min(k['defense']*(1+k['walls']/50)+k['field'] for k in known)*1.6 and s.day>=s.relations[relation_key(fid,other)].get('truce_until',0):
                declare(s,fid,other);r.last_war=s.day;break
            else:continue
            if not any(o['a']==fid and o['b']==other and o['kind']==kind and o['status'] in ['travelling','arrived','returning'] for o in data(s)['offers'].values()):propose(s,fid,other,kind)
            break

def public(s):
    d=data(s)
    return {'treaties':[dict(t,name=KINDS[t['kind']]) for t in d['treaties'].values() if 'ottoman' in [t['a'],t['b']] or t['status']=='active'],
            'offers':[{k:v for k,v in o.items() if k!='answer'}|{'name':KINDS[o['kind']]} for o in d['offers'].values() if o['a']=='ottoman' or o['b']=='ottoman' and o['status']!='travelling'],
            'subjects':{fid:dict(c) for fid,c in d['subjects'].items() if fid=='ottoman' or c['lord']=='ottoman'},
            'loans':[dict(x) for x in d['loans'].values() if 'ottoman' in [x['lord'],x['subject']]],
            'courts':[{'faction':f,'person':p,'name':s.people[p].name,'status':s.people[p].status} for f,p in d['rulers'].items() if f in contacts(s)],
            'contacts':contacts(s)}
