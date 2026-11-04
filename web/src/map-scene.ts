import {project} from './atlas-geometry';
import type {Geography,Point,Viewport} from './atlas-geometry';
export type Quality='low'|'medium'|'high';
export const profiles={low:{dpr:1,tolerance:.03,decor:0},medium:{dpr:1.5,tolerance:.01,decor:1},high:{dpr:2,tolerance:0,decor:2}};
export const factionColor=(id:string)=>({ottoman:'#315c46',byzantine:'#914b43',germiyan:'#9b814d'}[id]||`hsl(${[...id].reduce((v,c)=>v+c.charCodeAt(0)*17,0)%360} 28% 43%)`);
/** Ground footprints shrink near a real shore; geographic anchors never move. */
export function coastClearances(geo:Geography,points:Point[]){
 const edges=Object.values({land:geo.land,lakes:geo.lakes}).flatMap(polys=>polys.flatMap(poly=>poly.flatMap(ring=>{const r=ring.map(p=>project(...p));return r.slice(1).map((b,i)=>[r[i],b] as [Point,Point])})));
 return points.map(p=>{let distance=Infinity;for(const [a,b] of edges){const dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy,t=length?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)):0;distance=Math.min(distance,Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))}return distance});
}
export const groundScale=(clearance:number,unitsPerPixel:number)=>Math.min(1,clearance/(28*unitsPerPixel)*.9);
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
export function paths(geo:Geography,quality:Quality){return Object.fromEntries(['land','lakes'].map(key=>[key,geo[key as 'land'|'lakes'].map(poly=>{const path=new Path2D();for(const [index,ring] of poly.entries()){const points=simplifyRing(ring.map(([lon,lat])=>project(lon,lat)),index?0:profiles[quality].tolerance,(geo.settlements||[]).map(p=>project(...p)),(geo.precision_regions||[]).map(([w,s,e,n])=>[...project(w,n),...project(e,s)]));points.forEach(([x,y],i)=>{if(i)path.lineTo(x,y);else path.moveTo(x,y)});path.closePath()}return path})])) as Record<'land'|'lakes',Path2D[]>}
export function at(point:Point,v:Viewport,w:number,h:number):Point{return [(point[0]-v.x)/v.width*w,(point[1]-v.y)/v.height*h]}
export function zoomAt(v:Viewport,factor:number,p:Point,w:number,h:number):Viewport{const next=Math.max(.6,Math.min(7600,v.width*factor)),height=next*h/w;return {x:v.x+p[0]/w*(v.width-next),y:v.y+p[1]/h*(v.height-height),width:next,height}}
export type Hit={id:string;kind:'place'|'army';x:number;y:number};
export function hitIndex(items:Hit[]){const grid=new Map<string,Hit[]>();for(const p of items){const k=`${Math.floor(p.x/48)},${Math.floor(p.y/48)}`;grid.set(k,[...(grid.get(k)||[]),p])}return (x:number,y:number)=>{const hits:Hit[]=[];for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)hits.push(...(grid.get(`${Math.floor(x/48)+dx},${Math.floor(y/48)+dy}`)||[]));return hits.filter(p=>Math.abs(p.x-x)<=24&&Math.abs(p.y-y)<=24).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0]}}
/** Isometric symbols are painted once into reusable transparent sprite canvases. */
export function settlement(fort:boolean,port:boolean,quality:Quality){const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;const c=canvas.getContext('2d')!;c.scale(2,2);c.translate(32,40);c.lineJoin='round';c.lineWidth=.8;c.strokeStyle='#625139';
 const poly=(p:Point[],fill:string)=>{c.beginPath();p.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();c.stroke()};
 c.fillStyle='#7d715438';c.beginPath();c.ellipse(0,11,25,6,0,0,7);c.fill();
 if(fort){poly([[-22,-4],[0,5],[23,-4],[1,-13]],'#f0dcb0');poly([[-22,-4],[0,5],[0,18],[-22,9]],'#cfb580');poly([[0,5],[23,-4],[23,9],[0,18]],'#a78858');for(const [x,y] of [[-18,-6],[15,-11],[0,-17]]){poly([[x-5,y-16],[x+3,y-12],[x+3,y+8],[x-5,y+4]],'#e0ca96');poly([[x+3,y-12],[x+9,y-16],[x+9,y+4],[x+3,y+8]],'#a68b5b');poly([[x-6,y-16],[x+1,y-25],[x+10,y-16],[x+3,y-12]],'#6f7770')}c.fillStyle='#544c37';c.fillRect(-4,6,7,10)}else{for(const [x,y] of [[-14,0],[9,-5]]){poly([[x-9,y],[x+1,y+4],[x+11,y],[x+11,y+12],[x,y+16],[x-9,y+11]],'#dfc593');poly([[x-11,y],[x-1,y-12],[x+12,y],[x+1,y+5]],'#956f50')}}
 if(quality==='high'){c.strokeStyle='#7c694743';c.lineWidth=.5;for(let y=-8;y<12;y+=4){c.beginPath();c.moveTo(-19,y);c.lineTo(-2,y+7);c.stroke()}}
 if(port){c.strokeStyle='#356b72';c.beginPath();c.moveTo(-25,-3);c.lineTo(-25,15);c.moveTo(-31,10);c.quadraticCurveTo(-25,22,-19,10);c.stroke()}return canvas;
}
