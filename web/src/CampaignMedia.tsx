import {useEffect,useRef,useState} from 'react';
import lines from './narration.json';
import type {RulerState} from './ruler-types';
import type {GuideStage} from './RulerGuide';
import './media.css';

type Clip=keyof typeof lines;
const read=(key:string)=>{try{return localStorage.getItem(key)}catch{return null}};
const remember=(key:string,value:string)=>{try{localStorage.setItem(key,value)}catch{/* Optional browser preference. */}};

/** Authored recordings, loaded on demand. No API, hidden game data or voice service. */
export function Voice({clip}:{clip:Clip}){
 const [enabled,setEnabled]=useState(()=>read('ruler-voice')==='on'),[playing,setPlaying]=useState(false),[failed,setFailed]=useState(false);
 const audio=useRef<HTMLAudioElement|null>(null);
 function play(){setFailed(false);audio.current?.play().catch(()=>{setPlaying(false);setFailed(true)})}
 useEffect(()=>{
  const player=new Audio(`/media/voice/${clip}.mp3`);audio.current=player;player.preload='none';
  player.onplay=()=>setPlaying(true);player.onpause=player.onended=()=>setPlaying(false);player.onerror=()=>{setPlaying(false);setFailed(true)};
  setFailed(false);setPlaying(false);if(enabled)play();
  return()=>{player.onplay=player.onpause=player.onended=player.onerror=null;player.pause();player.removeAttribute('src');player.load();audio.current=null};
 },[clip,enabled]);
 return <div className="voice-controls"><button aria-pressed={enabled} onClick={()=>{const next=!enabled;remember('ruler-voice',next?'on':'off');setEnabled(next)}}>{enabled?'Выключить голос':'Включить голос'}</button>{enabled&&<button onClick={()=>playing?audio.current?.pause():play()}>{playing?'Пауза':'Прослушать'}</button>}{failed&&<small role="status">Звук недоступен. Текст остаётся на экране; можно повторить воспроизведение.</small>}</div>;
}

export function Prologue({busy,error,onDone}:{busy:boolean;error:string;onDone:()=>void}){
 const [step,setStep]=useState(0);const clip=(['prologue_home','prologue_border','prologue_word'] as const)[step];
 return <main className="prologue" data-testid="prologue"><div className="prologue-art" role="img" aria-label="Небольшой бейлик в Анатолии на рассвете"/><section className="prologue-copy"><div className="intro-top"><span className="eyebrow">Пролог · {step+1} из 3</span><button disabled={busy} onClick={onDone}>Пропустить пролог</button></div><h1>{lines[clip].title}</h1><p>{lines[clip].text}</p><Voice clip={clip}/><small>Иллюстрированная история. Выборы и время начнутся после пролога.</small>{error&&<p className="error" role="alert">{error}</p>}<div className="intro-actions">{step>0&&<button onClick={()=>setStep(step-1)}>Назад</button>}<button className="primary" disabled={busy} onClick={()=>step<2?setStep(step+1):onDone()}>{step<2?'Продолжить':'К первому совету →'}</button></div></section></main>;
}

export function adviserClip(s:RulerState,tab:string,stage:GuideStage):Clip{
 if(s.ruler_status==='dead')return 'succession';
 if(s.arrears>0)return 'arrears';
 if(Object.values(s.armies).some(a=>a.grain<Object.values(a.troops).reduce((n,v)=>n+v,0)*3))return 'supply';
 const guide:Partial<Record<GuideStage,Clip>>={council:'guide_council',map:'map',army:'army',state:'state',time:'guide_time',reports:'guide_reports'};
 if(guide[stage])return guide[stage]!;
 if(tab==='court')return s.council.choices.length?(s.agendas.find(a=>a.id===s.council.agenda)?.scene==='founding'?'first_decision':'decision'):'wait';
 return ({map:'map',army:'army',state:'state',archive:'archive'} as Record<string,Clip>)[tab]||'wait';
}

export function Adviser({state,tab,stage,onStart,onDismiss}:{state:RulerState;tab:string;stage:GuideStage;onStart:()=>void;onDismiss:()=>void}){
 const clip=adviserClip(state,tab,stage),active=!['welcome','done','dismissed'].includes(stage);
 return <aside className={`adviser ${active?'adviser-compact':''}`} aria-label="Совет наставника" {...(stage==='welcome'?{'data-guide-stage':'welcome'}:{})}><img src="/media/advisor.webp" alt="Салих, наставник игрока" width="72" height="96"/><div><span className="eyebrow">Салих · наставник</span><h2>{lines[clip].title}</h2>{!active&&<p>{lines[clip].text}</p>}<Voice clip={clip}/>{stage==='welcome'&&<div className="intro-actions"><button className="primary" onClick={onStart}>Начать обучение</button><button aria-label="Пропустить обучение" onClick={onDismiss}>Разберусь сам</button></div>}</div></aside>;
}

export function AccessionFilm({state,onClose}:{state:RulerState;onClose:()=>void}){
 const ref=useRef<HTMLElement>(null),video=useRef<HTMLVideoElement>(null),[failed,setFailed]=useState(false);
 useEffect(()=>{const before=document.activeElement as HTMLElement|null;ref.current?.querySelector('button')?.focus();const overflow=document.body.style.overflow;document.body.style.overflow='hidden';function key(e:KeyboardEvent){if(e.key==='Escape')onClose();if(e.key==='Tab'){const nodes=Array.from(ref.current?.querySelectorAll<HTMLElement>('button,video,a')||[]),first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}}document.addEventListener('keydown',key);return()=>{document.removeEventListener('keydown',key);document.body.style.overflow=overflow;before?.focus()}},[onClose]);
 if(state.accession?.to==='murad')return <div className="film-backdrop"><section className="accession-film" role="dialog" aria-modal="true" aria-labelledby="film-title" ref={ref}><span className="eyebrow">Новое правление</span><h1 id="film-title">Мурад принимает державу</h1><p>Печать Орхана лежит перед новым правителем. За дверями ждут люди с прежними обещаниями и новыми просьбами. Совету предстоит обсудить защиту рубежа и порядок в землях. Решение остаётся за вами.</p><p>Казна: {state.gold} монет. Армии, назначения и долги продолжают существовать. Смена правителя не отменяет обязательств.</p><button className="primary" onClick={onClose}>К совету Мурада →</button></section></div>;
 return <div className="film-backdrop"><section className="accession-film" role="dialog" aria-modal="true" aria-labelledby="film-title" ref={ref}><div className="intro-top"><span className="eyebrow">Передача власти · иллюстрированная сцена</span><button onClick={onClose}>Пропустить видео</button></div><h1 id="film-title">Наследие Османа</h1>{failed?<img className="film-still" src="/media/succession.webp" alt="Прощание с Османом и начало правления Орхана"/>:<video ref={video} controls playsInline preload="metadata" poster="/media/succession.webp" onError={()=>setFailed(true)} onEnded={onClose} aria-label="Прощание с Османом и признание Орхана"><source src="/media/succession.mp4" type="video/mp4"/></video>}{!failed&&<button onClick={()=>video.current?.play().catch(()=>setFailed(true))}>Начать просмотр</button>}<p>{lines.succession_farewell.text} {lines.succession_inherit.text} {lines.succession_orhan.text}</p><p className="muted">В вашей партии: день {state.accession?.day}, казна {state.gold} монет{state.arrears>0?`, задолженность ${state.arrears}`:''}. Приказы, войска и обязательства сохранены.</p><button className="primary" onClick={onClose}>Продолжить правление Орхана</button></section></div>;
}
export {read,remember};
