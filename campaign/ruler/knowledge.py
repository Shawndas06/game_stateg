"""People carry practical skills; workshops use local workers and dated projects."""
from collections import deque
from campaign.engine import RuleError,require
from campaign.content import ADJACENCY, TROOPS
from campaign.ruler.core import count, duration, learn, losses, name, record, roll, ruler_location, uid
from campaign.ruler.models import Cohort, Person
from campaign.ruler.diplomacy import data, capital, money, treasury

TECH={
 'carpentry':{'name':'Плотницкое дело','requires':[],'cost':35,'days':60,'effect':'Подготовка плотников и строительство таранов.'},
 'stonework':{'name':'Каменное строительство','requires':[],'cost':50,'days':90,'effect':'Крепостные работы и подготовка каменщиков.'},
 'stone_thrower':{'name':'Каменомёт','requires':['carpentry'],'cost':60,'days':90,'effect':'Сборка метательных машин у места сбора армии.'},
 'tower':{'name':'Осадная башня','requires':['carpentry'],'cost':55,'days':90,'effect':'Сборка башни для осадного войска.'},
 'counterweight':{'name':'Противовесный требушет','requires':['stone_thrower'],'cost':100,'days':180,'effect':'Крупная машина требует обученной команды и длительной сборки.'},
 'mining':{'name':'Осадные подкопы','requires':['stonework'],'cost':60,'days':90,'effect':'Подготовка сапёров, поиск скрытых проходов и подкоп стен.'},
 'logistics':{'name':'Дорожное и обозное дело','requires':[],'cost':40,'days':90,'effect':'Работы на охраняемой дороге и организация местной доставки.'},
}
ENGINES={'ram':{'name':'Таран','tech':'carpentry','cost':35,'days':30,'workers':5,'damage':2},'catapult':{'name':'Каменомёт','tech':'stone_thrower','cost':80,'days':60,'workers':8,'damage':4},'tower':{'name':'Осадная башня','tech':'tower','cost':70,'days':60,'workers':10,'damage':3},'trebuchet':{'name':'Требушет','tech':'counterweight','cost':140,'days':120,'workers':15,'damage':7}}

def enable(s):
    d=data(s);d.setdefault('engines',{});d.setdefault('siege_work',{})
    for title,site,skills,fee in [('Али, строитель','eskisehir',['carpentry','stonework','logistics'],35),('Димитрий, мастер осадного дела','nicomedia',['carpentry','stonework','stone_thrower','mining','tower'],60)]:
        pid=uid(s,'master');s.people[pid]=Person(pid,title,1265,site,'master',faction=s.places[site].controller,skills={'command':20,'stewardship':45,'siege':60,'logistics':50})
        d['specialists'][pid]={'knows':skills,'fee':fee,'wage':3,'until':s.day+120,'employer':None,'known':True}
    record(s,'Два мастера прислали условия найма. Их знания и плата указаны в разделе развития; предложение имеет срок.','master')

def path(start,end):
    queue=deque([(start,[])]);seen={start}
    while queue:
        at,steps=queue.popleft()
        if at==end:return steps
        for n in ADJACENCY[at]:
            if n not in seen:seen.add(n);queue.append((n,steps+[n]))
    require(False,'Нет дороги к месту службы')
def travel(s,p,target,purpose='master_move'):
    steps=path(p.location,target)
    if steps:p.travel={'purpose':purpose,'target':target,'path':steps,'left':duration(p.location,steps[0])}
def available(s,actor,site,tech):
    return [p for pid,p in s.people.items() if p.status=='active' and not p.travel and p.location==site and data(s)['specialists'].get(pid,{}).get('employer')==actor and tech in data(s)['specialists'][pid]['knows']]
