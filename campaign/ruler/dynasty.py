"""Third-generation court. Dates are historical anchors, outcomes are player-led."""
from campaign.engine import require
from campaign.ruler.models import Person
from campaign.ruler.core import calendar, record, spend
from campaign.ruler.civil import obligation

SCENES = {
 'orhan_handover': ('Печать Орхана', 'Правитель состарился. Писцы предлагают поручить державу Мураду, сохранив договоры и долги. Можно передать власть сейчас или оставить решение до конца правления. Добровольная передача — альтернативный путь этой партии.', [('handover','Передать власть Мураду и уйти от дел'),('remain','Продолжить правление Орхана')]),
 'murad_education': ('Наследник просит дела', 'Мурад хочет отвечать за собственное дело. Наставники предлагают военную подготовку или разбор счетов. Это займёт полгода при дворе, а не даст опыт одним приказом.', [('field','Поручить наставникам военную подготовку · 50 монет'),('court','Начать обучение управлению · 50 монет'),('defer','Пока сохранить нынешние обязанности')]),
 'murad_council': ('Чья власть на рубеже', 'Совет обсуждает полномочия командующих и учёт доходов. Обещанный доход нельзя одновременно считать деньгами казны. Кто будет опорой нового правления?', [('service','Обещать Лале Шахину 60 монет за службу через полгода'),('accounts','Оплатить подготовку Кара Халила к управлению · 60 монет'),('balance','Сохранить назначения и лично разбирать спорные поручения')]),
 'murad_reckoning': ('Цена первого обещания', 'Прошёл год нового правления. Совет возвращается к обещаниям, с которыми Мурад принял власть. Теперь важны исполненные дела.', [('honour','Исполнить записанное обещание, если оно ещё не исполнено'),('review','Сохранить обязательства и продолжить правление')]),
}


def heir(s):
    ident = {'osman':'orhan','orhan':'murad'}.get(s.ruler_id)
    person = s.people.get(ident)
    return person if person and person.status in ['active','wounded','ill'] and calendar(s)['year']-person.born >= 16 else None


def schedule(s, enqueue):
    if s.rules_version < 4: return
    year = calendar(s)['year']
    if year >= 1342 and not s.flags.get('murad_generation'):
        # No resurrection or free soldiers: these are people, not armies.
        for ident, name, born, role, skills in [
            ('murad','Мурад',1326,'heir',(48,40,30,42)),
            ('lala_sahin','Лала Шахин',1310,'officer',(62,35,48,58)),
            ('kara_halil','Чандарлы Кара Халил',1300,'officer',(25,68,20,48)),
        ]:
            if ident not in s.people:
                s.people[ident]=Person(ident,name,born,s.capital,role,True,skills=dict(zip(['command','stewardship','siege','logistics'],skills)))
                record(s,f'{name} прибыл ко двору в столице. Его можно вызвать, обучить или назначить на службу.','relationship')
        s.flags['murad_generation']=True
    if 'murad' not in s.people: return
    if year >= 1362 and s.ruler_id=='orhan' and heir(s): enqueue(s,'orhan_handover',deadline=365)
    if s.ruler_id != 'murad' and s.people['murad'].status == 'active': enqueue(s,'murad_education',deadline=365)
    if s.ruler_id == 'murad':
        enqueue(s,'murad_council',deadline=365)
        accession=s.flags.get('accession',{})
        if s.day >= accession.get('day',s.day)+365: enqueue(s,'murad_reckoning',deadline=365)


def decide(s, scene, choice):
    if scene == 'orhan_handover' and choice == 'handover':
        successor=heir(s)
        require(s.ruler_id=='orhan' and successor is not None,'Мурад сейчас не может принять власть')
        s.people[s.ruler_id].status='retired'
        s.flags['accession']={'from':s.ruler_id,'to':successor.id,'day':s.day}
        s.ruler_id=successor.id;successor.role='ruler'
        record(s,'Орхан передал печать Мураду и оставил дела. Государственные обязательства сохранены.','succession')
    elif scene == 'murad_education' and choice != 'defer':
        p=s.people['murad']
        require(p.status=='active' and p.location==s.capital and not p.travel,'Мурад должен прибыть в столицу для обучения')
        require(not any(p.id in [a.commander,a.deputy] for a in s.armies.values()),'Сначала освободите Мурада от командования')
        require(not any(x['person']==p.id for x in s.flags.get('courses',[])),'Мурад уже обучается')
        spend(s,50)
        s.flags.setdefault('courses',[]).append({'person':p.id,'place':s.capital,'ready':s.day+180,'skill':'command' if choice=='field' else 'stewardship','gain':8})
    elif scene == 'murad_council':
        if choice=='service':
            require(s.people['lala_sahin'].status=='active','Лала Шахин больше не может принять службу')
            ident=obligation(s,'reward','lala_sahin',s.day+180,amount=60)
            s.flags['murad_service']=ident
        elif choice=='accounts':
            require(s.people['kara_halil'].status=='active','Кара Халил не может руководить подготовкой')
            require(not any(x['person']=='kara_halil' for x in s.flags.get('courses',[])), 'Кара Халил уже занят подготовкой')
            spend(s,60)
            s.flags.setdefault('courses',[]).append({'person':'kara_halil','place':s.people['kara_halil'].location,'ready':s.day+180,'skill':'stewardship','gain':8})
    elif scene=='murad_reckoning' and choice=='honour':
        from campaign.ruler.civil import command
        ident=s.flags.get('murad_service')
        if ident and s.obligations[ident]['status'] in ['open','broken']:
            command(s,'fulfil',{'obligation':ident})


def advice(s,person,scene):
    if scene not in SCENES:return ''
    if person.id=='lala_sahin':
        promise=s.obligations.get(s.flags.get('murad_service',''))
        if promise:return ' Условие моей службы записано: '+str(promise['amount'])+' монет. '+('Выплата получена.' if promise['status']=='fulfilled' else 'Срок: день '+str(promise['due'])+'.')
        return ' Поручите одному командующему определённый рубеж и силы. Я не могу одновременно вести поход и оставаться наставником при дворе.'
    if person.id=='kara_halil':
        debt=sum(o['amount'] for o in s.obligations.values() if o['status'] in ['open','broken'])
        return f' В записанных обязательствах остаётся {debt} монет. Смена печати их не отменяет; обещанный бею доход нельзя считать свободным доходом казны.'
    return ''
