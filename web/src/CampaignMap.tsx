import {useEffect,useRef,useState} from 'react';
import GatherPanel from './GatherPanel';
import CampaignCoach from './CampaignCoach';
import CanvasMap from './CanvasMap';
import {read,remember} from './CampaignMedia';
import {useGraphics} from './GraphicsSettings';
import BuildingPanel from './BuildingPanel';
import MapDiplomacy from './MapDiplomacy';
import NumberField,{integer} from './NumberField';
import type {Catalog} from './types';
import type {RulerSave,RulerState} from './ruler-types';
import './campaign-map.css';

type Send=(kind:string,payload:Record<string,unknown>)=>Promise<RulerSave|undefined>;
type Props={active:boolean;campaign:string;onHelp:()=>void;onTime:()=>void;state:RulerState;catalog:Catalog;selected:string;select:(id:string)=>void;armyId:string;selectArmy:(id:string)=>void;busy:boolean;send:Send;council:(id:string)=>void;army:()=>void;civil:(section:string,province:string)=>void;office:(section:string,target?:string,province?:string)=>void};
const size=(v:Record<string,number>|null)=>Object.values(v||{}).reduce((a,b)=>a+b,0);
const purposes:Record<string,string>={march:'Переместиться',conquer:'Завоевать',defend:'Оборонять',cover:'Охранять дорогу',relieve:'Снять осаду',intercept:'Перехватить',return:'Вернуться'};
const phases:Record<string,string>={active:'Исполняется',issued:'Приказ в пути',awaiting:'Требуется решение',completed:'Выполнено',failed:'Сорвано',recalled:'Отозвано'};

