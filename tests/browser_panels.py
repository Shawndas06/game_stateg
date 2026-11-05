"""Physical hit/scroll/resize checks for the campaign's constrained card layout."""
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game,nav


def run(bt,width,url,out):
    if width!=390:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm')
    for name in ['Пропустить пролог','Пропустить обучение']:page.get_by_role('button',name=name,exact=True).click()
    search=page.get_by_label('Поиск поселения',exact=True);panel=page.locator('.campaign-inspector');body=page.locator('.inspector-body')
    close=page.get_by_role('button',name='Закрыть карточку',exact=True)
    def choose(text,ident):
        search.fill(text);page.locator(f'[data-search-place="{ident}"]').click();expect(panel).to_be_visible()
    def reachable(el):
        details=el.evaluate('(e)=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {ok:r.width>=48&&r.height>=48&&e.contains(hit),rect:r.toJSON(),hit:hit?.outerHTML.slice(0,250)}}')
        if not details['ok']:page.screenshot(path=str(out/f'{bt.name}-panel-hit-failure.png'))
        assert details['ok'],details
    def geometry():
        a=panel.bounding_box();b=body.bounding_box();h=page.locator('.inspector-heading').bounding_box();c=close.bounding_box()
        assert a['y']>=page.locator('.header').bounding_box()['height'] and a['y']+a['height']<=page.viewport_size['height']
        assert h['y']+h['height']<=b['y']+1 and c['y']+c['height']<=b['y']+1
        for el in [page.get_by_role('button',name='Передать ход времени',exact=True),page.get_by_role('button',name='Правление',exact=True)]:
            r=el.bounding_box()
            assert r['x']+r['width']<=a['x'] or r['x']>=a['x']+a['width'] or r['y']>=a['y']+a['height'] or r['y']+r['height']<=a['y'],(a,r)
            reachable(el)
        reachable(close)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth&&scrollY===0')
    for w,h in [(320,740),(390,844),(844,390),(568,320),(390,420),(1280,800)]:
        page.set_viewport_size({'width':w,'height':h})
        page.evaluate("document.documentElement.style.setProperty('--tg-top','25px');document.documentElement.style.setProperty('--tg-bottom','12px')")
        choose('Сёгют','sogut');geometry()
        if w>h:page.get_by_test_id('place-sogut').click(trial=True)
        bar=page.locator('.header').bounding_box()
        if bar['height']>74:page.screenshot(path=str(out/f'{bt.name}-bar-height-failure.png'))
        assert bar['height']<=74,(w,h,bar,page.locator('.header .brand').bounding_box(),search.bounding_box())
        page.get_by_role('tab',name='Стройка',exact=True).click();geometry()
        assert page.locator('.inspector-body .map-facts').count()==0
        page.screenshot(path=str(out/f'{bt.name}-{w}x{h}-construction.png'))
        before=close.bounding_box();close.hover();assert close.bounding_box()==before
        body.evaluate('(e)=>e.scrollTop=e.scrollHeight')
        assert body.evaluate('(e)=>e.scrollTop>0')
        geometry();assert close.bounding_box()==before
        last=page.get_by_role('button',name='Подготовить службы для крепости',exact=True);last.scroll_into_view_if_needed();reachable(last)
        page.get_by_role('tab',name='Набор',exact=True).click()
        assert body.evaluate('(e)=>e.scrollTop')==0
        troop=page.get_by_label('Род войск на карте',exact=True);assert troop.bounding_box()['height']>=48,troop.evaluate('(e)=>({rect:e.getBoundingClientRect().toJSON(),min:getComputedStyle(e).minHeight,height:getComputedStyle(e).height,appearance:getComputedStyle(e).appearance})')
        field=page.get_by_label('Число новобранцев на карте',exact=True);field.fill('')
        expect(page.get_by_role('button',name='Начать набор в городе',exact=True)).to_be_disabled();geometry()
        page.screenshot(path=str(out/f'{bt.name}-{w}x{h}-recruitment.png'))
        choose('Константинополь','constantinople');geometry()
        close.tap();expect(panel).to_be_hidden()
    page.set_viewport_size({'width':390,'height':844});choose('Сёгют','sogut')
    page.get_by_role('tab',name='Стройка',exact=True).click()
    page.add_style_tag(content='.inspector-body p,.inspector-body label,.inspector-body button,.inspector-body select{font-size:20px!important}')
    body.evaluate('(e)=>e.scrollTop=e.scrollHeight');geometry()
    close.tap();expect(panel).to_be_hidden()
    choose('Сёгют','sogut');nav(page,'Государство');expect(panel).to_be_hidden()
    page.get_by_role('button',name='Закрыть окно · к карте',exact=True).click();expect(panel).to_be_visible();geometry()
    close.tap();expect(panel).to_be_hidden()
    assert not errors,errors
    print(f'PASS adaptive panels {bt.name}: six sizes and enlarged text, safe areas, stable close, separate scroll, no footer overlap, tab reset, input, search, actual close tap',flush=True)
    ctx.close();browser.close()


if __name__=='__main__':harness.run=run;harness.main()
