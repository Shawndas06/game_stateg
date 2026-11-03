"""Authored situations; facts and statements are rendered from the current party."""
from __future__ import annotations

from campaign.engine import require, relation_key
from campaign.ruler.core import *
from campaign.ruler import chronicle, court, dynasty
from campaign.ruler.models import Person
from campaign.ruler.civil import obligation, obligation_text, settle, command as civil_command, budget

# Historical people are marked separately from fictional office holders.
SCENES = {
 'founding':('Первый совет','Чья поддержка станет опорой первых распоряжений?', [('frontier','Опереться на пограничных беев'),('merchants','Взять у купцов 60 монет с обязательством вернуть 90'),('stewardship','Выделить 25 монет на местные запасы и учёт')]),
 'frontier_letter':('Послание с границы','Представитель византийского наместника предлагает перемирие на полгода за платёж в 30 монет.', [('accept','Передать 30 монет и заключить перемирие'),('counter','Предложить перемирие без платежа'),('refuse','Отказать в предложении')]),
 'grain_offer':('Купцы из Кютахьи','Предлагается доставить 400 пайков за 40 монет. Охрану можно подготовить отдельно в разделе сделок.', [('buy','Согласовать доставку за 40 монет'),('toll','Предложить безопасный проезд с пошлиной'),('decline','Пока отказаться от сделки')]),
 'service_terms':('За какую службу платят доходом','Конур просит закрепить условия предоставления людей: четверть сборов Караджахисара либо награда в 40 монет через полгода.', [('grant','Пожаловать четверть сборов за службу'),('reward','Обещать выплату 40 монет'),('refuse','Оставить прежние условия без нового обещания')]),
 'village_petition':('Просьба Доманича','Жители просят облегчить сборы или обеспечить постоянную охрану дороги силами не менее двадцати воинов.', [('charter','Выдать грамоту об обычных сборах'),('guard','Обязаться обеспечить охрану в течение 90 дней'),('refuse','Отклонить просьбу')]),
 'quarter_accounts':('Ведомости перед новым сезоном','Совет рассматривает поступления, расходы и обязательства. Можно назначить проверку счетов Караджахисара за 15 монет.', [('audit','Назначить проверку'),('accept','Принять ведомости и оставить исполнителей'),('relief','Временно облегчить сборы в Доманиче')]),
 'road_warning':('Известия с дороги','У Доманича замечен разбойный отряд. Дорога остаётся опасной до прибытия достаточной охраны.', [('patrol','Подготовить поручение об охране дороги'),('local','Поручить местному гарнизону охрану при наличии двадцати воинов'),('ignore','Отложить вмешательство')]),
 'merchant_due':('Условия дальнейшего проезда','Представитель купцов просит рассмотреть расчёты и разрешение на очередной караван.', [('settle','Исполнить открытый денежный долг, если он есть'),('transit','Согласовать проезд каравана'),('refuse','Отказать в новом соглашении')]),
 'governor_accounts':('Кто отвечает за местные сборы','Поступили местные ведомости. Совет может сопоставить их с записями казны и полномочиями назначенца.', [('audit','Проверить Караджахисар за 15 монет'),('retain','Сохранить действующий порядок'),('relief','Облегчить сборы до следующего решения')]),
 'border_proposal':('Предложение о границе','Посланник предлагает обсудить прекращение столкновений и признание удерживаемых владений.', [('peace','Отправить предложение о мире'),('prepare','Оставить командующим действующие полномочия'),('talk','Продолжить переговоры без новых обещаний')]),
 'assembly_claim':('Слово правителя и права служилых','Беи и городские представители хотят закрепить порядок службы и сборов перед новым годом.', [('confirm','Подтвердить действующие грамоты и пожалования'),('centralize','Начать пересмотр пожалований'),('review','Проверить исполнение обязательств')]),
 'crisis':('Кому принадлежит власть в бейлике','Накопленные обязательства и положение на границе требуют окончательного распоряжения.', [('settlement','Урегулировать спор через признание прав и соглашение'),('authority','Подкрепить распоряжение собранными в столице силами'),('accounts','Опёреться на проверенные счета и исполненные обязательства')]),
 'charter_return':('Грамота вернулась на совет','Сборщик просит уточнить права, ранее обещанные Доманичу.', [('honour','Подтвердить грамоту'),('revoke','Отменить обещанное облегчение')]),
 'promise_broken':('Срок обещания истёк','Получатель ссылается на записанное обязательство. Писец предъявил первоначальные условия.', [('repair','Исполнить просроченное обязательство'),('negotiate','Просить новую отсрочку на 90 дней'),('refuse','Прямо отказаться от обязательства')]),
 'campaign_return':('Донесение о выполненном поручении','Совет разбирает фактические действия войска, состояние обоза и назначенный гарнизон.', [('reward','Назначить командующему награду в 20 монет'),('review','Принять отчёт и проверить расположение войск'),('rights','Подтвердить права жителей удерживаемого поселения')]),
 'casualty_hearing':('Кто примет выбывшее командование','Один из служителей выбыл. Совет рассматривает состояние человека и исполнение его обязанностей.', [('deputy','Подтвердить временное управление заместителем'),('ransom','Оплатить выкуп в 60 монет, если человек в плену'),('wait','Оставить временный порядок до нового известия')]),
 'delayed_supply':('Обоз не дошёл','Обоз задержан на дороге. Зерно остаётся при нём; повторная отправка того же груза невозможна.', [('resume','Найти разрешённый путь и продолжить'),('return','Вернуть груз в доступное владение'),('wait','Приказать ждать на месте')]),
 'accusation':('Несовпадающие ведомости','Проверка выявила различие между местными сборами и поступлением в казну. Требуется разбирательство, а не обвинение по одному слуху.', [('recover','Взыскать подтверждённую сумму с ответственного'),('dismiss','Снять исполнителя с местной должности'),('pardon','Оставить сумму на местные нужды под запись')]),
 'rival_letters':('Два донесения об одном обозе','Казённая накладная и донесение командующего не совпадают по исполнению отправки.', [('investigate','Сопоставить записи и опросить охрану за 15 монет'),('release','Отдать прямое распоряжение продолжить доставку'),('wait','Дождаться дополнительных сведений')]),
 'succession':('Власть после смерти правителя','Государственные договоры, долги и армии сохраняются. Требуется признать доступного наследника.', [('orhan','Признать Орхана и сохранить действующие обязательства')]),
}
CHAPTER_SCENES=dict(SCENES)
SCENES.update(chronicle.SCENES)
SCENES.update(court.SCENES)
SCENES.update(dynasty.SCENES)
SCHEDULE=[(0,'founding'),(30,'frontier_letter'),(60,'grain_offer'),(90,'service_terms'),(120,'village_petition'),(180,'quarter_accounts'),(270,'road_warning'),(360,'merchant_due'),(450,'governor_accounts'),(540,'border_proposal'),(630,'assembly_claim'),(720,'crisis')]


