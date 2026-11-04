import {createHash} from 'node:crypto';
import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
export function buildIdentity(roots:string[]){
 const hash=createHash('sha256');
 function visit(dir:string){for(const e of readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){const file=join(dir,e.name);if(e.isDirectory())visit(file);else hash.update(file).update('\0').update(readFileSync(file))}}
 roots.forEach(visit);return hash.digest('hex').slice(0,12);
}
