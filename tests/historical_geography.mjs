import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import ts from '../web/node_modules/typescript/lib/typescript.js';
const compile=async file=>ts.transpileModule(await readFile(new URL(file,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const data=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const geometry=data(await compile('../web/src/atlas-geometry.ts'));
const {onLand,project,layoutPlaces}=await import(geometry);
const {paths,coastClearances,groundScale}=await import(data((await compile('../web/src/map-scene.ts')).replace(/(['"])\.\/atlas-geometry\1/,JSON.stringify(geometry))));
const places=JSON.parse(execFileSync('python3',['-c','import json;from campaign.content import PLACES;print(json.dumps([dict(id=p[0],lon=p[2],lat=p[3]) for p in PLACES]))'],{cwd:new URL('..',import.meta.url),encoding:'utf8'}));
const geo=JSON.parse(await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url),'utf8'));
Object.assign(geo,JSON.parse(await readFile(new URL('../web/public/map-sites.json',import.meta.url),'utf8')));
assert.equal(geo.settlements.length,places.length,'Rebuild geography after changing the gazetteer');
places.forEach((p,i)=>assert.deepEqual(geo.settlements[i],[p.lon,p.lat]));
class Path {rings=[];moveTo(x,y){this.rings.push([[x,y]])}lineTo(x,y){this.rings.at(-1).push([x,y])}closePath(){}}
globalThis.Path2D=Path;
const distances=coastClearances(geo,places.map(p=>project(p.lon,p.lat)));
const waters=[[29,41.015],[28.965,41.024],[26.66,40.38],[28.58,40.16],[30.87,37.9]];
for(const quality of ['low','medium','high']){
 const rendered=paths(geo,quality),converted=Object.fromEntries(['land','lakes'].map(k=>[k,rendered[k].map(p=>p.rings.map(r=>r.map(([x,y])=>[x/20-10,50-y/23])))]));
 for(const p of places)assert(onLand(p.lon,p.lat,converted),`${quality}: ${p.id} must be on its own land, not snapped to shore`);
 for(const [lon,lat] of waters)assert(!onLand(lon,lat,converted),`${quality}: ${lon},${lat} must remain water`);
 places.forEach((p,i)=>{for(const units of [.001,.01,.1,1]){const scale=groundScale(distances[i],units);assert(scale>=0&&scale<=1);for(let angle=0;angle<8;angle++){const radius=26*scale*units,a=angle*Math.PI/4;assert(onLand(p.lon+Math.cos(a)*radius/20,p.lat-Math.sin(a)*radius/23,converted),`${quality}: ${p.id} ground footprint crosses shore`)}}});
}
// Dense neighbouring cities retain true coordinates in the legacy atlas too.
const pins=layoutPlaces(places,{x:0,y:0,width:1500,height:800},1500,800);
for(const p of pins)assert.deepEqual(p.position,p.anchor);
const byId=Object.fromEntries(places.map(p=>[p.id,p]));
assert(byId.constantinople.lon<29&&byId.galata.lon<29&&byId.chrysopolis.lon>29&&byId.chalcedon.lon>29);
assert(byId.karacahisar.lat<byId.eskisehir.lat&&byId.sogut.lat>40);
console.log(`PASS historical geography: ${places.length} real anchors, all LOD/ground footprints, straits/lakes and fixed atlas positions`);