def choices(s,scene):
    if scene=='succession':
        person=dynasty.heir(s)
        return [(person.id,'Признать '+person.name+' и сохранить обязательства государства')] if person else []
    return SCENES[scene][2]


def enqueue(s: RulerState,scene: str,context: dict | None=None,deadline: int=90) -> None:
    if scene in s.shown or any(x['scene']==scene for x in s.agendas):return
    context=dict(context or {})
    if scene in ['frontier_letter','border_proposal','grain_offer','merchant_due']:
        ident=uid(s,'envoy');faction='byzantine' if scene in ['frontier_letter','border_proposal'] else 'germiyan'
        s.people[ident]=Person(ident,'Посланник наместника' if faction=='byzantine' else 'Представитель купцов',1265,ruler_location(s),'envoy',status='guest',faction=faction)
        context['envoy']=ident
    s.agendas.append({'id':uid(s,'agenda'),'scene':scene,'context':context,'opened':s.day,'deadline':s.day+deadline,'consulted':[]})
    record(s,f'На совет вынесен вопрос: {SCENES[scene][0]}.','agenda')


def schedule(s: RulerState) -> None:
    if s.ending:return
    dynasty.schedule(s,enqueue)
    ruler=s.people[s.ruler_id]
    if ruler.status=='dead':
        heir=dynasty.heir(s)
        if heir:
            if 'succession' in s.shown:s.shown.remove('succession')
            enqueue(s,'succession',deadline=36500)
        else:s.ending='Династия лишилась доступного наследника. Летопись завершена.'
        return
    for day,scene in SCHEDULE:
        if s.day>=day:
            if scene=='road_warning' and scene not in s.shown and not any(x['scene']==scene for x in s.agendas):s.hazards.setdefault('domanic',12)
            enqueue(s,scene)
    if s.flags.get('charter') and s.day>=s.flags['charter']+90:enqueue(s,'charter_return',{'province':'domanic'})
    broken=next((o for o in s.obligations.values() if o['status']=='broken'),None)
    if broken:enqueue(s,'promise_broken',{'obligation':broken['id']})
    done=next((a for a in s.armies.values() if a.faction=='ottoman' and a.mission and a.mission['status']=='completed'),None)
    if done:enqueue(s,'campaign_return',{'army':done.id,'person':done.commander,'province':done.location})
    casualty=next((p for p in s.people.values() if p.faction=='ottoman' and p.id!=s.ruler_id and p.status in ['wounded','captured','dead']),None)
    if casualty:enqueue(s,'casualty_hearing',{'person':casualty.id})
    delayed=next((c for c in s.transports.values() if c['status']=='held'),None)
    if delayed:enqueue(s,'delayed_supply',{'transport':delayed['id']})
    if s.flags.get('sabotage_transport'):enqueue(s,'rival_letters',{'transport':s.flags['sabotage_transport']})
    evidence=next((p.id for p in s.places.values() if s.flags.get('evidence:'+p.id)),None)
    if evidence:enqueue(s,'accusation',{'province':evidence})
    # Expired letters produce explicit lack-of-answer outcomes, never invisible payments.
    for agenda in list(s.agendas):
        if s.day>agenda['deadline'] and agenda['scene']!='succession':
            envoy=s.people.get(agenda['context'].get('envoy'))
            if envoy and envoy.status=='guest':
                from campaign.ruler.civil import release_envoy
                release_envoy(s,envoy)
            if agenda['scene'] in chronicle.SCENES:chronicle.expire(s,agenda)
            if agenda['scene'] in court.SCENES:court.expire(s,agenda)
            s.agendas.remove(agenda);s.shown.append(agenda['scene']);s.flags['ignored']=s.flags.get('ignored',0)+1
            record(s,f'Срок ответа по вопросу «{SCENES[agenda["scene"]][0]}» истёк. Новых обязательств не принято.','expired')
            if agenda['scene']=='crisis':s.flags['crisis_resolved']='unsettled';s.flags['resolution_day']=s.day
    if s.rules_version>=4:
        chronicle.tick(s);return
    if s.flags.get('crisis_resolved') and s.day>=s.flags['resolution_day']+7:
        holdings=sum(p.controller=='ottoman' for p in s.places.values());open_promises=sum(o['status']=='open' for o in s.obligations.values());broken_count=sum(o['status']=='broken' for o in s.obligations.values())
        outcome={'settlement':'Власть закреплена соглашением и признанными правами.','authority':'Распоряжение поддержано собранными силами.','accounts':'Проверенные счета и исполненные обязательства укрепили власть.','unsettled':'Спор остался неразрешённым: власть встретит следующий год ослабленной.'}[s.flags['crisis_resolved']]
        forces=sum(a.size for a in s.armies.values() if a.faction=='ottoman');grants=sum(p.grant is not None for p in s.places.values() if p.controller=='ottoman')
        s.ending=f'{outcome} Под контролем {holdings} владений. В походных частях {forces} воинов; в казне {s.gold} монет. Пожалований доходов: {grants}. Опасных дорог: {len(s.hazards)}. Открытых обязательств: {open_promises}; нарушенных: {broken_count}. Первая глава завершена; дальнейшая междоусобная и имперская кампания ещё разрабатывается.'
        record(s,s.ending,'chapter')


