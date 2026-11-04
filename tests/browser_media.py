"""Real static media + persisted introduction + lawful combat succession in mobile browsers."""
from browser_navigation import new_game,resume_menu,nav as campaign_nav

import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import expect,sync_playwright
from sqlalchemy import delete
from campaign.ruler.engine import new_campaign,view,validate
from ruler_scenarios import Walk
from server.auth import read_session
from server.storage import Store,CampaignRow,ArchiveRow


def lawful_succession():
    w=Walk(10,'military');w.state=new_campaign(10,extended=True);w.act('begin_reign');w.answer()
    w.act('transfer',{'army':'ottoman-1','direction':'to_army','troops':{'militia':35}})
    w.act('lead',{'army':'ottoman-1','posture':'assault','regent':'hasan'})
    w.act('mission',{'army':'ottoman-1','target':'bursa','purpose':'conquer','funds':30,'allow_assault':True,'allow_requisition':True,'area':['sogut','inegol','bursa']})
    for _ in range(85):
        if w.state.people['osman'].status=='dead':break
        w.act('advance',{'days':1})
    assert w.state.people['osman'].status=='dead' and any(a['scene']=='succession' for a in w.state.agendas)
    validate(w.state);return w


def run(bt,width,url,db_url,prefix,out):
    browser=bt.launch();ctx=browser.new_context(viewport={'width':width,'height':844},is_mobile=width<800,has_touch=width<800)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("const original=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.lastMedia=this;return original.call(this)}")
    def state():return page.request.get(url+'/api/campaigns/latest').json()['state']
    def fits():assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.goto(url);expect(page.get_by_role('button',name='Новая игра',exact=True)).to_be_enabled();fits()
    for asset in ['cover','advisor','succession']:
        size=page.evaluate("src=>new Promise((ok,no)=>{const i=new Image();i.onload=()=>ok(i.naturalWidth);i.onerror=no;i.src=src})",f'/media/{asset}.webp')
        assert size>500,(asset,size)
    ranged=page.request.get(url+'/media/succession.mp4',headers={'Range':'bytes=0-31'})
    assert ranged.status==206 and len(ranged.body())==32 and b'ftyp' in ranged.body()
    page.screenshot(path=str(out/f'{bt.name}-{width}-splash.png'))
    new_game(page,'long');expect(page.get_by_test_id('prologue')).to_be_visible()
    before=state();assert before['day']==0 and before['prologue_pending']
    assert page.evaluate('!window.lastMedia'),'Unexpected automatic playback before consent'
    page.get_by_role('button',name='Включить голос',exact=True).click()
    try:page.wait_for_function('window.lastMedia && !lastMedia.paused && lastMedia.currentTime>0.1',timeout=10000)
    except Exception:
        print('Audio diagnostic',page.evaluate('({src:window.lastMedia?.src,paused:window.lastMedia?.paused,ready:window.lastMedia?.readyState,error:window.lastMedia?.error?.message,text:document.body.innerText})'),flush=True);raise
    assert 'prologue_home.mp3' in page.evaluate('lastMedia.src')
    page.get_by_role('button',name='Пауза',exact=True).click();page.wait_for_function('lastMedia.paused')
    page.get_by_role('button',name='Прослушать',exact=True).click();page.wait_for_function('!lastMedia.paused')
    for title in ['Мир не будет ждать','Первое слово правителя']:
        page.get_by_role('button',name='Продолжить',exact=True).click();expect(page.get_by_role('heading',name=title,exact=True)).to_be_visible();fits()
    page.screenshot(path=str(out/f'{bt.name}-{width}-prologue.png'))
    page.get_by_role('button',name='Выключить голос',exact=True).click()
    page.get_by_role('button',name='К первому совету',exact=False).click();campaign_nav(page,'Двор');expect(page.get_by_role('heading',name='Первый совет',exact=True)).to_be_visible()
    after=state();assert not after['prologue_pending'] and after['day']==before['day'] and after['gold']==before['gold']
    page.reload();resume_menu(page);expect(page.get_by_test_id('prologue')).to_have_count(0)
    page.get_by_role('button',name='Пропустить обучение',exact=True).click()
    page.screenshot(path=str(out/f'{bt.name}-{width}-adviser.png'),full_page=True);fits()
    for tab,title in [('Войско','Войско'),('Держава','Держава'),('Летопись','Летопись и люди')]:
        campaign_nav(page,tab);expect(page.get_by_role('heading',name=title,exact=True)).to_be_visible();expect(page.locator('.adviser')).to_have_count(0);fits()
    assert state()['revision']==after['revision'],'Media or navigation changed the campaign'
    # A complete, lawful prefix is restored solely to save repeating its commands
    # through each browser. No death, date, troops or scene is manufactured.
    owner=read_session(next(c['value'] for c in ctx.cookies() if c['name']=='campaign_session'),'media-check-only')
    store=Store(db_url);created=store.create(owner,prefix.state.seed,'ruler_v1','long')
    with store.session.begin() as db:
        row=db.get(CampaignRow,created['id']);row.snapshot=prefix.state.to_dict();row.revision=prefix.state.revision
        db.execute(delete(ArchiveRow).where(ArchiveRow.campaign==created['id']));store._archive(db,created['id'],prefix.state.reports)
    page.reload();resume_menu(page);expect(page.get_by_role('heading',name='Власть после смерти правителя',exact=True)).to_be_visible()
    assert page.locator('.accession-film').count()==0
    old=state();page.locator('[data-choice=orhan]').click();expect(page.get_by_role('dialog')).to_be_visible()
    changed=state();assert changed['ruler_id']=='orhan' and changed['accession']['day']==old['day']
    assert changed['gold']==old['gold'] and changed['obligations']==old['obligations']
    page.get_by_role('button',name='Начать просмотр',exact=True).click()
    page.wait_for_function("document.querySelector('video').currentTime>0.2 && !document.querySelector('video').paused")
    assert page.locator('video').evaluate('(v)=>v.videoWidth')==1280
    page.locator('video').evaluate('(v)=>new Promise(ok=>{v.pause();v.addEventListener("seeked",ok,{once:true});v.currentTime=10})');page.screenshot(path=str(out/f'{bt.name}-{width}-film.png'));fits()
    page.reload();resume_menu(page);expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button',name='Пропустить видео',exact=True).click();page.reload();resume_menu(page);expect(page.get_by_role('dialog')).to_have_count(0)
    campaign_nav(page,'Летопись');page.get_by_role('button',name='Вспомнить передачу власти',exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible();page.keyboard.press('Escape');expect(page.get_by_role('dialog')).to_have_count(0)
    page.get_by_role('button',name='Вспомнить передачу власти',exact=True).click()
    page.locator('video').evaluate('(v)=>new Promise(ok=>{v.addEventListener("loadedmetadata",ok,{once:true});if(v.readyState>=1)ok()})')
    page.locator('video').evaluate('(v)=>{v.currentTime=v.duration-0.3}')
    page.get_by_role('button',name='Начать просмотр',exact=True).click();expect(page.get_by_role('dialog')).to_have_count(0)
    assert state()==changed,'Film playback/skip/reload changed the world'
    # Test actual metadata for every committed recording, not only HTTP 200 (SPA
    # fallbacks can return an HTML page for a missing media URL).
    clips=json.loads(Path('web/public/media/manifest.json').read_text())['clips']
    for clip,duration in clips.items():
        actual=page.evaluate("async src=>{const a=new Audio();a.preload='metadata';return await new Promise((ok,no)=>{a.onloadedmetadata=()=>ok(a.duration);a.onerror=()=>no(Error(src));a.src=src})}",f'/media/voice/{clip}.mp3')
        assert abs(actual-duration)<0.3,(clip,actual,duration)
    # Reached by the 1299->1362 recorded walk; only browser preferences are set.
    from campaign.ruler.models import RulerState
    dynasty=json.loads(Path('/tmp/dynasty-acceptance.json').read_text())
    later=RulerState.from_dict(dynasty['prefixes']['orhan_handover'])
    created=store.create(owner,later.seed,'ruler_v1','long')
    with store.session.begin() as db:
        row=db.get(CampaignRow,created['id']);row.snapshot=later.to_dict();row.revision=later.revision
        db.execute(delete(ArchiveRow).where(ArchiveRow.campaign==created['id']));store._archive(db,created['id'],later.reports)
    if later.flags.get('accession'):
        page.evaluate("key=>localStorage.setItem(key,'seen')",f"accession:{created['id']}:{later.flags['accession']['day']}")
    page.reload();resume_menu(page);campaign_nav(page,'Двор')
    agenda=next(a for a in later.agendas if a['scene']=='orhan_handover')
    page.locator(f'[data-agenda="{agenda["id"]}"]').click()
    page.locator('[data-choice=handover]').click()
    expect(page.get_by_role('heading',name='Мурад принимает державу',exact=True)).to_be_visible();fits()
    assert state()['ruler_id']=='murad' and state()['gold']==later.gold
    page.screenshot(path=str(out/f'{bt.name}-{width}-murad.png'))
    page.get_by_role('button',name='К совету Мурада',exact=False).click()
    page.reload();resume_menu(page);expect(page.get_by_role('dialog')).to_have_count(0)
    assert not errors,errors
    print(f'PASS media {bt.name}{width}: consent/audio, three prologue cards, refresh, adviser context, lawful accession day{old["day"]}, decoded MP4, skip/replay and {len(clips)} MP3s',flush=True)
    store.engine.dispose();ctx.close();browser.close()


def main():
    out=Path('/tmp/media-evidence');out.mkdir(exist_ok=True);prefix=lawful_succession()
    (out/'lawful-succession.json').write_text(json.dumps({'seed':prefix.state.seed,'trace':prefix.trace,'day':prefix.state.day},ensure_ascii=False,indent=2))
    with tempfile.TemporaryDirectory(prefix='media-browser-') as tmp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}';db_url=f'sqlite:///{tmp}/state.db'
        with open(Path(tmp)/'server.log','w+') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':db_url,'SESSION_SECRET':'media-check-only','PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Fixture server did not start')
                with sync_playwright() as p:
                    for bt,width in [(p.chromium,390),(p.chromium,320),(p.webkit,390),(p.chromium,1280)]:run(bt,width,url,db_url,prefix,out)
            finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
