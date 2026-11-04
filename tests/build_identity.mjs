import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync,renameSync} from 'node:fs';
import {readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import ts from '../web/node_modules/typescript/lib/typescript.js';
const source=await readFile(new URL('../web/build-identity.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {buildIdentity}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const dir=mkdtempSync(join(tmpdir(),'campaign-build-'));
try{
 const src=join(dir,'src'),pub=join(dir,'public');mkdirSync(src);mkdirSync(pub);
 writeFileSync(join(src,'app.ts'),'game');writeFileSync(join(pub,'map.json'),'shore1');
 const a=buildIdentity([src,pub]);assert.equal(buildIdentity([src,pub]),a);
 writeFileSync(join(pub,'map.json'),'shore2');const b=buildIdentity([src,pub]);assert.notEqual(b,a);
 writeFileSync(join(pub,'sprite.bin'),Buffer.from([255]));const c=buildIdentity([src,pub]);
 writeFileSync(join(pub,'sprite.bin'),Buffer.from([254]));const d=buildIdentity([src,pub]);assert.notEqual(d,c);
 renameSync(join(pub,'map.json'),join(pub,'new-map.json'));assert.notEqual(buildIdentity([src,pub]),d);
 console.log('PASS build identity: geography, binary assets, names and deterministic readback');
}finally{rmSync(dir,{recursive:true,force:true})}
