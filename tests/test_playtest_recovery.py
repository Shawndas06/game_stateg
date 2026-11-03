import pytest
from fastapi.testclient import TestClient
from server.app import Settings, create_app
from server.auth import session_token
from campaign.ruler.engine import new_campaign, apply_command, view
from campaign.ruler import dynasty, story
from campaign.ruler.models import RulerState
from campaign.engine import RuleError


def test_cookie_free_session_and_ownership(tmp_path):
    app=create_app(Settings(mode='test',database_url=f'sqlite:///{tmp_path}/auth.db',session_secret='recovery-test'))
    with TestClient(app) as c:
        login=c.post('/api/auth/demo')
        assert login.headers['cache-control']=='no-store'
        token=login.json()['session_token'];c.cookies.clear()
        headers={'Authorization':'Bearer '+token}
        save=c.post('/api/campaigns',json={'scenario':'ruler_v1'},headers=headers).json()
        assert c.get('/api/campaigns/latest',headers=headers).json()['id']==save['id']
        assert c.get('/api/campaigns/latest').status_code==401
        for invalid in ['broken',session_token('demo:other','recovery-test',1),token+'tampered']:
            assert c.get('/api/campaigns/latest',headers={'Authorization':'Bearer '+invalid}).status_code==401
        other={'Authorization':'Bearer '+session_token('demo:other','recovery-test')}
        assert c.get('/api/campaigns/'+save['id'],headers=other).status_code==404
    app.state.store.engine.dispose()


def generation():
    # Boundary fixture, not a claimed full campaign walkthrough.
    s=new_campaign(11,extended=True);s.day=365*44;s.agendas=[]
    story.schedule(s)
    return s


def test_generation_does_not_create_soldiers_or_resurrect_people():
    s=new_campaign(11,extended=True);s.day=365*42;story.schedule(s)
    assert 'murad' not in s.people
    before={a.id:a.size for a in s.armies.values()}
    s.day=365*44;story.schedule(s)
    assert all(x in s.people for x in ['murad','lala_sahin','kara_halil'])
    assert {a.id:a.size for a in s.armies.values()}==before
    s.people['murad'].status='dead';story.schedule(s)
    assert s.people['murad'].status=='dead'


def test_two_successions_preserve_state_and_dynamic_choice():
    s=generation()
    for previous,successor in [('osman','orhan'),('orhan','murad')]:
        s.people[previous].status='dead';story.schedule(s)
        agenda=next(a for a in s.agendas if a['scene']=='succession')
        before=s.to_dict();public=view(s)
        assert public['council']['choices'][0]['id']==successor
        s=apply_command(s,'decide',{'agenda':agenda['id'],'choice':successor})
        assert s.ruler_id==successor
        after=s.to_dict()
        for key in ['gold','arrears','obligations','places','transports']:
            assert after[key]==before[key],key
        for ident,army in before['armies'].items():
            for key in ['cohorts','grain','funds','location','mission']:
                assert after['armies'][ident][key]==army[key]
        s=RulerState.from_dict(after)
    assert s.flags['accession']['to']=='murad'


@pytest.mark.parametrize('scene',dynasty.SCENES)
def test_all_new_choices_and_unauthorised_choice(scene):
    for choice,_ in dynasty.SCENES[scene][2]:
        s=generation();s.ruler_id='orhan' if scene=='orhan_handover' else 'murad';s.people[s.ruler_id].role='ruler';s.agendas=[]
        story.enqueue(s,scene);agenda=s.agendas[0];before=s.to_dict()
        with pytest.raises(RuleError):apply_command(s,'decide',{'agenda':agenda['id'],'choice':'invented'})
        assert s.to_dict()==before
        result=apply_command(s,'decide',{'agenda':agenda['id'],'choice':choice})
        assert scene in result.shown
        assert not any(a['id']==agenda['id'] for a in result.agendas)
        if scene=='murad_education' and choice!='defer':
            assert result.people['murad'].skills==s.people['murad'].skills
            assert result.flags['courses'][0]['ready']==s.day+180


def test_captured_heir_is_not_available():
    s=generation();s.ruler_id='orhan';s.people['murad'].status='captured'
    assert dynasty.heir(s) is None


def test_unknown_obligation_cannot_enter_accounts():
    from campaign.ruler.civil import obligation
    s=new_campaign(3,extended=True)
    with pytest.raises(RuleError):obligation(s,'invented','konur',90,amount=60)
    with pytest.raises(RuleError):obligation(s,'charter','community',90)
    assert not s.obligations
