"""Telegram viewport/back lifecycle and landscape controls with a mocked SDK."""
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game,resume_menu,nav


def run(bt,width,url,out):
    if width not in [390,320]:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=2)
    ctx.add_init_script('''window.sdk={fullscreen:0,locked:false,events:{},back:null};window.Telegram={WebApp:{initData:'',ready(){},expand(){},isVersionAtLeast(){return true},requestFullscreen(){sdk.fullscreen++},lockOrientation(){sdk.locked=true},unlockOrientation(){sdk.locked=false},safeAreaInset:{top:18,bottom:12,left:0,right:0},contentSafeAreaInset:{top:25,bottom:0,left:0,right:0},onEvent(k,f){sdk.events[k]=f},offEvent(k,f){if(sdk.events[k]===f)delete sdk.events[k]},BackButton:{show(){},hide(){},onClick(f){sdk.back=f},offClick(f){if(sdk.back===f)sdk.back=null}}}}''')
    ctx.route('https://telegram.org/js/**',lambda r:r.fulfill(body='/* SDK fixture */',content_type='application/javascript'))
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm');page.get_by_role('button',name='Пропустить пролог',exact=True).click();page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    assert page.evaluate('sdk.fullscreen')==1
    assert page.locator('.header').bounding_box()['y']>=25
    expect(page.get_by_test_id('place-sogut')).to_be_visible();page.get_by_test_id('place-sogut').click();expect(page.locator('.campaign-inspector')).to_be_visible()
    page.evaluate('sdk.back()');expect(page.locator('.campaign-inspector')).to_be_hidden()
    nav(page,'Государство');page.get_by_role('button',name='Мастера, учреждения и знания',exact=True).click();expect(page.get_by_role('tab',name='Мастера и знания',exact=True)).to_have_attribute('aria-selected','true')
    page.evaluate('sdk.back()');expect(page.locator('.canvas-world')).to_be_visible();expect(page.locator('.strategy-active')).to_have_count(1)
    page.evaluate('sdk.back()');expect(page.get_by_role('dialog',name='Меню кампании',exact=True)).to_be_visible()
    page.evaluate('sdk.back()');expect(page.get_by_role('dialog')).to_have_count(0)
    page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='Столица',exact=True).click();expect(page.locator('.campaign-inspector')).to_be_visible()
    assert page.locator('.campaign-inspector').bounding_box()['width']==390
    page.get_by_role('tab',name='Набор',exact=True).click();field=page.get_by_label('Число новобранцев на карте',exact=True);field.fill('');expect(page.get_by_role('button',name='Начать набор в городе',exact=True)).to_be_disabled()
    assert field.bounding_box()['width']>250
    page.evaluate('sdk.back()');page.screenshot(path=str(out/f'{bt.name}-landscape-portrait.png'))
    page.get_by_role('button',name='Передать ход времени',exact=True).click()
    expect(page.locator('main[aria-busy=true]')).to_have_count(0)
    before=page.request.get(url+'/api/campaigns/latest').json()['state']
    page.get_by_role('button',name='Открыть меню кампании',exact=True).click();page.get_by_role('button',name='Главное меню',exact=True).click();resume_menu(page)
    expect(page.get_by_test_id('prologue')).to_have_count(0)
    assert page.request.get(url+'/api/campaigns/latest').json()['state']['revision']==before['revision']
    page.evaluate('Telegram.WebApp.isVersionAtLeast=()=>false;Telegram.WebApp.lockOrientation=()=>{throw Error("Unsupported orientation must not be called")}')
    page.get_by_role('button',name='Открыть меню кампании',exact=True).click()
    expect(page.get_by_role('button',name='Закрепить / освободить текущее положение экрана',exact=True)).to_be_disabled()
    page.get_by_role('button',name='Продолжить',exact=True).click()
    assert not errors,errors
    print(f'PASS Telegram shell {bt.name}: landscape/portrait, fullscreen, safe areas, contextual back, masters shortcut, blank input',flush=True)
    ctx.close();browser.close()

if __name__=='__main__':
    original=run
    harness.run=lambda bt,w,u,o:original(bt,w,u,o) if w==390 else None
    harness.main()
