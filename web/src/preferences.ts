// Optional device preferences remain usable for this session when storage fails.
// Authentication credentials never enter this store.
const memory=new Map<string,string>();
export function read(key:string):string|null{if(memory.has(key))return memory.get(key)!;try{return localStorage.getItem(key)}catch{return null}}
export function remember(key:string,value:string){memory.set(key,value);try{localStorage.setItem(key,value)}catch{/* Session fallback is already updated. */}}
