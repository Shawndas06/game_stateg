import {useState} from 'react';
import {api} from './api';
export default function SavedCampaigns({load}:{load:(id:string)=>void}){
 const [items,setItems]=useState<{id:string;scenario:string;ruler:string;revision:number}[]|null>(null),[error,setError]=useState('');
 async function list(){try{setError('');setItems(await api('/campaigns'))}catch(e){setError((e as Error).message)}}
 return <section className="card"><h2>Сохранённые кампании</h2><button onClick={list}>Открыть список летописей</button>{error&&<p role="alert">{error}</p>}{items?.map(x=><div className="action-row" key={x.id}><div><strong>{x.ruler}</strong><small>{x.scenario==='ruler_v1'?'Управление живым государством':'Прежняя кампания'} · запись {x.revision}</small></div><button onClick={()=>load(x.id)}>Продолжить</button></div>)}</section>;
}