def decide(s: RulerState,d: dict) -> None:
    aid=str(d.get('agenda',''));agenda=next((a for a in s.agendas if a['id']==aid),None)
    require(agenda is not None,'Этот вопрос уже закрыт или не существует')
    scene=agenda['scene'];choice=str(d.get('choice',''));treatment=d.get('treatment','receive')
    decision_text=dict(choices(s,scene)).get(choice,'')
    require(choice in dict(choices(s,scene)),'Такого ответа нет в этом вопросе')
    require(treatment in ['receive','gift','detain','execute'],'Неизвестное обращение с посланником')
    require(treatment=='receive' or scene in ['frontier_letter','border_proposal','grain_offer','merchant_due'],'В этом вопросе нет иностранного посланника')
    envoy=s.people.get(agenda['context'].get('envoy'))
    if treatment in ['detain','execute']:require(choice in ['refuse','prepare','decline'],'Выбранное обращение исключает отправку мирного согласия с этим посланником')
    if treatment=='gift':
        spend(s,20)
        if envoy:envoy.wealth+=20
        record(s,'Посланник одарён на двадцать монет.','envoy')
    elif treatment in ['detain','execute']:
        if envoy:envoy.status='detained' if treatment=='detain' else 'dead'
        record(s,'Посланник '+('задержан.' if treatment=='detain' else 'казнён по распоряжению правителя.'),'envoy')
        s.flags['envoy_'+treatment]=s.flags.get('envoy_'+treatment,0)+1
        if scene in ['frontier_letter','border_proposal']:
            s.relations[relation_key('ottoman','byzantine')]['status']='war'
        if treatment=='execute':
            s.flags['execution_scene']=scene
            if scene in ['grain_offer','merchant_due']:s.flags['merchants_offended']=True
            # Execution itself is the reply; no peaceful acceptance in the same command.
            require(choice in ['refuse','prepare','decline'],'После казни посланника нельзя отправить с ним мирное согласие')
    if scene in dynasty.SCENES:dynasty.decide(s,scene,choice)
    elif scene in court.SCENES:court.decide(s,scene,agenda['context'],choice)
    elif scene in chronicle.SCENES:chronicle.decide(s,scene,agenda['context'],choice)
    elif scene=='founding':
        s.flags['founding']=choice
        if choice=='frontier':
            from campaign.ruler.models import Army
            p=s.places['karacahisar'];units=take(s,p.garrison,{'militia':20})
            a=Army(uid(s,'army'),'ottoman',p.id,units,'konur',grain=0,deputy_officer='Старший отряда Конура')
            load=min(p.grain,a.size*20);p.grain-=load;a.grain+=load;s.armies[a.id]=a;p.governor=None
            obligation(s,'reward','konur',s.day+270,40)
        elif choice=='merchants':
            require(s.merchant['gold']>=60,'Купцы не располагают обещанным займом');s.merchant['gold']-=60;s.gold+=60;obligation(s,'debt','merchants',s.day+180,90)
        else:
            require(s.merchant['grain']>=250,'Нет предложенного запаса');spend(s,25);s.merchant['gold']+=25;s.merchant['grain']-=250;s.places[s.capital].grain+=250;s.flags['accounting_started']=True
    elif scene=='frontier_letter':
        if choice=='accept' and treatment not in ['detain','execute']:
            spend(s,30);s.relations[relation_key('ottoman','byzantine')].update(status='peace',truce_until=s.day+180)
        elif choice=='counter':s.flags['negotiation']=s.day
    elif scene=='grain_offer':
        if choice=='buy':civil_command(s,'trade',{'mode':'purchase','province':s.capital,'amount':400})
        elif choice=='toll':civil_command(s,'trade',{'mode':'transit','province':s.capital,'amount':300})
    elif scene=='service_terms':
        if choice=='grant':civil_command(s,'grant',{'province':'karacahisar','person':'konur'})
        elif choice=='reward':obligation(s,'reward','konur',s.day+180,40)
    elif scene=='village_petition':
        p=owned(s,'domanic')
        if choice=='charter':p.tax='customary';s.flags['charter']=s.day;obligation(s,'charter','community:'+p.id,s.day+720,province=p.id)
        elif choice=='guard':obligation(s,'protection','community:'+p.id,s.day+90,province=p.id)
    elif scene in ['quarter_accounts','governor_accounts']:
        if choice=='audit':civil_command(s,'audit',{'province':'karacahisar'})
        elif choice=='relief':civil_command(s,'policy',{'province':'domanic','tax':'relief'})
    elif scene=='road_warning':
        if choice=='local':
            require(count(s.places['domanic'].garrison)>=20,'Местный гарнизон ещё не доведён до двадцати воинов')
            s.hazards.pop('domanic',None);record(s,'Гарнизон выставил охрану; дорога у Доманича проверена.','security')
        elif choice=='patrol':record(s,'Писец подготовил задачу об охране Доманича. Выберите армию и отправьте ей поручение.','instruction')
    elif scene=='merchant_due':
        if choice=='settle':
            debt=next((o for o in s.obligations.values() if o['creditor']=='merchants' and o['kind']=='debt' and o['status'] in ['open','broken']),None)
            if debt:settle(s,debt['id'])
            else:record(s,'Писец сверил долговую запись: непогашенного денежного долга купцам нет.','accounts')
        elif choice=='transit':civil_command(s,'trade',{'mode':'transit','province':s.capital,'amount':300})
    elif scene=='border_proposal':
        if choice=='peace':
            if war(s,'ottoman','byzantine'):civil_command(s,'diplomacy',{'target':'byzantine','proposal':'peace'})
            else:record(s,'Посланник подтвердил действующий мир.','diplomacy')
    elif scene=='assembly_claim':
        if choice=='centralize':
            for p in s.places.values():
                if p.controller=='ottoman' and p.grant:civil_command(s,'revoke_grant',{'province':p.id})
        elif choice=='confirm':s.flags['confirmed_rights']=True
        else:record(s,'Писец представил перечень действующих обязательств для исполнения.','accounts')
    elif scene=='charter_return':
        p=s.places[agenda['context']['province']]
        if choice=='honour':p.tax='customary';s.flags['charter_honoured']=True
        else:p.tax='extraordinary';s.flags['charter_revoked']=True;p.unrest+=10
    elif scene=='promise_broken':
        oid=agenda['context']['obligation'];o=s.obligations[oid]
        if choice=='repair':settle(s,oid)
        elif choice=='negotiate':
            require(not any(c['kind']=='extension' and c['obligation']==oid for c in s.couriers),'Просьба об отсрочке уже отправлена')
            s.couriers.append({'id':uid(s,'extension'),'kind':'extension','obligation':oid,'ready':s.day+14})
            record(s,'Просьба об отсрочке направлена получателю. До ответа первоначальные условия сохраняются.','negotiation')
        else:o['status']='repudiated'
    elif scene=='campaign_return':
        pid=agenda['context']['person']
        if choice=='reward':
            require(pid in s.people and s.people[pid].status!='dead','Названный командующий выбыл');spend(s,20);s.people[pid].wealth+=20
        elif choice=='rights':
            p=s.places[agenda['context']['province']];require(p.controller=='ottoman','Владение больше не удерживается');p.tax='customary';p.unrest=max(0,p.unrest-5);p.loyalty=min(90,p.loyalty+10);obligation(s,'charter','community:'+p.id,s.day+720,province=p.id)
        elif choice=='review':observation(s,agenda['context']['province'],'Сверка походной ведомости')
    elif scene=='casualty_hearing':
        if choice=='ransom':civil_command(s,'ransom',{'person':agenda['context']['person']})
    elif scene=='delayed_supply':
        cid=agenda['context']['transport']
        if choice!='wait':civil_command(s,'transport_order',{'transport':cid,'action':choice})
    elif scene=='accusation':
        p=s.places[agenda['context']['province']];evidence=s.flags.get('evidence:'+p.id);require(evidence,'Проверка не дала оснований для этого обвинения')
        person=s.people.get(evidence['person'])
        if choice=='recover':
            require(person is not None,'Нет установленного ответственного');amount=min(person.wealth,evidence['amount']);person.wealth-=amount;s.gold+=amount
        elif choice=='dismiss':p.governor=None
        else:s.flags['local_allowance:'+p.id]=evidence['amount']
        s.flags['evidence:'+p.id]=None;s.flags['diverted:'+p.id]=0
    elif scene=='rival_letters':
        if choice=='investigate':civil_command(s,'audit',{'province':'karacahisar'})
        elif choice=='release':civil_command(s,'transport_order',{'transport':agenda['context']['transport'],'action':'resume'})
    elif scene=='succession':
        heir=dynasty.heir(s);require(heir is not None and choice==heir.id,'Наследник сейчас не может принять власть')
        if s.rules_version>=4:s.flags['accession']={'from':s.ruler_id,'to':heir.id,'day':s.day}
        s.ruler_id=heir.id;heir.role='ruler';record(s,heir.name+' признан правителем. Договоры, долги, должности и состав войск сохранены.','succession')
    elif scene=='crisis':
        if choice=='settlement':
            p=owned(s,'karacahisar',True)
            if not p.grant:civil_command(s,'grant',{'province':p.id,'person':'konur'})
            s.flags['confirmed_rights']=True
        elif choice=='authority':
            strength=count(s.places[s.capital].garrison)+sum(a.size for a in s.armies.values() if a.faction=='ottoman' and a.location==s.capital and not a.travel)
            require(strength>=60,'В столице ещё не собраны силы, на которые опирается этот приказ')
        else:
            require(s.flags.get('audit_done') and not any(o['status'] in ['broken','repudiated'] for o in s.obligations.values()),'Нужны проведённая проверка и исполненные либо действующие обязательства')
        s.flags['crisis_resolved']=choice;s.flags['resolution_day']=s.day
    if envoy and treatment in ['receive','gift']:
        from campaign.ruler.civil import release_envoy
        release_envoy(s,envoy)
    s.shown.append(scene);s.flags['decision:'+scene]=choice;s.agendas.remove(agenda)
    record(s,f'{SCENES[scene][0]}: {decision_text}.','decision')


