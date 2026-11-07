"""Discover real mechanics, follow help to actions, and see low-quality landscape."""
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game


def run(bt,width,url,out):
    if width!=390:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm')
    for title in ['Пропустить пролог','Пропустить обучение']:page.get_by_role('button',name=title,exact=True).click()
    state=lambda:page.request.get(url+'/api/campaigns/latest').json()['state']
    revision=state()['revision']
    for topic,button,view in [
        ('Строительство, крепости и порты','Открыть строительство','Строительство'),
        ('Еда, обозы и торговля','Открыть торговлю и запасы','Торговля'),
        ('Договоры и вассалы','Открыть дипломатию','Договоры'),
        ('Люди, законы и местное управление','Открыть назначения','Назначения'),
        ('Мастера и знания','Открыть мастеров и знания','Мастера и знания'),
        ('Двор, интриги и наследование','Открыть дворы и связи','Дворы и связи'),
    ]:
        if view=='Мастера и знания':page.set_viewport_size({'width':1280,'height':800})
        page.get_by_role('button',name='Советник',exact=True).click()
        page.get_by_text(topic,exact=True).click();page.get_by_role('button',name=button,exact=True).click()
        title=page.locator('.window-heading h2').inner_text()
        expect(page.get_by_role('heading',name=title,exact=True)).to_have_count(1)
        expect(page.get_by_role('tab',name=view,exact=False)).to_have_attribute('aria-selected','true')
        expect(page.locator('.government-body .card').first).to_be_visible()
        if view=='Мастера и знания':
            page.locator('.government-body').evaluate('(e)=>e.scrollTop=e.scrollHeight')
            page.get_by_role('button',name='Советник: что делать?',exact=True).click()
            expect(page.get_by_role('region',name='Помощь по текущему делу',exact=True)).to_be_in_viewport(ratio=.9)
            page.get_by_role('button',name='Советник: что делать?',exact=True).click()
        page.get_by_role('button',name='Закрыть окно · к карте',exact=True).click()
        if view=='Мастера и знания':page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Советник',exact=True).click()
    page.get_by_text('Осады и полевые бои',exact=True).click()
    expect(page.get_by_role('button',name='Открыть осадные действия',exact=True)).to_have_count(0)
    expect(page.get_by_text('Сейчас осад нет.',exact=False)).to_be_visible()
    page.get_by_text('Армия и гарнизон',exact=True).click()
    page.get_by_role('button',name='Открыть набор',exact=True).click()
    expect(page.get_by_role('heading',name='Войско',exact=True)).to_have_count(1)
    expect(page.get_by_label('Число набираемых людей',exact=True)).to_be_visible()
    assert state()['revision']==revision,'Reading help or navigating must not issue commands'
    page.get_by_role('button',name='Закрыть окно · к карте',exact=True).click()
    search=page.get_by_label('Поиск поселения',exact=True);search.fill('Сёгют');page.locator('[data-search-place=sogut]').click()
    page.get_by_role('tab',name='Набор',exact=True).click()
    page.get_by_text('Куда попадут новобранцы?',exact=True).click()
    expect(page.get_by_text('После обучения люди появятся в гарнизоне этого города.',exact=False)).to_be_visible()
    page.get_by_label('Число новобранцев на карте',exact=True).fill('5')
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as reply:
        page.get_by_role('button',name='Начать набор в городе',exact=True).click()
    assert reply.value.status==200
    page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    assert page.locator('.canvas-world').get_attribute('data-quality')=='low'
    page.wait_for_function('''()=>{const c=document.querySelector('.canvas-world>canvas');if(!c?.width)return false;const p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;const b=c.getBoundingClientRect(),ratio=c.width/b.width,boxes=[...document.querySelectorAll('.map-hit-layer button')].map(e=>e.getBoundingClientRect());let n=0;for(let i=0;i<p.length;i+=4){if(!(p[i]<130&&p[i+1]>p[i]*1.08&&p[i+1]>p[i+2]*1.1))continue;const x=(i/4%c.width)/ratio+b.x,y=Math.floor(i/4/c.width)/ratio+b.y;if(!boxes.some(r=>x>r.left-16&&x<r.right+16&&y>r.top-24&&y<r.bottom+16))n++}return n>70}''')
    page.screenshot(path=str(out/f'{bt.name}-learning-landscape.png'))
    assert not errors,errors
    print(f'PASS learning {bt.name}: help to real recruitment, no navigation commands, contextual explanation, persisted order, low-quality forest pixels',flush=True)
    ctx.close();browser.close()


if __name__=='__main__':harness.run=run;harness.main()
