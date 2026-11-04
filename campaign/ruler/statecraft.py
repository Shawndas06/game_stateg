"""Living-state orchestration: authority, causal cases and bounded interference."""
from copy import deepcopy
from campaign.engine import RuleError, require
from campaign.content import FACTIONS
from campaign.ruler.core import count, learn, name, record, roll, ruler_location, spend, uid
from campaign.ruler import diplomacy, knowledge

def enable(s):
    diplomacy.enable(s)
    if not diplomacy.data(s)['specialists']:knowledge.enable(s)

def command(s,kind,d):
    if kind=='statecraft_enable':
        require(s.rules_version>=4,'Сначала перейдите в большую кампанию');enable(s);return True
    if s.rules_version<5:return False
    if diplomacy.command(s,kind,d) or knowledge.command(s,kind,d):return True
    state=diplomacy.data(s)
    if kind=='plan_order':
        summary=_plan(s,d)
        state['draft']={'revision':s.revision+1,'command':deepcopy(d),'summary':summary}
    elif kind=='execute_plan':
        draft=state.get('draft');require(draft and draft['revision']==s.revision,'Положение изменилось. Заново проверьте ведомость похода')
        _plan(s,draft['command'],execute=True);state.pop('draft',None)
    elif kind=='cancel_building':
        p=s.places.get(str(d.get('province','')))
        require(p and p.controller=='ottoman' and p.construction,'Здесь нет ваших текущих работ')
        p.reserve+=p.construction['workers'];p.construction=None
        record(s,'Строительство прекращено, оставшиеся работники освобождены. Израсходованные материалы не возвращаются.','building')
    elif kind=='governance_policy':
        pid=str(d.get('province',''));p=s.places.get(pid);person=s.people.get(p.governor) if p else None
        require(p and p.controller=='ottoman' and p.owner=='ottoman' and person and person.status=='active' and person.location==pid and not person.travel,'Нужен действующий управитель, прибывший в признанное владение')
        cap=d.get('budget');grain=d.get('grain_days',21);guards=d.get('guards',20)
        require(type(cap) is int and 0<=cap<=200 and type(grain) is int and 7<=grain<=60 and type(guards) is int and 0<=guards<=80,'Проверьте лимит расходов, запас и гарнизон')
        require(all(type(d.get(k,False)) is bool for k in ['repair','purchase','recruit']),'Разрешения должны быть явными')
        old=state['policies'].get(pid,{})
        state['policies'][pid]={'person':person.id,'budget':cap,'grain_days':grain,'guards':guards,'repair':d.get('repair',False),'purchase':d.get('purchase',False),'recruit':d.get('recruit',False),'period':s.day//30,'spent':old.get('spent',0) if old.get('period')==s.day//30 else 0,'status':'active'}
        record(s,person.name+f': получены пределы повседневных полномочий в {name(pid)}. Расходы допускаются по фактической необходимости, до {cap} монет за период.','order')
    elif kind=='intrigue':
        target=str(d.get('target',''));person=str(d.get('person',''));op=d.get('operation')
        require(target in diplomacy.contacts(s) and person==state['rulers'].get(target),'Сначала нужен известный вам правитель и установленный контакт')
        require(op in ['information','defection','revolt'],'Выберите цель тайного поручения')
        if op=='revolt':require(target in state['subjects'] and state['subjects'][target]['lord']!='ottoman','Нужен чужой вассал с собственным правителем')
        require(not any(x['target']==target and x['status']=='active' for x in state['plots'].values()),'У этого двора уже действует ваше поручение')
        cost=25 if op=='information' else 80;spend(s,cost);ident=uid(s,'agent')
        state['plots'][ident]={'id':ident,'target':target,'person':person,'operation':op,'ready':s.day+diplomacy.messenger(s,'ottoman',target)+30,'status':'active','cost':cost}
        record(s,'Связному выделены средства. О результате тайного поручения пока сведений нет.','order')
    elif kind=='resolve_case':
        case=state['cases'].get(str(d.get('case','')));choice=d.get('choice')
        require(case and case['status']=='open','Это дело уже закрыто или не существует')
        p=s.places[case['province']];person=s.people.get(case.get('person'))
        require(choice in ['acknowledge','fund','investigate','arrest'],'Выберите распоряжение по делу')
        if choice=='fund':
            spend(s,25)
            if case['kind']=='vassal':diplomacy.money(s,p.controller,25)
            elif person:person.wealth+=25
            if person:person.trust=min(100,person.trust+15)
            if case['kind']=='mutiny':p.unrest=max(0,p.unrest-20)
            else:
                from campaign.ruler.civil import obligation
                obligation(s,'protection','merchants',s.day+90,province=p.id)
        elif choice=='investigate':
            from campaign.ruler.civil import command as civil_command
            civil_command(s,'audit',{'province':p.id})
        elif choice=='arrest':
            require(person and person.location==ruler_location(s) and count(p.garrison)>=15,'Для задержания человек должен находиться при вашей охране; вызовите его и обеспечьте гарнизон')
            person.status='confined';person.role='officer';p.governor=None
            if not case.get('evidence'):p.unrest=min(100,p.unrest+10)
        if person:
            from campaign.ruler.court import remember
            remember(s,person.id,case['id'],person.name+': правитель рассмотрел дело «'+case['title']+'» и выбрал '+{'acknowledge':'принять доклад','fund':'выделить средства','investigate':'проверить сведения','arrest':'задержать исполнителя'}[choice]+'.')
        case.update(status='answered',choice=choice,answered=s.day)
    elif kind=='levy_return':
        loan=state['loans'].get(str(d.get('loan','')));require(loan and 'ottoman' in [loan['lord'],loan['subject']] and loan['status']=='serving','Контингент сейчас не находится на службе')
        loan['due']=s.day;record(s,'Передано распоряжение вернуть контингент. Воинам предстоит пройти обратную дорогу.','order')
    else:return False
    return True

def _plan(s,d,execute=False):
    from campaign.ruler import military
    from campaign.ruler.core import own_army, route, troops
    trial=s if execute else deepcopy(s);a=own_army(trial,str(d.get('army','')))
    add=d.get('troops',{})
    require(isinstance(add,dict),'Укажите состав подкрепления')
    if add:military.command(trial,'transfer',{'army':a.id,'direction':'to_army','troops':add})
    mission={k:v for k,v in d.items() if k!='troops'}
    military.command(trial,'mission',mission)
    p=trial.places[a.location];path=route(trial,a.location,str(d['target']),a.faction,military=True)
    warnings=[]
    if p.controller==a.faction and count(p.garrison)<15:warnings.append(f'{name(p.id)}: останется {count(p.garrison)} воинов. Охрана ворот и складов ослаблена.')
    food=a.grain//max(1,a.size)
    if food<14:warnings.append(f'В обозе продовольствия примерно на {food} дней. Подготовьте поставку или разрешите закупки в пределах походной казны.')
    return {'army':a.id,'commander':a.commander,'location':a.location,'target':d['target'],'troops':troops(a.cohorts),'garrison':troops(p.garrison),'food_days':food,'funds':d.get('funds',0),'deadline':s.day+d.get('days',180),'route':path or [],'warnings':warnings}

def _policy(s):
    from campaign.ruler import civil
    for pid in list(diplomacy.data(s)['policies']):
        rule=diplomacy.data(s)['policies'][pid]
        p=s.places[pid];person=s.people[rule['person']]
        valid=p.controller=='ottoman' and p.owner=='ottoman' and p.governor==person.id and person.status=='active' and person.location==pid and not person.travel and pid not in s.sieges
        if not valid:
            if rule['status']!='paused':record(s,f'{name(pid)}: полномочия приостановлены — исполнитель отсутствует, изменён или владение небезопасно.','obstruction')
            rule['status']='paused';continue
        rule['status']='active'
        if rule['period']!=s.day//30:rule.update(period=s.day//30,spent=0)
        limit=min(s.gold,max(0,rule['budget']-rule['spent']))
        if limit<=0:continue
        task=None;payload={'province':pid,'_delivered':True}
        if rule['repair'] and p.walls<p.max_walls and not p.construction and (p.max_walls-p.walls)*2<=limit:task='construction';payload['building']='repair'
        elif rule['purchase'] and p.grain<max(100,count(p.garrison)*rule['grain_days']) and limit>=10 and not any(c['target']==pid and c['kind']=='purchase' and c['status'] in ['moving','held','assembling'] for c in s.transports.values()):task='trade';payload.update(mode='purchase',amount=min(2000,limit//10*100),escort=0,escort_province=pid)
        elif rule['recruit'] and count(p.garrison)<rule['guards'] and not p.training:
            n=min(40,rule['guards']-count(p.garrison),p.reserve,limit//2)
            if n:task='raise';payload.update(troop='militia',count=n)
        if not task:continue
        trial=deepcopy(s);trial.outbox=[];start_gold=trial.gold
        try:
            if task=='raise':
                from campaign.ruler.military import command as military_command
                military_command(trial,task,payload)
            else:civil.command(trial,task,payload)
            used=start_gold-trial.gold;require(0<=used<=limit,'Превышены полномочия по расходам')
        except RuleError as error:
            reason=str(error)
            if rule.get('obstacle')!=reason:rule['obstacle']=reason;record(s,person.name+': '+reason,'obstruction')
            continue
        # Keep the state object identity; local references above refer to the old copy.
        trial.flags['statecraft']['policies'][pid]['spent']+=used
        trial.flags['statecraft']['policies'][pid].pop('obstacle',None)
        s.__dict__.update(trial.__dict__)
        record(s,person.name+f' распорядился по полученным полномочиям. Выделено {used} монет; исполнение подтверждается отдельно.','routine')

def _case(s,key,kind,pid,title,text,person=None,evidence=False):
    cases=diplomacy.data(s)['cases']
    if key in cases:return
    cases[key]={'id':key,'kind':kind,'province':pid,'title':title,'text':text,'person':person,'evidence':evidence,'status':'open','opened':s.day,'due':s.day+30}
    record(s,title+'. '+text,'new_case',s.people[person].name if person in s.people else 'Донесение местного писца')

def _cases(s):
    state=diplomacy.data(s)
    for pid,p in s.places.items():
        if p.controller!='ottoman':continue
        person=s.people.get(p.governor)
        if pid in s.hazards:
            _case(s,'road:'+pid,'road',pid,'Купцы просят защиты дороги',f'У {name(pid)} действует разбойный отряд. Деньги сами по себе не очистят дорогу: требуется реальная охрана.',p.governor)
            c=state['cases']['road:'+pid]
            if c['status']=='answered' and count(p.garrison)<15:_case(s,'garrison:'+pid,'garrison',pid,'Комендант просит оставить охрану',f'В гарнизоне {name(pid)} осталось {count(p.garrison)} воинов. Сборы и отправка войск не заменяют защиту складов.',p.governor)
        elif 'road:'+pid in state['cases'] and state['cases']['road:'+pid]['status']!='resolved':
            state['cases']['road:'+pid]['status']='resolved'
            from campaign.ruler.court import accomplish
            accomplish(s,'statecraft-road:'+pid,'Дорога открыта',name(pid)+': разбойный отряд действительно устранён; прежнее обращение купцов закрыто.')
        if person and person.status=='active' and p.unrest>=65:
            _case(s,'mutiny:'+pid,'mutiny',pid,'Управитель требует пересмотра условий',f'{name(pid)}: жалобы и тяжёлые сборы вызвали неповиновение. {person.name} требует разбирательства в течение месяца.',person.id)
        case=state['cases'].get('mutiny:'+pid)
        if case and case['status']=='open' and s.day>case['due'] and person and person.status=='active':
            case['status']='mutiny';person.trust=max(0,person.trust-20)
            for a in s.armies.values():
                if a.commander==person.id and a.mission:a.mission['status']='awaiting'
            p.tax='relief';record(s,person.name+' самовольно остановил чрезвычайные сборы. Прежние люди и гарнизон остаются на месте; требуется расследование или соглашение.','intrigue')
            case['status']='open';case['due']=s.day+90;case['evidence']=True
    for subject,c in list(state['subjects'].items()):
        if subject!='ottoman' and c['lord']=='ottoman' and c['arrears']>=max(20,c['tribute']*3):
            pid=diplomacy.capital(s,subject)
            if pid:_case(s,'subject:'+subject,'vassal',pid,'Вассал просит пересмотреть дань',FACTIONS[subject]+f': накопилась недоимка {c["arrears"]}. Прежде чем требовать новую службу, рассмотрите условия.',state['rulers'].get(subject))
        ruler=s.people.get(state['rulers'].get(subject));capital=diplomacy.capital(s,subject)
        strained=capital and ruler and (c['arrears']>=max(30,c['tribute']*4) or s.places[capital].unrest>=75)
        if subject!='ottoman' and strained:
            if 'demand_since' not in c:
                c['demand_since']=s.day
                if c['lord']=='ottoman':record(s,ruler.name+' требует облегчить присягу: недоимка или беспорядки не позволяют продолжать прежнюю службу. На ответ отведено 90 дней.','new_case')
            elif s.day-c['demand_since']>=90:
                lord=c['lord'];del state['subjects'][subject]
                diplomacy.declare(s,subject,lord,defensive=True)
                record(s,ruler.name+' отказался от присяги после неразрешённого спора. Его прежние владения и войска участвуют в мятеже.','intrigue')
        else:c.pop('demand_since',None)

def _plots(s):
    state=diplomacy.data(s)
    for x in state['plots'].values():
        if x['status']!='active' or s.day<x['ready']:continue
        p=s.people.get(x['person']);target=x['target'];site=diplomacy.capital(s,target)
        if not site or not p or p.status!='active':x['status']='failed';record(s,'Связной не смог завершить поручение: положение адресата изменилось.','intrigue');continue
        if x['operation']=='information':learn(s,site,'Донесение связного');x['status']='completed';record(s,'Доставлены сведения из '+name(site)+'. Они отражают день наблюдения, а не намерения противника.','delivery')
        elif x['operation']=='revolt':
            contract=state['subjects'].get(target)
            if contract and (contract['arrears']>0 or p.trust<35):
                lord=contract['lord'];del state['subjects'][target];diplomacy.money(s,target,x['cost']);diplomacy.declare(s,target,lord,defensive=True);x['status']='completed'
                record(s,FACTIONS[target]+' объявило об отказе от присяги. Средства переданы существующему двору; новые армии не созданы.','intrigue')
            else:x['status']='failed';record(s,'Правитель не принял предложение разорвать присягу. Верность нельзя купить одним письмом.','intrigue')
        else:
            # A ruler can change diplomatic allegiance, not donate an entire army for free.
            if p.trust<30 and s.polities[target].arrears>0 and target not in state['subjects']:
                diplomacy.propose(s,target,'ottoman','submit');x['status']='completed';record(s,'Через связного получено обещание направить предложение о покровительстве. Договор ещё не заключён.','intrigue')
            else:x['status']='failed';record(s,'Попытка склонить правителя не удалась; прежние обязательства оказались прочнее предложения.','intrigue')
        if roll(s,'agent-exposure:'+x['id'])<.25:
            state.setdefault('grievances',{})[target]=s.day;record(s,'Письмо связного оказалось известно другому двору. Дальнейшие переговоры осложнены.','intrigue')

def tick(s):
    if s.rules_version<5:return
    knowledge.tick(s);diplomacy.tick(s);_policy(s);_cases(s);_plots(s)

def tasks(s):
    result=[]
    for a in s.armies.values():
        if a.faction=='ottoman' and a.mission:result.append({'id':a.mission['id'] if 'id' in a.mission else a.id,'kind':'army','target':a.mission['target'],'army':a.id,'status':a.mission['status'],'person':a.commander,'due':a.mission['deadline'],'funds':a.funds})
    for e in s.edicts:result.append({'id':e['id'],'kind':'civil','target':e['province'],'status':'issued','due':None,'funds':e['escrow']})
    for x in s.couriers:
        if x['kind']=='order':result.append({'id':x['id'],'kind':'army','target':x['mandate']['target'],'army':x['army'],'status':'issued','due':x['mandate']['deadline'],'funds':x['mandate']['funds']})
    for c in s.transports.values():result.append({'id':c['id'],'kind':'cargo','target':c['target'],'status':c['status'],'due':None,'funds':0})
    for w in diplomacy.data(s)['projects'].values():
        if w['actor']=='ottoman':result.append({'id':w['id'],'kind':'workshop','target':w['province'],'status':w['status'],'due':s.day+w['left'] if w['status']=='active' else None,'funds':w['cost'],'person':w['master']})
    for pid,p in s.places.items():
        if p.controller!='ottoman':continue
        if p.construction:result.append({'id':pid,'kind':'construction','target':pid,'status':'awaiting' if p.construction.get('paused') else 'active','due':s.day+p.construction['work'],'funds':0})
        if p.training:result.append({'id':pid,'kind':'training','target':pid,'status':'active','due':max(t['ready'] for t in p.training),'funds':0})
    for x in s.appointments:result.append({'id':x['id'],'kind':'appointment','target':x['province'],'status':'moving','person':x['person'],'funds':0,'due':None})
    for pid,m in diplomacy.data(s)['specialists'].items():
        p=s.people[pid]
        if m['employer']=='ottoman' and p.travel:result.append({'id':pid,'kind':'master','target':p.travel['target'],'status':'moving','person':pid,'funds':0,'due':None})
    for o in diplomacy.data(s)['offers'].values():
        if 'ottoman' in [o['a'],o['b']] and o['status'] in ['travelling','returning'] and (o['a']=='ottoman' or o['status']=='returning'):
            result.append({'id':o['id'],'kind':'embassy','target':diplomacy.capital(s,o['b']) or s.capital,'status':'moving','funds':o['payment'],'due':o['ready']})
    return result

def waiting(s,w,initial=False):
    require(isinstance(w,dict),'Укажите ожидаемое дело')
    kind=w.get('kind');ident=w.get('id')
    require(isinstance(ident,str),'Укажите существующее дело из списка поручений')
    if kind=='workshop':
        p=diplomacy.data(s)['projects'].get(ident);require(p and p['actor']=='ottoman','Такое дело недоступно')
        return p['status'] in ['completed','cancelled','awaiting']
    if kind=='embassy':
        o=diplomacy.data(s)['offers'].get(ident);require(o and (o['a']=='ottoman' or o['b']=='ottoman' and o['status']!='travelling'),'Такое посольство недоступно')
        return o['status'] in ['arrived','accepted','rejected','expired']
    if kind=='master':
        p=s.people.get(ident);ours=diplomacy.data(s)['specialists'].get(ident,{}).get('employer')=='ottoman'
        if initial:require(p and ours,'Это не ваш служитель')
        return not p or not ours or not p.travel or p.status!='active'
    if kind=='cargo':
        c=s.transports.get(ident);require(c,'Груз недоступен');return c['status'] in ['completed','cancelled','seized']
    if kind=='training':
        p=s.places.get(ident)
        if initial:require(p and p.controller=='ottoman','Владение недоступно')
        return not p or p.controller!='ottoman' or not p.training
    if kind=='construction':
        p=s.places.get(ident)
        if initial:require(p and p.controller=='ottoman','Владение недоступно')
        return not p or p.controller!='ottoman' or bool(p.construction and p.construction.get('paused')) or not p.construction and not any(e['kind']=='construction' and e['province']==ident for e in s.edicts)
    require(False,'Выберите обучение, строительство, работу мастерской или доставку')

def validate(s):
    if s.rules_version<5:return
    d=diplomacy.data(s)
    for f,c in d['subjects'].items():assert f in FACTIONS and c['lord'] in FACTIONS and f!=diplomacy.root(s,f) and c['arrears']>=0
    for w in d['projects'].values():assert w['workers']>=0 and w['left']>=0 and w['province'] in s.places and w['master'] in s.people
    for r in d['policies'].values():assert 0<=r['spent']<=200 and r['person'] in s.people

def public(s):
    if s.rules_version<5:return None
    d=diplomacy.data(s)
    return {**diplomacy.public(s),**knowledge.public(s),'draft':deepcopy(d.get('draft',{}).get('summary')),'tasks':tasks(s),'policies':{k:dict(v) for k,v in d['policies'].items()},'cases':[dict(x) for x in d['cases'].values()],
            'plots':[{k:v for k,v in x.items() if k not in ['chance','loyalty']} for x in d['plots'].values()],
            'deliveries':[{k:v for k,v in c.items() if k in ['id','faction','seller','location','target','grain','trade']} for c in s.foreign_cargo if c.get('trade') and 'ottoman' in [c['faction'],c.get('seller')]]}
