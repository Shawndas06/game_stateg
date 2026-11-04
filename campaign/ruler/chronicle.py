"""Open campaign chapters and situation-driven petitions; no repeated free rewards."""
from campaign.engine import require, relation_key
from campaign.content import ADJACENCY
from campaign.ruler import court
from campaign.ruler.core import count, calendar, name, record, roll, spend, uid, war

SCENES={
 'scarcity':('Запасы под угрозой','Распорядитель просит решить, как пережить нехватку продовольствия.',[('buy','Заказать 400 пайков за 40 монет'),('relief','Облегчить местные сборы'),('wait','Оставить распорядителю прежние средства')]),
 'occupation':('Порядок в занятом городе','Представители жителей требуют определить порядок сборов и охраны.',[('charter','Ограничить сборы и признать местные права'),('customary','Сохранить обычные сборы под военным управлением'),('exaction','Распорядиться о чрезвычайном сборе')]),
 'war_pressure':('Требование соседа','Посол требует урегулировать пограничный спор до нового похода.',[('tribute','Передать 100 монет за двухлетнее перемирие'),('negotiate','Направить предложение мира на обычных условиях'),('refuse','Отказать и готовиться к продолжению войны')]),
 'alliance_offer':('Совместный противник','Сосед предлагает согласовать действия против общего противника.',[('subsidy','Выделить союзнику 60 монет на войну'),('pact','Закрепить взаимное ненападение за 40 монет'),('decline','Сохранить самостоятельность')]),
 'pay_dispute':('Требование жалованья','Войско требует расчёта по просроченным выплатам.',[('pay','Погасить текущую задолженность'),('release','Распустить двадцать воинов столичного гарнизона'),('refuse','Приказать продолжать службу без расчёта')]),
 'siege_school':('Обучение осадному делу','Опытные мастера готовы обучить командующего, если его можно оставить при дворе.',[('masters','Оплатить девяносто дней обучения за 80 монет'),('apprentice','Подготовить ученика за 40 монет и полгода'),('defer','Отложить обучение')]),
 'winter_quarters':('Зимняя ставка','Командующий просит определить зимнее снабжение и дальнейшее движение.',[('return','Отозвать армию в столицу'),('supply','Отправить обоз из указанного склада'),('persist','Оставить прежнее поручение')]),
 'heir_school':('Подготовка наследника','Писцы просят выделить время для обучения наследника управлению.',[('teach','Оставить наследника при дворе на полгода за 50 монет'),('field','Сохранить его нынешние обязанности'),('defer','Вернуться к этому вопросу позднее')]),
}
CHAPTERS=[
 ('Утвердить власть','Получить опору и разрешить первый кризис бейлика'),
 ('Удержать границу','Сохранить четыре владения, обеспечить дороги и выдержать год без долгов по содержанию'),
 ('Закрепиться в Вифинии','Закрепить шесть владений и наладить земельный учёт'),
 ('Опорный город','Закрепить Бурсу, обеспечить её гарнизон и снабжение'),
 ('Управление областями','Удержать десять владений, назначить управителей и рассчитаться с долгами'),
 ('Держава на перепутье','Закрепить Константинополь и шестнадцать владений, обеспечить действующие службы и расчёты'),
]


def status(s):
    n=s.flags.get('chapter',1)
    title,goal=CHAPTERS[n-1]
    return {'number':n,'name':title,'goal':goal,'complete':s.ending is not None}


def progress(s):
    own=[p for p in s.places.values() if p.controller==p.owner=='ottoman']
    n=s.flags.get('chapter',1)
    ready=(n==1 and s.flags.get('crisis_resolved') and s.day>=s.flags['resolution_day']+7 or
           n==2 and len(own)>=4 and s.day>=s.flags.get('chapter_started',s.day)+365 and not s.arrears and not any(pid in s.hazards for pid in [p.id for p in own]) or
           n==3 and len(own)>=6 and s.institutions.get('land_register',{}).get('status')=='active' or
           n==4 and any(p.id=='bursa' and count(p.garrison)>=20 and p.grain>=count(p.garrison)*14 for p in own) or
           n==5 and len(own)>=10 and sum(p.governor is not None for p in own)>=3 and not s.arrears)
    if ready:
        court.accomplish(s,'chapter:'+str(n),'Завершена глава «'+CHAPTERS[n-1][0]+'»',CHAPTERS[n-1][1]+'. Условия выполнены; государство продолжает действовать.')
        s.flags['chapter']=n+1;s.flags['chapter_started']=s.day
        record(s,f'Начинается глава «{CHAPTERS[n][0]}». {CHAPTERS[n][1]}. Государство и обязательства сохраняются.','chapter')
    if n==6 and len(own)>=16 and any(p.id=='constantinople' for p in own) and not s.arrears and all(s.institutions.get(k,{}).get('status')=='active' for k in ['land_register','builders','shipping']):
        s.ending='Держава закрепила Константинополь, области и действующие службы. Военное расширение стало устойчивым государством.'
        record(s,s.ending,'victory')


