import source from './map-landscape.json';
import {project} from './atlas-geometry';
import type {Geography,Point,Viewport} from './atlas-geometry';
import {landscapeMarks,reliefRegions} from './map-scene';
import type {Quality} from './map-scene';
type LandscapeData={mountains:Geography['land'];rivers:Point[][];hills:number[][];woods:number[][];cache?:{geometry:string;settlements:string;marks:[number,number,'mountain'|'forest'][]}};
const data=source as LandscapeData;

export function prepareLandscape(geo:Geography,towns:Point[]){
 const mountains=new Path2D(),rivers=new Path2D(),ridges=new Path2D();
 const regions=reliefRegions(data.mountains,data.hills),cache=data.cache;
 const marks=cache&&cache.geometry===geo.geometry_fingerprint&&cache.settlements===JSON.stringify(towns)?cache.marks.map(([lon,lat,kind])=>({lon,lat,kind})):landscapeMarks(geo,regions,data.woods,towns);
 for(const polygon of data.mountains)for(const ring of polygon){ring.forEach(([lon,lat],i)=>{const p=project(lon,lat);if(i)mountains.lineTo(...p);else mountains.moveTo(...p)});mountains.closePath()}
 for(const [lon,lat,rx,ry] of data.hills){const [x,y]=project(lon,lat);for(let i=0;i<7;i++){const xx=x+(i/3-1)*rx*20,yy=y+Math.sin(i*1.8)*ry*12;if(i)ridges.lineTo(xx,yy);else ridges.moveTo(xx,yy)}}
 for(const line of data.rivers)line.forEach(([lon,lat],i)=>{const p=project(lon,lat);if(i)rivers.lineTo(...p);else rivers.moveTo(...p)});
 return {mountains,rivers,ridges,marks:marks.map(m=>({...m,point:project(m.lon,m.lat)}))};
}

/** Draw only when the existing static terrain buffer is rebuilt. Caller clips to land. */
export function paintLandscape(c:CanvasRenderingContext2D,relief:ReturnType<typeof prepareLandscape>,view:Viewport,unit:number,quality:Quality){
 c.fillStyle='#b3a47c70';c.fill(relief.mountains,'evenodd');c.strokeStyle='#a7986b88';c.lineWidth=Math.min(.7,unit*2);c.stroke(relief.ridges);
 c.strokeStyle='#729fa5';c.lineWidth=Math.min(1.5,unit*1.4);c.lineJoin='round';c.stroke(relief.rivers);
 if(unit>.8)return;
 const scale=Math.max(.1,Math.min(1,unit*7));
 for(const [i,m] of relief.marks.entries()){
  const [x,y]=m.point;if(x<view.x-3||x>view.x+view.width+3||y<view.y-3||y>view.y+view.height+3||quality==='low'&&i%2)continue;
  c.save();c.translate(x,y);c.scale(scale,scale);c.lineWidth=.12;
  if(m.kind==='forest'){
   c.fillStyle='#70845a26';c.beginPath();c.ellipse(.3,1.2,2.4,.8,0,0,7);c.fill();
   c.fillStyle='#647c51';c.strokeStyle='#4c643e';
   for(const [x,y] of [[-.9,.4],[.7,0],[1.6,.8]]){c.beginPath();c.moveTo(x-.8,y+1);c.lineTo(x,y-1.6);c.lineTo(x+.8,y+1);c.closePath();c.fill();c.stroke();c.beginPath();c.moveTo(x,y+1);c.lineTo(x,y+1.6);c.stroke()}
   if(quality==='high'){c.fillStyle='#829364';c.beginPath();c.arc(.8,.4,.6,0,7);c.fill()}
  }else{
   c.fillStyle='#b0a17b';c.strokeStyle='#8f8367';c.beginPath();c.moveTo(-1.6,1);c.lineTo(0,-1.7);c.lineTo(1.7,1);c.closePath();c.fill();c.stroke();c.fillStyle='#e8dfbe';c.beginPath();c.moveTo(-.5,-.8);c.lineTo(0,-1.7);c.lineTo(.6,-.75);c.closePath();c.fill();
  }
  c.restore();
 }
}
