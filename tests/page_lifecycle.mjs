import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from '../web/node_modules/typescript/lib/typescript.js';
globalThis.window=new EventTarget();
const source=await readFile(new URL('../web/src/page-lifecycle.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const {pageController,releasePageController}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const show=()=>{const event=new Event('pageshow');Object.defineProperty(event,'persisted',{value:true});window.dispatchEvent(event)};
for(const event of ['beforeunload','pagehide']){
 show();const a=pageController(),b=pageController();let aborts=0;
 a.signal.addEventListener('abort',()=>aborts++);assert(!a.signal.aborted&&!b.signal.aborted);
 window.dispatchEvent(new Event(event));assert(a.signal.aborted&&b.signal.aborted);
 assert(pageController().signal.aborted,'Late effects must receive an already cancelled signal');
 window.dispatchEvent(new Event(event));releasePageController(a);assert.equal(aborts,1);
 show();const restored=pageController();assert(!restored.signal.aborted);
 assert(a.signal.aborted,'A restored document must use a fresh request');
 releasePageController(restored);assert(restored.signal.aborted);
}
console.log('PASS page lifecycle: existing/late loads cancelled, repeated shutdown idempotent, cached-page restore uses fresh controllers');
