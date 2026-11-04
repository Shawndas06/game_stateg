import {useEffect,useState} from 'react';
import {read,remember,Voice} from './CampaignMedia';
import type {RulerState} from './ruler-types';
export default function CampaignCoach({campaign,state:s,openCity,onTime,onCouncil}:{campaign:string;state:RulerState;openCity:()=>void;onTime:()=>void;onCouncil:()=>void}){
 const [step,set]=useState(()=>read('map-coach:'+campaign)||'welcome');
 const [baseline]=useState(s.day);
 const go=(next:string)=>{remember('map-coach:'+campaign,next);set(next)};
 useEffect(()=>{const restart=()=>go('welcome');window.addEventListener('campaign-teach',restart);return()=>window.removeEventListener('campaign-teach',restart)},[]);
 const work=s.provinces[s.capital];
 useEffect(()=>{if(step==='work'&&(work.construction||work.training.length||s.pending_edicts.some(e=>e.province===s.capital)))go('time');if(step==='time'&&s.day>baseline)go('result')},[step,s.day,work.construction,work.training.length,s.pending_edicts.length]);
 if(step==='done')return <button className="coach-reopen" onClick={()=>go('welcome')}>Помощь по карте</button>;
 return <aside className="campaign-coach" aria-label="Советник по карте"><strong>Салих · {step==='welcome'?'ваш первый приказ':step==='work'?'выберите работу':step==='time'?'дайте приказу исполниться':'проверьте результат'}</strong><p>{step==='welcome'?'Карта — ваше государство. Нажмите столицу, чтобы увидеть людей, запасы и доступные работы.':step==='work'?'Начните небольшой набор или зернохранилище. Цена и причины отказа указаны рядом с действием. Ресурсы не тратятся, пока вы не подтвердите приказ.':step==='time'?'Распоряжение записано. Продолжите время: гонец должен прибыть, а людям нужно завершить работу.':'Откройте столицу. Если работа ещё идёт, посмотрите оставшийся срок. Готовые новобранцы появляются в гарнизоне; здание — в списке построенного.'}</p>
 {step==='welcome'?<button className="primary" onClick={()=>{go('work');openCity()}}>Начать обучение</button>:step==='time'?<button className="primary" onClick={onTime}>Продолжить время</button>:<button onClick={openCity}>Показать столицу и работы</button>}
 {step==='result'&&<button onClick={()=>go('done')}>Понятно, продолжить правление</button>}<button onClick={onCouncil}>Выслушать совет</button><button className="quiet" onClick={()=>go('done')}>Пропустить обучение</button><details><summary>Озвучить подсказку</summary><Voice clip={step==='time'?'guide_time':step==='result'?'guide_reports':'map'}/></details></aside>;
}
