import {project,landSampler} from './atlas-geometry';
import type {Geography,Point,Viewport} from './atlas-geometry';
export type Quality='low'|'medium'|'high';
export const profiles={low:{dpr:1,tolerance:.03,decor:0},medium:{dpr:1.5,tolerance:.01,decor:1},high:{dpr:2,tolerance:0,decor:2}};
export const factionColor=(id:string)=>({ottoman:'#315c46',byzantine:'#914b43',germiyan:'#9b814d'}[id]||`hsl(${[...id].reduce((v,c)=>v+c.charCodeAt(0)*17,0)%360} 28% 43%)`);
/** Ground footprints shrink near a real shore; geographic anchors never move. */
export function coastClearances(geo:Geography,points:Point[]){
 const cached=geo.coast_cache;
 if(geo.geometry_fingerprint&&cached?.geometry===geo.geometry_fingerprint&&Array.isArray(cached.values)&&cached.values.length===points.length&&cached.values.every(v=>Number.isFinite(v)&&v>=0)&&geo.settlements?.length===points.length&&geo.settlements.every((p,i)=>{const xy=project(...p);return xy[0]===points[i][0]&&xy[1]===points[i][1]}))return cached.values.slice();
 const edges=Object.values({land:geo.land,lakes:geo.lakes}).flatMap(polys=>polys.flatMap(poly=>poly.flatMap(ring=>{const r=ring.map(p=>project(...p));return r.slice(1).map((b,i)=>[r[i],b] as [Point,Point])})));
 return points.map(p=>{let distance=Infinity;for(const [a,b] of edges){const dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy,t=length?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)):0;distance=Math.min(distance,Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))}return distance});
}
export const groundScale=(clearance:number,unitsPerPixel:number)=>Math.min(1,clearance/(28*unitsPerPixel)*.9);
export const reliefRegions=(mountains:Geography['land'],hills:number[][]):Geography['land']=>[...mountains,...hills.map(([lon,lat,rx,ry])=>[Array.from({length:13},(_,i)=>[lon+Math.cos(i*Math.PI/6)*rx,lat+Math.sin(i*Math.PI/6)*ry] as Point)])];
const extent=(geo:Geography)=>geo.land.reduce((b,p)=>p[0].reduce(([w,s,e,n],[x,y])=>[Math.min(w,x),Math.min(s,y),Math.max(e,x),Math.max(n,y)],b),[Infinity,Infinity,-Infinity,-Infinity]);
export function fitGeography(geo:Geography,w:number,h:number):Viewport{
 const [west,south,east,north]=extent(geo),a=project(west,north),b=project(east,south),width=Math.max(b[0]-a[0],(b[1]-a[1])*w/h)*1.08,height=width*h/w;
 return {x:(a[0]+b[0]-width)/2,y:(a[1]+b[1]-height)/2,width,height};
}
/** A bounded, stable lattice; only preparation samples geography, never a drag frame. */
export function landscapeMarks(geo:Geography,mountains:Geography['land'],woods:number[][],towns:Point[]){
 const land=landSampler(geo),mountain=landSampler({land:mountains,lakes:[]});
 const marks:{lon:number;lat:number;kind:'mountain'|'forest'}[]=[];
 const bounds=extent(geo);
 for(let row=0;row<Math.ceil((bounds[3]-bounds[1])/.24);row++)for(let col=0;col<Math.ceil((bounds[2]-bounds[0])/.3);col++){
  const lon=bounds[0]+col*.3+(row%2)*.15+Math.sin(row*17+col*13)*.03,lat=bounds[1]+row*.24;
  if(!land(lon,lat)||towns.some(([x,y])=>Math.hypot(x-lon,y-lat)<.14))continue;
  const wooded=woods.some(([x,y,rx,ry])=>((x-lon)/rx)**2+((y-lat)/ry)**2<1);
  const rock=mountain(lon,lat);if(wooded||rock)marks.push({lon,lat,kind:rock&&(!wooded||(row+col)%3===0)?'mountain':'forest'});
 }
 return marks;
}
/** Bounded Douglas-Peucker simplification; rings and holes remain separate. */
export function simplifyRing(points:Point[],tolerance:number,protectedPoints:Point[]=[],regions:number[][]=[]):Point[]{
 if(!tolerance||points.length<5)return points;
 const keep=new Set([0,points.length-1]);
 points.forEach((p,i)=>{if(regions.some(([left,top,right,bottom])=>p[0]>=left&&p[0]<=right&&p[1]>=top&&p[1]<=bottom)||protectedPoints.some(a=>Math.abs(a[0]-p[0])<.15&&Math.abs(a[1]-p[1])<.15))keep.add(i)});
 const fixed=[...keep].sort((a,b)=>a-b),stack:[number,number][]=fixed.slice(1).map((end,i)=>[fixed[i],end]);
 while(stack.length){const [start,end]=stack.pop()!,a=points[start],b=points[end],dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy;let far=-1,max=tolerance*tolerance;
  for(let i=start+1;i<end;i++){const p=points[i],t=length?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)):0,d=(p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2;if(d>max){max=d;far=i}}
  if(far>=0){keep.add(far);stack.push([start,far],[far,end])}
 }
 const result=[...keep].sort((a,b)=>a-b).map(i=>points[i]);return result.length>=4?result:points;
}
export function paths(geo:Geography,quality:Quality){
 const protectedPoints=(geo.settlements||[]).map(p=>project(...p)),regions=(geo.precision_regions||[]).map(([w,s,e,n])=>[...project(w,n),...project(e,s)]);
 return Object.fromEntries(['land','lakes'].map(key=>[key,geo[key as 'land'|'lakes'].map(poly=>{const path=new Path2D();for(const [index,ring] of poly.entries()){const points=simplifyRing(ring.map(([lon,lat])=>project(lon,lat)),index?0:profiles[quality].tolerance,protectedPoints,regions);points.forEach(([x,y],i)=>{if(i)path.lineTo(x,y);else path.moveTo(x,y)});path.closePath()}return path})])) as Record<'land'|'lakes',Path2D[]>}
