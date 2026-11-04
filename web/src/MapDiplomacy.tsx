import {useState} from 'react';
import NumberField,{integer} from './NumberField';
import type {RulerState,RulerSave} from './ruler-types';

type Props={state:RulerState;target:string;name:string;busy:boolean;send:(kind:string,payload:Record<string,unknown>)=>Promise<RulerSave|undefined>;advanced:()=>void};
const kinds:Record<string,string>={peace:'Мир',trade:'Торговое соглашение',nap:'Ненападение',alliance:'Оборонительный союз',access:'Право прохода',demand:'Предложить вассалитет',submit:'Признать себя вассалом',war:'Объявить войну'};
export default function MapDiplomacy({state:s,target,name,busy,send,advanced}:Props){
 const key=['ottoman',target].sort().join(':'),war=s.relations[key]?.status==='war',modern=!!s.statecraft;
 const [kind,setKind]=useState(war?'peace':modern?'trade':'access'),[days,setDays]=useState('720'),[payment,setPayment]=useState('0'),[tribute,setTribute]=useState('10'),[levy,setLevy]=useState('30'),[confirmed,setConfirmed]=useState<number|null>(null);
 const contacts=s.statecraft?.contacts||s.diplomatic_contacts||[],allowed=contacts.includes(target);
 const cost=modern?integer(payment,0,Math.min(500,s.gold)):kind==='peace'?40:kind==='access'?30:0;
 const term=integer(days,90,1825),tax=integer(tribute,0,100),quota=integer(levy,0,50),subject=['submit','demand'].includes(kind);
 const blocked=busy||!!s.ending||!allowed||(kind!=='war'&&(cost===null||cost>s.gold||modern&&(term===null||subject&&(tax===null||quota===null))));
 async function submit(){
  if(kind==='war'&&confirmed!==s.revision){setConfirmed(s.revision);return}
  await send(modern?'negotiate':'diplomacy',{target,proposal:kind,...(modern&&kind!=='war'?{days:term,payment:cost,...(subject?{tribute:tax,levy:quota}:{})}:{})});setConfirmed(null);
 }
 return <section className="map-diplomacy"><h3>Переговоры · {name}</h3><p>{war?'Между державами идёт война.':'Сейчас между державами нет войны.'}</p>{!allowed&&<p className="notice">Контакт с этим двором ещё не установлен. Доступные посольства открываются по мере появления связей с соседями.</p>}
 <label className="ruler-field">Условия посольства<select aria-label="Договор на карте" value={kind} onChange={e=>{setKind(e.target.value);setConfirmed(null)}}>{Object.entries(kinds).filter(([id])=>modern||['peace','access','war'].includes(id)).map(([id,title])=><option key={id} value={id}>{title}</option>)}</select></label>
 {kind!=='war'&&(modern?<><div className="ruler-form"><NumberField label="Срок соглашения на карте" value={days} onChange={setDays} min={90} max={1825}/><NumberField label="Платёж посольству" value={payment} onChange={setPayment} min={0} max={Math.min(500,s.gold)}/></div>{subject&&<div className="ruler-form"><NumberField label="Дань по соглашению" value={tribute} onChange={setTribute} min={0} max={100}/><NumberField label="Доля военной помощи" value={levy} onChange={setLevy} min={0} max={50}/></div>}<p className="muted">Платёж резервируется. Соглашение вступит в силу после ответа; отказ вернёт деньги.</p></>:<p>На посольство выделяется {cost} монет. Нужно дождаться ответа гонца.</p>)}
 {kind==='war'&&confirmed===s.revision&&<p className="notice">Вы объявляете войну государству «{name}». Проверьте действующие обещания и положение войск.</p>}
 <button className="primary" disabled={blocked} onClick={submit}>{kind==='war'?(confirmed===s.revision?'Подтвердить объявление войны':'Проверить объявление войны'):'Направить посольство'}</button>
 <button className="quiet" onClick={advanced}>{modern?'Все договоры, вассалы и переписка':'Открыть дипломатию державы'}</button></section>;
}
