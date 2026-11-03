"""Authored personal threads, remembered deeds and observable accomplishments."""
from campaign.engine import require
from campaign.ruler.core import calendar, count, name, record, ruler_location, spend, uid

SCENES={
 'konur_word':('Конур: «Что стоит наше слово?»','Конур требует определить, остаются ли прежние условия службы в силе.',[('honour','Подтвердить записанные условия'),('verify','Поручить сверку писцу за 15 монет'),('rebuke','Отказать в новых уступках')]),
 'konur_reply':('Ответ Конура','Конур вернулся к вопросу о людях, которых он предоставляет правителю.',[('settle','Подтвердить условия и исполнить наступившую выплату'),('verify','Разобрать спор по счетам за 15 монет'),('stand','Оставить последнее распоряжение в силе')]),
 'orhan_trial':('Орхан просит собственного дела','Орхан просит поручение, за результат которого сможет отвечать сам.',[('govern','Доверить Орхану управление Доманичем'),('field','Выделить ему двадцать воинов для охраны дороги'),('study','Оставить его при наставниках за 50 монет'),('wait','Отложить самостоятельное поручение')]),
 'orhan_account':('Первый отчёт Орхана','Наследник просит оценить его первое самостоятельное дело.',[('recognize','Выслушать отчёт и подтвердить доверие'),('inspect','Проверить местные ведомости за 15 монет'),('recall','Вернуть Орхана к двору')]),
 'turgut_men':('Тургут говорит за своих людей','После сражений Тургут просит решить, что будет с его отрядом дальше.',[('rest','Отозвать отряд к столице'),('reward','Выдать Тургуту награду в 20 монет'),('press','Не менять распоряжения о службе')]),
 'turgut_reply':('Тургут ждёт ответа','Командующий отвечает на распоряжение о его людях.',[('hear','Принять его доклад'),('summon','Вернуть Тургутa к двору'),('continue','Подтвердить прежние полномочия')]),
}


def remember(s,pid,key,text):
    p=s.people.get(pid)
    if not p or any(h['key']==key for h in p.history):return
    p.history.append({'key':key,'day':s.day,'date':calendar(s)['date'],'text':text,'ruler':s.ruler_id})
    record(s,text,'relationship',p.name)


def accomplish(s,key,title,text):
    deeds=s.flags.setdefault('accomplishments',[])
    if any(d['id']==key for d in deeds):return
    deeds.append({'id':key,'day':s.day,'date':calendar(s)['date'],'title':title,'text':text})
    record(s,title+'. '+text,'accomplishment')


def open_case(s,scene,context=None):
    if len(s.agendas)>=3 or scene in s.shown or any(a['scene']==scene for a in s.agendas):return False
    s.agendas.append({'id':uid(s,'agenda'),'scene':scene,'context':context or {},'opened':s.day,'deadline':s.day+90,'consulted':[]})
    record(s,'Поступило личное обращение: '+SCENES[scene][0]+'.','agenda')
    return True


