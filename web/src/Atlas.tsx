import {useEffect, useLayoutEffect, useId, useMemo, useRef, useState} from 'react';
import type {Catalog} from './types';
export type AtlasState={calendar:{year:number};capital:string;provinces:Record<string,{controller:string;fortress_level:number}>;armies:Record<string,{id:string;faction:string;location:string;troops:Record<string,number>;order:{target:string}|null}>;sieges:Record<string,unknown>};
import {layoutPlaces, landSampler, polygonPath, project, screenPoint} from './atlas-geometry';
import type {Geography, Point, Viewport} from './atlas-geometry';
import './atlas.css';

const factionColor: Record<string, string> = {ottoman: '#335d45', byzantine: '#934b42', germiyan: '#82704b'};
const colorFor = (fid: string) => factionColor[fid] || `hsl(${[...fid].reduce((a,c)=>a+c.charCodeAt(0)*17,0)%360} 29% 40%)`;
const troopCount = (troops: Record<string, number>) => Object.values(troops).reduce((a, b) => a + b, 0);

function Fortress({large, port}: {large: boolean; port: boolean}) {
  return <g stroke="#57452e" strokeWidth=".85" strokeLinejoin="round">
    <ellipse cy="8" rx="19" ry="5" fill="#70593c" opacity=".17" stroke="none"/>
    <path d="M-17 4L0 11 19 3 3-4Z" fill="#a78b60"/>
    <path d="M-14-6L2 0 2 9-14 3Z" fill="#d5bf8b"/>
    <path d="M2 0L16-5 16 3 2 9Z" fill="#a78c5b"/>
    <path d="M-15-8L1-2 17-8 3-14Z" fill="#eee0b2"/>
    <path d="M-15-8V-13L-11-12V-8L-7-7V-11L-3-10V-6L1-5V-9L5-10V-6L9-8V-12L13-14V-9L17-11V-6" fill="#dfcea0"/>
    <path d="M-16-6V-21L-9-18V-3Z" fill="#d9c08a"/>
    <path d="M-9-18L-3-21V-7L-9-3Z" fill="#ac8b55"/>
    <path d="M-17-21L-10-29-2-21-9-18Z" fill="#716f68"/>
    <path d="M9-9V-23L15-21V2L9 5Z" fill="#c8ab73"/>
    <path d="M15-21L20-24V0L15 2Z" fill="#9f804e"/>
    <path d="M8-24L14-31 21-24 15-21Z" fill="#77746b"/>
    {large && <><path d="M-4-4V-24L4-21V1Z" fill="#e7d6a9"/><path d="M4-21L10-24V-2L4 1Z" fill="#b89a65"/><path d="M-5-24L2-33 11-24 4-21Z" fill="#807b6c"/><path d="M0-17V-12M6-16V-11" stroke="#66543a" strokeWidth="2"/></>}
    <path d="M-6 4V-1Q-3-5 0 1V7Z" fill="#5c513c"/>
    <path d="M-13-17V-13M13-18V-13" stroke="#64533a" strokeWidth="1.5"/>
    {port && <g transform="translate(-23 8)" stroke="#3e6a6a" fill="none" strokeWidth="1.2"><path d="M0-8V4M-5 0Q0 9 5 0M-3-4H3"/><circle cy="-10" r="2"/></g>}
  </g>;
}

function Village() {
  return <g stroke="#6e5534" strokeWidth=".8" strokeLinejoin="round"><ellipse cy="7" rx="21" ry="5" fill="#85754e" opacity=".2"/><path d="M-19-5L-9-9 1-4V6L-9 10-19 5Z" fill="#d6bf88"/><path d="M-22-5L-11-17 3-5-9-1Z" fill="#9e6c47"/><path d="M2-7L10-10 20-6V5L11 9 2 5Z" fill="#e5ce98"/><path d="M0-7L8-18 22-7 11-3Z" fill="#8a6551"/><path d="M-13 7V0H-8V9M9 7V0H13V8" fill="#6b5740"/><path d="M-24 8H24" stroke="#7a8559"/></g>;
}

