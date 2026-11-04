import TroopIcon from './TroopIcon';
import {useEffect,useState} from 'react';
import type {FieldBattle} from './ruler-types';
import './tactics.css';

const lanes=[['left','Левый фланг'],['center','Центр'],['right','Правый фланг'],['reserve','Резерв']] as const;
const orders=[['hold','Держать позицию'],['advance','Наступать / ввести резерв'],['left','На левый фланг'],['center','В центр'],['right','На правый фланг'],['reserve','Отвести в резерв']] as const;
const terrain={plain:'Равнина: открытое поле для манёвра.',woods:'Лесистая местность: конница теряет часть преимущества.',hill:'Возвышенность: обороняющиеся лучше держат позицию.'};

export default function TacticalBattle({battle,place,busy,error,send}:{battle:FieldBattle;place:string;busy:boolean;error:string;send:(kind:string,payload:Record<string,unknown>)=>Promise<void>}){
 const own=battle.units.filter(u=>u.side===battle.player_side&&u.count>0);
 const [selected,setSelected]=useState(own[0]?.id||''),[retreat,setRetreat]=useState(false);
 const [draft,setDraft]=useState<Record<string,string>>({});
 useEffect(()=>setDraft({}),[battle.round,battle.phase]);
 const unit=own.find(u=>u.id===selected)||own[0];
 const act=(kind:string,payload:Record<string,unknown>={})=>send(kind,{battle:battle.id,...payload});
 function line(side:string,lane:string){return battle.units.filter(u=>u.side===side&&(battle.phase==='deploy'?(draft[u.id]||u.lane):u.lane)===lane&&u.count>0).map(u=><button key={u.id} className={'field-unit '+(side===battle.player_side?'friendly':'enemy')} disabled={busy||side!==battle.player_side} aria-label={`${u.name}, ${u.commander}, ${u.count} воинов`} aria-pressed={unit?.id===u.id} onClick={()=>setSelected(u.id)}><span aria-hidden="true"><TroopIcon troop={u.troop}/></span><strong>{u.name}</strong><b>{u.count}</b><small>из {u.initial}</small></button>)}
 const enemy=battle.player_side==='attack'?'defend':'attack';
 return <main className="tactical-screen" aria-busy={busy}>
  <header><span className="eyebrow">Полевое сражение · {place}</span><h1>{battle.phase==='deploy'?'Расставьте войска':`Этап ${battle.round} из 8`}</h1><p>{terrain[battle.terrain]}</p><small>{battle.player_side==='attack'?'Ваше войско наступает.':'Ваше войско обороняется.'} Схема поля условная. Календарь остановлен; каждый этап — короткий отрезок одного сражения.</small></header>
  {error&&<p className="error" role="alert">{error}</p>}
  <section className={'battlefield '+battle.terrain} aria-label="Поле боя">
   <h2>Противник</h2><div className="field-lines">{lanes.map(([id,label])=><div key={id} className={'field-lane '+id}><small>{label}</small>{line(enemy,id)}</div>)}</div>
   <div className="battle-divider" aria-hidden="true">· · · линия столкновения · · ·</div>
   <h2>Ваши войска</h2><div className="field-lines">{lanes.map(([id,label])=><div key={id} className={'field-lane '+id}><small>{label}</small>{line(battle.player_side,id)}</div>)}</div>
  </section>
  {unit&&<section className="card field-orders"><h2>{unit.name} · {unit.count} воинов</h2><small>Командующий: {unit.commander}</small><p>Нажмите свой отряд на поле, затем выберите {battle.phase==='deploy'?'позицию':'приказ'}. {battle.phase==='combat'&&'Перемещение произойдёт на следующем этапе.'}</p><div className="field-actions">{battle.phase==='deploy'?lanes.map(([id,label])=><button key={id} disabled={busy} aria-pressed={(draft[unit.id]||unit.lane)===id} onClick={()=>setDraft(d=>({...d,[unit.id]:id}))}>{label}</button>):orders.map(([id,label])=><button key={id} disabled={busy} aria-pressed={(draft[unit.id]||unit.order)===id} onClick={()=>setDraft(d=>({...d,[unit.id]:id}))}>{label}</button>)}</div></section>}
  <p className="battle-draft" role="status">Подготовлено приказов: {Object.keys(draft).length}. Они исполнятся вместе после подтверждения этапа.</p><section className="battle-controls"><button className="primary" disabled={busy} onClick={()=>act('battle_step',{orders:Object.entries(draft).map(([unit,value])=>({unit,[battle.phase==='deploy'?'lane':'order']:value}))})}>{busy?'Приказ исполняется…':battle.phase==='deploy'?'Начать сражение':'Исполнить приказы →'}</button><details><summary>Другие решения</summary><p>Командующий завершит бой имеющимися силами. Отступление тоже несёт потери. Если доступного пути нет, оставшиеся воины будут потеряны.</p><button disabled={busy} onClick={()=>act('battle_delegate')}>Доверить бой командующему</button><button disabled={busy} onClick={()=>setRetreat(!retreat)}>Отступить…</button>{retreat&&<button disabled={busy} onClick={()=>act('battle_retreat')}>Подтвердить отход с поля</button>}</details></section>
  <section className="card" aria-live="polite"><h2>Ход боя</h2>{battle.log.slice(-4).map((entry,i)=><p key={i}>{entry}</p>)}</section>
 </main>;
}
