"""Actual UI assembly: preview, escrow, courier, formation, march and return."""
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game


def run(bt,width,url,out):
    if width not in [390,320]:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':844 if width==390 else 320,'height':390 if width==390 else 740},is_mobile=True,has_touch=True);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def click(name):page.get_by_role('button',name=name,exact=True).click()
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def act(name):
        with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/commands')) as response:click(name)
        assert response.value.status==200,response.value.text();expect(page.locator('main[aria-busy=true]')).to_have_count(0);return response.value.json()['state']
    page.goto(url);new_game(page,'realm');click('Пропустить пролог');click('Пропустить обучение');page.locator('[data-map-army="ottoman-1"]').click();click('Подготовить поход · собрать и распределить силы')
    troop=page.request.get(url+'/api/catalog').json()['troops']['militia']['name']
    page.get_by_label('Караджахисар · гарнизон 30',exact=True).check();page.get_by_label(troop+' из Караджахисар',exact=True).fill('10');page.get_by_label('Казна нового отряда karacahisar',exact=True).fill('7');page.get_by_label('Дополнительные пайки ottoman-1',exact=True).fill('100')
    gold=state()['gold'];before=state()['revision'];n=act('Проверить весь сбор');assert n['gold']==gold and n['revision']==before+1 and len(n['statecraft']['gather_draft']['rows'])==2
    field=page.get_by_label('Казна сбора ottoman-1',exact=True);field.fill('');expect(page.get_by_role('button',name='Отправить распоряжения о сборе',exact=True)).to_be_disabled();field.fill('5')
    page.screenshot(path=str(out/f'{bt.name}-{width}-gather-review.png'))
    n=act('Отправить распоряжения о сборе');assert n['gold']==gold-17 and len(n['armies'])==1
    assert any(e.get('formation',{}).get('commander')=='konur' for e in n['pending_edicts'])
    expect(page.get_by_role('heading',name='Распоряжения о сборе отправлены',exact=True)).to_be_visible()
    click('Закрыть карточку')
    for _ in range(30):
        n=act('Передать ход времени')
        arrived=next((a for a in n['armies'].values() if a['commander']=='konur'),None)
        if arrived and arrived['location']=='sogut' and not arrived['travel']:break
    assert arrived and arrived['location']=='sogut' and sum(arrived['troops'].values())==10
    assert all(c['origin']=='karacahisar' for c in arrived['cohorts'])
    assert not errors,errors
    print(f'PASS gather {bt.name}{width}: two-source preview/empty field, no teleport, escrow, courier/formation, physical meeting and origin',flush=True)
    ctx.close();browser.close()

if __name__=='__main__':harness.run=run;harness.main()
