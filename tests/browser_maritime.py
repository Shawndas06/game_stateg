"""Real map selection and maritime discovery; no manufactured campaign state."""
import os
from playwright.sync_api import expect
from browser_navigation import new_game,nav
import browser_ruler_ux as harness

def run(bt,width,url,out):
    browser=bt.launch();context=browser.new_context(viewport={'width':width,'height':844 if width<800 else 740},is_mobile=width<800,has_touch=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm');page.get_by_role('button',name='Пропустить пролог',exact=True).click();page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    before=page.request.get(url+'/api/campaigns/latest').json()['state']['revision']
    for name,pid,port in [('Константинополь','constantinople',True),('Галата','galata',True),('Хрисополь','chrysopolis',True),('Халкидон','chalcedon',True),('Киос','cius',True),('Аполлония','apollonia',False),('Эгирдир','egirdir',False),('Афины','athens',True)]:
        page.get_by_label('Поиск поселения',exact=True).fill(name);page.locator(f'[data-search-place="{pid}"]').click()
        expect(page.locator('.campaign-inspector h2')).to_have_text(name)
        expect(page.get_by_test_id('place-'+pid)).to_be_visible()
        assert page.locator('.port-summary').count()==int(port)
        if pid=='athens':expect(page.locator('.port-summary')).to_contain_text('Пирей')
        if pid in ['constantinople','chrysopolis','apollonia','egirdir']:page.screenshot(path=str(out/f'{bt.name}-{width}-{pid}.png'))
        page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    assert page.request.get(url+'/api/campaigns/latest').json()['state']['revision']==before
    page.get_by_label('Поиск поселения',exact=True).fill('Сёгют');page.locator('[data-search-place="sogut"]').click()
    page.get_by_role('tab',name='Стройка',exact=True).click()
    port_work=page.locator('[data-building="harbor"]')
    expect(port_work).to_contain_text('Здесь нет исторической морской или речной пристани')
    expect(port_work.get_by_role('button')).to_be_disabled()
    page.screenshot(path=str(out/f'{bt.name}-{width}-port-requirements.png'))
    page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    nav(page,'Держава');page.get_by_role('button',name='Мастера, учреждения и знания',exact=True).click()
    expect(page.get_by_role('heading',name='Морское дело',exact=True)).to_be_visible()
    expect(page.get_by_role('heading',name='Михаил, мастер причалов и перевозок',exact=True)).to_be_visible()
    expect(page.get_by_text('Судоходство, Устройство портов',exact=False)).to_be_visible()
    assert not errors,errors
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    print(f'PASS maritime {bt.name}{width}: historic shores, port access, search, marine teacher, no state changes',flush=True)
    context.close();browser.close()

if __name__=='__main__':
    os.environ['RULER_UX_SCREENSHOTS']='/tmp/maritime-browser-evidence';harness.run=run;harness.main()
