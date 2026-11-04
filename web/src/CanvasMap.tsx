import {useEffect,useRef,useState} from 'react';
import type {Catalog} from './types';
import type {AtlasState} from './Atlas';
import {project} from './atlas-geometry';
import type {Geography,Point,Viewport} from './atlas-geometry';
import {at,factionColor,hitIndex,paths,profiles,settlement,zoomAt} from './map-scene';
import type {Hit,Quality} from './map-scene';
import {metric} from './diagnostics';
import {read,remember} from './CampaignMedia';

type Props={state:AtlasState;catalog:Catalog;selected:string;select:(id:string)=>void;selectArmy:(id:string)=>void;selectedArmy?:string;armyNames:Record<string,string>;focusToken:number;campaign:string;plannedRoute?:string[];planned?:{province:string;count:number}[];quality:Quality;onHelp:()=>void};
let geography:Promise<Geography>|undefined;
const load=()=>geography||(geography=fetch('/mediterranean-geography.json?v='+encodeURIComponent(document.querySelector('meta[name=build]')?.getAttribute('content')||'development')).then(r=>{if(!r.ok)throw Error('Карта не загрузилась');return r.json()}).catch(e=>{geography=undefined;throw e}));
export default function CanvasMap(props:Props){
 const {state,catalog,selected,select,selectArmy,selectedArmy,armyNames,campaign,quality,onHelp}=props;
 const root=useRef<HTMLDivElement>(null),canvas=useRef<HTMLCanvasElement>(null),camera=useRef<Viewport>({x:0,y:0,width:60,height:40});
 const priorSelected=useRef(selected);
 const draw=useRef<()=>void>(()=>{}),schedule=useRef<()=>void>(()=>{}),focus=useRef<(id:string)=>void>(()=>{}),moved=useRef(false),suppress=useRef(false);
 const [hits,setHits]=useState<Hit[]>([]),[query,setQuery]=useState(''),[political,setPolitical]=useState(false),[failure,setFailure]=useState(''),[attempt,setAttempt]=useState(0);
 const latest=useRef(props);latest.current=props;
 useEffect(()=>{
  const area=root.current!,surface=canvas.current!,ctx=surface.getContext('2d')!;let live=true,frame=0,w=1,h=1,geo:ReturnType<typeof paths>|null=null;
  let terrain:HTMLCanvasElement|null=null,terrainView:Viewport|null=null;
  const symbols=new Map<string,HTMLCanvasElement>(),points=catalog.places.map(p=>({...p,point:project(p.lon,p.lat)}));
  let lookup=hitIndex([]),active=false,dragged=false,lastFrame=0;const frames:number[]=[];const fingers=new Map<number,Point>();let last:Point=[0,0],start:Point=[0,0],distance=0;
  const persist=()=>remember('camera:'+campaign,JSON.stringify(camera.current));
  function paint(){
   frame=0;if(!live||document.hidden||!geo)return;if(active){const now=performance.now();if(lastFrame)frames.push(now-lastFrame);lastFrame=now;}const v=camera.current,p=latest.current,s=profiles[quality];
   const dpr=Math.min(window.devicePixelRatio||1,s.dpr);if(surface.width!==Math.round(w*dpr)||surface.height!==Math.round(h*dpr)){surface.width=Math.round(w*dpr);surface.height=Math.round(h*dpr)}
   ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#9bb9ba';ctx.fillRect(0,0,w,h);
   if(!terrainView||!terrain||v.width<terrainView.width/3||v.width>terrainView.width||v.x<terrainView.x||v.y<terrainView.y||v.x+v.width>terrainView.x+terrainView.width||v.y+v.height>terrainView.y+terrainView.height){
    terrainView={x:v.x-v.width/4,y:v.y-v.height/4,width:v.width*1.5,height:v.height*1.5};
    terrain=document.createElement('canvas');terrain.width=Math.ceil(w*dpr*1.5);terrain.height=Math.ceil(h*dpr*1.5);const t=terrain.getContext('2d')!;
    t.fillStyle='#9bb9ba';t.fillRect(0,0,terrain.width,terrain.height);t.scale(terrain.width/terrainView.width,terrain.height/terrainView.height);t.translate(-terrainView.x,-terrainView.y);
    t.fillStyle='#d8c99d';t.strokeStyle='#8a927b';t.lineWidth=v.width/w;
    for(const path of geo.land){t.fill(path,'evenodd');t.stroke(path)}t.fillStyle='#9bb9ba';for(const path of geo.lakes)t.fill(path,'evenodd');
    if(s.decor){t.strokeStyle='#8b845966';t.fillStyle='#b1a57955';t.lineWidth=v.width/w;for(const [lon,lat] of [[29.22,40.07],[30.1,39.4],[31.1,40.6],[32.5,37],[24.5,42.7],[35.5,38.6]]){const [x,y]=project(lon,lat);for(let n=0;n<s.decor*3;n++){const xx=x+n*.7,yy=y+(n%2)*.7;t.beginPath();t.moveTo(xx-.6,yy+.5);t.lineTo(xx,yy-.6);t.lineTo(xx+.6,yy+.5);t.closePath();t.fill();t.stroke()}}}
   }
   const origin=at([terrainView.x,terrainView.y],v,w,h);ctx.drawImage(terrain,...origin,terrainView.width/v.width*w,terrainView.height/v.height*h);
   const indexed=new Map(points.map(x=>[x.id,x]));ctx.lineWidth=1;ctx.strokeStyle='#9e8d65';
   for(const [a,b] of catalog.roads){const p1=indexed.get(a),p2=indexed.get(b);if(!p1||!p2)continue;const [x,y]=at(p1.point,v,w,h),[xx,yy]=at(p2.point,v,w,h);if(Math.max(x,xx)<0||Math.min(x,xx)>w||Math.max(y,yy)<0||Math.min(y,yy)>h)continue;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.stroke()}
   const visible:Hit[]=[],occupied=new Set<string>();const ordered=[...points].sort((a,b)=>Number(a.id===p.selected)-Number(b.id===p.selected));
   for(const place of ordered){const [x,y]=at(place.point,v,w,h);if(x<-40||x>w+40||y<-40||y>h+40)continue;const province=p.state.provinces[place.id];if(!province)continue;
    const chosen=place.id===p.selected;const cell=`${Math.floor(x/56)},${Math.floor(y/48)}`;const detailed=v.width<260;const label=chosen||detailed&&!occupied.has(cell);occupied.add(cell);
    if(political){ctx.globalAlpha=.2;ctx.fillStyle=factionColor(province.controller);ctx.beginPath();ctx.arc(x,y,34,0,7);ctx.fill();ctx.globalAlpha=1}
    if(chosen){ctx.strokeStyle='#bc8739';ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(x,y+6,25,12,0,0,7);ctx.stroke()}
    if(detailed||chosen){const key=`${province.fortress_level>0}:${place.port}`;if(!symbols.has(key))symbols.set(key,settlement(province.fortress_level>0,place.port,quality));ctx.drawImage(symbols.get(key)!,x-32,y-43,64,64)}else{ctx.fillStyle=factionColor(province.controller);ctx.fillRect(x-3,y-3,6,6)}
    ctx.fillStyle=factionColor(province.controller);ctx.fillRect(x+14,y-39,11,7);ctx.strokeStyle='#655a40';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x+14,y-39);ctx.lineTo(x+14,y-22);ctx.stroke();
    if(p.state.sieges[place.id]){ctx.strokeStyle='#a14535';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,28,0,7);ctx.stroke()}
    if(label){const text=(place.id===p.state.capital?'★ ':'')+place.name;ctx.font='14px Georgia';const width=ctx.measureText(text).width+10;ctx.fillStyle=chosen?'#234936':'#f3e6c8';ctx.fillRect(x-width/2,y+19,width,22);ctx.fillStyle=chosen?'#fff9e9':'#413f2c';ctx.textAlign='center';ctx.fillText(text,x,y+35)}
    visible.push({id:place.id,kind:'place',x,y});
   }
   for(const army of Object.values(p.state.armies)){if(army.faction!=='ottoman')continue;const place=indexed.get(army.location);if(!place)continue;const [x,y0]=at(place.point,v,w,h),y=y0-45;if(x<-24||x>w+24||y<-24||y>h+24)continue;const n=Object.values(army.troops).reduce((a,b)=>a+b,0);if(!n)continue;ctx.fillStyle=army.id===p.selectedArmy?'#a87532':'#244d39';ctx.fillRect(x-23,y-18,46,28);ctx.fillStyle='#fff9e8';ctx.font='bold 14px sans-serif';ctx.textAlign='center';ctx.fillText(String(n),x,y+1);visible.push({id:army.id,kind:'army',x,y});
    if(army.order){const target=indexed.get(army.order.target);if(target){const end=at(target.point,v,w,h);ctx.strokeStyle='#315b42';ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(x,y0);ctx.lineTo(...end);ctx.stroke();ctx.setLineDash([])}}
   }
   for(const order of p.planned||[]){const source=indexed.get(order.province);if(!source)continue;const [x,y]=at(source.point,v,w,h);ctx.strokeStyle='#a77a32';ctx.setLineDash([3,3]);ctx.strokeRect(x-32,y-60,64,22);ctx.setLineDash([]);ctx.fillStyle='#72501e';ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText(`Сбор: ${order.count}`,x,y-45)}
   if(p.plannedRoute?.length){ctx.strokeStyle='#e4b453';ctx.lineWidth=3;ctx.setLineDash([8,4]);ctx.beginPath();p.plannedRoute.forEach((id,i)=>{const point=indexed.get(id);if(point){const pos=at(point.point,v,w,h);if(i)ctx.lineTo(...pos);else ctx.moveTo(...pos)}});ctx.stroke();ctx.setLineDash([])}
   lookup=hitIndex(visible);if(!active)setHits(visible);
  }
  const queue=()=>{if(live&&!frame&&!document.hidden)frame=requestAnimationFrame(paint)};schedule.current=queue;draw.current=paint;
  const center=(id:string)=>{const point=points.find(p=>p.id===id)?.point;if(!point)return;camera.current={x:point[0]-w/32,y:point[1]-h/32,width:w/16,height:h/16};persist();queue()};focus.current=center;
  function resize(){const box=area.getBoundingClientRect();w=Math.max(1,box.width);h=Math.max(1,box.height);camera.current.height=camera.current.width*h/w;queue()}
  const observer=new ResizeObserver(resize);observer.observe(area);resize();
  try{const saved=JSON.parse(read('camera:'+campaign)||'null');if(saved&&['x','y','width','height'].every(k=>Number.isFinite(saved[k]))&&saved.width>=12&&saved.width<=7600)camera.current={...saved,height:saved.width*h/w};else center(state.capital)}catch{center(state.capital)}
  load().then(data=>{if(live){geo=paths(data,quality);setFailure('');queue()}}).catch(()=>{if(live)setFailure('Карта не загрузилась. Проверьте соединение и повторите.')});
  const position=(e:PointerEvent):Point=>{const b=area.getBoundingClientRect();return [e.clientX-b.x,e.clientY-b.y]};
  const down=(e:PointerEvent)=>{if((e.target as HTMLElement).closest('.map-hud'))return;if(!fingers.size){moved.current=false;dragged=false;lastFrame=0;frames.length=0;start=position(e)}fingers.set(e.pointerId,position(e));active=true;area.setPointerCapture(e.pointerId);const a=[...fingers.values()];last=a.length>1?[(a[0][0]+a[1][0])/2,(a[0][1]+a[1][1])/2]:a[0];distance=a.length>1?Math.hypot(a[1][0]-a[0][0],a[1][1]-a[0][1]):0;};
  const move=(e:PointerEvent)=>{if(!fingers.has(e.pointerId))return;fingers.set(e.pointerId,position(e));const a=[...fingers.values()],mid:Point=a.length>1?[(a[0][0]+a[1][0])/2,(a[0][1]+a[1][1])/2]:a[0];if(a.length>1){const d=Math.hypot(a[1][0]-a[0][0],a[1][1]-a[0][1]);if(distance>0)camera.current=zoomAt(camera.current,distance/Math.max(1,d),mid,w,h);distance=d;moved.current=true}else if(Math.hypot(mid[0]-start[0],mid[1]-start[1])>6)moved.current=true;if(moved.current){camera.current.x-=(mid[0]-last[0])*camera.current.width/w;camera.current.y-=(mid[1]-last[1])*camera.current.height/h;dragged=true;queue()}last=mid};
  const up=(e:PointerEvent)=>{if(!fingers.has(e.pointerId))return;const pos=position(e);fingers.delete(e.pointerId);if(area.hasPointerCapture(e.pointerId))area.releasePointerCapture(e.pointerId);if(fingers.size){last=[...fingers.values()][0];return}active=false;suppress.current=dragged||e.type==='pointercancel';if(!suppress.current){const hit=lookup(...pos);if(hit){suppress.current=true;if(hit.kind==='army')latest.current.selectArmy(hit.id);else latest.current.select(hit.id)}}persist();queue();if(dragged&&frames.length>=8){const sorted=[...frames].sort((a,b)=>a-b),p95=sorted[Math.min(sorted.length-1,Math.floor(sorted.length*.95))];metric({kind:'map_frame',duration_ms:p95});if(p95>50&&quality!=='low'&&read('map-auto')!=='off'){remember('map-quality',quality==='high'?'medium':'low');window.dispatchEvent(new Event('graphics-quality'))}}};
  const wheel=(e:WheelEvent)=>{if((e.target as HTMLElement).closest('.map-hud'))return;e.preventDefault();camera.current=zoomAt(camera.current,Math.exp(e.deltaY*.001),[e.offsetX,e.offsetY],w,h);persist();queue()};
  area.addEventListener('pointerdown',down);area.addEventListener('pointermove',move);area.addEventListener('pointerup',up);area.addEventListener('pointercancel',up);area.addEventListener('wheel',wheel,{passive:false});document.addEventListener('visibilitychange',queue);
  return()=>{live=false;cancelAnimationFrame(frame);observer.disconnect();area.removeEventListener('pointerdown',down);area.removeEventListener('pointermove',move);area.removeEventListener('pointerup',up);area.removeEventListener('pointercancel',up);area.removeEventListener('wheel',wheel);document.removeEventListener('visibilitychange',queue)};
 },[campaign,quality,political,attempt]);
 useEffect(()=>{if(priorSelected.current!==selected){priorSelected.current=selected;focus.current(selected)}else schedule.current()},[state,selected,selectedArmy,props.plannedRoute]);
 useEffect(()=>{if(props.focusToken)focus.current(selected)},[props.focusToken]);
 const choose=(id:string)=>{focus.current(id);select(id);setQuery('')};
 return <div className="canvas-world" ref={root} data-quality={quality}>
  <canvas ref={canvas} aria-label="Карта державы"/>
  <div className="map-hit-layer">{hits.map(hit=><button key={hit.kind+hit.id} data-testid={hit.kind==='place'?'place-'+hit.id:undefined} data-map-army={hit.kind==='army'?hit.id:undefined} aria-label={hit.kind==='army'?`Армия: ${armyNames[hit.id]}`:catalog.places.find(p=>p.id===hit.id)?.name} aria-pressed={hit.kind==='army'?hit.id===selectedArmy:hit.id===selected} style={{left:hit.x-24,top:hit.y-24,zIndex:hit.id===selected||hit.id===selectedArmy?3:1}} onClick={e=>{if(e.detail&&suppress.current)return;hit.kind==='army'?selectArmy(hit.id):select(hit.id)}}/>)}</div>
  <div className="map-hud map-tools"><button onClick={()=>choose(state.capital)}>Столица</button><button onClick={()=>{const el=root.current!;camera.current={x:-3400,y:1150-3600*el.clientHeight/el.clientWidth,width:7200,height:7200*el.clientHeight/el.clientWidth};remember('camera:'+campaign,JSON.stringify(camera.current));draw.current()}}>Весь мир</button><button aria-pressed={political} onClick={()=>setPolitical(x=>!x)}>Границы</button><button onClick={onHelp}>Советник</button></div>
  <div className="map-hud map-search"><input aria-label="Поиск поселения" placeholder="Найти город…" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<div className="map-search-results">{catalog.places.filter(p=>p.name.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru'))).slice(0,12).map(p=><button key={p.id} data-search-place={p.id} onClick={()=>choose(p.id)}>{p.name}</button>)}</div>}</div>
  {failure&&<div className="map-hud map-failure" role="alert">{failure}<button onClick={()=>setAttempt(x=>x+1)}>Повторить загрузку карты</button></div>}
 </div>;
}