def tick(s):
    if s.rules_version<4:return
    tracks=s.flags.setdefault('personal_threads',{})
    for agenda in list(s.agendas):
        if agenda['scene'] not in SCENES:continue
        pid=agenda['context']['person'];person=s.people[pid]
        if pid==s.ruler_id or person.status in ['dead','retired']:
            s.agendas.remove(agenda);s.shown.append(agenda['scene'])
            tracks.setdefault(pid,{})['stage']='closed'
            remember(s,pid,'closed:'+agenda['scene'],'Личное обращение '+person.name+' закрыто: его положение в государстве изменилось.')
    for pid,scene,follow in [('konur','konur_word','konur_reply'),('orhan','orhan_trial','orhan_account'),('turgut','turgut_men','turgut_reply')]:
        person=s.people.get(pid)
        if not person or person.status!='active' or person.id==s.ruler_id:continue
        track=tracks.get(pid)
        if track and track['stage']=='waiting' and s.day>=track['due']:
            if open_case(s,follow,{'person':pid,'previous':track['choice'],'since':track['day']}):track['stage']='answer'
        elif not track and s.day>=90:
            armies=[a for a in s.armies.values() if pid in [a.commander,a.deputy] and a.size]
            if pid=='orhan' and (armies or s.places['domanic'].governor==pid):
                tracks[pid]={'stage':'waiting','day':s.day,'due':s.day+90,'choice':'field' if armies else 'govern'}
                remember(s,pid,'first-duty','Орхан уже несёт самостоятельную службу; двор ожидает его отчёт.')
                continue
            eligible=(pid=='konur' and 'service_terms' in s.shown or pid=='orhan' and 'founding' in s.shown or pid=='turgut' and bool(armies) and sum(person.experience.get(k,0) for k in ['battle','siege'])>0)
            if eligible and open_case(s,scene,{'person':pid}):tracks[pid]={'stage':'opened','day':s.day}
    if 'domanic' not in s.hazards and s.day>=270:
        p=s.places['domanic'];guards=count(p.garrison)+sum(a.size for a in s.armies.values() if a.faction=='ottoman' and a.location==p.id and not a.travel)
        if p.controller=='ottoman' and guards>=20:accomplish(s,'road','На дороге снова безопасно','Охрана действительно находится у Доманича. Караваны могут пользоваться дорогой без прежнего разбойного отряда.')
    delivered=next((c for c in s.transports.values() if c['kind']=='purchase' and c['status']=='completed'),None)
    if delivered:accomplish(s,'supplies','Первая поставка принята',f'Груз добрался до {name(delivered["target"])}. Зерно принято на местный склад, а не осталось обещанием купца.')
    ledger=s.flags.get('last_accounts')
    if ledger and ledger['day']!=s.flags.get('court_accounts_day'):
        s.flags['court_accounts_day']=ledger['day']
        s.flags['paid_months']=s.flags.get('paid_months',0)+1 if ledger['income']>=ledger['expense'] and not s.arrears else 0
        if s.flags['paid_months']>=3:accomplish(s,'accounts','Три ведомости без недоимки','Три месяца текущие расходы покрывались поступлениями. Жалованье и управление оплачены без новых долгов.')


def work_evidence(s):
    p=s.people['orhan'];track=s.flags['personal_threads']['orhan'];choice=track['choice']
    if choice=='govern':return s.places['domanic'].governor==p.id and p.location=='domanic' and not p.travel and s.day-s.flags.get('governor_started:'+p.id,s.day)>=90
    if choice=='field':return s.places['domanic'].controller=='ottoman' and 'domanic' not in s.hazards and any(a.commander==p.id and a.location=='domanic' and not a.travel and a.size for a in s.armies.values())
    return any(h['key'].startswith('course:') and h['day']>=track['day'] for h in p.history)


def describe(s,agenda):
    c=agenda['context'];scene=agenda['scene'];p=s.people[c['person']]
    text=SCENES[scene][1]
    if scene.startswith('konur'):
        obligations=[o for o in s.obligations.values() if o['creditor']=='konur']
        broken=any(o['status'] in ['broken','repudiated'] for o in obligations)
        text+=' «Слово о службе осталось без исполнения», — пишет он.' if broken else ' «Я хочу знать, на каких условиях мои люди будут служить дальше», — пишет он.'
        if s.places['karacahisar'].grant:text+=' Доходы Караджахисара по-прежнему пожалованы за службу.'
    elif scene=='orhan_account':
        text+=' Его поручение подтверждено прибытием и текущими ведомостями.' if work_evidence(s) else 'Писец пока не может подтвердить завершение поручения. Это нужно выяснить до похвалы.'
    elif scene=='turgut_reply':
        armies=[a for a in s.armies.values() if p.id in [a.commander,a.deputy] and a.size]
        text+=f' Его отряд находится у {name(armies[0].location)}.' if armies else ' Прежний отряд больше не числится под его командованием.'
    return text+' Последнее известное местонахождение: '+name(p.location)+'.'


