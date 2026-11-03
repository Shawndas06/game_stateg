import {useId} from 'react';

// An unfinished edit is not a number. In particular, '' must never become 0.
export function integer(value:string,min:number,max:number,step=1):number|null {
  if(!/^\d+$/.test(value))return null;
  const n=Number(value);
  return Number.isSafeInteger(n)&&n>=min&&n<=max&&(n-min)%step===0?n:null;
}

export default function NumberField({label,value,onChange,min,max,step=1,hint}:{
  label:string;value:string;onChange:(value:string)=>void;min:number;max:number;step?:number;hint?:string;
}){
  const id=useId(),valid=integer(value,min,max,step)!==null;
  return <label className="number-field" htmlFor={id}>{label}
    <input id={id} aria-label={label} type="number" inputMode="numeric" min={min} max={max} step={step}
      value={value} onChange={e=>onChange(e.target.value)} aria-invalid={!valid} aria-describedby={id+'-hint'}/>
    <small id={id+'-hint'} className={valid?'field-hint':'field-error'}>
      {!valid?`Введите целое число от ${min} до ${max}${step>1?`, шаг ${step}`:''}.`:hint||`${min}–${max}${step>1?`, шаг ${step}`:''}`}
    </small>
  </label>;
}
