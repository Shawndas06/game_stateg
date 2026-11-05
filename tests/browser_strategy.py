"""Map campaign: real commands, completions, qualities and persisted context."""
import os,re
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game,resume_menu,nav


def run(bt,width,url,out):
    height=390 if width==844 else 740 if width==320 else 844
    browser=bt.launch();ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<1000,has_touch=True)
    page=ctx.new_page();errors=[];commands=[];page.on('pageerror',lambda e:errors.append(str(e)+'\n'+e.stack))
    page.on('request',lambda r:commands.append(r.post_data_json) if r.method=='POST' and r.url.endswith('/commands') else None)
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def click(name):page.get_by_role('button',name=name,exact=True).click()
    def act(name):
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as response:click(name)
        assert response.value.status==200,response.value.text()
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        return response.value.json()['state']
    def choose(title,ident):
        page.get_by_label('Поиск поселения',exact=True).fill(title);page.locator(f'[data-search-place="{ident}"]').click()
        expect(page.locator('.campaign-inspector')).to_be_visible()
    def close():click('Закрыть карточку')
    def time(days):
        click('Выбрать ожидание');return act('Один день или до известия' if days==1 else 'До значимого события · не более сезона')
    page.goto(url);expect(page.locator('.campaign-main-menu')).to_be_visible();expect(page.get_by_role('button',name='Продолжить',exact=True)).to_be_disabled()
    new_game(page,'realm');click('Пропустить пролог');click('Пропустить обучение')
    expect(page.locator('.canvas-world canvas')).to_be_visible();expect(page.get_by_test_id('place-sogut')).to_be_visible()
    assert not page.locator('.campaign-inspector').is_visible()
    # Search belongs to the compact bar, not a second overlay on the map.
    assert page.locator('.header .map-search').count()==1
    assert page.locator('.canvas-world .map-search').count()==0
    bar=page.locator('.header').bounding_box();search=page.get_by_label('Поиск поселения',exact=True).bounding_box()
    assert bar['y']==0 and bar['height']<=49,(bar,search)
    assert search['y']>=bar['y'] and search['y']+search['height']<=bar['y']+bar['height']
    assert search['height']>=48 and search['width']>=100
    assert page.locator('.canvas-world').bounding_box()['height']==height
    before=state();page.reload();resume_menu(page);expect(page.locator('.canvas-world')).to_be_visible();assert state()['revision']==before['revision']
    page.screenshot(path=str(out/f'{bt.name}-{width}-first-map.png'))
    act(re.compile('^Совет: Первый совет'));gold=state()['gold']
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as response:page.locator('[data-choice=stewardship]').click()
    assert response.value.status==200 and response.value.json()['state']['gold']==gold-25
    choose('Сёгют','sogut');page.get_by_role('tab',name='Набор',exact=True).click()
    field=page.get_by_label('Число новобранцев на карте',exact=True);field.fill('');expect(page.get_by_role('button',name='Начать набор в городе',exact=True)).to_be_disabled()
    field.fill('3');gold=state()['gold'];guards=sum(state()['provinces']['sogut']['garrison'].values());n=act('Начать набор в городе');assert n['gold']==gold-6
    page.get_by_role('tab',name='Стройка',exact=True).click();gold=n['gold'];n=act('Зернохранилище · 60 монет');assert n['gold']==gold-60
    # A map HUD may remain behind the sheet, but must not paint over its work cards.
    assert page.evaluate('''() => { const search=document.querySelector('.map-search'), panel=document.querySelector('.campaign-inspector');
      const a=search.getBoundingClientRect(), b=panel.getBoundingClientRect();
      const x=Math.max(a.left,b.left)+2,y=Math.max(a.top,b.top)+2;
      return x>=Math.min(a.right,b.right)||y>=Math.min(a.bottom,b.bottom)||!!document.elementFromPoint(x,y)?.closest('.campaign-inspector'); }''')
    page.screenshot(path=str(out/f'{bt.name}-{width}-construction.png'));close()
    # Settings are presentation only; each level must retain the same controls.
    for quality in ['medium','high','low']:
        revision=state()['revision'];click('Открыть меню кампании');page.get_by_label('Качество карты',exact=True).select_option(quality);click('Продолжить')
        expect(page.locator('.canvas-world')).to_have_attribute('data-quality',quality);assert state()['revision']==revision
    requests=len(commands);page.locator('[data-map-army="ottoman-1"]').click();assert len(commands)==requests
    field=page.get_by_label('Казна приказа на карте',exact=True);field.fill('');expect(page.get_by_role('button',name='Проверить приказ на карте',exact=True)).to_be_disabled();field.fill('5')
    page.get_by_label('Задача на карте',exact=True).select_option('conquer');page.get_by_label('Разрешить штурм',exact=True).check();page.get_by_label('Задача на карте',exact=True).select_option('march')
    click('Указать цель на карте');choose('Доманич','domanic');expect(page.get_by_test_id('map-order-target')).to_contain_text('Доманич')
    gold=state()['gold'];n=act('Проверить приказ на карте');assert n['gold']==gold
    n=act('Отправить проверенный приказ');assert n['gold']==gold-5 and not n['armies']['ottoman-1']['mission']['allow_assault']
    page.reload();resume_menu(page);n=time(1);assert n['day']==1 and n['armies']['ottoman-1']['travel']
    for _ in range(20):
        if n['day']>=14:break
        n=time(1)
    assert n['armies']['ottoman-1']['location']=='domanic' and not n['provinces']['sogut']['training']
    choose('Доманич','domanic');click('Выбрать отряд: Осман · 80');n=act('Отозвать к столице')
    for _ in range(30):
        if n['armies']['ottoman-1']['location']=='sogut' and not n['armies']['ottoman-1']['travel']:break
        n=time(1)
    assert sum(n['provinces']['sogut']['garrison'].values())==guards+3
    for _ in range(30):
        if not n['provinces']['sogut']['construction']:break
        n=time(90)
    assert 'granary' in n['provinces']['sogut']['buildings']
    choose('Кютахья','kutahya');page.get_by_role('tab',name='Переговоры',exact=True).click();page.get_by_label('Договор на карте',exact=True).select_option('trade');page.get_by_label('Платёж посольству',exact=True).fill('20')
    gold=n['gold'];n=act('Направить посольство');assert n['gold']==gold-20 and any(o['b']=='germiyan' and o['status']=='travelling' for o in n['statecraft']['offers'])
    close();before=state();page.reload();resume_menu(page);assert state()['revision']==before['revision'];expect(page.get_by_test_id('place-kutahya')).to_be_visible()
    # No horizontal page overflow or unreadable narrow action fields.
    choose('Сёгют','sogut');page.get_by_role('tab',name='Набор',exact=True).click()
    assert page.get_by_label('Число новобранцев на карте',exact=True).bounding_box()['width']>=150
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(out/f'{bt.name}-{width}-persisted-map.png'))
    assert not errors,errors
    print(f'PASS strategy {bt.name}{width}: menu, clean canvas, three qualities, city training/building, army draft/march/return, actual completions, diplomacy, reload',flush=True)
    ctx.close();browser.close()

if __name__=='__main__':
    os.environ['RULER_UX_SCREENSHOTS']=os.environ.get('STRATEGY_SCREENSHOTS','/tmp/strategy-browser-evidence')
    harness.run=run;harness.main()
