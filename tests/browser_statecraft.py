"""New office through real UI/API/storage on a disposable server, both engines."""
import os
from pathlib import Path
from playwright.sync_api import expect
import browser_ruler_ux as harness


def run(browser_type,width,url,out):
    browser=browser_type.launch();context=browser.new_context(viewport={'width':width,'height':740 if width==320 else 844},is_mobile=width<800,has_touch=width<800)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def click(name):page.get_by_role('button',name=name,exact=True).click()
    def action(name):
        with page.expect_response(lambda r:r.url.endswith('/commands') and r.request.method=='POST') as response:click(name)
        assert response.value.status==200,response.value.json()
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        return response.value.json()['state']
    def section(name):page.get_by_role('tab',name=name,exact=True).click()
    page.goto(url);page.get_by_role('button',name='Стать правителем',exact=False).click();click('Пропустить пролог');click('Держава')
    before=state();n=action('Включить живое государство');assert n['gold']==before['gold'] and n['day']==before['day']
    click('Двор');page.evaluate('scrollTo(0,0)')
    start=page.get_by_role('button',name='Начать обучение',exact=True);box=start.bounding_box();nav=page.locator('.bottom-nav').bounding_box()
    assert box['y']>=0 and box['y']+box['height']<=nav['y'],'New office must not push first learning action below navigation'
    assert start.evaluate('(el)=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}')
    page.screenshot(path=str(out/f'{browser_type.name}-{width}-living-welcome.png'))
    click('Пропустить обучение')
    page.get_by_role('button',name='Поручения и донесения',exact=False).click()
    expect(page.get_by_role('heading',name='Дела правления',exact=True)).to_be_visible()
    section('Договоры');page.get_by_label('Государство для переговоров').select_option('germiyan')
    page.get_by_label('Платёж при согласии').fill('')
    expect(page.get_by_role('button',name='Отправить условия',exact=True)).to_be_disabled()
    page.get_by_label('Платёж при согласии').fill('20');n=action('Отправить условия')
    assert n['gold']==before['gold']-20 and n['statecraft']['offers'][-1]['status']=='travelling'
    page.reload();page.get_by_role('button',name='Поручения и донесения',exact=False).click();section('Мастера и знания')
    master=state()['statecraft']['masters'][0];n=action('Нанять: '+master['name'])
    assert n['gold']==before['gold']-20-master['fee']
    assert next(m for m in n['statecraft']['masters'] if m['id']==master['id'])['travelling']
    # Preview is a UI command; only confirmation allocates the campaign funds.
    click('Войско');page.get_by_label('Задача армии',exact=True).select_option('cover');page.get_by_label('Цель поручения',exact=True).select_option('sogut')
    garrison=sum(state()['provinces']['sogut']['garrison'].values());page.get_by_label('Включить подкрепление из местного гарнизона в ведомость').check()
    page.get_by_label('Подкрепление из гарнизона',exact=True).fill('');expect(page.get_by_role('button',name='Проверить ведомость похода',exact=True)).to_be_disabled()
    page.get_by_label('Подкрепление из гарнизона',exact=True).fill('10')
    gold=state()['gold'];n=action('Проверить ведомость похода');assert n['gold']==gold and n['statecraft']['draft']
    click('Открыть ведомость и подтвердить');n=action('Подтвердить проверенное поручение')
    assert n['gold']==gold-20 and n['armies']['ottoman-1']['mission']['purpose']=='cover'
    assert sum(n['provinces']['sogut']['garrison'].values())==garrison-10
    page.reload();page.get_by_role('button',name='Поручения и донесения',exact=False).click()
    for title in ['Поручения','Договоры','Мастера и знания','Полномочия','Дворы и связи']:
        section(title);expect(page.get_by_role('tab',name=title,exact=True)).to_have_css('color','rgb(255, 248, 231)');expect(page.get_by_role('tab',name=title,exact=True)).to_have_css('background-color','rgb(33, 78, 61)');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),title
        page.screenshot(path=str(out/f'{browser_type.name}-{width}-{title}.png'),full_page=True)
    section('Полномочия');page.get_by_label('Лимит управителя за 30 дней').fill('');expect(page.get_by_role('button',name='Утвердить полномочия',exact=True)).to_be_disabled()
    page.get_by_label('Лимит управителя за 30 дней').fill('10');n=action('Утвердить полномочия');assert n['statecraft']['policies']['sogut']['budget']==10
    assert not errors,errors
    print(f'PASS statecraft {browser_type.name} {width}: opt-in, embassy escrow, hire/travel, checked campaign, confirmation, reload, empty inputs, all office views',flush=True)
    context.close();browser.close()

if __name__=='__main__':
    os.environ['RULER_UX_SCREENSHOTS']=os.environ.get('STATECRAFT_SCREENSHOTS','/tmp/statecraft-browser-evidence')
    harness.run=run;harness.main()
