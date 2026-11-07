import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import ts from '../web/node_modules/typescript/lib/typescript.js';
const compile=async p=>ts.transpileModule(await readFile(new URL(p,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const module=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const geometry=await import(module(await compile('../web/src/atlas-geometry.ts')));
const scene=await import(module((await compile('../web/src/map-scene.ts')).replace(/(['"])\.\/atlas-geometry\1/,JSON.stringify(module(await compile('../web/src/atlas-geometry.ts'))))));
const raw=await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url)),hash=createHash('sha256').update(raw).digest('hex');
const sites=JSON.parse(await readFile(new URL('../web/public/map-sites.json',import.meta.url),'utf8')),data=JSON.parse(await readFile(new URL('../web/src/map-landscape.json',import.meta.url),'utf8'));
assert(sites.coast_cache,'Static coastal distances must be built before deployment');
assert(data.cache,'Static landscape marks must be built before deployment');
assert.equal(sites.coast_cache.geometry,hash);assert.equal(data.cache.geometry,hash);
assert.equal(data.cache.settlements,JSON.stringify(sites.settlements));
const geo={...JSON.parse(raw),settlements:sites.settlements},points=sites.settlements.map(p=>geometry.project(...p));
const cold=scene.coastClearances(geo,points);
assert.equal(sites.coast_cache.values.length,162);
for(const [i,v] of sites.coast_cache.values.entries())assert(v>=0&&v<=cold[i]&&cold[i]-v<1e-7,'Cached clearance must conservatively match the actual shoreline');
const cached={...geo,geometry_fingerprint:hash,coast_cache:sites.coast_cache};
assert.deepEqual(scene.coastClearances(cached,points),sites.coast_cache.values);
// A valid cache must not walk raw polygon edges again on a slow device.
assert.deepEqual(scene.coastClearances({...cached,get land(){throw Error('Unnecessary cold shoreline scan')}},points),sites.coast_cache.values);
const square={land:[[[[0,0],[2,0],[2,2],[0,2],[0,0]]]],lakes:[],settlements:[[.5,1]],geometry_fingerprint:'current'};
for(const cache of [{geometry:'stale',values:[999]},{geometry:'current',values:[]},{geometry:'current',values:[-1]}])assert.deepEqual(scene.coastClearances({...square,coast_cache:cache},[geometry.project(.5,1)]),[10]);
assert.deepEqual(scene.coastClearances({...square,coast_cache:{geometry:'current',values:[10]}},[geometry.project(.75,1)]),[15]);
const marks=scene.landscapeMarks(geo,scene.reliefRegions(data.mountains,data.hills),data.woods,sites.settlements);
assert.equal(data.cache.marks.length,marks.length);
for(const [i,m] of marks.entries()){
 const [lon,lat,kind]=data.cache.marks[i];assert.equal(kind,m.kind);
 assert(Math.abs(lon-m.lon)<1e-9&&Math.abs(lat-m.lat)<1e-9,'Derived marks must match cold geometry well below a rendered pixel');
}
console.log('PASS derived map assets: actual geometry fingerprint, 162 conservative distances, fast cache, stale/changed/invalid fallback, exact landscape marks');
