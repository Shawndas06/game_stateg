import {defineConfig} from 'vite';
import {buildIdentity} from './build-identity';
const build=buildIdentity(['src','public']);
export default defineConfig({plugins:[{name:'build-identity',transformIndexHtml(){return [{tag:'meta',attrs:{name:'build',content:build},injectTo:'head'}]}}],server:{proxy:{'/api':'http://127.0.0.1:8000'}}});
