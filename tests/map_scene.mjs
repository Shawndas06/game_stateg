import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from '../web/node_modules/typescript/lib/typescript.js';
import {Worker} from 'node:worker_threads';
const compile=async path=>ts.transpileModule(await readFile(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const data=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const geometry=data(await compile('../web/src/atlas-geometry.ts'));
const scene=await import(data((await compile('../web/src/map-scene.ts')).replace(/(['"])\.\/atlas-geometry\1/,JSON.stringify(geometry))));
const {hitIndex,zoomAt,at,simplifyRing,paths,profiles}=scene;
let seed=19;const random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/2**32);
const points=Array.from({length:350},(_,i)=>({id:String(i),kind:i%3?'place':'army',x:random()*844,y:random()*390}));
const lookup=hitIndex(points);
for(let i=0;i<500;i++){const x=random()*844,y=random()*390;const expected=points.filter(p=>Math.abs(p.x-x)<=24&&Math.abs(p.y-y)<=24).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];assert.equal(lookup(x,y)?.id,expected?.id)}
const view={x:350,y:100,width:80,height:40},anchor=[271,139],world=[view.x+anchor[0]/844*view.width,view.y+anchor[1]/422*view.height];
for(const factor of [.01,.5,2,10000]){const next=zoomAt(view,factor,anchor,844,422),screen=at(world,next,844,422);assert(Math.abs(screen[0]-anchor[0])<1e-8&&Math.abs(screen[1]-anchor[1])<1e-8);assert(next.width>=.6&&next.width<=7600)}
const ring=[[0,0],[1,.001],[2,0],[3,0],[3,3],[0,3],[0,0]];
for(const q of ['low','medium','high']){const result=simplifyRing(ring,profiles[q].tolerance);assert.deepEqual(result[0],result.at(-1));assert(result.length>=4);assert(result.includes(ring[4]));assert(result.includes(ring[5]))}
class Path{points=[];moveTo(x,y){this.points.push([x,y])}lineTo(x,y){this.points.push([x,y])}closePath(){}}
globalThis.Path2D=Path;
const geo=JSON.parse(await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url),'utf8'));const counts={};
for(const q of ['low','medium','high'])counts[q]=paths(geo,q).land.reduce((n,p)=>n+p.points.length,0);
assert(counts.low<=counts.medium&&counts.medium<=counts.high);
console.log('PASS map scene: 500 indexed picks, anchored/clamped zoom, closed rings, LOD vertex counts',counts);

const prefs=await import(data(await compile('../web/src/preferences.ts')));
globalThis.localStorage={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}};
prefs.remember('diagnostics','off');assert.equal(prefs.read('diagnostics'),'off');
prefs.remember('map-quality','low');assert.equal(prefs.read('map-quality'),'low');
globalThis.localStorage={getItem(){return 'on'},setItem(){throw Error('quota')}};
prefs.remember('voice','off');assert.equal(prefs.read('voice'),'off');
console.log('PASS optional preferences: blocked storage and quota failures retain current-session choices');
for(const quality of Object.keys(profiles)){
 for(const [size,kind] of [['small','fortress'],['medium','city'],['large','city']]){
  assert.equal(scene.settlementSize({map_size:size,kind},1),size,quality);
  assert.equal(scene.settlementSize({map_size:size,kind},0),size);
 }
}
assert.equal(scene.settlementSize({kind:'fortress'},1),'small');
assert.equal(scene.settlementSize({kind:'city'},1),'medium');
assert.equal(scene.settlementSize({kind:'village',map_size:'small'},2),'medium');
assert.equal(scene.settlementSize({kind:'village',map_size:'small'},3),'large');
console.log('PASS settlement display scale: catalogue/fallback/upgrades, no capital or garrison inputs, quality-independent');
assert.equal(typeof scene.landscapeMarks,'function','Landscape must exist at low quality, not only six decorative peaks');
const fixture={land:[[[[0,0],[2,0],[2,2],[0,2],[0,0]]]],lakes:[[[[.7,.7],[1.3,.7],[1.3,1.3],[.7,1.3],[.7,.7]]]]};
const marks=scene.landscapeMarks(fixture,fixture.land,[[.4,.4,.4,.4]],[[.3,.3]]);
assert(marks.some(m=>m.kind==='mountain')&&marks.some(m=>m.kind==='forest'));
const geoTools=await import(geometry);
for(const m of marks){assert(geoTools.onLand(m.lon,m.lat,fixture));assert(Math.hypot(m.lon-.3,m.lat-.3)>.1)}
assert.deepEqual(marks,scene.landscapeMarks(fixture,fixture.land,[[.4,.4,.4,.4]],[[.3,.3]]));
console.log('PASS landscape: deterministic mountain/forest marks avoid sea, lakes and town anchors');
assert.equal(typeof scene.fitGeography,'function','World view must fit available geography rather than a mostly empty ocean');
assert.equal(typeof scene.labelFits,'function','Overview names must not overlap');
const nameBox={x:10,y:20,width:100,height:22};
assert(scene.labelFits(nameBox,[]));
assert(!scene.labelFits({x:90,y:25,width:80,height:22},[nameBox]));
assert(scene.labelFits({x:120,y:20,width:80,height:22},[nameBox]));
for(const [w,h] of [[390,844],[844,390],[1900,1010]]){
 const fit=scene.fitGeography(fixture,w,h);
 assert(Math.abs(fit.x+fit.width/2-220)<1e-6&&Math.abs(fit.y+fit.height/2-1127)<1e-6);
 for(const point of [[200,1104],[240,1150]]){const [x,y]=at(point,fit,w,h);assert(x>=0&&x<=w&&y>=0&&y<=h)}
 assert(Math.max(40/fit.width,46/fit.height)>.9);
}
// Detect a cache-breaking sampler change before it can freeze the first map frame.
const landscape=JSON.parse(await readFile(new URL('../web/src/map-landscape.json',import.meta.url),'utf8'));
const worker=new Worker(`const {parentPort,workerData:d}=require('node:worker_threads');import(d.module).then(s=>{const start=performance.now();const marks=s.landscapeMarks(d.geo,d.landscape.mountains,d.landscape.woods,[]);parentPort.postMessage({count:marks.length,ms:performance.now()-start})}).catch(e=>{throw e})`,{eval:true,workerData:{module:data((await compile('../web/src/map-scene.ts')).replace(/(['"])\.\/atlas-geometry\1/,JSON.stringify(geometry))),geo,landscape}});
let deadline;
try{
 const result=await Promise.race([new Promise((resolve,reject)=>{worker.once('message',resolve);worker.once('error',reject)}),new Promise((_,reject)=>{deadline=setTimeout(()=>reject(Error('Landscape preparation exceeded 8s: check scanline cache and per-point geometry work')),8000)})]);
 assert(result.count>100);console.log('PASS full landscape preparation:',result);
}finally{clearTimeout(deadline);await worker.terminate()}
