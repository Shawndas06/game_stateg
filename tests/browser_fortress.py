"""Check the paid Murad-era flow in a disposable local database and real browser."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from campaign.engine import apply_command, new_campaign, relation
from server.storage import CampaignRow, Store


def run():
    with tempfile.TemporaryDirectory(prefix='campaign-fortress-') as temp:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        db_url=f'sqlite:///{temp}/state.db'
        process=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:create_app','--factory','--host','127.0.0.1','--port',str(port)],env={**os.environ,'APP_ENV':'test','DATABASE_URL':db_url,'SESSION_SECRET':'isolated-browser-fixture-secret','PUBLIC_URL':url},stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if process.poll() is not None:raise RuntimeError(process.stderr.read().decode())
                try:
                    with urlopen(url+'/api/health',timeout=1):break
                except OSError:time.sleep(.1)
            else:raise AssertionError('Fixture server did not start')
            with sync_playwright() as p:
                browser=p.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                page.goto(url);page.get_by_text('Другие режимы',exact=True).click();page.get_by_role('button',name='Начать историю').click();page.get_by_role('heading',name='Первый диван').wait_for()
                save=page.request.get(url+'/api/campaigns/latest').json()
                store=Store(db_url)
                with store.session.begin() as db:
                    row=db.get(CampaignRow,save['id'])
                    state=apply_command(new_campaign(42),'choose',{'choice':'stewardship'})
                    state.turn=252;state.ruler='Мурад I';state.ruler_id='murad_1';state.ruler_rank=3
                    state.shown_events+=['succession','accession_murad_1'];state.factions['ottoman'].gold=1000
                    relation(state,'ottoman','byzantine')['status']='peace'
                    row.snapshot=state.to_dict();row.revision=state.revision
                store.engine.dispose();page.reload();page.get_by_role('button',name='Карта',exact=True).click()
                def domanic():
                    page.get_by_label('Поиск поселения',exact=True).fill('Доманич')
                    page.locator('[data-search-place="domanic"]').click()
                    expect(page.locator('.place-card h2')).to_have_text('Доманич ')
                domanic();page.get_by_role('button',name='Заложить',exact=True).click()
                expect(page.locator('.place-card')).to_contain_text('Строится новая крепость · 4 сезона')
                result=page.request.get(url+'/api/campaigns/latest').json()['state']
                assert result['factions']['ottoman']['gold']==750
                page.reload();page.get_by_role('button',name='Карта',exact=True).click();domanic()
                expect(page.locator('.place-card')).to_contain_text('Строится новая крепость · 4 сезона')
                for season in range(4):
                    page.get_by_role('button',name='Завершить сезон').click()
                    page.get_by_role('button',name='Подтвердить приказы').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(page.locator('.ruler small')).to_contain_text(f'ход {253+season}')
                expect(page.locator('.place-card .eyebrow')).to_have_text('Укреплённое владение')
                result=page.request.get(url+'/api/campaigns/latest').json()['state']
                assert result['provinces']['domanic']['walls']==60
                assert result['provinces']['domanic']['construction'] is None
                assert result['provinces']['domanic']['buildings'].count('new_fortress')==1
                assert page.get_by_role('button',name='Заложить',exact=True).count()==0
                assert page.get_by_role('alert').count()==0
                browser.close()
            print('PASS Chromium390: Murad foundation, exact payment, reload, four seasons, fortress icon/card transition')
        finally:
            process.terminate();process.wait(timeout=10)


if __name__=='__main__':run()