export default function CampaignMap({active,campaign,onHelp,onTime,state:s,catalog,selected,select,armyId,selectArmy,busy,send,council,army:advancedArmy,civil,office}:Props){
 const [panel,setPanel]=useState(false);const [quality]=useGraphics();
 const panelState=useRef({active,panel,picking:false});
 useEffect(()=>{const close=(e:Event)=>{const current=panelState.current;if(!current.active)return;if(current.picking){e.preventDefault();setPicking(false);setPanel(true)}else if(current.panel){e.preventDefault();setPanel(false)}};window.addEventListener('campaign-back',close);return()=>window.removeEventListener('campaign-back',close)},[]);
 const [focus,setFocus]=useState<'place'|'army'>(()=>read('map-object:'+campaign)==='army'?'army':'place'),[section,setSection]=useState('overview'),[picking,setPicking]=useState(false),[focusToken,setFocusToken]=useState(0);
 panelState.current={active,panel,picking};
 const [orderTarget,setOrderTarget]=useState(selected),[purpose,setPurpose]=useState('march'),[funds,setFunds]=useState('0'),[assault,setAssault]=useState(false),[requisition,setRequisition]=useState(false);
 const [troop,setTroop]=useState('militia'),[recruits,setRecruits]=useState('10'),[warehouse,setWarehouse]=useState(s.capital),[grain,setGrain]=useState('800');
 const [review,setReview]=useState<{revision:number;key:string}|null>(null);
 const mapRef=useRef<HTMLDivElement>(null),inspector=useRef<HTMLElement>(null);
 const p=s.provinces[selected],a=s.armies[armyId],own=Object.values(s.provinces).filter(x=>x.controlled),armies=Object.values(s.armies).filter(x=>size(x.troops)>0);
 const place=(id:string)=>catalog.places.find(x=>x.id===id)?.name||id;
 const person=(id:string|null)=>s.people[id||'']?.name||'Старший отряда';
 const names=Object.fromEntries(armies.map(x=>[x.id,person(x.commander)]));
 const letters=s.statecraft?.offers.filter(o=>o.b==='ottoman'&&o.status==='arrived').length||0;
 const decisions=(s.statecraft?.cases.filter(c=>c.status==='open').length||0)+(s.statecraft?.tasks.filter(t=>['awaiting','held'].includes(t.status)).length||0);
 const blocked=busy||!!s.ending||s.ruler_status==='dead';
 const n=integer(recruits,1,40),allocation=integer(funds,0,Math.min(5000,s.gold)),food=integer(grain,1,10000);
 const payload={army:armyId,target:orderTarget,purpose,funds:allocation,allow_assault:purpose==='conquer'&&assault,allow_requisition:requisition};
 const orderKey=JSON.stringify(payload),validReview=!!review&&review.revision===s.revision&&review.key===orderKey;
 const draft=s.statecraft?.draft?.army===armyId?s.statecraft.draft:null;
 function showInspector(){setPanel(true)}
 function showMap(){setPanel(false)}
 function choosePlace(id:string){
  select(id);if(!picking)remember('map-object:'+campaign,'place');setPanel(true);setReview(null);
  if(picking){setOrderTarget(id);setPicking(false)}else{setFocus('place');setSection('overview')}
  if(picking)showInspector();
 }
 function chooseArmy(id:string){const unit=s.armies[id];if(!unit)return;selectArmy(id);remember('map-object:'+campaign,'army');select(unit.location);setFocus('army');setPanel(true);setPicking(false);setOrderTarget(unit.mission?.target||unit.location);setPurpose(unit.mission?.purpose||'march');setFocusToken(x=>x+1);setReview(null);void 0}
 async function inspectOrder(){
  if(allocation===null||!a)return;
  if(s.statecraft){const result=await send('plan_order',payload);if(result)setReview({revision:result.state.revision,key:orderKey})}
  else setReview({revision:s.revision,key:orderKey});
 }
 async function confirmOrder(){if(!validReview)return;const result=await send(s.statecraft?'execute_plan':'mission',s.statecraft?{}:payload);if(result)setReview(null)}
 const recruitmentProblems=[...(p.owner!=='ottoman'?['Сначала закрепите управление владением через совет.']:[]),...(s.sieges[selected]?['Крепость осаждена: сначала снимите осаду.']:[]),...(p.training.length?['Здесь уже готовят людей. Дождитесь завершения набора.']:[]),...(s.pending_edicts.some(e=>e.kind==='raise'&&e.province===selected)?['Приказ о наборе уже в пути. Дождитесь исполнителя.']:[]),...(n!==null&&n>(p.reserve||0)?['Для этого набора не хватает свободных местных людей.']:[]),...(n!==null&&n*catalog.troops[troop].cost>s.gold?['В казне не хватает денег. Уменьшите набор.']:[])];
 return <section inert={!active} aria-hidden={!active} className={`campaign-map ${active?'':'map-background-only'}`}  data-testid="campaign-command-map">

  {picking&&<p className="map-instruction">Выберите город назначения. Приказ ещё не отправлен. <button onClick={()=>{setPicking(false);setPanel(true)}}>Отменить выбор цели</button></p>}
  <div className="campaign-attention">{s.agendas.length>0&&<button className="map-council-call" disabled={busy} onClick={()=>council(s.agendas[0].id)}>Совет: {s.agendas[0].title}<small>Ждут ответа: {s.agendas.length}</small></button>}{letters>0&&<button className="map-council-call" onClick={()=>office('diplomacy')}>Посольства ждут ответа · {letters}</button>}{s.statecraft&&<button onClick={()=>office('orders')}>{decisions?`Дела требуют решения · ${decisions}`:'Поручения и донесения'}<small>{s.statecraft.tasks.filter(t=>!['completed','cancelled','returned'].includes(t.status)).length} в работе</small></button>}</div>
  <CampaignCoach campaign={campaign} state={s} openCity={()=>{choosePlace(s.capital);setSection('recruit');setFocusToken(x=>x+1)}} onTime={onTime} onCouncil={()=>{if(s.agendas.length)council(s.agendas[0].id)}}/>
  <div className="campaign-map-layout"><div className="campaign-map-surface" ref={mapRef}>
   <CanvasMap campaign={campaign} planned={s.pending_edicts.filter(e=>e.formation).map(e=>({province:e.province,count:size(e.formation!.troops)}))} plannedRoute={draft?[draft.location,...draft.route]:[]} quality={quality} onHelp={onHelp} state={s} catalog={catalog} selected={selected} select={choosePlace} selectArmy={chooseArmy} selectedArmy={focus==='army'?armyId:undefined} armyNames={names} focusToken={focusToken}/>

   <div className="campaign-armies" aria-label="Выбрать походную армию">{armies.map(unit=><button key={unit.id} aria-pressed={focus==='army'&&armyId===unit.id} onClick={()=>chooseArmy(unit.id)}><strong>{names[unit.id]}</strong><span>{size(unit.troops)} воинов · {place(unit.location)}{unit.travel?' · в пути':''}</span></button>)}</div>
  </div>
  <aside hidden={!panel} className={`campaign-inspector ${focus==='place'?'ruler-place-card':''}`} ref={inspector} aria-label="Управление выбранным объектом" tabIndex={-1}>
   <button className="quiet back-to-map" onClick={showMap}>Закрыть карточку</button>
   {focus==='army'&&a?<>
    {s.statecraft?<button className="quiet" onClick={()=>setSection(section==='gather'?'overview':'gather')}>Подготовить поход · собрать и распределить силы</button>:<button onClick={advancedArmy}>Подготовить поход</button>}{section==='gather'&&s.statecraft&&<GatherPanel state={s} catalog={catalog} army={a.id} send={send} busy={blocked} orders={()=>office('orders')}/>} {section!=='gather'&&<><span className="eyebrow">Выбрана армия</span><h2>{person(a.commander)}</h2><p>{size(a.troops)} воинов · {place(a.location)}</p>
    <p>{a.travel?`В пути к ${place(a.travel.target)}. До участка ${a.travel.days} дн.`:a.morale_state}</p>
    <div className="map-facts"><span>Обоз <b>{a.grain}</b> пайков</span><span>Примерно <b>{Math.floor(a.grain/Math.max(1,size(a.troops)))}</b> дней довольствия</span><span>Походная казна <b>{a.funds}</b> монет</span></div>
    {a.mission&&<p className="notice">{purposes[a.mission.purpose]}: {place(a.mission.target)}. {phases[a.mission.status]||a.mission.status}.</p>}
    {s.pending_orders.filter(o=>o.army===a.id).map(o=><p className="notice" key={o.id}>Гонец в пути: {purposes[o.purpose]} — {place(o.target)}. Новый приказ ещё не получен армией.</p>)}
    <h3>Приказ на карте</h3><button className={picking?'primary':''} onClick={()=>{setPicking(!picking);showMap()}}>{picking?'Выберите город на карте':'Указать цель на карте'}</button>
    <p className="map-target" data-testid="map-order-target">Назначение: <strong>{place(orderTarget)}</strong></p>
    <label className="ruler-field">Задача<select aria-label="Задача на карте" value={purpose} onChange={e=>setPurpose(e.target.value)}>{Object.entries(purposes).map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>
    <NumberField label="Казна приказа на карте" value={funds} onChange={setFunds} min={0} max={Math.min(5000,s.gold)} hint="Новая походная казна для поручения. 0 — без средств. Срок — 180 дней."/>
    {purpose==='conquer'&&<label className="ruler-check"><input type="checkbox" checked={assault} onChange={e=>setAssault(e.target.checked)}/>Разрешить штурм</label>}
    <label className="ruler-check"><input type="checkbox" checked={requisition} onChange={e=>setRequisition(e.target.checked)}/>Разрешить реквизиции</label>
    {purpose==='march'&&<p className="muted">Переход требует права прохода по мирным чужим землям. Он не разрешает нападение.</p>}
    <button disabled={blocked||allocation===null||allocation>s.gold||size(a.troops)===0} onClick={inspectOrder}>Проверить приказ на карте</button>
    {review&&<section className="map-order-review" aria-label="Подтверждение приказа"><h3>{purposes[purpose]} · {place(orderTarget)}</h3><p>Исполнитель: {person(a.commander)}. {size(a.troops)} воинов; выделить {allocation??'—'} монет.</p>{draft&&<><p>Маршрут: {[draft.location,...draft.route].map(place).join(' → ')}. Расчёт движения: {draft.travel_days??'—'} дней после получения приказа, если дорога останется доступной.</p><p>В месте сбора остаётся {size(draft.garrison)} воинов. Обоз примерно на {draft.food_days} дней.</p>{draft.warnings.map(w=><p className="notice" key={w}>{w}</p>)}</>}{a.funds>0&&<p>Прежний неизрасходованный остаток {a.funds} монет вернётся в общую казну после получения нового приказа.</p>}{!validReview&&<p className="notice">Положение или условия изменились. Заново проверьте приказ.</p>}<button className="primary" disabled={blocked||!validReview} onClick={confirmOrder}>Отправить проверенный приказ</button><small>Сначала приказ должен дойти до исполнителя; движение начнётся после продолжения времени.</small></section>}
    <details><summary>Снабжение армии</summary><label className="ruler-field">Склад<select aria-label="Склад на карте" value={warehouse} onChange={e=>setWarehouse(e.target.value)}>{own.map(x=><option key={x.id} value={x.id}>{place(x.id)}</option>)}</select></label><NumberField label="Пайки обоза на карте" value={grain} onChange={setGrain} min={1} max={10000}/><button disabled={blocked||food===null||s.gold<5} onClick={()=>send('provision',{army:a.id,province:warehouse,amount:food})}>Отправить снабжение · 5 монет</button><p>Пайки берутся со склада и доставляются обозом. Оформление не пополняет армию мгновенно.</p></details>
    <div className="button-grid"><button disabled={blocked} onClick={()=>send('recall',{army:a.id})}>Отозвать к столице</button><button onClick={advancedArmy}>Состав, гарнизоны и личное командование</button></div>
   </>} </>:<>
    <span className="eyebrow">{p.fortress_level?'Укреплённое владение':'Поселение'}</span><h2>{place(selected)}</h2><p>{catalog.factions[p.controller]}{p.owner!==p.controller&&` · прежний владелец: ${catalog.factions[p.owner]}`}</p>
    <small className="map-source">{p.source}{p.known_day!==null&&` · день ${p.known_day}`}</small>
    <div className="map-facts"><span>Гарнизон <b>{p.garrison===null?'Неизвестен':size(p.garrison)}</b></span><span>Запасы <b>{p.grain??'Нет сведений'}</b></span><span>Стены <b>{p.walls??'Нет сведений'}</b></span></div>
    <div className="task-tabs" role="tablist" aria-label="Действия выбранного города">{[['overview','Сведения'],...(p.controlled?[['recruit','Набор'],['build','Стройка']]:[['diplomacy','Переговоры']])].map(([id,title])=><button key={id} role="tab" aria-selected={section===id} onClick={()=>setSection(id)}>{title}</button>)}</div>
    {section==='overview'&&<>
     {p.controlled?<><p>Управитель: {person(p.governor)}. Резерв: {p.reserve} человек.</p>{p.assessment&&<p>По смете в казну: {p.assessment.treasury} монет за 30 дней{p.assessment.granted>0&&` после пожалований на ${p.assessment.granted}`}. Фактический сбор подтвердит ведомость.</p>}
      <div className="button-grid"><button onClick={()=>setSection('recruit')}>Набрать войска здесь</button><button onClick={()=>setSection('build')}>Строить в этом городе</button></div><button className="quiet" onClick={()=>civil('appointments',selected)}>Управитель, сборы и назначения</button><button className="quiet" onClick={()=>civil('trade',selected)}>Закупить запасы для города</button>{s.statecraft&&<button className="quiet" onClick={()=>office('governance',undefined,selected)}>Полномочия местного управителя</button>}
     </>:<><p>Числа отражают последнее донесение. Поход требует состояния войны; мирное движение — согласованного прохода.</p><button onClick={()=>setSection('diplomacy')}>Переговоры с владельцем</button></>}
     {armies.filter(x=>x.location===selected).map(x=><button key={x.id} className="map-local-army" onClick={()=>chooseArmy(x.id)}>Выбрать отряд: {names[x.id]} · {size(x.troops)}</button>)}
     {s.sieges[selected]&&<p className="notice">Идёт осада. {s.statecraft&&<button onClick={()=>office('sieges',undefined,selected)}>Осадные действия</button>}</p>}
    </>}
    {section==='recruit'&&p.controlled&&<section className="map-recruitment"><h3>Набор · {place(selected)}</h3><label className="ruler-field">Род войск<select aria-label="Род войск на карте" value={troop} onChange={e=>setTroop(e.target.value)}>{Object.entries(catalog.troops).map(([id,t])=><option key={id} value={id}>{t.name}</option>)}</select></label><NumberField label="Число новобранцев на карте" value={recruits} onChange={setRecruits} min={1} max={40}/><p>{n===null?'Введите число людей.':`${n*catalog.troops[troop].cost} монет · ${troop==='militia'?14:troop==='archers'?30:60} дней обучения.`} Резерв владения: {p.reserve}.</p>{recruitmentProblems.map(r=><p className="notice" key={r}>{r}</p>)}<button className="primary" disabled={blocked||n===null||recruitmentProblems.length>0} onClick={()=>send('raise',{province:selected,troop,count:n})}>Начать набор в городе</button><p>Готовые люди поступят в гарнизон этого владения. Для похода их нужно передать в армию.</p>{p.training.map((t,i)=><p className="notice" key={i}>Готовятся {t.count} воинов, осталось {Math.max(0,t.ready-s.day)} дней.</p>)}</section>}
    {section==='build'&&p.controlled&&<BuildingPanel state={s} province={selected} place={place} onPlace={choosePlace} send={send} busy={blocked}/>}
    {section==='diplomacy'&&!p.controlled&&<MapDiplomacy key={p.controller} state={s} target={p.controller} name={catalog.factions[p.controller]} busy={blocked} send={send} advanced={()=>s.statecraft?office('diplomacy',p.controller):civil('diplomacy',selected)}/>}
    {p.construction&&<p className="notice">Стройка: осталось {p.construction.work} рабочих дней.</p>}
    {s.pending_edicts.filter(e=>e.province===selected).map(e=><p className="notice" key={e.id}>{e.kind==='raise'?'Приказ о наборе':e.kind==='construction'?'Строительное распоряжение':e.formation?`Собрать ${size(e.formation.troops)} воинов под командованием ${person(e.formation.commander)}${e.formation.rally?' к '+place(e.formation.rally):''}`:'Распоряжение'}: {e.held?'доставка задержана':'в пути к исполнителю'}. Выделено {e.escrow} монет.</p>)}
   </>}
  </aside></div>
  <details hidden className="map-recent"><summary>Последние известия</summary>{s.reports.slice(-4).reverse().map(r=><article key={r.seq}><small>{r.date} · {r.source}</small><p>{r.text}</p></article>)}</details>
 </section>;
}
