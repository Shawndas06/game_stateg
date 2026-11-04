"""First-play teaching and input behavior against a disposable real server.

PYTHONPATH=. .venv/bin/python tests/browser_ruler_ux.py
"""
from pathlib import Path
import os
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from playwright.sync_api import expect, sync_playwright


def run(browser_type, width, url, out):
    browser=browser_type.launch()
    context=browser.new_context(viewport={'width':width,'height':844},is_mobile=width<800,has_touch=width<800)
    page=context.new_page();errors=[];commands=[];external_fonts=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:commands.append(r.post_data_json) if '/commands' in r.url and r.method=='POST' else None)
    page.on('request',lambda r:external_fonts.append(r.url) if 'fonts.googleapis.com' in r.url or 'fonts.gstatic.com' in r.url else None)
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def nav(name):
        page.get_by_role('button',name=name,exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    def act(callback):
        with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:callback()
        assert response.value.status==200,response.value.json()
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        return response.value.json()['state']
    def stage(name):expect(page.locator('[data-guide-stage]')).to_have_attribute('data-guide-stage',name)
    def matrix(label, buttons, invalid, valid):
        field=page.get_by_label(label,exact=True)
        for value in invalid:
            count=len(commands);field.fill(value)
            expect(field).to_have_value(value)
            expect(field).to_have_attribute('aria-invalid','true')
            for name in buttons:
                button=page.get_by_role('button',name=name,exact=True)
                expect(button).to_be_disabled();button.evaluate('(el)=>el.click()')
            assert len(commands)==count,'Invalid input submitted a command'
        for value in valid:
            field.fill(value);expect(field).to_have_attribute('aria-invalid','false')
            for name in buttons:expect(page.get_by_role('button',name=name,exact=True)).to_be_enabled()
    page.goto(url)
    expect(page.get_by_role('button',name='Стать правителем',exact=False)).to_be_visible()
    for family in ['manrope','prata']:
        response=page.request.get(url+f'/media/fonts/{family}-cyrillic.woff2')
        assert response.status==200 and response.body()[:4]==b'wOF2','Font route must return actual WOFF2 bytes'
    loaded=page.evaluate('async()=>{await Promise.all([document.fonts.load("20px Prata","Осман"),document.fonts.load("14px Manrope","Осман")]);await document.fonts.ready;return [...document.fonts].filter(f=>f.status==="loaded").map(f=>f.family.replaceAll("\\\"",""))}')
    assert 'Manrope' in loaded and 'Prata' in loaded,loaded
    page.get_by_role('button',name='Стать правителем',exact=False).click();page.get_by_role('button',name='Пропустить пролог',exact=True).click();stage('welcome')
    expect(page.get_by_role('heading',name=state()['chapter']['name'],exact=True)).to_be_visible()
    revision=state()['revision']
    page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    page.reload();expect(page.locator('[data-guide-stage]')).to_have_count(0)
    page.get_by_role('button',name='? Как играть',exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.keyboard.press('Shift+Tab');expect(page.get_by_role('button',name='Вернуться к игре',exact=True)).to_be_focused()
    page.keyboard.press('Tab');expect(page.get_by_text('Почему после приказа ничего не произошло?',exact=True)).to_be_focused()
    page.keyboard.press('Escape');expect(page.get_by_role('dialog')).to_have_count(0)
    page.get_by_role('button',name='? Как играть',exact=True).click()
    page.get_by_role('button',name='Пройти обучение заново',exact=True).click();stage('council')
    assert state()['revision']==revision and state()['day']==0,'Teaching changed the simulation'
    page.screenshot(path=str(out/f'{browser_type.name}-{width}-first-advice.png'),full_page=True)
    page.screenshot(path=str(out/f'{browser_type.name}-{width}-first-viewport.png'))
    before=state()
    opened=act(lambda:page.get_by_role('button',name='К вопросу совета',exact=True).click())
    assert opened['council']['agenda']==before['agendas'][0]['id']
    assert opened['day']==before['day'] and opened['gold']==before['gold']
    page.get_by_role('button',name='Читать вопрос и мнения',exact=False).click()
    box=page.locator('[data-testid=ruler-council]').bounding_box();assert 90<=box['y']<250,box
    page.locator('.ruler-speech-group > summary').click()
    speeches=page.locator('.council-speech');assert speeches.count()==5
    for speech in speeches.all():
        if speech.get_attribute('open') is None:speech.locator('summary').click()
        expect(speech.locator('p')).to_be_visible();assert len(speech.locator('p').inner_text())>20
    page.get_by_role('button',name='Перейти к решению',exact=False).click()
    for choice in page.locator('[data-choice]').all():
        choice.evaluate('(el)=>el.scrollIntoView({block:"center"})')
        assert choice.evaluate('(el)=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}'),'A status message or toolbar covers a decision'
    gold=state()['gold']
    decided=act(lambda:page.locator('[data-choice="stewardship"]').click())
    assert decided['gold']==gold-25,'The first choice must actually pay once'
    page.get_by_role('button',name='Дальше: ваши владения',exact=False).click();stage('map')
    page.get_by_label('Поиск поселения',exact=True).fill('Сёгют')
    page.locator('[data-search-place="sogut"]').click()
    expect(page.locator('.ruler-place-card h2')).to_have_text('Сёгют')
    page.get_by_role('button',name='Дальше: как устроены войска',exact=False).click();stage('army')
    expect(page.get_by_role('tab',name='Мои армии',exact=True)).to_have_attribute('aria-selected','true')
    page.get_by_role('button',name='Дальше: казна и управление',exact=False).click();stage('state')
    expect(page.get_by_role('heading',name='Счета казны',exact=True)).to_be_visible()
    expect(page.get_by_label('Торговый груз',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Дальше: дать приказам исполниться',exact=False).click();stage('time')
    page.reload();stage('time')
    before=state();page.get_by_role('button',name='Попробовать ожидание',exact=True).click()
    act(lambda:page.get_by_role('button',name='Семь дней или до известия',exact=True).click());stage('reports')
    assert before['day']<state()['day']<=before['day']+7
    page.get_by_role('button',name='Читать новые донесения',exact=False).click()
    box=page.get_by_role('heading',name='Последние донесения',exact=True).bounding_box()
    toolbar=page.locator('.ruler-toolbar').bounding_box();nav_box=page.locator('.bottom-nav').bounding_box()
    # The last section may reach the document scroll limit before aligning at
    # the top. Require actual visibility between controls, not an arbitrary Y.
    assert box['y']>=toolbar['y']+toolbar['height'] and box['y']+box['height']<=nav_box['y'],box
    page.get_by_role('button',name='Понятно, продолжить правление',exact=True).click()
    page.reload();expect(page.locator('[data-guide-stage]')).to_have_count(0)
    # Raw editing, per-form isolation and zero semantics.
    nav('Войско');page.get_by_text('Личное командование и распределение',exact=True).click()
    matrix('Число передаваемых воинов',['Из гарнизона в армию','Оставить в гарнизоне','Выделить отдельную армию'],['','0','-1','1.5','5001'],['1','10'])
    page.get_by_label('Число передаваемых воинов',exact=True).fill('')
    expect(page.get_by_role('button',name='Лично возглавить',exact=True)).to_be_enabled()
    page.get_by_label('Число передаваемых воинов',exact=True).fill('1')
    before=state();after=act(lambda:page.get_by_role('button',name='Из гарнизона в армию',exact=True).click())
    assert after['armies']['ottoman-1']['troops']['militia']==before['armies']['ottoman-1']['troops']['militia']+1
    matrix('Походная казна',['Отправить поручение'],['','-1','1.5','5001'],['0','20'])
    page.get_by_label('Походная казна',exact=True).fill('')
    expect(page.get_by_role('button',name='Отозвать к столице',exact=True)).to_be_enabled()
    page.get_by_text('Местное снабжение',exact=True).click()
    matrix('Пайки для обоза',['Отправить обоз · 5 ◈','Реквизировать местные запасы'],['','0','1.5','10001'],['1','800'])
    page.get_by_label('Пайки для обоза',exact=True).fill('')
    page.get_by_role('tab',name='Набор и сбор',exact=True).click()
    expect(page.get_by_label('Число набираемых людей',exact=True)).to_have_value('10')
    matrix('Число набираемых людей',['Начать подготовку'],['','0','-1','1.5','41'],['1','40'])
    page.get_by_label('Число набираемых людей',exact=True).fill('2')
    matrix('Число воинов для формирования или роспуска',['Сформировать из гарнизона','Распустить местных воинов'],['','0','-1','1.5','5001'],['1','10'])
    page.get_by_label('Число воинов для формирования или роспуска',exact=True).fill('')
    expect(page.get_by_role('button',name='Начать подготовку',exact=True)).to_be_enabled()
    after=act(lambda:page.get_by_role('button',name='Начать подготовку',exact=True).click())
    assert after['provinces']['sogut']['training'][0]['count']==2
    nav('Держава')
    for title,heading in [('Назначения','Назначения и местные правила'),('Строительство','Строительство и службы'),('Дипломатия','Соседние государства'),('Казна','Счета казны'),('Торговля','Запасы и торговые сделки')]:
        page.get_by_role('tab',name=title,exact=True).click()
        expect(page.get_by_role('heading',name=heading,exact=True)).to_be_visible()
        assert page.get_by_role('tabpanel').count()==1
        if title=='Строительство':
            page.get_by_role('button',name='Подготовить службы для крепости',exact=True).click()
            expect(page.locator('#institution-builders')).to_contain_text('Земельный учёт')
            expect(page.locator('#institution-builders button').last).to_be_disabled()
            page.locator('#institution-builders').get_by_role('button',name='Показать нужную службу').click()
            expect(page.locator('#institution-land_register')).to_be_in_viewport()
            expect(page.locator('#institution-land_register')).to_contain_text('Служба писцов')
            page.get_by_label('Владение для строительства',exact=True).select_option('domanic')
            expect(page.get_by_label('Владение для строительства',exact=True)).to_have_value('domanic')
            ordered=act(lambda:page.get_by_role('button',name='Зернохранилище · 60 монет',exact=True).click())
            assert any(e['kind']=='construction' and e['province']=='domanic' for e in ordered['pending_edicts'])
            expect(page.locator('[data-building=granary]')).to_contain_text('уже в пути')
            expect(page.locator('[data-building=granary] button')).to_be_disabled()
            page.screenshot(path=str(out/f'{browser_type.name}-{width}-building.png'),full_page=True)
    page.get_by_label('Место торговой сделки',exact=True).select_option('sogut')
    expect(page.get_by_label('Торговый груз',exact=True)).to_have_value('400')
    matrix('Торговый груз',['Заказать продовольствие','Согласовать проезд'],['','0','-100','100.5','150','2100'],['100','2000'])
    page.get_by_label('Торговый груз',exact=True).fill('100')
    matrix('Охрана каравана',['Заказать продовольствие','Согласовать проезд'],['','-1','1.5','31'],['0','30'])
    page.get_by_label('Охрана каравана',exact=True).fill('0')
    after=act(lambda:page.get_by_role('button',name='Заказать продовольствие',exact=True).click())
    purchase=next(c for c in after['transports'] if c['kind']=='purchase')
    assert purchase['grain']==100 and purchase['escort_count']==0
    page.reload();nav('Держава');page.get_by_role('tab',name='Торговля',exact=True).click()
    assert any(c['id']==purchase['id'] for c in state()['transports'])
    page.screenshot(path=str(out/f'{browser_type.name}-{width}-trade.png'),full_page=True)
    # All tasks remain accessible with one fixed navigation row and readable input widths.
    for title in ['Двор','Атлас','Войско','Держава','Летопись']:
        nav(title);page.screenshot(path=str(out/f'{browser_type.name}-{width}-{title}.png'),full_page=True)
    assert page.locator('.season-bar').count()==0
    assert not errors,errors
    assert not external_fonts,'Interface fonts must be served by the game itself'
    print(f'PASS UX {browser_type.name}{width}: guided real decision/time/report; skip/restart/reload; numeric matrix and persisted hiring/trade; task navigation',flush=True)
    context.close();browser.close()


def main():
    out=Path(os.getenv('RULER_UX_SCREENSHOTS','/tmp/ruler-ux-evidence'));out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ruler-ux-') as temp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        with open(Path(temp)/'server.log','w+') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':f'sqlite:///{temp}/state.db','SESSION_SECRET':'isolated-ruler-ux-check','PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Disposable server did not start')
                with sync_playwright() as p:
                    for bt,width in [(p.chromium,390),(p.chromium,320),(p.webkit,390),(p.chromium,1280)]:run(bt,width,url,out)
            finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