def petition(s,scene,context):
    if len(s.agendas)>=3:return
    key=scene+':'+str(context.get('province',context.get('faction','court')))
    cooldown=s.flags.setdefault('petition_dates',{})
    if s.day-cooldown.get(key,-10000)<360 or any(a['scene']==scene for a in s.agendas):return
    s.agendas.append({'id':uid(s,'agenda'),'scene':scene,'context':context,'opened':s.day,'deadline':s.day+60,'consulted':[]})
    cooldown[key]=s.day;record(s,f'На совет вынесен вопрос: {SCENES[scene][0]}.','agenda')


def tick(s):
    if s.rules_version<4:return
    court.tick(s)
    progress(s)
    for job in list(s.flags.get('courses',[])):
        person=s.people[job['person']]
        if person.location!=job['place'] or person.travel or person.status!='active':
            s.flags['courses'].remove(job);record(s,f'Обучение {person.name} прервано: он больше не находится при наставниках.','institution')
        elif s.day>=job['ready']:
            person.skills[job['skill']]=min(90,person.skills[job['skill']]+job['gain']);s.flags['courses'].remove(job)
            court.remember(s,person.id,'course:'+str(job['ready'])+job['skill'],person.name+' завершил обучение '+('управлению' if job['skill']=='stewardship' else 'осадному делу')+'.')
            court.accomplish(s,'school','Первый подготовленный служитель',person.name+' прошёл полный курс. Его навыки теперь участвуют в исполнении поручений.')
            record(s,f'{person.name} завершил обучение. Опыт применяется в новых поручениях.','institution')
    if s.day%30 or s.flags.get('chapter',1)<2 or len(s.agendas)>=3:return
    own=[p for p in s.places.values() if p.controller=='ottoman']
    armies=[a for a in s.armies.values() if a.faction=='ottoman' and a.size]
    for p in sorted(own,key=lambda p:p.id):
        if p.grain<count(p.garrison)*14:petition(s,'scarcity',{'province':p.id})
        if p.owner!='ottoman' and p.loyalty<50 and s.day-(p.occupied_since or 0)>=30:petition(s,'occupation',{'province':p.id})
    if s.arrears and armies:petition(s,'pay_dispute',{'army':armies[0].id,'province':s.capital})
    for fid,r in s.polities.items():
        adjacent=any(s.places[n].controller==fid for p in own for n in ADJACENCY[p.id])
        if not adjacent:continue
        if war(s,'ottoman',fid) and r.plan=='attack':petition(s,'war_pressure',{'faction':fid})
        elif fid!='byzantine':
            enemies=[e for e in s.polities if war(s,'ottoman',e) and any(p.controller==fid and any(s.places[n].controller==e for n in ADJACENCY[p.id]) for p in s.places.values())]
            if enemies:petition(s,'alliance_offer',{'faction':fid,'enemy':enemies[0]})
    free=[p for p in s.people.values() if p.faction=='ottoman' and p.status=='active' and p.location==s.capital and not p.travel and p.id!=s.ruler_id and p.skills['siege']<80]
    if s.institutions.get('builders',{}).get('status')=='active' and free:petition(s,'siege_school',{'person':max(free,key=lambda p:p.skills['command']).id})
    from campaign.ruler.dynasty import heir
    successor=heir(s)
    if s.people[s.ruler_id].born+60<=calendar(s)['year'] and successor and successor.status=='active' and successor.skills['stewardship']<80:petition(s,'heir_school',{'person':successor.id})
    if calendar(s)['season']=='Зима':
        for a in armies:
            if a.location!=s.capital and a.grain<a.size*14:petition(s,'winter_quarters',{'army':a.id,'province':s.capital})


