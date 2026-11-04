"""Real Telegram HMAC, rejected cookies, failed login and lost create response.

Disposable local server only. No real credentials or production campaigns.
"""
import hashlib, hmac, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

from browser_navigation import new_game,resume_menu,nav

TOKEN='test-only-telegram-bot'


def init_data(uid):
    fields={'auth_date':str(int(time.time())),'user':json.dumps({'id':uid})}
    key=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest()
    fields['hash']=hmac.new(key,'\n'.join(f'{k}={v}' for k,v in sorted(fields.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode(fields)


def run(bt,url,uid):
    browser=bt.launch()
    context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    context.add_init_script('window.Telegram={WebApp:{initData:'+json.dumps(init_data(uid)) + ',ready(){},expand(){}}}')
    context.route('https://telegram.org/js/**',lambda route:route.fulfill(status=200,body='/* mock SDK injected before application */',content_type='application/javascript'))
    page=context.new_page();errors=[];failed_resources=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('requestfailed',lambda r:failed_resources.append({'url':r.url.split('?')[0],'reason':r.failure}) if 'geography.json' in r.url or 'map-sites.json' in r.url else None)
    auth_calls=[]
    def auth(route):
        auth_calls.append(1)
        if len(auth_calls)==1:
            route.fulfill(status=503,json={'detail':'Временный отказ входа'});return
        response=route.fetch();context.clear_cookies();headers={k:v for k,v in response.headers.items() if k.lower()!='set-cookie'}
        route.fulfill(response=response,headers=headers)
    page.route('**/api/auth/telegram',auth)
    page.goto(url)
    expect(page.get_by_role('button',name='Повторить вход',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Стать правителем',exact=False)).to_have_count(0)
    page.get_by_role('button',name='Повторить вход',exact=True).click()
    # Server commits creation, but connection is lost before browser receives it.
    created=[];replays=[]
    def lose_creation(route):
        if route.request.method=='POST' and not created:
            response=route.fetch();assert response.status==201;created.append(response.json()['id']);route.abort()
        elif route.request.method=='POST':
            response=route.fetch();replays.append(response.json()['id']);route.fulfill(response=response)
        else:route.continue_()
    page.route('**/api/campaigns',lose_creation)
    new_game(page,'long')
    expect(page.get_by_role('alert')).to_be_visible()
    expect(page.get_by_role('button',name='Начать кампанию',exact=True)).to_be_enabled()
    page.get_by_role('button',name='Начать кампанию',exact=True).click()
    expect(page.get_by_test_id('prologue')).to_be_visible()
    assert not context.cookies(),'Fixture must reject session cookies'
    # One rejected mutation is re-authenticated and retried with same receipt ID.
    commands=[]
    def reject_once(route):
        commands.append(route.request.post_data_json)
        if len(commands)==1:route.fulfill(status=401,json={'detail':'Сессия истекла'})
        else:route.continue_()
    page.route('**/commands',reject_once)
    page.get_by_role('button',name='Пропустить пролог',exact=True).click()
    expect(page.get_by_test_id('prologue')).to_have_count(0)
    assert len(commands)==2 and commands[0]['command_id']==commands[1]['command_id']
    page.reload();resume_menu(page)
    expect(page.locator('.canvas-world')).to_be_visible()
    page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    expect(page.get_by_test_id('campaign-command-map')).to_be_visible()
    nav(page,'Двор')
    expect(page.get_by_text('Что делать сейчас',exact=True)).to_be_visible()
    page.get_by_role('button',name='Открыть меню кампании',exact=True).click();page.get_by_role('button',name='Главное меню',exact=True).click()
    created.clear();new_game(page,'realm')
    expect(page.get_by_role('alert')).to_be_visible();page.get_by_role('button',name='Начать кампанию',exact=True).click()
    expect(page.get_by_test_id('prologue')).to_be_visible()
    assert replays and replays[-1]==created[0],'Retry with an existing save created another campaign'
    assert not errors,{'pageerrors':errors,'failed_map_requests':failed_resources}
    context.close();browser.close()
    print(bt.name+': failed login -> retry, blocked cookies, lost create -> resume, 401 command -> same-ID retry, reload PASS',flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix='auth-browser-') as tmp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        with open(Path(tmp)/'server.log','w+') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':f'sqlite:///{tmp}/state.db','SESSION_SECRET':'test-auth-only','TELEGRAM_BOT_TOKEN':TOKEN,'PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Fixture did not start')
                with sync_playwright() as p:
                    # A distinct identity/database is needed for each fresh-start flow.
                    run(p.chromium,url,101)
                    run(p.webkit,url,102)
            finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
