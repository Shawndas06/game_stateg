from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from math import ceil
from campaign.content import FACTIONS, PLACES, PLACE_KINDS, TROOPS
from campaign.engine import RuleError, require, relation_key
from campaign.ruler.models import Army, Cohort, Person, Place, RulerState
from campaign.ruler.core import *
from campaign.ruler import military, civil, story, world, chronicle, tactics


def new_campaign(seed: int, extended: bool=False) -> RulerState:
    s=RulerState(seed)
    for pid,_,_,_,owner,guards,walls,_ in PLACES:
        sponsor='konur' if pid=='karacahisar' else 'crown'
        s.places[pid]=Place(pid,owner,owner,[Cohort(uid(s,'cohort'),'militia',guards,pid,sponsor)],walls,walls,int(walls>0),grain=3500 if walls else 2400,reserve=80 if walls else 60)
    for i,a in enumerate(FACTIONS):
        for b in list(FACTIONS)[i+1:]:s.relations[relation_key(a,b)]={'status':'war' if {a,b}=={'ottoman','byzantine'} else 'peace','truce_until':0}
    s.people={
      'osman':Person('osman','Осман',1258,'sogut','ruler',True,skills={'command':60,'stewardship':45,'siege':35,'logistics':45}),
      'turgut':Person('turgut','Тургут',1260,'sogut','deputy',True,skills={'command':55,'stewardship':30,'siege':50,'logistics':45}),
      'konur':Person('konur','Конур',1265,'karacahisar','governor',True,skills={'command':50,'stewardship':28,'siege':30,'logistics':35},ambition=65),
      'hasan':Person('hasan','Хасан, хранитель казны',1247,'sogut','treasurer',skills={'command':15,'stewardship':65,'siege':10,'logistics':50}),
      'ibrahim':Person('ibrahim','Ибрахим, кадий',1245,'sogut','judge',skills={'command':10,'stewardship':60,'siege':10,'logistics':25}),
      'ahmed':Person('ahmed','Ахмед, писец',1270,'sogut','scribe',skills={'command':20,'stewardship':50,'siege':10,'logistics':40}),
      'orhan':Person('orhan','Орхан',1281,'sogut','heir',True,skills={'command':32,'stewardship':35,'siege':20,'logistics':30}),
    }
    s.places['karacahisar'].governor='konur';s.places['sogut'].governor='hasan'
    s.armies['ottoman-1']=Army('ottoman-1','ottoman','sogut',[Cohort(uid(s,'cohort'),'militia',60,'sogut'),Cohort(uid(s,'cohort'),'archers',20,'sogut')],'osman','turgut',grain=2400,deputy_officer='Старший десятник дружины')
    p=s.places['nicomedia'];units=take(s,p.garrison,{'militia':40})
    s.armies['byzantine-frontier']=Army('byzantine-frontier','byzantine',p.id,units,None,grain=3000,deputy_officer='Начальник пограничного отряда')
    for pid,p in s.places.items():
        if p.controller=='ottoman' or pid in ['bilecik','inegol','kutahya','nicomedia']:learn(s,pid,'Первоначальная ведомость')
    record(s,'Весна 1299 года. Две крепости и поселения требуют охраны, содержания и признанного порядка. Совет ждёт первого распоряжения.','opening')
    if extended:
        world.enable(s);s.flags['prologue_unread']=True
    story.schedule(s);validate(s);return s


