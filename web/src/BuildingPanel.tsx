import {useState} from 'react';
import type {RulerState} from './ruler-types';

export default function BuildingPanel({state:s,province,place,onPlace,send,busy}:{state:RulerState;province:string;place:(id:string)=>string;onPlace:(id:string)=>void;send:(kind:string,payload:Record<string,unknown>)=>void;busy:boolean}){
 const [work,setWork]=useState('granary'),[services,setServices]=useState(false);
 return <section className="card"><h2>Строительство и службы</h2><p>Выберите владение и одну работу. Подготовка служб нужна для новых крепостей; обычное зернохранилище можно строить без них.</p>
  <label className="ruler-field">Владение для строительства<select aria-label="Владение для строительства" value={province} onChange={e=>onPlace(e.target.value)}>{Object.values(s.provinces).filter(p=>p.controlled).map(p=><option key={p.id} value={p.id}>{place(p.id)}</option>)}</select></label>
  <label className="ruler-field">Что построить<select aria-label="Что построить" value={work} onChange={e=>setWork(e.target.value)}>{s.provinces[province].construction_options?.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
  <div id="building-works">{s.provinces[province].construction_options?.filter(x=>x.id===work).map(x=><article className="building-option" key={x.id} data-building={x.id}><h3>{x.name}</h3><p>{x.cost} монет · {x.days} дней</p>{x.reasons.length?<div className="advisor-explanation"><strong>Салих · что мешает начать</strong>{x.reasons.map(reason=><p key={reason}>{reason}</p>)}</div>:<p>Можно начать. После распоряжения продолжите время; о завершении придёт донесение.</p>}<button disabled={busy||!!x.reasons.length} onClick={()=>send('construction',{province,building:x.id})}>{x.name} · {x.cost} монет</button></article>)}</div>
  <button aria-expanded={services} onClick={()=>setServices(v=>!v)}>{services?'Скрыть подготовку служб':'Подготовить службы для крепости'}</button>
  {services&&<div><h2>Подготовка служб</h2><p>Порядок для новой крепости: Служба писцов, затем Земельный учёт, затем Строительная служба. Дождитесь готовности каждой, прежде чем учреждать следующую.</p>
  {s.institutions.map(x=><p className="notice" key={x.id}>{x.name}: {x.status==='active'?'действует':`готовится, осталось ${Math.max(0,x.ready-s.day)} дней`}.</p>)}
  {s.available_institutions.map(x=><article className="building-option" id={'institution-'+x.id} key={x.id}><h3>{x.name}</h3><p>{x.cost} монет · {x.days} дней · содержание {x.upkeep} в месяц</p>{!!x.reasons?.length&&<div className="advisor-explanation"><strong>Салих · что подготовить</strong>{x.reasons.map(reason=><p key={reason}>{reason}</p>)}{x.next_institution&&<button onClick={()=>document.getElementById('institution-'+x.next_institution)?.scrollIntoView({block:'center'})}>Показать нужную службу</button>}</div>}<button disabled={busy||s.gold<x.cost||!!x.reasons?.length} onClick={()=>send('institution',{institution:x.id})}>Учредить</button></article>)}
 </div>}
 </section>;
}
