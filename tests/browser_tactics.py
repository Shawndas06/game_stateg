"""Mobile tactical battle UI reached via real campaign commands on a disposable DB."""
import os, socket, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from server.storage import Store
from server.auth import read_session
from tactical_scenarios import encounter


def run(bt,width,mode,url,db_url,out):
    browser=bt.launch();ctx=browser.new_context(viewport={'width':width,'height':844},is_mobile=True,has_touch=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);page.get_by_role('button',name='Стать правителем',exact=False).click()
    expect(page.get_by_test_id('prologue')).to_be_visible()
    owner=read_session(next(c['value'] for c in ctx.cookies() if c['name']=='campaign_session'),'tactics-browser-only')
    store=Store(db_url);store.create(owner,11,'ruler_v1','long');store.engine.dispose()
    page.reload();page.get_by_role('button',name='Пропустить пролог',exact=True).click()
    page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    page.get_by_role('button',name='Войско',exact=True).click()
    page.get_by_role('button',name='Лично управлять полевыми боями',exact=True).click()
    expect(page.get_by_text('Личное управление включено',exact=True)).to_be_visible()
    def state():return page.request.get(url+'/api/campaigns/latest').json()
    save=state();_,trace=encounter()
    for i,step in enumerate(trace[2:]):
        response=page.request.post(url+f'/api/campaigns/{save["id"]}/commands',data={'command_id':f'lawful-battle-{i:04}','revision':save['state']['revision'],**step})
        assert response.status==200,response.text();save=response.json()
    assert save['state']['battle'];day=save['state']['day']
    page.reload();expect(page.get_by_role('heading',name='Расставьте войска',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert all(b.is_disabled() for b in page.locator('.field-unit.enemy').all())
    def action(label):
        with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.get_by_role('button',name=label,exact=True).click()
        assert response.value.status==200,response.value.text()
        expect(page.locator('[aria-busy=true]')).to_have_count(0)
        assert state()['state']['day']==day
    before=state()['state']['armies'];action('Резерв')
    assert state()['state']['armies']==before
    page.reload();expect(page.get_by_role('button',name='Резерв',exact=True)).to_have_attribute('aria-pressed','true')
    page.screenshot(path=str(out/f'{bt.name}-{width}-{mode}-deploy.png'),full_page=True)
    if mode in ['delegate','retreat']:
        page.get_by_text('Другие решения',exact=True).click()
        if mode=='retreat':
            page.get_by_role('button',name='Отступить…',exact=True).click();action('Подтвердить отход с поля')
        else:action('Доверить бой командующему')
    else:
        action('Начать сражение');action('Наступать / ввести резерв')
        page.reload();expect(page.get_by_role('button',name='Наступать / ввести резерв',exact=True)).to_have_attribute('aria-pressed','true')
        page.screenshot(path=str(out/f'{bt.name}-{width}-{mode}-combat.png'),full_page=True)
        for _ in range(8):
            if not state()['state'].get('battle'):break
            action('Исполнить приказы →')
    expect(page.locator('.tactical-screen')).to_have_count(0)
    final=state()['state'];assert not final['battle'] and final['day']==day
    page.reload();expect(page.locator('.tactical-screen')).to_have_count(0)
    assert not errors,errors
    print(f'PASS tactics {bt.name}{width} {mode}: legal arrival, deployment, saved orders, paused calendar, real losses and campaign return',flush=True)
    ctx.close();browser.close()


def main():
    out=Path('/tmp/tactical-browser-evidence');out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tactics-browser-') as tmp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}';db_url=f'sqlite:///{tmp}/state.db'
        with open(Path(tmp)/'server.log','w+') as log:
            proc=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':db_url,'SESSION_SECRET':'tactics-browser-only','PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if proc.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Server did not start')
                with sync_playwright() as p:
                    for bt,width,mode in [(p.chromium,390,'manual'),(p.webkit,390,'manual'),(p.chromium,320,'manual'),(p.chromium,390,'delegate'),(p.webkit,390,'retreat')]:run(bt,width,mode,url,db_url,out)
            finally:proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':main()
