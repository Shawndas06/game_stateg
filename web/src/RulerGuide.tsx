import {useEffect,useState} from 'react';

export type GuideStage='welcome'|'council'|'map'|'army'|'state'|'time'|'reports'|'done'|'dismissed';
type Progress={stage:GuideStage;decision:boolean};
const stages:GuideStage[]=['welcome','council','map','army','state','time','reports','done','dismissed'];
export function useRulerGuide(campaign:string){
  const key=`ruler-guide-v1:${campaign}`;
  const [progress,setProgress]=useState<Progress>(()=>{
    try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(saved&&stages.includes(saved.stage))return {stage:saved.stage,decision:saved.decision===true}}catch{}
    return {stage:'welcome',decision:false};
  });
  useEffect(()=>{try{localStorage.setItem(key,JSON.stringify(progress))}catch{/* Help still works if browser storage is unavailable. */}},[key,progress]);
  return {progress,setProgress};
}

export default function RulerGuide({stage,decision,hasChoices,tab,busy,onStage,onTab,onTime,onCouncil,onReports}:{
  stage:GuideStage;decision:boolean;hasChoices:boolean;tab:string;busy:boolean;
  onStage:(stage:GuideStage)=>void;onTab:(tab:string)=>void;onTime:()=>void;onCouncil:()=>void;onReports:()=>void;
}){
  if(stage==='done'||stage==='dismissed')return null;
  const go=(next:GuideStage,tab:string)=>{onStage(next);onTab(tab)};
  const index=Math.max(0,stages.indexOf(stage)-1);
  return <aside className="play-guide" aria-label="Обучение правлению" data-guide-stage={stage}>
    <div className="guide-heading"><span className="eyebrow">{stage==='welcome'?'Первые шаги':`Обучение · ${index+1} из 6`}</span>
      <button className="quiet" onClick={()=>onStage('dismissed')} aria-label="Пропустить обучение">Пропустить</button></div>
    {stage==='welcome'&&<><h2>Как стать правителем</h2><p>Вы управляете небольшим бейликом. Выслушивайте людей, отдавайте приказы и проверяйте исполнение. Цель первой главы — удержать власть и определить порядок управления.</p><p>Пройдём шесть коротких шагов в вашей партии. Решения вы принимаете сами; обучение не тратит ресурсы и не двигает время за вас.</p><button className="primary" onClick={()=>go('council','court')}>Начать обучение</button></>}
    {stage==='council'&&<><h2>1. Выслушайте и решите</h2><p>Откройте речи советников под вопросом совета. Они сообщают известные им факты и предлагают свой путь. Затем выберите свой ответ в блоке «Решение правителя».</p><p>Игра не раскрывает будущие последствия выбора. Решение записывается сразу; его исполнение может занять время.</p>{tab!=='court'?<button onClick={()=>onTab('court')}>Открыть совет</button>:hasChoices&&!decision?<button className="primary" onClick={onCouncil}>Читать вопрос и мнения ↓</button>:<button disabled={busy} onClick={()=>go('map','map')}>Дальше: ваши владения →</button>}</>}
    {stage==='map'&&<><h2>2. Найдите свои владения</h2><p>Зелёные флаги — ваши владения. Нажмите на крепость или найдите город через поиск. Карточка ниже карты показывает гарнизон, запасы и дату сведений. «—» означает отсутствие сведений, а не ноль.</p>{tab!=='map'?<button onClick={()=>onTab('map')}>Открыть атлас</button>:<button onClick={()=>go('army','army')}>Дальше: как устроены войска →</button>}</>}
    {stage==='army'&&<><h2>3. Гарнизон и армия — разные силы</h2><p>Гарнизон охраняет крепость. Походная армия движется с командующим. В «Наборе и сборе» люди сначала обучаются и попадают в гарнизон; затем из готовых воинов можно собрать армию.</p><p>В «Моих армиях» выдаются поручения. Командующему нужны цель, средства и продовольствие. Для обучения начинать войну или нанимать людей не требуется.</p>{tab!=='army'?<button onClick={()=>onTab('army')}>Открыть войско</button>:<button onClick={()=>go('state','state')}>Дальше: казна и управление →</button>}</>}
    {stage==='state'&&<><h2>4. Отдавайте конкретные распоряжения</h2><p>В «Державе» выберите нужное дело: счета, назначения, торговлю, строительство или отношения с соседями. Казна — доступные деньги, а месячная смета — ожидаемые регулярные поступления и расходы.</p><p>Приказ в дальнее владение сначала доставляет гонец. Купленное зерно тоже должно прибыть: деньги списаны — это ещё не доставка.</p>{tab!=='state'?<button onClick={()=>onTab('state')}>Открыть державу</button>:<button onClick={()=>go('time','court')}>Дальше: дать приказам исполниться →</button>}</>}
    {stage==='time'&&<><h2>5. Дайте миру время</h2><p>Пока вы читаете и выбираете, календарь стоит. Кнопка «Продолжить время» запускает движение войск, гонцов и обозов. Ожидание остановится у важного известия.</p><p>Сроки оставленных писем и обещаний тоже идут. В открывшемся окне можно выбрать короткое ожидание или вернуться без изменений.</p><button disabled={busy} className="primary" onClick={onTime}>Попробовать ожидание</button></>}
    {stage==='reports'&&<><h2>6. Проверьте, что произошло</h2><p>Ниже, в «Последних донесениях», прочтите новые известия. Проверяйте не только текст: местонахождение войск — в «Войске», запас после доставки — в карточке владения. Письма, обещания и протоколы сохраняются в «Летописи».</p><p>Дальше цикл тот же: сведения → решение → приказ → ожидание → проверка. Справка «Как играть» всегда доступна над разделом.</p>{tab!=='court'?<button onClick={()=>onTab('court')}>Открыть донесения</button>:<><button onClick={onReports}>Читать новые донесения ↓</button><button className="primary" onClick={()=>onStage('done')}>Понятно, продолжить правление</button></>}</>}
  </aside>;
}