def apply_command(state: RulerState,kind: str,payload: dict) -> RulerState:
    require(not state.flags.get('battle') or kind in ['battle_deploy','battle_step','battle_delegate','battle_retreat'],'Сначала завершите полевое сражение')
    if kind=='continue_campaign':
        require(state.rules_version==3 and (not state.ending or state.flags.get('crisis_resolved')),'Эту кампанию нельзя продолжить в новом режиме')
        s=deepcopy(state);s.outbox=[];s.ending=None;world.enable(s);chronicle.progress(s);s.revision+=1;validate(s);return s
    require(state.ending is None,'Эта глава завершена; можно изучить летопись или начать другую партию')
    require(isinstance(payload,dict),'Нужны параметры распоряжения')
    require(not any(str(k).startswith('_') for k in payload),'Служебные параметры недоступны в распоряжении игрока')
    s=deepcopy(state);s.outbox=[]
    dead=s.people[s.ruler_id].status=='dead'
    require(not dead or kind in ['decide','ransom','consult'],'Сначала решите вопрос преемственности')
    if tactics.command(s,kind,payload):pass
    elif kind=='begin_reign':
        require(s.rules_version>=4,'Пролог относится к большой кампании')
        s.flags['prologue_unread']=False
    elif kind=='decide':
        if dead:require(any(a['id']==payload.get('agenda') and a['scene']=='succession' for a in s.agendas),'После смерти правителя сначала требуется признание наследника')
        story.decide(s,payload)
    elif kind=='consult':
        topic=str(payload.get('topic','state'));aid=payload.get('army')
        agenda=next((a for a in s.agendas if a['id']==payload.get('agenda')),None)
        council=story.council(s,agenda,topic,aid)
        record(s,council['title']+': '+council['body'],'council')
        for speech in council['speeches']:record(s,speech['text'],'speech',speech['name'])
        s.flags['last_council']={'day':s.day,'topic':topic,'army':aid,'agenda':agenda['id'] if agenda else None}
    elif kind=='advance':
        require(type(payload.get('until_event',True)) is bool,'Режим ожидания должен быть логическим значением')
        days=payload.get('days',90);require(type(days) is int and 1<=days<=360,'Можно передать от одного до 360 дней')
        require(s.people[s.ruler_id].status!='dead','Требуется решение о наследовании')
        before_agendas={a['id'] for a in s.agendas}
        for _ in range(days):
            before=s.archive_seq;s.day+=1;civil.tick(s);civil.reconcile_obligations(s);world.tick(s);military.tick(s)
            _personal_events(s);story.schedule(s)
            if not any(p.controller=='ottoman' for p in s.places.values()):
                s.ending='Все владения утрачены. Первый опыт правления завершился распадом бейлика.';record(s,s.ending,'defeat')
            if s.ending or s.people[s.ruler_id].status=='dead' or s.flags.get('battle'):break
            if payload.get('until_event',True):
                new=[r for r in s.reports if r['seq']>before]
                if any(a['id'] not in before_agendas for a in s.agendas) or any(r['kind'] in ['battle','capture','death','wound','broken_promise','obstruction','delivery','mission_complete','audit','appointment','recruitment','building','institution','acknowledgement','agreement','illness','release','capital_loss','service','chapter','accomplishment','relationship'] for r in new):break
            # Personal or delegated active warfare advances at most one week per request.
            active=any(a.faction=='ottoman' and (a.travel or a.mission and a.mission['status']=='active') for a in s.armies.values())
            if active and s.day%7==0:break
    elif not military.command(s,kind,payload) and not civil.command(s,kind,payload):raise RuleError('Неизвестное распоряжение')
    civil.reconcile_obligations(s);military.cleanup(s);military.repair_leadership(s);_personal_events(s);story.schedule(s)
    s.revision+=1;validate(s);return s


def _personal_events(s: RulerState) -> None:
    ruler=s.people[s.ruler_id]
    if ruler.status=='captured' and not s.flags.get('ruler_captured_notice'):
        s.flags['ruler_captured_notice']=True
        record(s,f'Правитель в плену. Текущие поручения сохраняются; тыл ведёт {s.people[s.regent].name if s.regent and s.people[s.regent].status=="active" else "временный хранитель дел"}. Для освобождения можно передать выкуп.','capture')


