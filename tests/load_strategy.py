"""Bounded load test: ten isolated campaigns on a disposable local server."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,time,urllib.request,http.cookiejar
import browser_ruler_ux as harness

readings=[]
def run(bt,width,url,out):
    if bt.name!='chromium' or width!=390:return
    def player(i):
        client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def call(path,body):
            request=urllib.request.Request(url+'/api'+path,json.dumps(body).encode(),{'Content-Type':'application/json'})
            with client.open(request,timeout=30) as response:return json.load(response)
        call('/auth/demo',{});save=call('/campaigns',{'scenario':'ruler_v1','campaign_mode':'realm'})
        def command(kind,payload):
            nonlocal save
            started=time.perf_counter();save=call('/campaigns/'+save['id']+'/commands',{'command_id':f'load-{i}-{save["state"]["revision"]:08}','revision':save['state']['revision'],'kind':kind,'payload':payload});return (time.perf_counter()-started)*1000
        command('begin_reign',{})
        week=command('advance',{'days':7,'strategic':True});season=command('advance',{'days':90,'strategic':True})
        assert save['state']['day']>0
        return {'campaign':i,'week_ms':round(week,1),'season_ms':round(season,1)}
    with ThreadPoolExecutor(max_workers=10) as pool:readings.extend(pool.map(player,range(10)))
    summary={key:sorted(x[key] for x in readings)[-1] for key in ['week_ms','season_ms']}
    Path('/tmp/strategy-load.json').write_text(json.dumps({'environment':'isolated local SQLite; not Render capacity proof','players':readings,'p95':summary},indent=2))
    print('PASS ten isolated API campaigns '+json.dumps(summary),flush=True)

if __name__=='__main__':harness.run=run;harness.main()