def busy(s,pid):return any(p.get('master')==pid and p['status'] in ['active','awaiting'] for p in data(s)['projects'].values()) or any(p.get('master')==pid and p['status']=='active' for p in data(s)['siege_work'].values()) or any(p.construction and p.construction.get('master')==pid for p in s.places.values())
def start(s,actor,site,kind,master,**args):
    require(site in s.places,'Выберите существующее место работы')
    p=s.places[site];require(p.controller==actor and p.owner==actor and site not in s.sieges,'Для работы нужно безопасное, признанное владение')
    if kind=='engine':
        engine=args.get('engine');require(isinstance(engine,str),'Выберите осадное орудие');item=ENGINES.get(engine);require(item is not None,'Выберите осадное орудие')
        require(isinstance(args.get('army'),str),'Выберите принимающую армию')
        army=s.armies.get(args.get('army'));require(army and army.faction==actor and army.location==site and not army.travel,'Армия должна находиться у мастерской')
        require(army.engines<5,'Для этой армии уже достаточно машин; организуйте другой отряд')
        tech=item['tech'];cost=item['cost'];days=item['days'];workers=item['workers']
    elif kind=='learn':
        tech=args.get('tech');require(isinstance(tech,str) and tech in TECH,'Выберите практическое знание');item=TECH[tech]
        require(tech not in data(s)['skills'].get(actor,[]),'Служители уже освоили это знание')
        require(all(k in data(s)['skills'].get(actor,[]) for k in item['requires']),'Сначала подготовьте людей по основным знаниям: '+', '.join(TECH[k]['name'] for k in item['requires']))
        require(not any(x['actor']==actor and x['kind']=='learn' and x.get('tech')==tech and x['status'] in ['active','awaiting'] for x in data(s)['projects'].values()),'Такое обучение уже идёт')
        cost=item['cost'];days=item['days'];workers=3
    else:
        require(kind=='road' and 'road' not in p.buildings,'Дорога уже устроена');tech='logistics';cost=60;days=90;workers=5
    require(any(x.id==master for x in available(s,actor,site,tech)),'Нужен знающий мастер, который уже прибыл в это владение')
    require(not busy(s,master),'Этот мастер уже занят другим делом')
    capacity=2 if s.institutions.get('scribes',{}).get('status')=='active' and actor=='ottoman' else 1
    require(sum(x['province']==site and x['status'] in ['active','awaiting'] for x in data(s)['projects'].values())<capacity,'Местная мастерская занята; писцы позволяют вести вторую ведомость работ')
    require(p.reserve>=workers,f'Нужно {workers} местных работников; свободно {p.reserve}')
    require(p.grain>=workers*7,'Сначала обеспечьте работников продовольствием хотя бы на неделю')
    money(s,actor,-cost);p.reserve-=workers;ident=uid(s,'workshop')
    data(s)['projects'][ident]={'id':ident,'kind':kind,'actor':actor,'province':site,'master':master,'workers':workers,'left':days,'cost':cost,'status':'active',**args}
    if actor=='ottoman':record(s,f'{name(site)}: начаты работы «{item["name"] if kind in ["engine","learn"] else "Дорога"}». Выделено {cost} монет и {workers} работников.','building')

def command(s,kind,d):
    if kind=='hire_master':
        pid=str(d.get('person',''));m=data(s)['specialists'].get(pid);p=s.people.get(pid);site=str(d.get('province',s.capital))
        require(m and p and p.status=='active' and not m['employer'] and s.day<=m['until'],'Мастер уже нанят, выбыл или отозвал предложение')
        require(site in s.places and s.places[site].controller=='ottoman','Выберите своё место службы')
        money(s,'ottoman',-m['fee']);p.wealth+=m['fee'];m['employer']='ottoman';p.faction='ottoman';travel(s,p,site)
        record(s,p.name+' принял плату и приглашение. Работать он сможет после прибытия в '+name(site)+'.','master')
    elif kind=='move_master':
        pid=str(d.get('person',''));p=s.people.get(pid);site=str(d.get('province',''))
        require(p and data(s)['specialists'].get(pid,{}).get('employer')=='ottoman' and p.status=='active' and not p.travel and not busy(s,pid),'Этот мастер не может сейчас выехать')
        require(site in s.places and (s.places[site].controller=='ottoman' or s.sieges.get(site,{}).get('faction')=='ottoman'),'Укажите своё владение или место собственной осады');travel(s,p,site)
    elif kind in ['learn_craft','commission_engine','improve_road']:
        start(s,'ottoman',str(d.get('province',s.capital)),{'learn_craft':'learn','commission_engine':'engine','improve_road':'road'}[kind],str(d.get('person','')),**({'tech':d.get('tech')} if kind=='learn_craft' else {'army':d.get('army'),'engine':d.get('engine')} if kind=='commission_engine' else {}))
    elif kind=='cancel_project':
        p=data(s)['projects'].get(str(d.get('project','')));require(p and p['actor']=='ottoman' and p['status'] in ['active','awaiting'],'Работа уже завершена или не ваша')
        s.places[p['province']].reserve+=p['workers'];p['workers']=0;p['status']='cancelled';record(s,'Работники освобождены. Закупленные материалы и выплаченная плата не возвращаются.','building')
    elif kind=='siege_operation':siege_command(s,d)
    elif kind=='support_claim':
        pid=str(d.get('person',''));p=s.people.get(pid);target=str(d.get('target',''))
        require(p and p.faction=='ottoman' and p.id!=s.ruler_id and p.role!='heir' and p.status=='active' and not p.travel and not any(p.id in [a.commander,a.deputy] for a in s.armies.values()),'Нужен свободный человек при дворе')
        require(p.location==ruler_location(s) and target in s.polities and capital(s,target),'Претендент должен прибыть к вам, а государство — существовать')
        require(not busy(s,pid) and not any(x.governor==pid for x in s.places.values()),'Сначала освободите человека от прежних обязанностей')
        require(pid not in data(s)['claims'],'Притязание уже подготовлено или рассматривается');money(s,'ottoman',-40)
        data(s)['claims'][pid]={'target':target,'ready':s.day+90,'status':'preparing'}
        record(s,p.name+' получил средства на переговоры с местными сторонниками. Подготовка притязания займёт 90 дней; признание ещё предстоит получить.','intrigue')
    else:return False
    return True

