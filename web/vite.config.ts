import {defineConfig} from 'vite';
import {createHash} from 'node:crypto';
import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
function source(dir:string):string{return readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name)).map(e=>e.isDirectory()?source(join(dir,e.name)):readFileSync(join(dir,e.name),'utf8')).join('\n')}
const build=createHash('sha256').update(source('src')).digest('hex').slice(0,12);
export default defineConfig({plugins:[{name:'build-identity',transformIndexHtml(){return [{tag:'meta',attrs:{name:'build',content:build},injectTo:'head'}]}}],server:{proxy:{'/api':'http://127.0.0.1:8000'}}});
