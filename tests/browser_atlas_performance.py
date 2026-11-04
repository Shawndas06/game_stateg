"""Atlas interaction benchmark against an isolated built application, never production.

ATLAS_PERF_OUT=/tmp/atlas-before.json PYTHONPATH=. python tests/browser_atlas_performance.py
Use ATLAS_PERF_ASSERT=1 after the optimization to enforce stable coastline paths.
"""
import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect


def run(bt,width,url):
    browser=bt.launch();context=browser.new_context(viewport={'width':width,'height':844},is_mobile=True,has_touch=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);page.get_by_role('button',name='Стать правителем',exact=False).click()
    page.get_by_role('button',name='Пропустить пролог',exact=True).click();page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    cdp=context.new_cdp_session(page) if bt.name=='chromium' else None
    if cdp:cdp.send('Emulation.setCPUThrottlingRate',{'rate':4});cdp.send('Performance.enable')
    started=time.perf_counter();page.get_by_role('button',name='Атлас',exact=True).click();page.locator('.map-load-state').wait_for(state='hidden')
    page.locator('.illustrated-map').scroll_into_view_if_needed()
    opened=round((time.perf_counter()-started)*1000)
    readings=[]
    for mode in ['campaign','world']:
        if mode=='world':page.get_by_role('button',name='Весь мир',exact=False).click()
        page.locator('.illustrated-map').scroll_into_view_if_needed()
        page.evaluate('''() => {
          const svg=document.querySelector('.illustrated-map');
          window.atlasSample={frames:[],long:[],pathWrites:0,requests:0,coastWrites:0,active:true};
          window.atlasObserver=new MutationObserver(list=>{atlasSample.pathWrites+=list.filter(m=>m.attributeName==='d').length;atlasSample.coastWrites+=list.filter(m=>m.target.closest('[data-coastline]')).length});
          atlasObserver.observe(svg,{subtree:true,attributes:true,attributeFilter:['d']});
          if(PerformanceObserver.supportedEntryTypes.includes('longtask'))new PerformanceObserver(list=>{if(atlasSample.active)atlasSample.long.push(...list.getEntries().map(e=>e.duration))}).observe({type:'longtask'});
          let last=performance.now();function frame(now){if(!atlasSample.active)return;atlasSample.frames.push(now-last);last=now;requestAnimationFrame(frame)}requestAnimationFrame(frame);
        }''')
        # The local raster snapshot uses a blob URL, not a server/network request.
        requests=[];on_request=lambda request:requests.append(request) if request.url.startswith(('http:','https:')) else None;page.on('request',on_request)
        before={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']} if cdp else {}
        box=page.locator('.illustrated-map').bounding_box();x=box['x']+box['width']*.3;y=box['y']+box['height']*.45
        start=time.perf_counter()
        for direction in [1,-1,1,-1]:
            page.mouse.move(x,y);page.mouse.down()
            writes=page.evaluate('atlasSample.pathWrites')
            page.mouse.move(x+direction*70,y+direction*35,steps=24)
            assert page.evaluate('atlasSample.pathWrites')==writes,'Paths/layout must stay frozen while the pointer is held'
            page.mouse.up()
        elapsed=(time.perf_counter()-start)*1000
        after={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']} if cdp else {}
        sample=page.evaluate('''() => {atlasSample.active=false;atlasObserver.disconnect();return atlasSample}''')
        page.remove_listener('request',on_request)
        frames=sorted(sample['frames'][1:]);p95=frames[min(len(frames)-1,int(len(frames)*.95))]
        report={'browser':bt.name,'width':width,'mode':mode,'cpu_throttle':4 if cdp else None,'open_ms':opened,'drag_ms':round(elapsed),'frame_p95_ms':round(p95,1),'long_tasks':len(sample['long']),'max_long_ms':round(max(sample['long'],default=0),1),'path_writes':sample['pathWrites'],'coastline_writes':sample['coastWrites'],'script_ms':round((after.get('ScriptDuration',0)-before.get('ScriptDuration',0))*1000),'network_requests':len(requests)}
        if os.getenv('ATLAS_PERF_ASSERT'):
            assert len(requests)==0,'Dragging should not request server state or geography'
            # Routes may change their d; the large coastline geometry must stay fixed.
            assert page.locator('[data-coastline]').count()>0
            assert sample['coastWrites']==0,'Coastline geometry was rebuilt during a drag'
            assert page.locator('feTurbulence,feDropShadow').count()==0
        print(json.dumps(report),flush=True);readings.append(report)
    page.get_by_label('Поиск поселения',exact=True).fill('Бурса');page.locator('[data-search-place=bursa]').click()
    expect(page.get_by_test_id('place-bursa')).to_be_in_viewport()
    assert 'is-selected' in page.get_by_test_id('place-bursa').get_attribute('class')
    page.get_by_test_id('place-bursa').locator('.place-hit-target').click();expect(page.locator('.ruler-place-card h2')).to_have_text('Бурса')
    page.get_by_role('button',name='Моя столица',exact=False).click()
    expect(page.get_by_test_id('place-sogut')).to_be_in_viewport()
    page.get_by_role('button',name='Приблизить карту',exact=True).click();page.get_by_role('button',name='Отдалить карту',exact=True).click()
    assert not errors,errors
    context.close();browser.close();return readings


def main():
    readings=[]
    with tempfile.TemporaryDirectory(prefix='atlas-benchmark-') as tmp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        with open(Path(tmp)/'server.log','w+') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':f'sqlite:///{tmp}/state.db','SESSION_SECRET':'atlas-benchmark-only','PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Fixture server did not start')
                with sync_playwright() as p:
                    for bt,width in [(p.chromium,390),(p.webkit,390)]:readings+=run(bt,width,url)
            finally:process.terminate();process.wait(timeout=10)
    Path(os.getenv('ATLAS_PERF_OUT','/tmp/atlas-performance.json')).write_text(json.dumps(readings,indent=2))


if __name__=='__main__':main()
