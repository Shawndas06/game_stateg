// The short-lived session stays in memory: embedded browsers may reject cookies.
// Never persist Telegram credentials or session tokens in browser storage.
export class ApiError extends Error {constructor(message:string, public status:number){super(message)}}
let token='';
let login:Promise<void>|null=null;

async function fetchJson<T>(path:string,body?:unknown):Promise<T>{
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),65000);
 try{
  const response=await fetch('/api'+path,{signal:controller.signal,credentials:'same-origin',headers:{...(token?{Authorization:`Bearer ${token}`}:{ }),...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{method:'POST',body:JSON.stringify(body)})});
  const data=await response.json().catch(()=>{throw new Error('Invalid JSON')});
  if(!response.ok)throw new ApiError(typeof data?.detail==='string'?data.detail:'Сервер временно недоступен. Повторите попытку.',response.status);
  return data;
 }catch(e){
  if(e instanceof ApiError)throw e;
  throw new Error(controller.signal.aborted?'Ответ задерживается. Проверьте связь и повторите попытку.':'Не удалось получить ответ. Проверьте соединение и повторите попытку.');
 }finally{clearTimeout(timer)}
}

export async function authenticate(demo=false):Promise<void>{
 if(login)return login;
 const init=window.Telegram?.WebApp.initData;
 if(!init&&!demo)throw new ApiError('Откройте игру кнопкой в Telegram, чтобы восстановить вход.',401);
 login=(async()=>{const data=await fetchJson<{session_token:string}>(init?'/auth/telegram':'/auth/demo',init?{init_data:init}:{});token=data.session_token;})();
 try{await login}finally{login=null}
}

export async function api<T>(path:string,body?:unknown):Promise<T>{
 try{return await fetchJson<T>(path,body)}catch(e){
  // A 401 is rejected before execution; replay once with the same command ID.
  // Network failures are NOT automatically replayed: their outcome is unknown.
  if(!(e instanceof ApiError)||e.status!==401||path.startsWith('/auth/')||!window.Telegram?.WebApp.initData)throw e;
  await authenticate();
  return fetchJson<T>(path,body);
 }
}