def council(s: RulerState,agenda: dict | None=None,topic: str='state',army_id: str | None=None) -> dict:
    b=budget(s);a=s.armies.get(army_id or 'ottoman-1');loc=ruler_location(s)
    attending=[p for p in s.people.values() if p.status=='active' and p.location==loc and not p.travel]
    obligations=[o for o in s.obligations.values() if o['status'] in ['open','broken']]
    due=sum(o['amount'] for o in obligations if o['due']<=s.day+90)
    speeches=[]
    for p in attending:
        evidence=[]
        if p.role=='treasurer' or p.id=='hasan':
            text=f'В казне свободно {s.gold} монет. На ближайшие тридцать дней по действующему содержанию требуется {b["expense"]}. '
            if due:text+=f'В ближайшие девяносто дней наступают записанные выплаты на {due} монет. '
            text+=('Новых средств без пересмотра обязательств не хватает.' if s.gold<due+b['expense'] else 'Сопоставьте новый расход с действующими обязательствами.')
            evidence=['treasury','payroll','obligations']
        elif p.role=='judge':
            charters=[o for o in obligations if o['kind']=='charter']
            text=('Грамота Доманичу остаётся действующей. Её условия нужно сопоставить с распоряжением о сборах.' if charters else 'Крупные споры можно передать мне с указанием сторон и оснований. Непроверенное обвинение ещё не доказывает вины.')
            evidence=['charters']
        elif p.role=='scribe':
            text=f'В делах совета {len(s.agendas)} вопросов. '
            text+=('Есть просроченные обязательства; первоначальные условия сохранены.' if any(o['status']=='broken' for o in obligations) else 'Обещания и полученные письма записаны с датами. Для далёких мест нужно дождаться донесения.')
            evidence=['archive','obligations']
        elif p.role in ['commander','deputy','officer','heir'] or p.id in ['konur','turgut']:
            own=next((x for x in s.armies.values() if p.id in [x.commander,x.deputy]),None)
            if own:
                text=f'При войске в {name(own.location)} {own.size} человек, в обозе {own.grain} пайков. '
                text+=('Обоза не хватит на месяц: требуется поставка или разрешённая закупка.' if own.grain<own.size*30 else 'Текущий обоз позволяет планировать следующий участок пути.')
                evidence=['army:'+own.id]
            else:
                local=s.places[p.location];text=f'В гарнизоне {name(local.id)} {count(local.garrison)} воинов. '
                text+=('Если вывести всех, крепость останется без вооружённой охраны.' if count(local.garrison)<20 else 'Выделение людей в поход уменьшит охрану места сбора.')
                evidence=['garrison:'+local.id]
            promises=[o for o in obligations if o['creditor']==p.id]
            if promises:text+=' Моё условие службы записано: '+obligation_text(s,promises[0])+'.'
        elif p.id==s.ruler_id:continue
        else:text='По делам за пределами моего поручения у меня нет подтверждённых сведений.'
        text+=contextual_advice(s,agenda['scene'] if agenda else ('military' if topic=='military' else 'state'),p,agenda['context'] if agenda else {},a)
        text+=court.reaction(s,p,agenda) if s.rules_version>=4 else ''
        if agenda:text+=dynasty.advice(s,p,agenda['scene'])
        speeches.append({'person':p.id,'name':p.name,'role':p.role,'text':text,'observed_day':s.day,'sources':evidence})
    if topic=='military' and a and a.commander not in {p.id for p in attending}:
        reports=[(k['day'],pid,data) for pid,k in s.knowledge.items() for data in k.get('armies',[]) if data['id']==a.id]
        if reports:
            day,pid,data=max(reports,key=lambda x:x[0]);text=f'Донесение из {name(pid)}, день {day}: в отряде {data["size"]} воинов, при обозе {data["grain"]} пайков. Более позднего подтверждения пока нет.'
        else:day=s.day;text='Командующий находится вне ставки. Подтверждённой походной ведомости ещё нет; требуется дождаться гонца.'
        speeches.append({'person':'dispatch:'+str(a.commander),'name':'Писец читает походное донесение','role':'dispatch','text':text,'observed_day':day,'sources':['dispatch']})
    if not speeches:speeches=[{'person':'clerk','name':'Походный писец','role':'scribe','text':'У двора нет присутствующих служителей по этому вопросу. Можно затребовать донесение.','observed_day':s.day,'sources':[]}]
    title=SCENES[agenda['scene']][0] if agenda else ('Военный совет' if topic=='military' else 'Дела правления')
    body=SCENES[agenda['scene']][1] if agenda else 'Присутствующие докладывают по своим обязанностям. После обсуждения правитель отдаёт распоряжение.'
    if agenda and agenda['scene'] in chronicle.SCENES:body=chronicle.describe(s,agenda)
    if agenda and agenda['scene'] in court.SCENES:body=court.describe(s,agenda)
    if agenda and agenda['scene']=='crisis':
        if any(o['status']=='broken' for o in obligations):body='На совет предъявлены неисполненные обещания. Их получатели требуют определить порядок службы и расчётов.'
        elif war(s,'ottoman','byzantine'):body='На границе продолжается война. Беи требуют определить силы обороны и полномочия командующих.'
        else:body='Соседи и местные представители хотят закрепить признанные права и порядок исполнения распоряжений.'
    return {'agenda':agenda['id'] if agenda else None,'title':title,'body':body,'date':calendar(s)['date'],'speeches':speeches,'choices':[{'id':cid,'text':text,'allowed_treatments':['receive','gift','detain','execute'] if cid in ['refuse','prepare','decline'] else ['receive','gift']} for cid,text in choices(s,agenda['scene'])] if agenda else []}