def siege_command(s,d):
    pid=str(d.get('province',''));sg=s.sieges.get(pid);op=d.get('operation')
    require(sg and pid in s.knowledge,'Здесь нет известной вам осады')
    own=sg['faction']=='ottoman';p=s.places[pid]
    if op=='sortie':
        require(not own and p.controller=='ottoman','Вылазка доступна защитникам вашей крепости')
        require(s.day>=sg.get('last_sortie',-30)+14,'После вылазки нужно 14 дней на подготовку')
        n=d.get('count');require(type(n) is int and 1<=n<=count(p.garrison),'Укажите действительное число воинов гарнизона')
        attackers=[s.armies[x] for x in sg['armies'] if x in s.armies and s.armies[x].size]
        require(attackers,'У стен больше нет осаждающих');sg['last_sortie']=s.day
        defender_loss=max(1,int(n*(.12 if roll(s,'sortie:'+pid)>.5 else .28)))
        losses(p.garrison,defender_loss)
        for a in attackers:losses(a.cohorts,max(1,n//max(1,len(attackers))//5));a.grain=max(0,a.grain-n*3)
        record(s,f'{name(pid)}: вылазка завершена. Гарнизон потерял {defender_loss} воинов; у осаждающих понесены потери и уничтожены припасы.','battle');return
    require(own and op in ['search','tunnel','infiltrate'],'Выберите поиск прохода, подкоп или попытку проникновения')
    require(not any(x['province']==pid and x['status']=='active' for x in data(s)['siege_work'].values()),'У этой крепости уже действует поручение сапёрам')
    armies=[s.armies[x] for x in sg['armies'] if x in s.armies and s.armies[x].size]
    require(armies,'Нужны реальные осаждающие войска')
    if op=='infiltrate':require(sg.get('passage_found') and not sg.get('passage_used'),'Сначала нужен найденный и ещё не использованный проход')
    master=str(d.get('person',''));require(any(p.id==master for p in available(s,'ottoman',pid,'mining')),'Для такой работы нужен прибывший к осаде мастер подкопов')
    require(not busy(s,master),'Мастер уже выполняет другую работу')
    fee=20 if op=='search' else 35;money(s,'ottoman',-fee);ident=uid(s,'sapper')
    data(s)['siege_work'][ident]={'id':ident,'province':pid,'operation':op,'master':master,'ready':s.day+(14 if op=='search' else 30 if op=='tunnel' else 7),'status':'active','siege_started':sg['started']}
    record(s,f'{name(pid)}: сапёры получили поручение. Результат пока неизвестен.','order')

def _projects(s):
    from campaign.ruler.court import accomplish
    for w in data(s)['projects'].values():
        if w['status'] not in ['active','awaiting']:continue
        p=s.places[w['province']];master=s.people[w['master']]
        if p.controller!=w['actor']:
            p.reserve+=w['workers'];w['workers']=0;w['status']='cancelled';continue
        ready=master.status=='active' and not master.travel and master.location==p.id and data(s)['specialists'][master.id]['employer']==w['actor'] and p.id not in s.sieges and p.grain>=w['workers']
        if not ready:
            w['obstacle']='Проверьте мастера, безопасность владения и продовольствие работников.'
            if w['status']!='awaiting' and w['actor']=='ottoman':record(s,f'{name(p.id)}: работа приостановлена — мастер, безопасность или продовольствие недоступны.','obstruction')
            w['status']='awaiting';continue
        p.grain-=w['workers'];w.pop('obstacle',None);w['status']='active';w['left']=max(0,w['left']-1)
        if w['left']:continue
        if w['kind']=='engine':
            a=s.armies.get(w['army'])
            if not a or a.faction!=w['actor'] or a.location!=p.id or a.travel:
                w['status']='awaiting';w['obstacle']='Армия должна вернуться к мастерской, чтобы принять готовую машину и команду.';continue
            a.engines+=1;data(s)['engines'].setdefault(a.id,[]).append({'id':w['id'],'type':w['engine']})
            a.cohorts.append(Cohort(uid(s,'engine-crew'),'militia',w['workers'],p.id,service='engine_crew'));w['workers']=0
        elif w['kind']=='learn':
            skills=data(s)['skills'].setdefault(w['actor'],[])
            if w['tech'] not in skills:skills.append(w['tech'])
            apprentice=uid(s,'craftsman');s.people[apprentice]=Person(apprentice,'Обученный мастер: '+TECH[w['tech']]['name'],1275+s.day//365,p.id,'master',faction=w['actor'])
            data(s)['specialists'][apprentice]={'knows':[w['tech']],'fee':0,'wage':2,'until':0,'employer':w['actor'],'known':w['actor']=='ottoman'}
        else:
            if p.id in s.hazards and count(p.garrison)<15:w['status']='awaiting';continue
            if 'road' not in p.buildings:p.buildings.append('road');p.prosperity=min(90,p.prosperity+5)
        p.reserve+=w['workers'];w['workers']=0;w['status']='completed'
        if w['actor']=='ottoman':
            record(s,f'{name(p.id)}: работа завершена. Результат внесён в состояние владения, людей или армии.','building')
            accomplish(s,w['id'],'Дело доведено до результата',name(p.id)+': '+(TECH[w['tech']]['name'] if w['kind']=='learn' else ENGINES[w['engine']]['name'] if w['kind']=='engine' else 'устроена дорога'))

def tick(s):
    for p in s.people.values():
        tr=p.travel
        if not tr or tr.get('purpose') not in ['master_move','installation']:continue
        tr['left']-=1
        if tr['left']>0:continue
        p.location=tr['path'].pop(0)
        if tr['path']:tr['left']=duration(p.location,tr['path'][0])
        else:p.travel=None;record(s,p.name+' прибыл в '+name(p.location)+'.','appointment')
    _projects(s)
    if s.day%720==0 and len(data(s)['specialists'])<40:
        site=next((capital(s,f) for f in ['genoa','byzantine','germiyan'] if capital(s,f)),s.capital)
        pid=uid(s,'master');s.people[pid]=Person(pid,['Юсуф','Мануил','Исхак','Михаил'][(s.day//720)%4]+', приглашённый инженер',1265+s.day//365,site,'master',faction=s.places[site].controller,skills={'command':20,'stewardship':45,'siege':65,'logistics':55})
        data(s)['specialists'][pid]={'knows':['carpentry','stone_thrower','counterweight','tower'],'fee':100,'wage':4,'until':s.day+120,'employer':None,'known':True}
        record(s,'Новый мастер прислал условия службы и перечень своих знаний. Предложение ограничено по времени.','master')
    for w in data(s)['siege_work'].values():
        if w['status']!='active' or s.day<w['ready']:continue
        sg=s.sieges.get(w['province']);p=s.places[w['province']];master=s.people[w['master']]
        if not sg or sg['faction']!='ottoman' or sg['started']!=w['siege_started'] or master.status!='active' or master.location!=p.id or master.travel:w['status']='failed';continue
        if w['operation']=='search':
            # Procedural fortifications can have a passage; repeat search cannot reroll it.
            passages=data(s).setdefault('passages',{})
            if p.id not in passages:passages[p.id]=roll(s,'fortress-passage:'+p.id)<.3
            found=passages[p.id];sg['passage_found']=found
            record(s,f'{name(p.id)}: '+('найден узкий проход к укреплению. Охрана и надёжность ещё требуют проверки.' if found else 'пригодного скрытого прохода не найдено.'),'siege_report')
        elif w['operation']=='tunnel':p.walls=max(0,p.walls-12);record(s,f'{name(p.id)}: подкоп повредил участок стены. Это ещё не занятие крепости.','battle')
        else:
            sg['passage_used']=True;success=roll(s,'passage:'+p.id)<.45
            if success:p.walls=max(0,p.walls-15);sg['morale']=max(0,sg['morale']-20)
            else:
                for aid in sg['armies']:losses(s.armies[aid].cohorts,max(1,s.armies[aid].size//10))
            record(s,f'{name(p.id)}: '+('отряд нарушил оборону изнутри; для захвата ещё требуется штурм или сдача.' if success else 'попытка проникновения обнаружена; отряд понёс потери.'),'battle')
        w['status']='completed'
    for pid,m in list(data(s)['specialists'].items()):
        p=s.people[pid]
        if m['employer'] and p.status=='active' and s.day%30==0:
            paid=min(treasury(s,m['employer']),m['wage']);money(s,m['employer'],-paid);p.wealth+=paid
            if m['employer']=='ottoman':
                accounts=s.flags.get('last_accounts',{})
                if accounts.get('day')==s.day:accounts['expense']+=paid
            if paid<m['wage']:
                m['missed']=m.get('missed',0)+1
                if m['missed']>=3:m.update(employer=None,until=s.day+90,fee=max(20,m['fee']));record(s,p.name+' расторг службу после трёх невыплат. Его знания остались при нём.','master')
            else:m['missed']=0
        if not m['employer'] and p.status=='active' and s.day>m['until'] and not p.travel:
            rivals=[f for f in s.polities if capital(s,f) and treasury(s,f)>=m['fee']]
            if rivals:
                buyer=max(rivals,key=lambda f:(treasury(s,f),f));money(s,buyer,-m['fee']);p.wealth+=m['fee'];m['employer']=buyer;p.faction=buyer;travel(s,p,capital(s,buyer))
                if m['known']:record(s,p.name+' принял оплаченный контракт другого двора и выехал к новому месту службы.','master')
    if s.day%90==0:
        for pid,m in list(data(s)['specialists'].items()):
            actor=m['employer'];p=s.people[pid]
            if not actor or actor=='ottoman' or p.status!='active' or p.travel or busy(s,pid):continue
            armies=[a for a in s.armies.values() if a.faction==actor and a.location==p.location and not a.travel and a.size and a.engines<2]
            if not armies:
                homes=[a for a in s.armies.values() if a.faction==actor and a.size and not a.travel and s.places[a.location].owner==actor and s.places[a.location].controller==actor and a.location not in s.sieges]
                if homes:travel(s,p,homes[0].location)
            for k,e in ENGINES.items():
                if armies and e['tech'] in m['knows'] and treasury(s,actor)>=e['cost'] and s.places[p.location].reserve>=e['workers']:
                    try:start(s,actor,p.location,'engine',pid,army=armies[0].id,engine=k)
                    except RuleError:pass
                    break

def cleanup(s):
    for a in s.armies.values():
        if not a.size:a.engines=0;data(s)['engines'].pop(a.id,None)
def siege_bonus(s,a):
    known=data(s).get('engines',{}).get(a.id,[])
    return sum(ENGINES[x['type']]['damage'] for x in known)+max(0,a.engines-len(known))*3
def public(s):
    d=data(s)
    return {'technologies':[dict(v,id=k,learned=k in d['skills'].get('ottoman',[])) for k,v in TECH.items()],
            'masters':[{'id':pid,'name':s.people[pid].name,'location':s.people[pid].location,'status':s.people[pid].status,'travelling':bool(s.people[pid].travel),'busy':busy(s,pid),**{k:m[k] for k in ['knows','fee','wage','until','employer']}} for pid,m in d['specialists'].items() if m['known'] or m['employer']=='ottoman'],
            'projects':[dict(w) for w in d['projects'].values() if w['actor']=='ottoman'],
            'siege_work':[dict(w) for w in d['siege_work'].values()],
            'engines':[dict(v,id=k) for k,v in ENGINES.items()],
            'claims':[dict(c,person=pid,name=s.people[pid].name) for pid,c in d['claims'].items()]}
