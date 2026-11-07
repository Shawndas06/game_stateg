"""A slow CPU must restore a searched city promptly, not block behind geography work."""
from collections import Counter
import json
from playwright.sync_api import expect
import browser_ruler_ux as harness
from browser_navigation import new_game,resume_menu


def run(bt,width,url,out):
    if bt.name!='chromium' or width!=390:return
    browser=bt.launch();ctx=browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);new_game(page,'realm')
    for title in ['Пропустить пролог','Пропустить обучение']:page.get_by_role('button',name=title,exact=True).click()
    search=page.get_by_label('Поиск поселения',exact=True);search.fill('Бурса');page.locator('[data-search-place=bursa]').click()
    expect(page.get_by_test_id('place-bursa')).to_be_visible();page.get_by_role('button',name='Закрыть карточку',exact=True).click()
    cdp=ctx.new_cdp_session(page);cdp.send('Emulation.setCPUThrottlingRate',{'rate':12});cdp.send('Profiler.enable');cdp.send('Profiler.start')
    try:
        page.reload();resume_menu(page);expect(page.get_by_test_id('place-bursa')).to_be_visible()
    except Exception:
        profile=cdp.send('Profiler.stop')['profile'];(out/'map-boot-failure-profile.json').write_text(json.dumps(profile))
        counts=Counter(profile.get('samples',[]));nodes={n['id']:n for n in profile['nodes']}
        print('Slow map CPU profile',[(n,dict(nodes[n]['callFrame']),count) for n,count in counts.most_common(8)],flush=True)
        raise
    cdp.send('Profiler.stop');cdp.send('Emulation.setCPUThrottlingRate',{'rate':1})
    # Changed response bytes invalidate even plausible-looking derived metadata.
    raw=page.request.get(url+'/mediterranean-geography.json').body()
    sites=page.request.get(url+'/map-sites.json').json();sites['coast_cache']['values']=[999]*len(sites['settlements'])
    ctx.route('**/mediterranean-geography.json*',lambda r:r.fulfill(body=b'\n'+raw,content_type='application/json'))
    ctx.route('**/map-sites.json*',lambda r:r.fulfill(json=sites))
    page.reload();resume_menu(page);expect(page.get_by_test_id('place-bursa')).to_be_visible()
    search=page.get_by_label('Поиск поселения',exact=True);search.fill('Константинополь');page.locator('[data-search-place=constantinople]').click()
    expect(page.get_by_test_id('place-constantinople')).to_be_visible()
    camera=json.loads(page.evaluate('localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith("camera:")))'))
    assert 0<camera['width']<20,'Stale distances must not turn a narrow coastal footprint into a full-size inland city'
    assert not errors,errors
    print('PASS map boot: 12x CPU original deadline, restored city, changed geometry rejects poisoned shoreline cache',flush=True)
    ctx.close();browser.close()


if __name__=='__main__':harness.run=run;harness.main()