def describe(s,agenda):
    c=agenda['context'];parts=[SCENES[agenda['scene']][1]]
    if 'province' in c:
        p=s.places[c['province']];parts.append(f'Место: {name(p.id)}.')
    if 'army' in c:
        a=s.armies.get(c['army']);parts.append(f'Последнее поручение относится к армии у {name(a.location)}.' if a else 'Прежний отряд уже прекратил существование.')
    if 'faction' in c:
        from campaign.content import FACTIONS
        parts.append('Отправитель: '+FACTIONS[c['faction']]+'.')
    return ' '.join(parts)


def decide(s,scene,c,choice):
    from campaign.ruler import civil,military
    p=s.places.get(c.get('province'));a=s.armies.get(c.get('army'));fid=c.get('faction')
    if scene in ['scarcity','occupation']:
        require(p and p.controller=='ottoman','Владение больше не находится под вашим управлением')
        if choice=='buy':civil.command(s,'trade',{'province':p.id,'mode':'purchase','amount':400})
        elif choice in ['relief','charter']:civil.command(s,'policy',{'province':p.id,'tax':'relief'})
        elif choice=='customary':civil.command(s,'policy',{'province':p.id,'tax':'customary'})
        elif choice=='exaction':civil.command(s,'policy',{'province':p.id,'tax':'extraordinary'})
    elif scene=='war_pressure':
        if choice=='tribute' and s.rules_version>=5:
            from campaign.ruler.diplomacy import propose
            propose(s,'ottoman',fid,'peace',payment=100)
        elif choice=='tribute':
            spend(s,100)
            # Use the ordinary peace pipeline to reconcile occupations and sieges.
            s.couriers.append({'id':uid(s,'peace'),'kind':'diplomacy','target':fid,'ready':s.day+14,'payment':100,'guaranteed':True,'truce':720})
        elif choice=='negotiate':civil.command(s,'diplomacy',{'target':fid,'proposal':'peace'})
    elif scene=='alliance_offer':
        require(not war(s,'ottoman',fid),'Предложение устарело: отношения изменились')
        if choice in ['subsidy','pact'] and s.rules_version>=5:
            from campaign.ruler.diplomacy import propose
            propose(s,'ottoman',fid,'alliance',payment=60 if choice=='subsidy' else 40)
        elif choice in ['subsidy','pact']:
            if choice=='subsidy':
                enemy=c['enemy'];rel=s.relations[relation_key(fid,enemy)]
                require(war(s,'ottoman',enemy) and s.day>=rel.get('truce_until',0),'Положение изменилось: совместный поход сейчас не согласован')
                rel['status']='war'
            spend(s,60 if choice=='subsidy' else 40);s.polities[fid].gold+=60 if choice=='subsidy' else 40
            s.relations[relation_key('ottoman',fid)]['truce_until']=s.day+720
    elif scene=='pay_dispute':
        if choice=='pay':spend(s,s.arrears);s.arrears=0
        elif choice=='release':
            require(a and a.size>=20,'В прежнем отряде нет двадцати воинов')
            military.command(s,'demobilize',{'province':c['province'],'troops':{'militia':20}})
        elif a:a.morale=max(10,a.morale-10)
    elif scene in ['siege_school','heir_school'] and choice not in ['defer','field']:
        person=s.people[c['person']]
        require(person.status=='active' and person.location==s.capital and not person.travel,'Ученик должен находиться при столичных наставниках')
        require(not any(j['person']==person.id for j in s.flags.get('courses',[])),'Этот человек уже проходит обучение')
        spend(s,50 if scene=='heir_school' else 80 if choice=='masters' else 40)
        s.flags.setdefault('courses',[]).append({'person':person.id,'place':s.capital,'ready':s.day+(90 if choice=='masters' else 180),'skill':'stewardship' if scene=='heir_school' else 'siege','gain':10 if choice=='masters' else 8})
    elif scene=='winter_quarters':
        require(a and a.size,'Армия больше не существует')
        if choice=='return':military.command(s,'recall',{'army':a.id})
        elif choice=='supply':military.command(s,'provision',{'army':a.id,'province':p.id,'amount':max(100,a.size*20)})


def expire(s,agenda):
    if agenda['scene']=='pay_dispute':
        a=s.armies.get(agenda['context']['army'])
        if a:a.morale=max(10,a.morale-10)