def decide(s,scene,c,choice):
    from campaign.ruler import civil,military
    pid=c['person'];p=s.people[pid]
    require(p.status=='active','Этот человек сейчас не может исполнить новое поручение')
    tracks=s.flags.setdefault('personal_threads',{});track=tracks.setdefault(pid,{'stage':'opened','day':s.day})
    if scene.startswith('konur'):
        if choice=='verify':civil.command(s,'audit',{'province':'karacahisar'})
        elif choice=='settle':
            for o in list(s.obligations.values()):
                if o['creditor']=='konur' and o['kind']=='reward' and o['status'] in ['open','broken'] and s.day>=o['due']:civil.settle(s,o['id'])
        if choice in ['honour','settle']:p.trust=min(90,p.trust+5)
        if choice=='rebuke':p.trust=max(0,p.trust-10)
    elif scene=='orhan_trial':
        if choice=='govern':civil.command(s,'appoint',{'person':pid,'role':'governor','province':'domanic'})
        elif choice=='field':
            military.command(s,'form_army',{'province':ruler_location(s),'commander':pid,'troops':{'militia':20}})
            army=next(a for a in s.armies.values() if a.commander==pid and a.size)
            military.command(s,'mission',{'army':army.id,'target':'domanic','purpose':'cover','funds':10})
        elif choice=='study':
            from campaign.ruler.chronicle import decide as train
            train(s,'heir_school',{'person':pid},'teach')
    elif scene=='orhan_account':
        if choice=='recognize':
            require(work_evidence(s),'Результат поручения ещё не подтверждён. Можно проверить дела или отозвать исполнителя')
            p.trust=min(90,p.trust+8);accomplish(s,'heir_duty','Первое дело наследника',f'{p.name} исполнил самостоятельное поручение. Его опыт и местонахождение сохраняются в ведомостях.')
        elif choice=='inspect':civil.command(s,'audit',{'province':p.location})
        else:
            armies=[a for a in s.armies.values() if pid in [a.commander,a.deputy] and a.size]
            if armies:military.command(s,'recall',{'army':armies[0].id})
            else:civil.command(s,'summon',{'person':pid})
    else:
        army=next((a for a in s.armies.values() if pid in [a.commander,a.deputy] and a.size),None)
        if choice in ['rest','summon']:
            if army:military.command(s,'recall',{'army':army.id})
            else:
                require(choice=='summon','Прежний отряд уже не находится под его командованием')
                civil.command(s,'summon',{'person':pid})
        elif choice=='reward':spend(s,20);p.wealth+=20;p.trust=min(90,p.trust+8)
        elif choice=='press':
            p.trust=max(0,p.trust-8)
            if army:army.morale=max(10,army.morale-5)
    remember(s,pid,'choice:'+scene,f'{p.name}: правитель решил — {dict(SCENES[scene][2])[choice].lower()}.')
    if scene=='orhan_trial' and choice=='wait':
        tracks[pid]={'stage':'closed','choice':choice,'day':s.day}
    elif scene in ['konur_word','orhan_trial','turgut_men']:
        tracks[pid]={'stage':'waiting','choice':choice,'day':s.day,'due':s.day+(210 if pid=='orhan' else 90)}
    else:track['stage']='closed'


def reaction(s,p,agenda):
    if not agenda or agenda['scene'] not in SCENES:return ''
    if agenda['context']['person']==p.id:
        last=p.history[-1] if p.history else None
        return ' Я помню предыдущее распоряжение: '+last['text'] if last else ' Прошу дать мне ясное поручение и возможность ответить за результат.'
    if p.id=='hasan':return ' Запись о расходе сама по себе не подтверждает исполнение. Я сопоставлю её с поступившим отчётом.'
    if p.role=='judge':return ' Прежние условия службы сохраняют силу, пока их не пересмотрят отдельным распоряжением.'
    return ''


def expire(s,agenda):
    pid=agenda['context']['person'];track=s.flags.get('personal_threads',{}).get(pid)
    if track:track['stage']='closed'
    remember(s,pid,'silence:'+agenda['scene'],s.people[pid].name+' не получил ответа на личное обращение в установленный срок.')
    s.people[pid].trust=max(0,s.people[pid].trust-5)
