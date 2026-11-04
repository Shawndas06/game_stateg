import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from '../web/node_modules/typescript/lib/typescript.js';
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
for(const factor of [.01,.5,2,10000]){const next=zoomAt(view,factor,anchor,844,422),screen=at(world,next,844,422);assert(Math.abs(screen[0]-anchor[0])<1e-8&&Math.abs(screen[1]-anchor[1])<1e-8);assert(next.width>=12&&next.width<=7600)}
const ring=[[0,0],[1,.001],[2,0],[3,0],[3,3],[0,3],[0,0]];
for(const q of ['low','medium','high']){const result=simplifyRing(ring,profiles[q].tolerance);assert.deepEqual(result[0],result.at(-1));assert(result.length>=4);assert(result.includes(ring[4]));assert(result.includes(ring[5]))}
class Path{points=[];moveTo(x,y){this.points.push([x,y])}lineTo(x,y){this.points.push([x,y])}closePath(){}}
globalThis.Path2D=Path;
const geo=JSON.parse(await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url),'utf8'));const counts={};
for(const q of ['low','medium','high'])counts[q]=paths(geo,q).land.reduce((n,p)=>n+p.points.length,0);
assert(counts.low<=counts.medium&&counts.medium<=counts.high);
console.log('PASS map scene: 500 indexed picks, anchored/clamped zoom, closed rings, LOD vertex counts',counts);
