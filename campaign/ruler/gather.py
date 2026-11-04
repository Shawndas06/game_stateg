"""One checked assembly order; troops and couriers keep their physical locations."""
from copy import deepcopy
from campaign.engine import require
from campaign.ruler.core import count,owned,own_army,route,duration,selection,war


def plan(s,d,execute=False):
    from campaign.ruler import military
    trial=s if execute else deepcopy(s)
    target=str(d.get('target',''));owned(trial,target)
    armies=d.get('armies',[]);sources=d.get('sources',[])
    require(isinstance(armies,list) and isinstance(sources,list) and 1<=len(armies)+len(sources)<=20,'Выберите от одного до двадцати отрядов или мест формирования')
    require(all(isinstance(x,dict) for x in armies+sources),'Неверная ведомость сбора')
    require(all(isinstance(x.get('army'),str) for x in armies) and all(isinstance(x.get('province'),str) for x in sources),'Укажите идентификаторы армий и владений')
    require(len({x.get('army') for x in armies})==len(armies) and len({x.get('province') for x in sources})==len(sources),'Армия или гарнизон указан дважды')
    require(type(d.get('personal',False)) is bool,'Выберите способ командования')
    if d.get('personal'):
        require(armies,'Для личного похода выберите существующую главную армию')
        regent=d.get('regent');participants=[trial.armies.get(x.get('army')) for x in armies]
        require(not any(a and regent in [a.commander,a.deputy] for a in participants) and not any(x.get('commander')==regent for x in sources),'Заместитель должен оставаться в столице, а не участвовать в сборе')
        military.command(trial,'lead',{'army':armies[0].get('army'),'regent':d.get('regent'),'posture':'rear'})
    before=trial.gold;rows=[]
    peaceful=[p.id for p in trial.places.values() if p.controller=='ottoman' or not war(trial,'ottoman',p.controller)]
    for row in armies:
        a=own_army(trial,str(row.get('army','')))
        require(not a.travel and a.location not in trial.sieges,'Дождитесь прибытия армии или завершите осаду перед новым сбором')
        food=row.get('food',0);require(type(food) is int and 0<=food<=10000,'Укажите от нуля до 10000 пайков')
        if food:military.command(trial,'provision',{'army':a.id,'province':row.get('warehouse',a.location),'amount':food})
        military.command(trial,'mission',{'army':a.id,'target':target,'purpose':'march','funds':row.get('funds',0)})
        path=route(trial,a.location,target,a.faction,peaceful,hostile_end=False,military=True)
        rows.append({'source':a.location,'army':a.id,'commander':a.commander,'soldiers':a.size,'garrison':count(trial.places[a.location].garrison),'food_days':a.grain//max(1,a.size),'transport_food':food,'route':path or []})
    for row in sources:
        pid=str(row.get('province',''));p=owned(trial,pid);troops=selection(row.get('troops'));n=sum(troops.values())
        guards=count(p.garrison)-n
        # Validate route before escrow, including the peaceful destination itself.
        path=route(trial,pid,target,'ottoman',peaceful,hostile_end=False,military=True)
        require(path is not None,'Нет разрешённого мирного пути к месту сбора')
        rations=row.get('ration_days',20);require(type(rations) is int and 0<=rations<=60,'Запас от нуля до 60 дней')
        estimated=max(0,min(p.grain-max(0,guards)*14,n*rations))//max(1,n)
        military.command(trial,'form_army',{'province':pid,'commander':row.get('commander'),'troops':troops,'rally':target,'funds':row.get('funds',0),'ration_days':row.get('ration_days',20)})
        rows.append({'source':pid,'army':None,'commander':row.get('commander'),'soldiers':n,'garrison':guards,'food_days':estimated,'transport_food':0,'route':path})
    for row in rows:
        path=row['route'];row['travel_days']=sum(duration(a,b) for a,b in zip([row['source']]+path,path))
        row['warnings']=[]
        if row['garrison']<15:row['warnings'].append('Охрана ворот и складов ослаблена: остаётся '+str(row['garrison'])+' воинов.')
        if row['food_days']<14:row['warnings'].append('Текущего обоза меньше чем на две недели; доставка нового снабжения ещё должна состояться.')
    return {'target':target,'funds':sum(x.get('funds',0) for x in armies+sources)+sum(5 for x in armies if x.get('food',0)),'balance_delta':trial.gold-before,'rows':rows,'personal':d.get('personal',False),'regent':d.get('regent') if d.get('personal') else None}
