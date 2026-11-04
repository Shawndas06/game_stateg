import {read} from './preferences';
export type Metric={kind:'manual'|'command'|'http_error'|'map_frame';duration_ms:number;status?:number;request_id?:string};
const buffer:Metric[]=[];
export function metric(event:Metric){if(read('diagnostics')==='off')return;buffer.push({...event,duration_ms:Math.max(0,Math.min(300000,Math.round(event.duration_ms)))});if(buffer.length>20)buffer.shift()}
export function metrics(){return buffer.slice()}
