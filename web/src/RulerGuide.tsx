import {useEffect,useState} from 'react';
import {Voice} from './CampaignMedia';

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
    <div className="guide-heading"><img src="/media/advisor.webp" width="36" height="44" alt=""/><span className="eyebrow">{stage==='welcome'?'Первые шаги':`Обучение · ${index+1} из 6`}</span>
      <button className="quiet" onClick={()=>onStage('dismissed')} aria-label="Пропустить обучение">Пропустить</button></div>
    {stage==='welcome'&&<><h2>Как стать правителем</h2><p>Вы управляете небольшим бейликом. Выслушивайте людей, отдавайте приказы и проверяйте исполнение. Цель первой главы — удержать власть и определить порядок управления.</p><p>Пройдём шесть коротких шагов в вашей партии. Решения вы принимаете сами; обучение не тратит ресурсы и не двигает время за вас.</p><button className="primary" onClick={()=>go('council','court')}>Начать обучение</button></>}
    {stage==='council'&&<><h2>1. Выслушайте и решите</h2><p>Прочтите вопрос совета и выберите один ответ. Вариант про 25 монет сам перечислит деньги — искать отдельную оплату не нужно.</p>{tab!=='court'?<button onClick={()=>onTab('court')}>Открыть совет</button>:hasChoices&&!decision?<button className="primary" onClick={onCouncil}>Читать вопрос и мнения</button>:<button disabled={busy} onClick={()=>go('map','map')}>Дальше: ваши владения →</button>}</>}
    {stage==='map'&&<><h2>2. Найдите свои владения</h2><p>Нажмите «Моя столица» над картой. Под картой находятся запасы и гарнизон. Поиск также приближает выбранный город.</p>{tab!=='map'?<button onClick={()=>onTab('map')}>Открыть атлас</button>:<button onClick={()=>go('army','army')}>Дальше: как устроены войска →</button>}</>}
    {stage==='army'&&<><h2>3. Гарнизон и армия — разные силы</h2><p>Посмотрите готовую армию ниже: люди, командующий и запас еды. Гарнизоны охраняют крепости отдельно. Для этого шага нанимать людей и начинать войну не требуется.</p>{tab!=='army'?<button onClick={()=>onTab('army')}>Открыть войско</button>:<button onClick={()=>go('state','state')}>Дальше: казна и управление →</button>}</>}
    {stage==='state'&&<><h2>4. Отдавайте конкретные распоряжения</h2><p>Сравните доходы и расходы в «Счетах казны» ниже. Покупать ничего не нужно. Другие дела открываются вкладками: например, «Строительство» покажет стоимость и требования каждой работы.</p>{tab!=='state'?<button onClick={()=>onTab('state')}>Открыть державу</button>:<button onClick={()=>go('time','court')}>Дальше: дать приказам исполниться →</button>}</>}
    {stage==='time'&&<><h2>5. Дайте миру время</h2><p>Теперь можно дать приказам исполниться. Выберите короткое ожидание; гонцы, войска и грузы начнут движение. Важное известие остановит время.</p><button disabled={busy} className="primary" onClick={onTime}>Попробовать ожидание</button></>}
    {stage==='reports'&&<><h2>6. Проверьте, что произошло</h2><p>Откройте последние донесения. Затем проверьте результат в самом владении или армии. Приказ, который ещё в пути, пока ничего там не изменил.</p>{tab!=='court'?<button onClick={()=>onTab('court')}>Открыть донесения</button>:<><button onClick={onReports}>Читать новые донесения</button><button className="primary" onClick={()=>onStage('done')}>Понятно, продолжить правление</button></>}</>}
    {!['welcome','done','dismissed'].includes(stage)&&<details className="guide-voice"><summary>Озвучить подсказку</summary><Voice clip={({council:'guide_council',map:'map',army:'army',state:'state',time:'guide_time',reports:'guide_reports'} as const)[stage as 'council'|'map'|'army'|'state'|'time'|'reports']}/></details>}
  </aside>;
}
