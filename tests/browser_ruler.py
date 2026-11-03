"""Real mobile UI acceptance, isolated server/database. No user saves are edited.

Uses legal-prefix snapshots from ruler_scenarios.py for exhaustive branch UI
inspection; also plays a fresh campaign through actual UI from start to ending.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import delete
from campaign.ruler.engine import validate,view
from campaign.ruler.court import SCENES as PERSONAL_SCENES
from campaign.ruler.models import RulerState
from server.auth import read_session
from server.storage import Store,CampaignRow,ArchiveRow

PREF={'founding':'stewardship','frontier_letter':'accept','grain_offer':'buy','service_terms':'reward','village_petition':'charter','quarter_accounts':'audit','road_warning':'patrol','merchant_due':'settle','governor_accounts':'audit','border_proposal':'peace','assembly_claim':'confirm','crisis':'settlement','charter_return':'honour','promise_broken':'repair','campaign_return':'review','casualty_hearing':'deputy','delayed_supply':'wait','accusation':'recover','rival_letters':'investigate','succession':'orhan'}


def no_overflow(page):
    page.evaluate('document.fonts.ready')
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),page.evaluate('document.documentElement.scrollWidth')


def run(browser_type,width,url,out):
    browser=browser_type.launch();context=browser.new_context(viewport={'width':width,'height':844 if width==390 else 740},is_mobile=True,has_touch=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);page.get_by_text('Другие режимы',exact=True).click();page.get_by_role('button',name='Первая глава · учебная партия',exact=False).click();page.get_by_role('heading',name='Первый совет',exact=True).wait_for()
    assert page.locator('[data-speaker]').count()==5
    assert page.locator('.ruler-decisions small').count()==0
    def nav(title):
        page.get_by_role('button',name=title,exact=True).click();no_overflow(page)
        if title=='Атлас':
            search=page.get_by_label('Поиск поселения',exact=True)
            assert search.bounding_box()['width']>=100,'Map search must remain usable alongside its filter'
            search.fill('Бурса')
            expect(page.locator('[data-search-place="bursa"]')).to_be_visible()
            search.fill('')
    def state():return page.request.get(url+'/api/campaigns/latest').json()
    def action(click):
        with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:click()
        data=response.value.json()
        assert response.value.status==200,data
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        return data
    def clock():
        page.get_by_role('button',name='Передать ход времени',exact=False).click()
        return action(lambda:page.get_by_role('button',name='До значимого события',exact=False).click())
    action(lambda:page.locator('[data-choice="stewardship"]').click())
    nav('Войско');page.get_by_text('Личное командование и распределение',exact=True).click()
    page.get_by_label('Число передаваемых воинов',exact=True).fill('10');page.get_by_label('Командующий новым отрядом',exact=True).select_option('orhan')
    result=action(lambda:page.get_by_role('button',name='Выделить отдельную армию',exact=True).click())
    assert len(result['state']['armies'])==2
    page.locator('.ruler-army-list button').filter(has_text='Орхан').click()
    page.get_by_label('Задача армии',exact=True).select_option('cover');page.get_by_label('Цель поручения',exact=True).select_option('domanic');page.get_by_label('Походная казна',exact=True).fill('10')
    action(lambda:page.get_by_role('button',name='Отправить поручение',exact=True).click())
    clock();result=state();child=next(a for a in result['state']['armies'].values() if a['commander']=='orhan')
    assert child['location']=='domanic' and result['state']['people']['orhan']['location']=='domanic'
    assert result['state']['people'][result['state']['ruler_id']]['location']=='sogut'
    nav('Войско');page.get_by_role('tab',name='Набор и сбор',exact=True).click();page.get_by_label('Число набираемых людей',exact=True).fill('10')
    action(lambda:page.get_by_role('button',name='Начать подготовку',exact=True).click())
    result=state();assert result['state']['provinces']['sogut']['training']
    clock();clock();result=state()
    assert not result['state']['provinces']['sogut']['training']
    nav('Держава');page.get_by_role('tab',name='Торговля',exact=True).click();page.get_by_label('Торговый груз',exact=True).fill('400');page.get_by_label('Охрана каравана',exact=True).fill('10')
    result=action(lambda:page.get_by_role('button',name='Заказать продовольствие',exact=True).click())
    caravan=next(c for c in result['state']['transports'] if c['kind']=='purchase')
    assert caravan['status']=='assembling' and caravan['location']=='kutahya'
    for _ in range(5):
        clock();result=state()
        if any(c['id']==caravan['id'] and c['status']=='completed' for c in result['state']['transports']):break
    assert any(c['id']==caravan['id'] and c['status']=='completed' for c in result['state']['transports'])
    for title in ['Двор','Атлас','Войско','Держава','Летопись']:
        nav(title)
        if title=='Атлас':page.locator('.map-load-state').wait_for(state='hidden')
        page.screenshot(path=str(out/f'{browser_type.name}-{width}-{title}.png'),full_page=True)
    page.reload();nav('Войско');assert len(state()['state']['armies'])==2
    nav('Летопись');page.get_by_role('button',name='Открыть список летописей',exact=True).click();expect(page.get_by_role('button',name='Продолжить',exact=True)).to_have_count(1)
    nav('Двор')
    # A complete party through UI: inspect each council and give an explicit answer.
    for iteration in range(180):
        saved=state();s=saved['state']
        if s['ending']:break
        if s['agendas']:
            agenda=s['agendas'][0]
            action(lambda:page.locator(f'[data-agenda="{agenda["id"]}"]').click())
            assert page.locator('[data-speaker]').count()>=1
            choices=state()['state']['council']['choices']
            desired=PREF[agenda['scene']]
            # Business refusals are allowed, then select an available alternative.
            ordered=[c for c in choices if c['id']==desired]+[c for c in choices if c['id']!=desired]
            succeeded=False
            for choice in ordered:
                with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.locator(f'[data-choice="{choice["id"]}"]').click()
                expect(page.locator('main[aria-busy=true]')).to_have_count(0)
                if response.value.status==200:succeeded=True;break
                assert response.value.status==422
                page.get_by_role('button',name='Закрыть сообщение',exact=True).click()
            assert succeeded,agenda
        else:clock()
    assert state()['state']['ending'],'Fresh UI campaign did not reach its ending'
    expect(page.get_by_role('heading',name='Летопись сохранена',exact=True)).to_be_visible()
    page.screenshot(path=str(out/f'{browser_type.name}-{width}-итог.png'),full_page=True)
    assert not errors,errors
    print(f'PASS {browser_type.name}{width}: fresh full UI party, split army, remote campaign, training, caravan, all tabs, reload, archive',flush=True)
    return browser,context,page


def branches(page,url,db_url,secret,data,out):
    cookie=next(c for c in page.context.cookies() if c['name']=='campaign_session')
    owner=read_session(cookie['value'],secret)
    store=Store(db_url)
    for index,branch in enumerate(data['branches']):
        prefix=RulerState.from_dict(branch['prefix_snapshot']);validate(prefix)
        created=store.create(owner,prefix.seed,'ruler_v1')
        prefix.outbox=[]
        # These are complete legal-prefix states from recorded command walks,
        # not manufactured pending-event fixtures. Full archive persistence is
        # separately checked on the fresh browser game and API tests.
        with store.session.begin() as db:
            row=db.get(CampaignRow,created['id']);row.snapshot=prefix.to_dict();row.revision=prefix.revision
            db.execute(delete(ArchiveRow).where(ArchiveRow.campaign==created['id']))
            store._archive(db,created['id'],prefix.reports)
        page.reload();page.get_by_role('heading',name=view(prefix)['chapter']['name'],exact=True).wait_for()
        ag=next(a for a in prefix.agendas if a['scene']==branch['scene'])
        with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.locator(f'[data-agenda="{ag["id"]}"]').click()
        assert response.value.status==200
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        text=page.locator('.ruler-council').inner_text();assert text and 'undefined' not in text and 'NaN' not in text
        assert page.locator('[data-speaker]').count()>0
        with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.locator(f'[data-choice="{branch["choice"]}"]').click()
        assert response.value.status==200,(branch['scene'],branch['choice'],response.value.json())
        expect(page.locator('main[aria-busy=true]')).to_have_count(0)
        result=response.value.json()['state'];assert ag['id'] not in {x['id'] for x in result['agendas']}
        restored=store.get(created['id'],owner)['state'];assert restored==result
        no_overflow(page)
        if index%10==0:print(f'UI branches {index+1}/{len(data["branches"])}',flush=True)
        if index%3==0:page.screenshot(path=str(out/f'branch-{branch["scene"]}-{branch["choice"]}.png'),full_page=True)
        if branch['scene'] in PERSONAL_SCENES:
            result=page.request.get(url+'/api/campaigns/latest').json()['state']
            actor=ag['context']['person']
            note=next(h for h in result['people'][actor]['history'] if h['key']=='choice:'+branch['scene'])
            page.get_by_role('button',name='Летопись',exact=True).click()
            page.locator('.people-directory summary').click()
            expect(page.locator('.ruler-person').filter(has_text=result['people'][actor]['name']).get_by_text(note['text'],exact=False)).to_be_visible()
            if result.get('accomplishments'):expect(page.get_by_role('heading',name='Что удалось изменить',exact=True)).to_be_visible()
            page.screenshot(path=str(out/f'person-history-{branch["scene"]}-{branch["choice"]}.png'),full_page=True)
    for scene,cid in [('frontier_letter','refuse'),('border_proposal','prepare'),('grain_offer','decline'),('merchant_due','refuse')]:
        branch=next(x for x in data['branches'] if x['scene']==scene and x['choice']==cid)
        for treatment in ['gift','detain','execute']:
            prefix=RulerState.from_dict(branch['prefix_snapshot']);created=store.create(owner,prefix.seed,'ruler_v1');prefix.outbox=[]
            with store.session.begin() as db:
                row=db.get(CampaignRow,created['id']);row.snapshot=prefix.to_dict();row.revision=prefix.revision
                db.execute(delete(ArchiveRow).where(ArchiveRow.campaign==created['id']));store._archive(db,created['id'],prefix.reports)
            page.reload();page.get_by_role('heading',name=view(prefix)['chapter']['name'],exact=True).wait_for()
            ag=next(x for x in prefix.agendas if x['scene']==scene)
            with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST'):page.locator(f'[data-agenda="{ag["id"]}"]').click()
            expect(page.locator('main[aria-busy=true]')).to_have_count(0)
            page.get_by_label('Обращение с посланником',exact=True).select_option(treatment)
            if treatment in ['detain','execute']:
                for option in page.locator('.ruler-decisions [data-choice]').all():
                    if option.get_attribute('data-choice') not in ['refuse','prepare','decline']:assert option.is_disabled()
            with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.locator(f'[data-choice="{cid}"]').click()
            assert response.value.status==200,response.value.json()
            result=response.value.json()['state'];envoy=ag['context']['envoy']
            assert result['people'][envoy]['status']==('dead' if treatment=='execute' else 'detained' if treatment=='detain' else 'leaving')
            if treatment=='gift':assert result['gold']==prefix.gold-20
            if treatment=='detain':
                expect(page.locator('main[aria-busy=true]')).to_have_count(0);page.get_by_role('button',name='Летопись',exact=True).click();page.locator('.people-directory summary').click()
                with page.expect_response(lambda r:'/commands' in r.url and r.request.method=='POST') as response:page.get_by_role('button',name='Отпустить посланника',exact=True).click()
                assert response.value.status==200 and response.value.json()['state']['people'][envoy]['status']=='leaving'
    store.engine.dispose();print(f'PASS {len(data["branches"])} authored choices and12 envoy treatment cases through actual council UI',flush=True)



def main():
    acceptance=Path(os.getenv('RULER_ACCEPTANCE','/private/tmp/ruler-acceptance.json'))
    data=json.loads(acceptance.read_text()) if acceptance.exists() else None
    with tempfile.TemporaryDirectory(prefix='ruler-browser-') as temp:
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        url=f'http://127.0.0.1:{port}';db_url=f'sqlite:///{temp}/state.db';secret='isolated-ruler-browser-secret'
        out=Path(os.getenv('RULER_SCREENSHOTS','/private/tmp/ruler-browser-evidence'));out.mkdir(exist_ok=True,parents=True)
        with open(Path(temp)/'server.log','w+') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':db_url,'SESSION_SECRET':secret,'PUBLIC_URL':url},stdout=log,stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                    try:
                        with urlopen(url+'/api/health',timeout=1):break
                    except OSError:time.sleep(.1)
                else:raise AssertionError('Fixture server did not start')
                with sync_playwright() as p:
                    browser,context,page=run(p.chromium,390,url,out)
                    if data:branches(page,url,db_url,secret,data,out)
                    context.close();browser.close()
                    for bt,width in [(p.chromium,320),(p.webkit,390)]:
                        browser,context,page=run(bt,width,url,out);context.close();browser.close()
            finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
