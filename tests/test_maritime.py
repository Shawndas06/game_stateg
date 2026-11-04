"""Boundary fixtures test accounting; full legal command walks are separate."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from campaign.engine import RuleError
from campaign.ruler.engine import new_campaign,apply_command as act,view
from campaign.ruler import civil,knowledge,maritime
from campaign.ruler.core import route
from campaign.ruler.models import RulerState

def prepared():
    s=new_campaign(19,extended=True,living=True);s.gold=2000
    p=s.places['mudanya'];p.owner=p.controller='ottoman';p.grain=30000
    s.people[s.ruler_id].location=p.id;s.armies['ottoman-1'].location=p.id
    pid=next(k for k,m in s.flags['statecraft']['specialists'].items() if 'harbor_building' in m['knows'])
    s.people[pid].location=p.id;s.flags['statecraft']['specialists'][pid]['employer']='ottoman'
    s.flags['statecraft']['skills']['ottoman']=['carpentry','stonework','navigation','harbor_building']
    return s,pid

@pytest.mark.parametrize('obstacle',['inland','money','workers','grain','knowledge','master_absent','master_busy','occupied','siege','duplicate'])
def test_port_reasons_and_rejections_are_atomic(obstacle):
    s,pid=prepared();p=s.places['mudanya']
    if obstacle=='inland':p=s.places['sogut'];s.people[s.ruler_id].location=p.id;s.people[pid].location=p.id
    elif obstacle=='money':s.gold=119
    elif obstacle=='workers':p.reserve=11
    elif obstacle=='grain':p.grain=83
    elif obstacle=='knowledge':
        s.flags['statecraft']['skills']['ottoman'].remove('harbor_building');s.flags['statecraft']['specialists'][pid]['knows'].remove('harbor_building')
    elif obstacle=='master_absent':s.people[pid].location='sogut'
    elif obstacle=='master_busy':s.flags['statecraft']['projects']['test']={'master':pid,'status':'active'}
    elif obstacle=='occupied':p.owner='byzantine'
    elif obstacle=='siege':s.sieges[p.id]={}
    else:p.buildings.append('harbor')
    reasons=next(x['reasons'] for x in civil.construction_options(s,p) if x['id']=='harbor')
    assert reasons and all(len(x)>20 for x in reasons)
    before=s.to_dict()
    with pytest.raises(RuleError):act(s,'construction',{'province':p.id,'building':'harbor'})
    assert s.to_dict()==before

def test_port_work_real_cost_pause_completion_accounting_and_save():
    s,pid=prepared();p=s.places['mudanya'];start_money=s.gold;workers=p.reserve
    before=civil.budget(s);tax=civil.assessment(s,p)['gross']
    n=act(s,'construction',{'province':p.id,'building':'harbor'});p=n.places[p.id]
    assert n.gold==start_money-120 and p.reserve==workers-12 and 'harbor' not in p.buildings
    assert knowledge.busy(n,pid)
    civil._construction_tick(n,p,False);assert p.construction['work']==120
    n.people[pid].location='sogut';civil._construction_tick(n,p,True);assert p.construction['work']==120
    n.people[pid].location=p.id
    for _ in range(119):civil._construction_tick(n,p,True)
    assert p.construction['work']==1 and 'harbor' not in p.buildings
    civil._construction_tick(n,p,True)
    assert p.reserve==workers and p.buildings.count('harbor')==1 and p.construction is None and not knowledge.busy(n,pid)
    assert civil.budget(n)['expense']==before['expense']+3
    assert civil.assessment(n,p)['gross']==tax+6
    n=RulerState.from_dict(n.to_dict());assert view(n)['provinces'][p.id]['harbor']['developed']
    with pytest.raises(RuleError):act(n,'construction',{'province':p.id,'building':'harbor'})
    # A land siege alone does not create a magical naval blockade.
    n.sieges[p.id]={};assert maritime.harbour(n,p.id)

def test_invited_expert_can_build_before_teaching_a_local_school():
    s,pid=prepared();s.flags['statecraft']['skills']['ottoman']=[]
    n=act(s,'construction',{'province':'mudanya','building':'harbor'})
    assert n.places['mudanya'].construction['master']==pid
    assert not n.flags['statecraft']['skills']['ottoman']

def test_navigation_ferries_shipping_requirements_and_old_shipping_compatibility():
    s=new_campaign(11,extended=True,living=True)
    ferry=lambda:route(s,'chrysopolis','constantinople',area=['constantinople'])
    sea=lambda:route(s,'marseille','barcelona',area=['barcelona'])
    assert ferry() is None and sea() is None
    s.flags['statecraft']['skills']['ottoman']=['navigation'];assert ferry()==['constantinople'] and sea() is None
    assert any('порт' in x for x in civil.institution_help(s,'shipping')['reasons'])
    s.places['mudanya'].owner=s.places['mudanya'].controller='ottoman';s.places['mudanya'].buildings=['harbor']
    s.institutions['scribes']={'status':'active','ready':0}
    assert not civil.institution_help(s,'shipping')['reasons']
    s=act(s,'institution',{'institution':'shipping'});assert s.institutions['shipping']['maritime'] and sea() is None
    s.institutions['shipping']['status']='active';assert sea()==['barcelona']
    s.places['mudanya'].controller='byzantine';assert sea() is None
    # Previously issued shipping service remains usable in existing saves.
    s.institutions['shipping'].pop('maritime');assert sea()==['barcelona']
    old=new_campaign(11,extended=True);old.institutions['shipping']={'status':'active','ready':0}
    assert route(old,'marseille','barcelona',area=['barcelona'])==['barcelona']
    with pytest.raises(RuleError):act(old,'construction',{'province':'sogut','building':'harbor'})

def test_paid_naval_project_uses_actual_teacher_days_workers_and_no_duplicate():
    s,pid=prepared();s.flags['statecraft']['skills']['ottoman']=[];p=s.places['mudanya'];before=p.reserve
    s=act(s,'learn_craft',{'province':p.id,'person':pid,'tech':'navigation'});p=s.places[p.id]
    assert p.reserve==before-3 and not maritime.navigation(s)
    with pytest.raises(RuleError):act(s,'learn_craft',{'province':p.id,'person':pid,'tech':'navigation'})
    for _ in range(89):s.day+=1;knowledge._projects(s)
    assert not maritime.navigation(s)
    s.day+=1;knowledge._projects(s);assert maritime.navigation(s) and p.reserve==before
    assert any('navigation' in m['knows'] and m['employer']=='ottoman' and k!=pid for k,m in s.flags['statecraft']['specialists'].items())

def test_marine_offer_added_once_to_old_realms_and_no_hidden_foreign_port_data():
    s=new_campaign(11,extended=True,living=True);marine=[k for k,m in s.flags['statecraft']['specialists'].items() if 'navigation' in m['knows']]
    assert len(marine)==1
    for k in marine:s.flags['statecraft']['specialists'].pop(k);s.people.pop(k)
    s.flags.pop('maritime_master_introduced');s.day=365*80;knowledge.maritime_master(s);counter=s.counter;knowledge.maritime_master(s)
    assert s.counter==counter and view(s)['provinces']['mudanya']['harbor'] is None
    marine=next(p for k,p in s.people.items() if 'navigation' in s.flags['statecraft']['specialists'].get(k,{}).get('knows',[]))
    assert view(s)['people'].get(marine.id) is None  # Unhired foreign specialist remains in the offer directory.
    from campaign.ruler.core import calendar
    assert calendar(s)['year']-marine.born==39
    s.places['mudanya'].buildings.append('harbor');assert view(s)['provinces']['mudanya']['harbor'] is None

def test_cargo_waits_without_losing_stock_when_port_service_lost_before_departure():
    s,pid=prepared();s.institutions['shipping']={'status':'active','ready':0,'maritime':True}
    cargo={'kind':'supply','location':'marseille','path':['barcelona'],'left':0,'grain':200}
    before=deepcopy(cargo);assert not civil._journey(s,cargo)
    assert cargo['grain']==200 and cargo['path']==before['path'] and cargo['held']
    s.places['mudanya'].buildings.append('harbor');assert not civil._journey(s,cargo)
    assert not cargo['held'] and cargo['left']>0 and cargo['grain']==200

def test_geography_public_contract_and_versioned_protection_are_both_served(tmp_path):
    from fastapi.testclient import TestClient
    from server.app import Settings,create_app
    from campaign.content import PLACES
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/geo.db',session_secret='geo-contract-test'))
    with TestClient(app) as c:
        assert set(c.get('/mediterranean-geography.json').json())=={'land','lakes'}
        response=c.get('/map-sites.json?v=test-build');assert response.status_code==200
        assert response.json()['settlements']==[list(p[2:4]) for p in PLACES]
        assert 'max-age=86400' in response.headers['cache-control']
        assert c.get('/map-sites.json').headers['cache-control']=='no-cache'

def test_recorded_legal_maritime_school_walk_without_resource_or_date_injection():
    script=json.loads((Path(__file__).parent/'fixtures/maritime-school.json').read_text())
    s=new_campaign(script['seed'],extended=True,living=True)
    for i,(kind,payload) in enumerate(script['commands']):
        s=act(s,kind,payload)
        if i%15==0:s=RulerState.from_dict(s.to_dict())
    assert not s.ending and s.day==430
    assert {'navigation','carpentry','stonework','harbor_building'}<=set(s.flags['statecraft']['skills']['ottoman'])
    assert any('harbor_building' in m['knows'] and m['fee']==0 and m['employer']=='ottoman' for m in s.flags['statecraft']['specialists'].values())

def test_port_command_receipt_and_reload_do_not_double_charge(tmp_path):
    from fastapi.testclient import TestClient
    from server.app import Settings,create_app
    from server.storage import CampaignRow
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/port.db',session_secret='port-receipt-test'))
    with TestClient(app) as c:
        c.post('/api/auth/demo');save=c.post('/api/campaigns',json={'scenario':'ruler_v1','campaign_mode':'realm'}).json()
        s,pid=prepared()
        with app.state.store.session.begin() as db:
            row=db.get(CampaignRow,save['id']);row.snapshot=s.to_dict();row.revision=s.revision
        url=f"/api/campaigns/{save['id']}/commands"
        cmd={'command_id':'port-once','revision':s.revision,'kind':'construction','payload':{'province':'mudanya','building':'harbor'}}
        first=c.post(url,json=cmd);assert first.status_code==200
        assert c.post(url,json=cmd).json()==first.json()==c.get(f"/api/campaigns/{save['id']}").json()
        assert first.json()['state']['gold']==1880
        assert first.json()['state']['provinces']['mudanya']['reserve']==68