def validate(s: RulerState) -> None:
    battle=s.flags.get('battle')
    if battle:
        assert 0<=battle['round']<8 and battle['phase'] in ['deploy','combat']
        assert len({u['id'] for u in battle['units']})==len(battle['units'])
        for u in battle['units']:
            assert u['army'] in s.armies and u['lane'] in tactics.LANES
            assert 0<=tactics.count(s,u)<=u['initial']
    assert s.day>=0 and s.gold>=0 and s.arrears>=0
    assert all(r.gold>=0 and r.arrears>=0 for r in s.polities.values())
    assert all(c['grain']>=0 and c['location'] in s.places for c in s.foreign_cargo)
    ids=[]
    for c in all_cohorts(s):
        assert c.troop in TROOPS and type(c.count) is int and c.count>0
        assert c.origin in s.places
        ids.append(c.id)
    assert len(ids)==len(set(ids)), 'A cohort exists in more than one physical container'
    personnel=[]
    for a in s.armies.values():
        assert a.location in s.places and a.grain>=0 and a.funds>=0 and 0<=a.morale<=100
        for pid in [a.commander,a.deputy]:
            if pid is not None:
                assert pid in s.people
                if a.size:personnel.append(pid)
        if a.travel:assert a.travel['path'] and a.travel['path'][0] in ADJACENCY[a.location]
    assert len(personnel)==len(set(personnel)), 'One person commands two physically separate armies'
    for p in s.places.values():
        assert p.grain>=0 and p.reserve>=0 and 0<=p.walls<=p.max_walls<=150
        assert p.owner in FACTIONS and p.controller in FACTIONS
        assert all(t['count']>0 for t in p.training)
    for c in s.transports.values():assert c['grain']>=0 and c['location'] in s.places
    for pid,sg in s.sieges.items():
        assert sg['armies'] and len(sg['armies'])==len(set(sg['armies']))
        assert s.places[pid].controller!=sg['faction'] and war(s,sg['faction'],s.places[pid].controller)
        assert all(aid in s.armies and s.armies[aid].size and s.armies[aid].location==pid and not s.armies[aid].travel for aid in sg['armies'])


