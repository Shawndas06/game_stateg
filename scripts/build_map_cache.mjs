/** Offline derivative preparation: no shoreline scans or forest sampling at startup. */
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import ts from '../web/node_modules/typescript/lib/typescript.js';
const compile=async p=>ts.transpileModule(await readFile(new URL(p,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const module=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const geometryURL=module(await compile('../web/src/atlas-geometry.ts')),geometry=await import(geometryURL);
const scene=await import(module((await compile('../web/src/map-scene.ts')).replace(/(['"])\.\/atlas-geometry\1/,JSON.stringify(geometryURL))));
const raw=await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url)),fingerprint=createHash('sha256').update(raw).digest('hex');
const sitesURL=new URL('../web/public/map-sites.json',import.meta.url),landscapeURL=new URL('../web/src/map-landscape.json',import.meta.url);
const sites=JSON.parse(await readFile(sitesURL,'utf8')),data=JSON.parse(await readFile(landscapeURL,'utf8')),geo={...JSON.parse(raw),settlements:sites.settlements};
sites.coast_cache={geometry:fingerprint,values:scene.coastClearances(geo,sites.settlements.map(p=>geometry.project(...p))).map(v=>Math.floor(v*1e8)/1e8)};
const marks=scene.landscapeMarks(geo,scene.reliefRegions(data.mountains,data.hills),data.woods,sites.settlements);
data.cache={geometry:fingerprint,settlements:JSON.stringify(sites.settlements),marks:marks.map(m=>[m.lon,m.lat,m.kind])};
await writeFile(sitesURL,JSON.stringify(sites));await writeFile(landscapeURL,JSON.stringify(data));
console.log('Prepared map cache:',sites.coast_cache.values.length,'shore clearances,',marks.length,'landscape marks, geometry',fingerprint);