export function at(point:Point,v:Viewport,w:number,h:number):Point{return [(point[0]-v.x)/v.width*w,(point[1]-v.y)/v.height*h]}
export function zoomAt(v:Viewport,factor:number,p:Point,w:number,h:number):Viewport{const next=Math.max(.6,Math.min(7600,v.width*factor)),height=next*h/w;return {x:v.x+p[0]/w*(v.width-next),y:v.y+p[1]/h*(v.height-height),width:next,height}}
export type Hit={id:string;kind:'place'|'army';x:number;y:number};
export type LabelBox={x:number;y:number;width:number;height:number};
export const labelFits=(b:LabelBox,others:LabelBox[])=>!others.some(a=>a.x<b.x+b.width+4&&a.x+a.width+4>b.x&&a.y<b.y+b.height+4&&a.y+a.height+4>b.y);
export function hitIndex(items:Hit[]){const grid=new Map<string,Hit[]>();for(const p of items){const k=`${Math.floor(p.x/48)},${Math.floor(p.y/48)}`;grid.set(k,[...(grid.get(k)||[]),p])}return (x:number,y:number)=>{const hits:Hit[]=[];for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)hits.push(...(grid.get(`${Math.floor(x/48)+dx},${Math.floor(y/48)+dy}`)||[]));return hits.filter(p=>Math.abs(p.x-x)<=24&&Math.abs(p.y-y)<=24).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0]}}
export type SettlementSize='small'|'medium'|'large';
export function settlementSize(place:{kind:string;map_size?:SettlementSize},level=0):SettlementSize{return level>=3?'large':level>=2&&place.map_size!=='large'?'medium':place.map_size||(place.kind==='city'?'medium':'small')}
export function settlementLabel(place:{kind:string;map_size?:SettlementSize},level:number){const size=settlementSize(place,level);return level>0?({small:'Малая крепость',medium:'Укреплённый город',large:'Крупный укреплённый город'}[size]):({small:'Малое поселение',medium:'Город',large:'Крупный город'}[size])}
/** One cached sprite per type/scale/port. Every ground footprint fits the same coastal guard. */
export function settlement(fort:boolean,port:boolean,quality:Quality,size:SettlementSize='medium'){
 const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;const c=canvas.getContext('2d')!;
 c.scale(2,2);c.translate(32,40);c.lineJoin='round';c.lineWidth=.8;c.strokeStyle='#625139';
 const poly=(p:Point[],fill:string)=>{c.beginPath();p.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();c.stroke()};
 const house=(x:number,y:number)=>{poly([[x-6,y],[x+1,y+3],[x+8,y],[x+8,y+8],[x,y+11],[x-6,y+7]],'#dfc593');poly([[x-8,y],[x,y-9],[x+9,y],[x+1,y+4]],'#956f50')};
 const tower=(x:number,y:number)=>{poly([[x-4,y-13],[x+2,y-10],[x+2,y+7],[x-4,y+4]],'#e0ca96');poly([[x+2,y-10],[x+7,y-13],[x+7,y+4],[x+2,y+7]],'#a68b5b');poly([[x-5,y-13],[x,y-21],[x+8,y-13],[x+2,y-10]],'#6f7770')};
 const r={small:14,medium:20,large:24}[size];c.fillStyle='#7d715438';c.beginPath();c.ellipse(0,11,r,5,0,0,7);c.fill();
 if(fort){
  poly([[-r,-3],[0,5],[r,-3],[0,-11]],'#f0dcb0');poly([[-r,-3],[0,5],[0,17],[-r,9]],'#cfb580');poly([[0,5],[r,-3],[r,9],[0,17]],'#a78858');
  const towers:Point[]=size==='small'?[[0,-5]]:size==='medium'?[[-13,-3],[10,-7]]:[[-18,-3],[14,-7],[0,-16]];
  for(const [x,y] of towers)tower(x,y);
  if(size==='large'){house(-7,3);house(7,0)}c.fillStyle='#544c37';c.fillRect(-3,8,6,8);
 }else{for(const [x,y] of (size==='small'?[[-7,0],[7,-4]]:size==='medium'?[[-12,0],[0,-9],[12,0]]:[[-16,0],[-7,-11],[7,-12],[16,-1],[0,5]]) as Point[])house(x,y)}
 if(quality==='high'&&fort){c.strokeStyle='#7c694743';c.lineWidth=.5;for(let y=5;y<14;y+=4){c.beginPath();c.moveTo(-r+3,y);c.lineTo(-2,y+6);c.stroke()}}
 if(port){c.strokeStyle='#356b72';c.beginPath();c.moveTo(-25,-3);c.lineTo(-25,15);c.moveTo(-29,10);c.quadraticCurveTo(-25,20,-19,10);c.stroke()}return canvas;
}
