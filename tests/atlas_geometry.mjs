// Compare the cached sampler against the existing geometric predicate and
// analytic hole/lake boundaries; no browser/server or new runtime dependency.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from '../web/node_modules/typescript/lib/typescript.js';
const source=await readFile(new URL('../web/src/atlas-geometry.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const {onLand,landSampler}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
const square=(x,y,n)=>[[x,y],[x+n,y],[x+n,y+n],[x,y+n],[x,y]];
const fixture={land:[[square(0,0,10),square(2,2,2)]],lakes:[[square(6,6,2)]]};
const sample=landSampler(fixture);
for(const [x,y,expected] of [[1,1,true],[3,3,false],[7,7,false],[-1,5,false],[0,1,true],[10,1,false],[2,3,false],[4,3,true],[5,10,false]])assert.equal(sample(x,y),expected,`${x},${y}`);
const real=JSON.parse(await readFile(new URL('../web/public/mediterranean-geography.json',import.meta.url),'utf8')),cached=landSampler(real);
let seed=7;const random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/2**32);
for(let i=0;i<2500;i++){const x=-10+random()*58,y=25+random()*26;assert.equal(cached(x,y),onLand(x,y,real),`real ${x},${y}`)}
// Many samples on shared scanlines plus eviction and revisit exercise the cache.
for(let row=0;row<550;row++)for(const x of [0,12,29,35]){const y=25+row*.05;assert.equal(cached(x,y),onLand(x,y,real))}
for(const y of [29,35,40,49])for(const x of [0,12,29,35])assert.equal(cached(x,y),onLand(x,y,real));
console.log('PASS atlas sampler: analytic coast/hole/lake boundaries, 2500 seeded world points, scanline reuse and eviction');
