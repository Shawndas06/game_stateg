"""Canvas camera benchmarks and interaction invariants; isolated server only."""
import json,os
from pathlib import Path
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game,resume_menu

readings=[]

def run(bt,width,url,out):
    browser=bt.launch();ctx=browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=3)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm');page.get_by_role('button',name='Пропустить пролог',exact=True).click();page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    expect(page.get_by_test_id('place-sogut')).to_be_visible()
    cdp=ctx.new_cdp_session(page) if bt.name=='chromium' else None
    if cdp:cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    for quality in ['low','medium','high']:
        page.get_by_role('button',name='Открыть меню кампании',exact=True).click();page.get_by_label('Качество карты',exact=True).select_option(quality);page.get_by_role('button',name='Продолжить',exact=True).click()
        expect(page.locator('.canvas-world')).to_have_attribute('data-quality',quality)
        for mode in ['campaign','world']:
            if mode=='world':page.get_by_role('button',name='Весь мир',exact=True).click()
            revision=state()['revision'];requests=[];on_request=lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None;page.on('request',on_request)
            page.evaluate('''()=>{window.sample={frames:[],writes:0,last:0,active:true};window.mo=new MutationObserver(xs=>sample.writes+=xs.length);mo.observe(document.querySelector('.map-hit-layer'),{subtree:true,childList:true,attributes:true});function tick(t){if(!sample.active)return;if(sample.last)sample.frames.push(t-sample.last);sample.last=t;requestAnimationFrame(tick)}requestAnimationFrame(tick)}''')
            # Begin on clear map space, away from fixed HUD/panels.
            for direction in [1,-1]:
                page.mouse.move(540,240);page.mouse.down();writes=page.evaluate('sample.writes');page.mouse.move(540+direction*60,260,steps=24)
                assert page.evaluate('sample.writes')==writes,'Camera gestures must not rebuild marker DOM'
                page.mouse.up();page.evaluate('()=>new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)))')
            sample=page.evaluate('()=>{sample.active=false;mo.disconnect();return sample}');page.remove_listener('request',on_request)
            assert not requests,requests
            assert state()['revision']==revision
            frames=sorted(sample['frames']);p95=frames[min(len(frames)-1,int(len(frames)*.95))] if frames else None
            limits={'low':1,'medium':1.5,'high':2};ratio=page.locator('canvas').evaluate('(c)=>c.width/c.clientWidth')
            assert ratio<=limits[quality]+.01
            page.screenshot(path=str(out/f'canvas-{bt.name}-{quality}-{mode}.png'))
            readings.append({'browser':bt.name,'quality':quality,'mode':mode,'cpu_throttle':4 if cdp else None,'frame_p95_ms':round(p95,1) if p95 else None,'requests':len(requests),'dpr':ratio})
        page.get_by_role('button',name='Столица',exact=True).click();page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    # Real native pinch starts at an interactive army marker.
    if cdp:
        marker=page.locator('[data-map-army="ottoman-1"]');box=marker.bounding_box();x=box['x']+24;y=box['y']+24
        before=page.evaluate('localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith("camera:")))');revision=state()['revision']
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1},{'x':x+60,'y':y,'id':2}]})
        for delta in [10,20,30]:cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x-delta,'y':y,'id':1},{'x':x+60+delta,'y':y,'id':2}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        after=page.evaluate('localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith("camera:")))')
        assert json.loads(after)['width']<json.loads(before)['width']*.8
        assert state()['revision']==revision and not page.locator('.campaign-inspector').is_visible()
    page.get_by_label('Поиск поселения',exact=True).fill('Бурса');page.locator('[data-search-place=bursa]').click();expect(page.get_by_test_id('place-bursa')).to_be_visible()
    page.get_by_role('button',name='Закрыть карточку',exact=True).click();revision=state()['revision']
    camera=page.evaluate('localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith("camera:")))')
    page.reload();resume_menu(page);expect(page.get_by_test_id('place-bursa')).to_be_visible()
    assert page.evaluate('localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith("camera:")))')==camera and state()['revision']==revision
    assert not errors,errors
    print('PASS canvas '+bt.name+': all qualities, camera without requests/DOM churn, native marker pinch, search and saved camera',flush=True)
    ctx.close();browser.close()

if __name__=='__main__':
    original=run
    def once(bt,width,url,out):
        if width==390:original(bt,width,url,out)
    harness.run=once;harness.main();Path(os.getenv('ATLAS_PERF_OUT','/tmp/atlas-performance.json')).write_text(json.dumps(readings,indent=2));print(json.dumps(readings),flush=True)
