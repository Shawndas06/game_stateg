// Registered when the module loads, before a late React effect can start I/O.
const requests=new Set<AbortController>();
let leaving=false;
function leave(){leaving=true;for(const request of requests)request.abort();requests.clear()}
window.addEventListener('beforeunload',leave,{capture:true});
window.addEventListener('pagehide',leave);
window.addEventListener('pageshow',event=>{if(event.persisted)leaving=false});
export function pageController(){const request=new AbortController();if(leaving)request.abort();else requests.add(request);return request}
export function releasePageController(request:AbortController){requests.delete(request);request.abort()}
