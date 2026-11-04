"""Map-first campaign: actual UI -> API -> storage -> execution -> reload."""
import os,re
from playwright.sync_api import expect
import browser_ruler_ux as harness


def run(bt,width,url,out):
    browser=bt.launch();ctx=browser.new_context(viewport={'width':width,'height':740 if width==320 else 844},is_mobile=width<800,has_touch=width<800)
    page=ctx.new_page();errors=[];commands=[];page.on('pageerror',lambda e:errors.append(str(e)+'\n'+e.stack))
    page.on('request',lambda r:commands.append(r.post_data_json) if r.method=='POST' and r.url.endswith('/commands') else None)
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def click(name):page.get_by_role('button',name=name,exact=True).click()
    def act(name):
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as response:click(name)
        assert response.value.status==200,response.value.text()
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        return response.value.json()['state']
    def inspect():
        button=page.get_by_role('button',name='Открыть действия',exact=True)
        if button.is_visible():button.click()
    def choose(title,ident):
        search=page.get_by_label('Поиск поселения',exact=True);search.fill(title)
        page.locator(f'[data-search-place="{ident}"]').click()
        expect(page.get_by_test_id('place-'+ident)).to_have_class(re.compile('is-selected'))
    def time(days):
        click('Передать ход времени')
        return act('Один день или до известия' if days==1 else 'До значимого события · не более сезона')
    page.goto(url);page.get_by_role('button',name='Стать правителем',exact=False).click();click('Пропустить пролог')
    expect(page.get_by_role('button',name='Начать обучение',exact=True)).to_be_visible();click('Пропустить обучение')
    expect(page.get_by_test_id('campaign-command-map')).to_be_visible()
    page.evaluate('scrollTo(0,0)');box=page.locator('.illustrated-map').bounding_box();nav=page.locator('.bottom-nav').bounding_box()
    assert min(box['y']+box['height'],nav['y'])-box['y']>=140,('Map must be visible on first strategy screen',box,nav)
    before=state();page.reload();expect(page.get_by_test_id('campaign-command-map')).to_be_visible();assert state()['revision']==before['revision']
    page.screenshot(path=str(out/f'{bt.name}-{width}-first-map.png'))
    label=page.locator('[data-place=sogut] .place-name')
    assert label.evaluate('(el)=>{const r=el.getBoundingClientRect();const n=document.querySelector(".bottom-nav").getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return r.y>=0&&r.bottom<=n.top&&hit?.closest("[data-place]")?.getAttribute("data-place")==="sogut"}'),'Capital label must be visible and tappable above navigation on first map'

    if bt.name=='chromium' and width==390:
        # Native touch sequence starts on a new interactive army flag. Both
        # fingers must still reach the shared map gesture handler.
        page.locator('.illustrated-map').scroll_into_view_if_needed();cdp=ctx.new_cdp_session(page)
        def zoom():return float(re.search(r'scale\(([^)]+)\)',page.locator('[data-coastline]').evaluate('(el)=>el.parentElement.getAttribute("transform")')).group(1))
        flag=page.locator('[data-map-army="ottoman-1"]').bounding_box();x=flag['x']+flag['width']/2;y=flag['y']+flag['height']/2;initial_zoom=zoom();revision=state()['revision']
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1},{'x':x+65,'y':y,'id':2}]})
        for delta in [10,20,30]:cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x-delta,'y':y,'id':1},{'x':x+65+delta,'y':y,'id':2}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        page.evaluate('()=>new Promise(ok=>requestAnimationFrame(()=>requestAnimationFrame(ok)))')
        assert zoom()>initial_zoom*1.4,'Pinch beginning on an army flag must zoom instead of panning'
        assert state()['revision']==revision
        page.get_by_role('button',name='Моя столица',exact=False).click()
    n=act(re.compile('^Совет: Первый совет'));assert n['day']==0
    gold=n['gold'];n=act('На местные запасы и учёт · 25 монет') if page.get_by_role('button',name='На местные запасы и учёт · 25 монет',exact=True).count() else None
    if n is None:
        with page.expect_response(lambda r:r.url.endswith('/commands') and r.request.method=='POST') as response:page.locator('[data-choice=stewardship]').click()
        assert response.value.status==200;n=response.value.json()['state']
    assert n['gold']==gold-25
    click('Держава');n=act('Включить живое государство');assert n['statecraft']
    click('Атлас');inspect();page.get_by_role('tab',name='Набор',exact=True).click()
    field=page.get_by_label('Число новобранцев на карте',exact=True);field.fill('');expect(page.get_by_role('button',name='Начать набор в городе',exact=True)).to_be_disabled()
    field.fill('3');gold=state()['gold'];garrison=sum(state()['provinces']['sogut']['garrison'].values());n=act('Начать набор в городе')
    assert n['gold']==gold-6 and n['provinces']['sogut']['training'][0]['count']==3
    page.get_by_role('tab',name='Стройка',exact=True).click();gold=n['gold'];n=act('Зернохранилище · 60 монет')
    assert n['gold']==gold-60 and n['provinces']['sogut']['construction']['building']=='granary'
    page.locator('.illustrated-map').scroll_into_view_if_needed();requests=len(commands)
    page.locator('[data-map-army="ottoman-1"]').click()
    expect(page.locator('[data-map-army="ottoman-1"]')).to_have_attribute('aria-pressed','true')
    assert len(commands)==requests,'Selecting an army must not issue orders'
    inspect();page.get_by_label('Казна приказа на карте',exact=True).fill('');expect(page.get_by_role('button',name='Проверить приказ на карте',exact=True)).to_be_disabled()
    page.get_by_label('Задача на карте',exact=True).select_option('conquer');page.get_by_label('Разрешить штурм',exact=True).check()
    page.get_by_label('Задача на карте',exact=True).select_option('march')
    page.get_by_label('Казна приказа на карте',exact=True).fill('5');click('Указать цель на карте');choose('Доманич','domanic');inspect()
    expect(page.get_by_test_id('map-order-target')).to_contain_text('Доманич')
    gold=state()['gold'];n=act('Проверить приказ на карте');assert n['gold']==gold and n['armies']['ottoman-1']['mission'] is None
    page.screenshot(path=str(out/f'{bt.name}-{width}-order-review.png'),full_page=True)
    n=act('Отправить проверенный приказ');assert n['gold']==gold-5 and n['armies']['ottoman-1']['location']=='sogut'
    assert n['armies']['ottoman-1']['mission']['purpose']=='march' and not n['armies']['ottoman-1']['mission']['allow_assault']
    page.reload();expect(page.get_by_test_id('campaign-command-map')).to_be_visible()
    n=time(1);assert n['day']==1 and n['armies']['ottoman-1']['travel']
    for _ in range(20):
        n=time(1)
        if n['day']>=14:break
    assert not n['provinces']['sogut']['training']
    # The ruler is away: a dated garrison report is not a live counter. Return
    # physically before verifying the new men in the capital.
    assert n['armies']['ottoman-1']['location']=='domanic' and n['armies']['ottoman-1']['mission']['status']=='completed'
    page.locator('.campaign-armies button').first.click();inspect();n=act('Отозвать к столице')
    for _ in range(30):
        if n['armies']['ottoman-1']['location']=='sogut' and not n['armies']['ottoman-1']['travel']:break
        n=time(1)
    assert sum(n['provinces']['sogut']['garrison'].values())==garrison+3
    for _ in range(30):
        if not n['provinces']['sogut']['construction']:break
        n=time(90)
    assert 'granary' in n['provinces']['sogut']['buildings']
    choose('Кютахья','kutahya');inspect();page.get_by_role('tab',name='Переговоры',exact=True).click()
    page.get_by_label('Договор на карте',exact=True).select_option('trade');page.get_by_label('Платёж посольству',exact=True).fill('20')
    gold=state()['gold'];n=act('Направить посольство');assert n['gold']==gold-20
    assert any(o['b']=='germiyan' and o['kind']=='trade' and o['status']=='travelling' for o in n['statecraft']['offers'])
    page.reload();expect(page.get_by_test_id('campaign-command-map')).to_be_visible();assert state()['gold']==n['gold']
    page.screenshot(path=str(out/f'{bt.name}-{width}-persisted-map.png'),full_page=True)
    choose('Лиссабон','lisbon');inspect();page.get_by_role('tab',name='Переговоры',exact=True).click()
    expect(page.get_by_role('button',name='Направить посольство',exact=True)).to_be_disabled()
    before_revision=state()['revision'];click('Все договоры, вассалы и переписка')
    assert page.get_by_label('Государство для переговоров',exact=True).input_value() in state()['statecraft']['contacts']
    assert state()['revision']==before_revision
    if width==320:
        response=page.request.post(url+'/api/campaigns',data={'scenario':'ruler_v1','campaign_mode':'chapter'});assert response.status==201,response.text()
        chapter=response.json();page.reload();click('Пропустить обучение')
        expect(page.get_by_test_id('campaign-command-map')).to_have_count(0)
        click('? Как играть');click('Переключить на карту кампании')
        expect(page.get_by_test_id('campaign-command-map')).to_be_visible();page.reload()
        expect(page.get_by_test_id('campaign-command-map')).to_be_visible();assert state()['revision']==chapter['state']['revision']
        click('? Как играть');click('Переключить на отдельные разделы');page.reload()
        expect(page.get_by_test_id('campaign-command-map')).to_have_count(0)
        assert state()['revision']==chapter['state']['revision']
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors,errors
    print(f'PASS strategy {bt.name}{width}: default/reload, council, city training/building, army flag/target/confirmation, physical march, actual completions and diplomacy',flush=True)
    ctx.close();browser.close()

if __name__=='__main__':
    os.environ['RULER_UX_SCREENSHOTS']=os.environ.get('STRATEGY_SCREENSHOTS','/tmp/strategy-browser-evidence')
    harness.run=run;harness.main()