def view(s: RulerState) -> dict:
    """Allowlist projection: no RNG seed, hidden loyalty, intentions or future effects."""
    now=calendar(s);loc=ruler_location(s);ruler=s.people[s.ruler_id]
    public_places={}
    for pid,p in s.places.items():
        k=s.knowledge.get(pid);mine=p.controller=='ottoman'
        public_places[pid]={'id':pid,'owner':k['owner'] if k else PLACE_INDEX[pid][4],'controller':k['controller'] if k else PLACE_INDEX[pid][4],'garrison':troops(p.garrison) if mine and loc==pid else k['garrison'] if k else None,'walls':p.walls if mine and loc==pid else k['walls'] if k else None,'fortress_level':p.fortress_level if mine else int(PLACE_INDEX[pid][6]>0),'max_walls':p.max_walls if mine else None,'grain':p.grain if mine and loc==pid else k.get('grain') if k else None,'reserve':p.reserve if mine else None,'governor':p.governor if mine else None,'tax':p.tax if mine else None,'grant':deepcopy(p.grant) if mine else None,'training':[{'troop':t['troop'],'count':t['count'],'ready':t['ready']} for t in p.training] if mine else [],'construction':deepcopy(p.construction) if mine else None,'buildings':list(p.buildings) if mine else [],'known_day':s.day if mine and loc==pid else k['day'] if k else None,'source':'Личное присутствие' if mine and loc==pid else k['source'] if k else 'Картографический справочник; гарнизон не проверен','controlled':mine,'construction_options':civil.construction_options(s,p) if mine else []}
    people={p.id:{'id':p.id,'name':p.name,'age':now['year']-p.born,'approximate_age':p.approximate_birth,'historical':p.historical,'faction':p.faction,'location':p.location,'role':p.role,'status':p.status,'travel':{'target':p.travel.get('target')} if p.travel else None,'reputation':('Опытный военачальник' if p.skills['command']>=50 else 'Опытный распорядитель' if p.skills['stewardship']>=50 else 'Опыт ещё складывается'),'service':dict(p.experience),'history':deepcopy(p.history)} for p in s.people.values() if p.faction=='ottoman' or p.role=='envoy'}
    armies={a.id:{'id':a.id,'faction':a.faction,'location':a.location,'troops':troops(a.cohorts),'commander':a.commander,'deputy':a.deputy,'acting_officer':a.deputy_officer,'grain':a.grain,'morale_state':'Войско держит строй' if a.morale>=65 else 'Войско утомлено и требует внимания','engines':a.engines,'funds':a.funds,'travel':{'target':a.travel['path'][0],'days':a.travel['left']} if a.travel else None,'mission':{k:v for k,v in a.mission.items() if k not in ['spent']} if a.mission else None,'order':{'kind':'move','target':a.travel['path'][0]} if a.travel else None,'cohorts':[{'troop':c.troop,'count':c.count,'origin':c.origin,'sponsor':c.sponsor,'service':c.service} for c in a.cohorts]} for a in s.armies.values() if a.faction=='ottoman'}
    agendas=[{'id':a['id'],'scene':a['scene'],'opened':a['opened'],'deadline':a['deadline'],'title':story.SCENES[a['scene']][0]} for a in s.agendas]
    last=s.flags.get('last_council',{})
    current=next((a for a in s.agendas if a['scene']=='succession'),None)
    if current is None:
        current=next((a for a in s.agendas if a['id']==last.get('agenda')),None)
        if current is None and last.get('topic')!='military':current=next(iter(s.agendas),None)
    return {'battle':tactics.public(s),'tactical_mode':bool(s.flags.get('tactical_mode')),'scenario':s.scenario,'schema_version':s.schema_version,'rules_version':s.rules_version,'revision':s.revision,'day':s.day,'calendar':now,'capital':s.capital,'ruler':ruler.name,'ruler_id':s.ruler_id,'ruler_status':ruler.status,'court_location':loc,'regent':s.regent,'gold':s.gold,'trade_access':{'available':not s.flags.get('merchants_offended',False),'review_day':s.flags.get('reconciliation_ready')},'arrears':s.arrears,'budget':civil.budget(s),'provinces':public_places,'people':people,'armies':armies,'sieges':{pid:{'province':pid,'armies':list(v['armies']),'faction':v['faction']} for pid,v in s.sieges.items() if any(s.armies[aid].faction=='ottoman' for aid in v['armies']) or s.places[pid].controller=='ottoman'},'agendas':agendas,'council':story.council(s,current,last.get('topic','state'),last.get('army')),'obligations':[dict(o,text=civil.obligation_text(s,o)) for o in s.obligations.values()],'reports':deepcopy(s.reports),'transports':[{k:deepcopy(v) for k,v in c.items() if k not in ['ambushed','escorts','escort_join']}|{'escort_count':sum(x['count'] for x in c.get('escorts',[]))} for c in list(s.transports.values()) if c['status'] not in ['completed','cancelled','seized'] or c['id'] in list(s.transports)[-6:]],'appointments':[{k:deepcopy(v) for k,v in x.items() if k not in ['path','left']} for x in s.appointments],'institutions':[{**v,'id':k,**civil.INSTITUTIONS[k]} for k,v in s.institutions.items()],'available_institutions':[dict(v,id=k,**civil.institution_help(s,k)) for k,v in civil.INSTITUTIONS.items() if k not in s.institutions],'relations':{k:dict(v) for k,v in s.relations.items() if 'ottoman' in k.split(':')},'pending_edicts':[{'id':e['id'],'kind':e['kind'],'province':e['province'],'issued':e['issued'],'escrow':e['escrow'],'held':e.get('held',False)} for e in s.edicts],'pending_orders':[{'id':c['id'],'army':c['army'],'target':c['mandate']['target'],'purpose':c['mandate']['purpose'],'issued':c['mandate']['issued']} for c in s.couriers if c['kind']=='order'],'campaign_mode':'long' if s.rules_version>=4 else 'chapter','continuation_available':s.rules_version==3 and (not s.ending or bool(s.flags.get('crisis_resolved'))),'diplomatic_contacts':world.contacts(s) if s.rules_version>=4 else ['byzantine','germiyan'],'chapter':chronicle.status(s) if s.rules_version>=4 else {'number':1,'name':'Утвердить власть','goal':'Получить опору, исполнить распоряжения и разрешить первый кризис бейлика','complete':s.ending is not None},'ending':s.ending,'prologue_pending':bool(s.flags.get('prologue_unread') and s.day==0 and 'founding' not in s.shown), 'accession':deepcopy(s.flags.get('accession')), 'accomplishments':deepcopy(s.flags.get('accomplishments',[])),'archive_cursor':s.archive_seq}