function Compass({x, y}: {x: number; y: number}) {
  return <g transform={`translate(${x} ${y})`} className="atlas-compass" pointerEvents="none">
    <circle r="24" fill="#f3e7c9" fillOpacity=".8" stroke="#a78b52" strokeWidth=".7"/>
    <circle r="19" fill="none" stroke="#b9a477" strokeWidth=".6"/>
    <path d="M0-30L5-5 0 0-5 5ZM0 30L-5 5 0 0 5-5Z" fill="#6f8072" stroke="#6b6950" strokeWidth=".6"/>
    <path d="M-27 0L-5-5 0 0 5 5ZM27 0L5 5 0 0-5-5Z" fill="#c2a56a" stroke="#6b6950" strokeWidth=".6"/>
    <circle r="3" fill="#b88e40"/>
    <text y="-36" textAnchor="middle" fontFamily="Georgia" fontSize="11" fill="#6f7358">С</text>
  </g>;
}

export default function Atlas({state, catalog, selected, select}: {state: AtlasState; catalog: Catalog; selected: string; select: (id: string) => void}) {
  const [world, setWorld] = useState(false);
  const [zoom, setZoom] = useState(3);
  const [pan, setPan] = useState<Point>(()=>{const p=catalog.places.find(p=>p.id===state.capital)!;const [x,y]=project(p.lon,p.lat);return [x-794,y-226.5]});
  const [size, setSize] = useState({width: 350, height: 520});
  const [geography, setGeography] = useState<Geography | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [fullScreen, setFullScreen] = useState(false);
  const [layers, setLayers] = useState(true);
  const [region, setRegion] = useState('');
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState('all');
  const [attempt, setAttempt] = useState(0);
  const area = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const pointers = useRef(new Map<number, Point>());
  const moved = useRef(false);
  const cameraFrame = useRef<number | null>(null);
  const cameraDelta = useRef({x:0,y:0,zoom:1});
  useEffect(()=>()=>{if(cameraFrame.current!==null)cancelAnimationFrame(cameraFrame.current)},[]);
  const uid = useId().replace(/:/g, '');
  const id = (name: string) => `${uid}-${name}`;
  const width = size.width, height = size.height;
  const baseWidth = world ? Math.max(1240, 655 * width / height) : Math.max(59, 42 * width / height);
  const baseCenter: Point = world ? [535, 310] : [794, 226.5];
  const chapterWidth = baseWidth / zoom;
  const view: Viewport = {x: baseCenter[0] - chapterWidth / 2 + pan[0], y: baseCenter[1] - chapterWidth * height / width / 2 + pan[1], width: chapterWidth, height: chapterWidth * height / width};
  const toScreen = (lon: number, lat: number) => screenPoint(project(lon, lat), view, width, height);
  const visible = useMemo(() => catalog.places.filter(p => {const [x,y]=screenPoint(project(p.lon,p.lat),view,width,height);return x>15&&x<width-15&&y>30&&y<height-90}), [catalog.places,view.x,view.y,view.width,view.height,width,height]);
  const detailed = visible.length <= Math.max(12, Math.floor(width * (height-150) / 9000));
  const pins = useMemo(() => detailed ? layoutPlaces(visible, view, width, height) : [], [visible,detailed,view.x,view.y,view.width,view.height,width,height]);
  const results = catalog.places.filter(p => (kind==='all'||(kind==='village' ? state.provinces[p.id].fortress_level===0 : state.provinces[p.id].fortress_level>0)) && p.name.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru')));

  useEffect(() => {
    const controller = new AbortController();
    setLoadError(false);
    fetch('/mediterranean-geography.json', {signal: controller.signal}).then(response => {
      if (!response.ok) throw new Error('Map unavailable');
      return response.json();
    }).then(data => setGeography(data)).catch(error => {if (error.name !== 'AbortError') setLoadError(true)});
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    if (!area.current) return;
    const observer = new ResizeObserver(entries => {
      const {width, height} = entries[0].contentRect;
      if (width && height) setSize({width, height});
    });
    observer.observe(area.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!fullScreen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const escape = (e: KeyboardEvent) => {if (e.key === 'Escape') setFullScreen(false)};
    window.addEventListener('keydown', escape);
    return () => {document.body.style.overflow = previous; window.removeEventListener('keydown', escape)};
  }, [fullScreen]);

  // Coastline geometry is independent of the camera. React only updates the
  // surrounding transform during a gesture; the 26k vertices stay unchanged.
  const coastlines = useMemo(() => {
    if (!geography) return null;
    const coordinates = {x:0,y:0,width:1,height:1};
    return <g data-coastline="true" fillRule="evenodd" strokeLinejoin="round" pointerEvents="none">
      {geography.land.map((poly,i)=><path key={`shore-${i}`} d={polygonPath(poly,coordinates,1,1)} fill={`url(#${id('earth')})`} stroke="#f0e3b8" strokeWidth="7" vectorEffect="non-scaling-stroke"/>)}
      {geography.land.map((poly,i)=><path key={i} d={polygonPath(poly,coordinates,1,1)} fill={`url(#${id('earth')})`} stroke="#75846d" strokeWidth="1.15" vectorEffect="non-scaling-stroke"/>)}
      {geography.lakes.map((poly,i)=><path key={`lake-${i}`} d={polygonPath(poly,coordinates,1,1)} fill="#a1b7a4" stroke="#728b77" strokeWidth=".8" vectorEffect="non-scaling-stroke"/>) }
    </g>;
  }, [geography,uid]);
  const isLand = useMemo(() => geography ? landSampler(geography) : null, [geography]);

  const terrain = useMemo(() => {
    if (!isLand || width < 700) return [];
    const result: {lon: number; lat: number; kind: number; scale: number}[] = [];
    const step = view.width > 150 ? 1.3 : .14;
    const west = view.x / 20 - 10, north = 50 - view.y / 23;
    for (let row = 0; row < 35; row++) for (let col = 0; col < 42; col++) {
      const lon = (Math.floor(west / step) + col) * step;
      const lat = (Math.ceil(north / step) - row) * step;
      const n = Math.abs(Math.round(lon * 113 + lat * 79)) % 101;
      if (n > 40 || !isLand(lon, lat)) continue;
      const mountain = (lat > 41 && lon > 6 && lon < 25) || (lat > 36 && lat < 40 && lon > 28) || (lat < 35 && lat > 30 && lon < 10);
      result.push({lon, lat, kind: mountain ? n % 3 : 3, scale: .6 + (n % 5) * .12});
    }
    return result;
  }, [isLand, width < 700, Math.floor((view.x/20-10)/(view.width>150?1.3:.14)), Math.ceil((50-view.y/23)/(view.width>150?1.3:.14)), view.width > 150]);

  // Gesture frames move one composited surface, without React/layout/path updates.
  function paintCamera() {
    cameraFrame.current=null;
    const d=cameraDelta.current;
    if(svg.current)svg.current.style.transform=`translate3d(${-d.x*width/view.width*d.zoom}px,${-d.y*height/view.height*d.zoom}px,0) scale(${d.zoom})`;
  }
  useLayoutEffect(()=>{if(svg.current)svg.current.style.transform=''},[pan,zoom]);
  function flushCamera() {
    if(cameraFrame.current!==null)cancelAnimationFrame(cameraFrame.current);
    cameraFrame.current=null;
    const delta=cameraDelta.current;cameraDelta.current={x:0,y:0,zoom:1};
    if(delta.x||delta.y)setPan(p=>[Math.max(-baseCenter[0]-10,Math.min(1090-baseCenter[0],p[0]+delta.x)),Math.max(-baseCenter[1],Math.min(635-baseCenter[1],p[1]+delta.y))]);
    if(delta.zoom!==1)setZoom(z=>Math.max(.8,Math.min(world?80:6,z*delta.zoom)));
  }
  function queueCamera(x=0,y=0,scale=1) {
    cameraDelta.current.x+=x;cameraDelta.current.y+=y;cameraDelta.current.zoom=Math.max(.8/zoom,Math.min((world?80:6)/zoom,cameraDelta.current.zoom*scale));
    if(cameraFrame.current===null)cameraFrame.current=requestAnimationFrame(paintCamera);
  }
  function reset(toWorld = world, overview = false) {if(cameraFrame.current!==null)cancelAnimationFrame(cameraFrame.current);cameraFrame.current=null;cameraDelta.current={x:0,y:0,zoom:1};setWorld(toWorld); setRegion(''); setZoom(toWorld || overview ? 1 : 3); setPan([0, 0]); pointers.current.clear(); moved.current = false}
  function pointerMove(e: React.PointerEvent<SVGSVGElement | HTMLDivElement>) {
    const old = pointers.current.get(e.pointerId);
    if (!old) return;
    const next: Point = [e.clientX, e.clientY];
    if (pointers.current.size === 1) {
      const dx = next[0] - old[0], dy = next[1] - old[1];
      if (Math.abs(dx) + Math.abs(dy) > 2) moved.current = true;
      queueCamera(-dx*view.width/width,-dy*view.height/height);
    } else {
      moved.current = true;
      const other = [...pointers.current.entries()].find(([key]) => key !== e.pointerId)![1];
      const before = Math.hypot(old[0] - other[0], old[1] - other[1]);
      if (before > 10) queueCamera(0,0,Math.hypot(next[0]-other[0],next[1]-other[1])/before);
    }
    pointers.current.set(e.pointerId, next);
  }
  const endPointer = (e: React.PointerEvent<SVGSVGElement | HTMLDivElement>) => {
    flushCamera();
    pointers.current.delete(e.pointerId);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };
  const selectedPlace = catalog.places.find(p => p.id === selected)!;
  function focusPlace(pid: string, scale = 18) {
    const p = catalog.places.find(p=>p.id===pid)!;
    const [x,y] = project(p.lon,p.lat);
    setZoom(baseWidth / scale); setPan([x-baseCenter[0],y-baseCenter[1]]); select(pid);
    requestAnimationFrame(()=>area.current?.scrollIntoView({block:'center'}));
  }
  function focusSelected() {focusPlace(selectedPlace.id)}
  const choose = (pid: string) => {if (!moved.current) select(pid)};
  const previousSelection = useRef(selected);
  useEffect(()=>{
    if (previousSelection.current === selected) return;
    previousSelection.current = selected;
    focusPlace(selected);
  },[selected]);

  return <section className={`illustrated-atlas ${fullScreen ? 'atlas-fullscreen' : ''}`} aria-label="Карта кампании">
    <header className="atlas-map-heading"><div><span className="eyebrow">{world ? 'Средиземноморье' : 'Вифиния · кампания'}</span><strong>{world ? 'Карта известного мира' : 'На подступах к Бурсе'}</strong></div><button className="map-heading-button" onClick={() => reset(!world)}>{world ? 'К кампании' : 'Весь мир'}</button></header>
    <div className="atlas-home"><button className="primary" onClick={()=>focusPlace(state.capital)}>Моя столица · {catalog.places.find(p=>p.id===state.capital)?.name}</button><span>Выбрано: {selectedPlace.name}</span></div><div className="atlas-navigation"><label>Регион<select aria-label="Регион карты" value={region} onChange={e=>{const r=catalog.regions.find(r=>r.id===e.target.value);setRegion(e.target.value);if(r){const [x,y]=project(r.lon,r.lat);setPan([x-baseCenter[0],y-baseCenter[1]]);setZoom(baseWidth/(r.width*20))}}}><option value="">Выбрать регион…</option>{catalog.regions.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><span>{visible.length} в окне · {catalog.places.length} всего</span></div>
    <div className="atlas-search"><input aria-label="Поиск поселения" placeholder="Найти город или поселение…" value={query} onChange={e=>setQuery(e.target.value)}/><select aria-label="Тип поселения" value={kind} onChange={e=>setKind(e.target.value)}><option value="all">Все места</option><option value="fortress">Укреплённые</option><option value="village">Поселения</option></select></div>
    {(query || kind!=='all') && <div className="atlas-search-results" aria-label="Результаты поиска"><small>Найдено: {results.length}</small>{results.map(p=><button key={p.id} data-search-place={p.id} onClick={()=>{focusPlace(p.id);setQuery('');setKind('all')}}>{p.name}<small>{catalog.factions[state.provinces[p.id].controller]}</small></button>)}</div>}
    <div ref={area} className={`illustrated-map-canvas ${world ? 'world-map-canvas' : ''}`}>
      <svg ref={svg} className="illustrated-map" aria-label="Стратегическая карта Средиземноморья" data-detail={detailed ? 'fortresses' : 'overview'} viewBox={`0 0 ${width} ${height}`} onPointerDown={e => {
        if (!pointers.current.size) moved.current = false;
        pointers.current.set(e.pointerId, [e.clientX, e.clientY]);
        // Keep target clicks on their marker; capture only background drags.
        const marker = (e.target as Element).closest('[data-place]');
        (marker || e.currentTarget).setPointerCapture(e.pointerId);
      }} onPointerMove={pointerMove} onPointerUp={endPointer} onPointerCancel={endPointer}>
        <defs>
          <linearGradient id={id('sea')} x2=".3" y2="1"><stop stopColor="#829f9a"/><stop offset=".55" stopColor="#a8c0b4"/><stop offset="1" stopColor="#bdcebc"/></linearGradient>
          <linearGradient id={id('earth')} x2=".7" y2="1"><stop stopColor="#eaddb9"/><stop offset=".5" stopColor="#e2d0a0"/><stop offset="1" stopColor="#cdbb8b"/></linearGradient>
          <radialGradient id={id('vignette')}><stop offset=".5" stopColor="#725f39" stopOpacity="0"/><stop offset="1" stopColor="#725f39" stopOpacity=".24"/></radialGradient>
          <pattern id={id('waves')} width="35" height="25" patternUnits="userSpaceOnUse"><path d="M2 9Q7 6 12 9T22 9M21 20Q26 17 31 20" fill="none" stroke="#eff2d9" strokeOpacity=".18" strokeWidth=".6"/></pattern>
          <pattern id={id('paper')} width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".5" fill="#675630" opacity=".12"/><circle cx="7" cy="8" r=".4" fill="#fff2c9" opacity=".22"/></pattern>
          <pattern id={id('hatch')} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><path d="M0 0V4" stroke="#766e4a" strokeWidth=".7" opacity=".3"/></pattern>
        </defs>
        <rect width={width} height={height} fill={`url(#${id('sea')})`}/>
        <rect width={width} height={height} fill={`url(#${id('waves')})`}/>
        <g transform={`translate(${-view.x*width/view.width} ${-view.y*height/view.height}) scale(${width/view.width})`}>{coastlines}</g>
        <g pointerEvents="none">
          {terrain.map((item, i) => {
            const [x, y] = toScreen(item.lon, item.lat);
            if (x < -25 || x > width + 25 || y < -25 || y > height + 25) return null;
            const scale = item.scale * Math.min(1.4, Math.sqrt(width / view.width / 4));
            return <g key={i} transform={`translate(${x} ${y}) scale(${scale})`} opacity={item.kind === 3 ? '.36' : '.49'}>
              {item.kind === 3 ? <><ellipse cy="4" rx="13" ry="4" fill="#829367" opacity=".5"/><path d="M-8 4V-9M0 6V-6M8 3V-11" stroke="#687954" strokeWidth=".8"/><path d="M-13-1L-8-12-3-1ZM-5 1L0-9 5 1ZM3-3L8-14 13-3Z" fill="#84966c" stroke="#617c53" strokeWidth=".6"/></> : <><path d="M-19 8L-6-13 1-2 8-20 25 8" fill="#c2b081" stroke="#8d835d" strokeWidth=".8"/><path d="M-6-13L-1 8H-13ZM8-20L17 8H2Z" fill={`url(#${id('hatch')})`}/><path d="M-10-7L-6-13-1-6M3-10L8-20 14-9" fill="none" stroke="#f1e6bd" strokeWidth="1.2"/></>}
            </g>;
          })}
          <rect width={width} height={height} fill={`url(#${id('paper')})`}/>
          <rect width={width} height={height} fill={`url(#${id('vignette')})`}/>
        </g>
        <g className="map-geographic-labels" pointerEvents="none">
          {(view.width < 130 ? [[28.9, 40.92, 'Мраморное море', -9], [29.05, 39.62, 'УЛУ-ДАГ', -14], [30.5, 40.5, 'ВИФИНИЯ', -7]] : [[15,36,'Средиземное море',-8], [33,43,'Чёрное море',0], [3,42,'ЕВРОПА',0], [7,29,'МАГРИБ',0], [33,38.5,'АНАТОЛИЯ',0]]).map(([lon, lat, label, angle]) => {
            const [x, y] = toScreen(Number(lon), Number(lat));
            return <text key={label} x={x} y={y} transform={`rotate(${angle} ${x} ${y})`} textAnchor="middle" className={String(label).includes('море') ? 'sea-name' : 'region-name'}>{label}</text>;
          })}
        </g>
        {layers && <g fill="none" strokeLinecap="round" pointerEvents="none">{catalog.roads.map(([from, to]) => {
          const p = catalog.places.find(p => p.id === from)!, q = catalog.places.find(p => p.id === to)!;
          const [x, y] = toScreen(p.lon, p.lat), [tx, ty] = toScreen(q.lon, q.lat);
          const route = `M${x} ${y}Q${(x + tx) / 2 + 7} ${(y + ty) / 2 - 5} ${tx} ${ty}`;
          const highlighted = from === selected || to === selected;
          return <g key={from + to} opacity={highlighted ? '.85' : '.42'}><path d={route} stroke="#f6eccb" strokeWidth={highlighted ? 4 : 2.5}/><path d={route} stroke={highlighted ? '#a47c3e' : '#96865b'} strokeWidth={highlighted ? 1.6 : 1} strokeDasharray={highlighted ? undefined : '3 4'}/></g>;
        })}</g>}
        {Object.values(state.armies).filter(a => a.order).map(a => {
          const p = catalog.places.find(p => p.id === a.location)!, q = catalog.places.find(p => p.id === a.order!.target)!;
          const [x, y] = toScreen(p.lon, p.lat), [tx, ty] = toScreen(q.lon, q.lat);
          return <path key={a.id} d={`M${x} ${y}Q${(x + tx) / 2 - 9} ${(y + ty) / 2 - 15} ${tx} ${ty}`} stroke="#963f2d" strokeWidth="2.5" strokeDasharray="6 4" fill="none" pointerEvents="none"/>;
        })}
        {!detailed && <g className="overview-settlements">{visible.map(p=>{const [x,y]=toScreen(p.lon,p.lat);const active=selected===p.id;return <g key={p.id} data-overview-place={p.id} transform={`translate(${x} ${y})`}><path d="M-5 3V-6H-3V-3H0V-6H3V-3H5V3Z" fill={colorFor(state.provinces[p.id].controller)} stroke="#f5e7bf" strokeWidth=".8"/>{(active || p.kind==='city' && view.width<350)&&<text y="14" textAnchor="middle" fontSize="9" fill="#3f4934" paintOrder="stroke" stroke="#eee0b5" strokeWidth="2">{p.name}</text>}</g>})}<rect x="0" y="0" width={width} height={height-90} fill="transparent" role="button" aria-label="Приблизить область карты" tabIndex={0} onClick={e=>{if(moved.current)return;const bounds=e.currentTarget.getBoundingClientRect();const x=view.x+(e.clientX-bounds.left)/width*view.width;const y=view.y+(e.clientY-bounds.top)/height*view.height;setPan([x-baseCenter[0],y-baseCenter[1]]);setZoom(z=>Math.min(80,z*3))}} onKeyDown={e=>{if(e.key==='Enter')setZoom(z=>Math.min(80,z*3))}}/></g>}
        <g pointerEvents="none" className="map-leader-lines">{pins.map(p => Math.hypot(p.position[0] - p.anchor[0], p.position[1] - p.anchor[1]) > 10 && <g key={p.id}><path d={`M${p.anchor.join(' ')}L${p.position.join(' ')}`} stroke="#6c7153" opacity=".6" strokeWidth=".8"/><circle cx={p.anchor[0]} cy={p.anchor[1]} r="2" fill="#856e43" stroke="#ecdfb8" strokeWidth=".7"/></g>)}</g>
        {pins.map(p => {
          const place = state.provinces[p.id], color = colorFor(place.controller);
          const active = p.id === selected, besieged = !!state.sieges[p.id];
          const stationed = Object.values(state.armies).filter(a => a.location === p.id && troopCount(a.troops) > 0);
          return <g key={p.id} data-place={p.id} data-testid={`place-${p.id}`} className={`illustrated-place ${active ? 'is-selected' : ''}`} role="button" tabIndex={0} aria-label={`Выбрать ${p.name}`} transform={`translate(${p.position.join(' ')})`} onClick={() => choose(p.id)} onKeyDown={e => {if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); select(p.id)}}}>
            <rect className="place-hit-target" x="-46" y="-36" width="92" height="68" rx="10" fill="transparent"/>
            {active && <ellipse cy="2" rx="26" ry="14" fill="#eee0a3" stroke="#aa7836" strokeWidth="1.5"/>}
            {besieged && <ellipse cy="2" rx="29" ry="17" fill="none" stroke="#9e4834" strokeWidth="1.6" strokeDasharray="4 3"/>}
            <g pointerEvents="none">{place.fortress_level>0 ? <Fortress large={p.id === state.capital || p.kind==='city'} port={p.port}/> : <Village/>}</g>
            <path d="M-3-27V-45" stroke="#665437" strokeWidth="1.1" pointerEvents="none"/>
            <path d="M-3-45Q3-48 11-44L10-35Q3-39-3-36Z" fill={color} stroke="#fff0c6" strokeWidth=".7" pointerEvents="none"/>
            {place.controller === 'ottoman' && <path d="M3-43A3 3 0 1 0 6-38A2.6 2.6 0 1 1 3-43" fill="#f8edc9" pointerEvents="none"/>}
            {stationed.map((army, i) => <g key={army.id} transform={`translate(${19 + i * 25} -18)`} pointerEvents="none"><path d="M-2-12V6" stroke="#6b5436"/><path d="M-2-12H20L16 0H-2Z" fill={colorFor(army.faction)} stroke="#f0e0b5" strokeWidth=".7"/><text x="8" y="-4" textAnchor="middle" fontSize="8" fill="#fff4d5">{troopCount(army.troops)}</text></g>)}
            <rect x={-Math.max(35, p.name.length * 3.8)} y="14" width={Math.max(70, p.name.length * 7.6)} height="20" rx="3" fill={active ? '#395a43' : '#f2e5bf'} fillOpacity={active ? '.97' : '.92'} stroke={active ? '#263f32' : '#c3ab77'} strokeWidth=".6" pointerEvents="none"/>
            <text className="place-name" y="28" textAnchor="middle" fill={active ? '#fff1c8' : '#4f4933'} pointerEvents="none">{p.id === state.capital ? '★ ' : ''}{p.name}</text>
          </g>;
        })}
        <Compass x={43} y={width < 500 ? 90 : height - 53}/>
        <path d={`M8 35V8H35M${width - 35} 8H${width - 8}V35M8 ${height - 35}V${height - 8}H35M${width - 35} ${height - 8}H${width - 8}V${height - 35}`} fill="none" stroke="#9f8551" strokeWidth="1" opacity=".7" pointerEvents="none"/>
      </svg>
      {!geography && <div className="map-load-state" role="status">{loadError ? <><p>Не удалось загрузить карту</p><button onClick={() => setAttempt(n => n + 1)}>Повторить</button></> : 'Разворачиваем карту…'}</div>}
      <div className="illustrated-map-tools">
        <button aria-label="Приблизить карту" onClick={() => setZoom(z => Math.min(world ? 80 : 6, z * 1.3))}>+</button><button aria-label="Отдалить карту" onClick={() => setZoom(z => Math.max(.8, z / 1.3))}>−</button>
        <button aria-label="Показать выбранную крепость" onClick={focusSelected}>Выбранный город</button>
        {world && <button aria-label="Показать всю карту" onClick={()=>reset(true)}>Вся карта</button>}
        <button aria-label="Вернуть карту" onClick={() => reset()}>Обзор</button>
        <button aria-label={fullScreen ? 'Свернуть карту' : 'Развернуть карту'} onClick={() => setFullScreen(v => !v)}>{fullScreen ? 'Свернуть' : 'Во весь экран'}</button>
      </div>
      {<div className="map-corner-caption"><span>Кампания {state.calendar.year} года</span><small>{detailed ? 'Двигайте карту · увеличивайте двумя пальцами' : 'Нажмите на область для приближения'}</small></div>}
    </div>
    <footer className="illustrated-map-legend"><span><i style={{background: factionColor.ottoman}}/>Османы</span><span><i style={{background: factionColor.byzantine}}/>Византия</span><span className="siege-key">◌ Осада</span>{<button aria-pressed={layers} onClick={() => setLayers(v => !v)}>{layers ? 'Скрыть дороги' : 'Показать дороги'}</button>}</footer>

  </section>;
}
