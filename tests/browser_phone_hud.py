"""Phone orders window, desktop footer, inset painting and real symbol pixels."""
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game


def run(bt,width,url,out):
    if width!=390:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    ctx.add_init_script("window.sdk={events:{}};window.Telegram={WebApp:{initData:'',ready(){},expand(){},isVersionAtLeast(){return false},safeAreaInset:{top:60,bottom:12,left:0,right:0},contentSafeAreaInset:{top:60,bottom:0,left:0,right:0},onEvent(k,f){sdk.events[k]=f},offEvent(k,f){if(sdk.events[k]===f)delete sdk.events[k]}}}")
    ctx.route('https://telegram.org/js/**',lambda r:r.fulfill(body='/* explicit SDK fixture */',content_type='application/javascript'))
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm')
    for label in ['Пропустить пролог','Пропустить обучение']:page.get_by_role('button',name=label,exact=True).click()
    search=page.get_by_label('Поиск поселения',exact=True)
    def choose(label,ident):
        search.fill(label);page.locator(f'[data-search-place="{ident}"]').click()
        expect(page.get_by_test_id('place-'+ident)).to_be_visible()
    def hit(el):
        assert el.evaluate('(e)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}')
    choose('Сёгют','sogut');page.get_by_role('tab',name='Набор',exact=True).click()
    page.get_by_label('Число новобранцев на карте',exact=True).fill('5')
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as reply:
        page.get_by_role('button',name='Начать набор в городе',exact=True).click()
    assert reply.value.status==200
    page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    for w,h in [(320,740),(390,844),(844,390),(568,320),(1280,800),(1900,1010),(1366,500)]:
        page.set_viewport_size({'width':w,'height':h})
        page.evaluate("sdk.events.viewportChanged()")
        style=page.locator('.header').evaluate('(e)=>getComputedStyle(e).backgroundImage.replaceAll(" ","")')
        assert 'rgba(0,0,0,0)' in style,style
        menu=page.get_by_role('button',name='Открыть меню кампании',exact=True).bounding_box();assert menu['y']>=60,(menu,page.evaluate('({top:getComputedStyle(document.documentElement).getPropertyValue("--tg-top"),scroll:scrollY})'))
        choose('Сёгют','sogut')
        time=page.get_by_role('button',name='Передать ход времени',exact=True)
        if w>1000:assert abs(time.bounding_box()['x']+time.bounding_box()['width']-(w-12))<=2
        page.get_by_role('button',name='Закрыть карточку',exact=True).click()
        page.get_by_role('button',name='Поручения и донесения',exact=False).click()
        window=page.locator('.strategy-window>.content');body=page.locator('.government-body')
        expect(window).to_be_visible();a=window.bounding_box();t=time.bounding_box()
        feedback=body.locator('.ruler-feedback')
        expect(feedback).to_have_css('position','static')
        assert feedback.evaluate('(e)=>e.getBoundingClientRect().bottom<=e.nextElementSibling.getBoundingClientRect().top')
        if w<=1000:
            assert a['width']<w and a['height']<h*.75,(w,h,a)
            if w>h:assert a['width']<=w-160
        assert a['y']+a['height']<=t['y'],(a,t)
        close=page.get_by_role('button',name='Закрыть окно · к карте',exact=True);before=close.bounding_box()
        body.evaluate('(e)=>e.scrollTop=e.scrollHeight');hit(close);hit(time)
        assert close.bounding_box()==before
        page.screenshot(path=str(out/f'{bt.name}-{w}x{h}-orders.png'))
        close.click();expect(window).to_have_count(0)
    for ident,label,size in [('sogut','Сёгют','small'),('bursa','Бурса','medium'),('constantinople','Константинополь','large')]:
        choose(label,ident);expect(page.get_by_test_id('place-'+ident)).to_have_attribute('data-site-size',size)
        page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    page.get_by_role('button',name='Открыть меню кампании',exact=True).click()
    page.get_by_text('Что означают значки на карте',exact=True).click()
    pixels=page.locator('[data-map-symbol]').evaluate_all('''(nodes)=>nodes.map(c=>{const d=c.getContext('2d').getImageData(0,0,128,128).data;let lo=128,hi=0;for(let i=3;i<d.length;i+=4)if(d[i]){const x=((i-3)/4)%128;lo=Math.min(lo,x);hi=Math.max(hi,x)}return {image:c.toDataURL(),width:hi-lo+1}})''')
    assert len(pixels)==3 and len({p['image'] for p in pixels})==3
    assert pixels[0]['width']<pixels[1]['width']<pixels[2]['width'],[p['width'] for p in pixels]
    assert not errors,errors
    print(f'PASS phone HUD {bt.name}: seven sizes/inset60, real order, bounded orders, fixed close, desktop corner, catalogue scale and three distinct sprite footprints',flush=True)
    ctx.close();browser.close()


if __name__=='__main__':harness.run=run;harness.main()
