import type {RulerState} from './ruler-types';
const plural=new Intl.PluralRules('ru');
const word=(n:number,one:string,few:string,many:string)=>plural.select(n)==='one'?one:plural.select(n)==='few'?few:many;

export default function CampaignBrief({state:s,place,onAgenda,onWait,busy}:{state:RulerState;place:(id:string)=>string;onAgenda:(id:string)=>void;onWait:()=>void;busy:boolean}){
 const next=[...s.agendas].sort((a,b)=>a.deadline-b.deadline)[0];
 const own=Object.values(s.provinces).filter(p=>p.controlled).length;
 const work=s.pending_edicts.length+s.pending_orders.length+s.appointments.length;
 return <section className="campaign-brief" aria-label="Ваше правление">
  <div className="brief-scene"><span className="eyebrow">Глава {s.chapter.number||1} · {place(s.capital)}</span><h1>{s.chapter.name}</h1><p>{s.chapter.goal}</p><div className="reign-facts"><span><b>{own}</b> {word(own,'владение','владения','владений')} под контролем</span><span><b>{s.day}</b> {word(s.day,'день','дня','дней')} кампании</span></div></div>
  <div className="brief-current"><span className="eyebrow">{next?'Требуется ваше слово':'Дела державы'}</span><strong>{next?next.title:work?'Распоряжения исполняются':'Совет ожидает новых известий'}</strong><p>{next?(next.deadline<s.day?'Срок ответа истёк. Разберите вопрос, пока положение не изменилось.':`До срока ответа: ${next.deadline-s.day} дн. Решение остаётся за вами.`):work?`Ожидают прибытия: ${work}. Дайте исполнителям время добраться.`:'Проверьте донесения или продолжите время. Пока вы читаете, календарь стоит.'}</p><button disabled={busy||!!s.ending} onClick={()=>next?onAgenda(next.id):onWait()}>{next?'К вопросу совета':'Дождаться известий'}<span aria-hidden="true">›</span></button></div>
 </section>;
}