def contextual_advice(s: RulerState,scene: str,person,context: dict,army) -> str:
    """Role-specific interpretation of dated facts. No invented omniscient facts."""
    finance=person.role=='treasurer' or person.id=='hasan'
    military=person.role in ['commander','deputy','officer','heir'] or person.id in ['konur','turgut']
    judge=person.role=='judge';scribe=person.role=='scribe'
    if scene in ['frontier_letter','border_proposal']:
        treaty=s.relations[relation_key('ottoman','byzantine')]
        if finance:return ' В предложении посланника речь идёт о тридцати монетах.' if scene=='frontier_letter' else ' Удерживаемые земли и предложенный платёж нужно записать раздельно; расходы на действующие войска пока продолжаются.'
        if judge:return f' Сейчас действует данное слово о перемирии до дня {treaty["truce_until"]}.' if treaty['status']=='peace' and treaty.get('truce_until',0)>s.day else ' Пока согласие другой стороны не получено, нового договора нет. Полномочия посланника и признание владений нужно записать.'
        if military:
            k=s.knowledge.get('bilecik')
            return f' По ведомости из Биледжика, составленной в день {k["day"]}, там было {sum(k["garrison"].values())} защитников. Перед новым походом стоит затребовать свежую разведку.' if k else 'Сведений о гарнизоне цели у меня пока нет.'
        if scribe:return ' Ответ и обращение с гонцом будут записаны отдельно; задержанный гонец не сможет отвезти согласие.'
    if scene in ['service_terms','assembly_claim']:
        p=s.places['karacahisar']
        if finance:return ' Часть доходов Караджахисара уже пожалована и второй раз в казну не поступает.' if p.grant else ' Доход Караджахисара пока не пожалован. При определении службы следует указать, какие поступления будут оставлены получателю.'
        if judge:return ' Право получать установленную долю сборов за службу не меняет собственника земли. Условия службы и основания отзыва следует записать.'
        if military:return ' Силы, предоставленные беем, нужно отличать от людей на постоянном содержании казны. Их условия службы уже есть в записях.'
        if scribe:return ' По действующим делам можно отдельно проверить пожалования, денежные награды и обещания жителям.'
    if scene in ['village_petition','charter_return']:
        pid=context.get('province','domanic');p=s.places[pid];k=s.knowledge.get(pid)
        if judge:return ' Сейчас установлен чрезвычайный сбор; он противоречит обещанным обычным сборам, если грамота уже выдана.' if p.tax=='extraordinary' else ' В просьбе жителей речь о порядке сборов и охране дороги. Эти обязательства исполняются разными распоряжениями.'
        if military:return f' Последняя полученная ведомость {name(pid)} датирована днём {k["day"]}: в гарнизоне {sum(k["garrison"].values())} человек. Сначала сопоставьте её с последующими отправками людей.' if k else ' От этого поселения ещё нет проверенной военной ведомости.'
        if finance:return ' Послабление нужно учитывать в местных сборах; выделенные на охрану люди продолжат получать довольствие.'
        if scribe:return ' Жители просят защиты своих дворов и дороги. Условия военной службы беев следует рассматривать отдельным делом.'
    if scene in ['grain_offer','merchant_due']:
        if finance:return ' Поставка оплачивается по условиям сделки; пошлина за проезд поступит после доставки, а не при подписании.'
        if military:return ' Военная охрана каравана выделяется из существующих частей. Эти люди на время сопровождения не участвуют в походе.'
        if judge:return ' У договора должны быть стороны, груз, место передачи и срок. Просьба об отсрочке сама не меняет старый долг.'
        if scribe:return ' Купцы приостановили новые сделки после казни представителя; ответа на возмещение ещё нет.' if s.flags.get('merchants_offended') else ' Получение груза и уплата пошлины подтверждаются отдельными записями.'
    if scene in ['road_warning','delayed_supply','rival_letters']:
        cid=context.get('transport');c=s.transports.get(cid)
        if scribe and c:return f' В деле обоза {cid} записано {c["grain"]} пайков. Последнее положение: {name(c["location"])}; состояние — '+{'held':'ожидает распоряжения','moving':'в пути','completed':'передача завершена','seized':'груз утрачен'}.get(c['status'],'сбор или возвращение')+'.'
        if judge:return ' Проверка подтвердила удержание обоза местным распоряжением после отметки об отправке.' if s.flags.get('sabotage_proven') and scene=='rival_letters' else ' Задержка сама по себе не доказывает умысел. Нужно сопоставить накладную, путь и показания охраны.'
        if military:return ' Для охраны дороги нужны силы на месте. Полученный приказ ещё не означает, что отряд уже прибыл.'
        if finance:return ' Заплаченные припасы ещё в пути. Казна ждёт подтверждения доставки, прежде чем принимать новые расчёты.'
    if scene in ['quarter_accounts','governor_accounts','accusation']:
        pid=context.get('province','karacahisar');evidence=s.flags.get('evidence:'+pid)
        if finance:return f' Подтверждённое проверкой расхождение в {name(pid)} составляет {evidence["amount"]} монет.' if evidence else ' Утверждённая смета и фактическое поступление — разные записи. Для обвинения нужна сверка.'
        if judge:return ' Сначала установите ответственного за проверенный период. Уволить человека и взыскать доказанную сумму — разные распоряжения.'
        if scribe:return ' У назначения есть дата принятия дел. В пути к месту службы человек ещё не управляет новым владением.'
        if military:return ' Расходы на охрану следует сопоставить с фактическими частями, а не только с просьбой местного начальника.'
    if scene=='promise_broken':
        o=s.obligations.get(context.get('obligation'))
        if scribe and o:return f' Первоначальный срок записан: день {o["due"]}. Предмет: {obligation_text(s,o)}.'
        if judge:return ' Нарушенное условие сохраняется в записи. Для изменения срока требуется ответ получателя.'
        if finance:return ' Прежде чем обещать новую выплату, следует сверить её с уже наступившими обязательствами.'
        if military:return ' Договорённость с поставившим людей беем определяет продолжение именно его службы, а не всякого отряда в державе.'
    if scene in ['casualty_hearing','succession']:
        affected=s.people.get(context.get('person',s.ruler_id))
        if judge:return ' Государственные договоры и долги сохраняются при смене правителя; личные пожалования рассматриваются по их условиям.'
        if military:return ' Оставшимся в строю людям нужен начальник. Сначала следует получить подтверждение, кто принял управление после выбытия командующего.'
        if finance:return ' Выкуп потребует отдельной суммы. Оставшимся на службе людям по-прежнему положено жалованье.'
        if scribe and affected:
            status={'active':'снова на службе','wounded':'ранен','captured':'в плену','dead':'погиб','ill':'болен'}.get(affected.status,affected.status)
            return f' По последней записи, {affected.name} — {status}. Поступающие распоряжения нужно сопоставить с датой его выбытия.'
    if scene=='campaign_return':
        if military:return ' Состав выступивших, потери, выделенный гарнизон и оставшиеся части следует сверить по одному поручению.'
        if judge:return ' Занятие ворот ещё не устанавливает порядок управления. Права жителей и признание владения требуют отдельных решений.'
        if finance:return ' Неиспользованные средства завершённого поручения должны вернуться в казну.'
    if scene=='crisis':
        if finance:return ' Улаживая спор, нужно сохранить средства на уже действующие обязательства и содержание людей.'
        if military:
            k=s.knowledge.get(s.capital)
            return f' По полученной ведомости столицы, день {k["day"]}, гарнизон насчитывал {sum(k["garrison"].values())} человек. Для распоряжения силой нужно сверить ещё и прибывшие части.' if k else ' Подтверждённой ведомости столицы сейчас нет.'
        if judge:return ' Соглашение о правах, распоряжение собранным силам и решение на основании проверенных счетов требуют разных оснований.'
        if scribe:return ' После распоряжения остаётся проверить исполнение и записать, какие обязательства переходят в следующий год.'
    return ''
