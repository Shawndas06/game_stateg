from copy import deepcopy
import pytest
from campaign.engine import RuleError
from campaign.ruler.engine import new_campaign,apply_command,view
from campaign.ruler.civil import institution_help


@pytest.mark.parametrize('status',[None,'preparing','active'])
def test_named_prerequisite_matches_command_and_public_view(status):
    s=new_campaign(11,extended=True)
    if status:s.institutions['scribes']={'status':status,'ready':s.day+60}
    hint=next(x for x in view(s)['available_institutions'] if x['id']=='land_register')
    assert hint['reasons']==institution_help(s,'land_register')['reasons']
    before=deepcopy(s.to_dict())
    if status!='active':
        assert 'Служба писцов' in hint['reasons'][0]
        assert ('60 дней' in hint['reasons'][0])==(status=='preparing')
        with pytest.raises(RuleError,match='Служба писцов'):apply_command(s,'institution',{'institution':'land_register'})
        assert s.to_dict()==before
    else:
        result=apply_command(s,'institution',{'institution':'land_register'})
        assert result.gold==s.gold-100


@pytest.mark.parametrize('problem',['money','workers','busy','walls','unsettled','built'])
def test_construction_explanation_and_atomic_refusal(problem):
    s=new_campaign(11,extended=True);p=s.places['sogut'];kind='granary'
    if problem=='money':s.gold=0
    if problem=='workers':kind='fortress';p.fortress_level=0;p.reserve=0
    if problem=='busy':p.construction={'building':'granary','work':32,'workers':0}
    if problem=='walls':kind='repair';p.walls=p.max_walls
    if problem=='unsettled':p.owner='byzantine'
    if problem=='built':p.buildings.append('granary')
    hint=next(x for x in view(s)['provinces']['sogut']['construction_options'] if x['id']==kind)
    assert hint['reasons'] and all(len(x)>20 for x in hint['reasons'])
    before=s.to_dict()
    with pytest.raises(RuleError):apply_command(s,'construction',{'province':'sogut','building':kind})
    assert s.to_dict()==before


@pytest.mark.parametrize('province',['sogut','domanic'])
def test_first_decision_and_granary_legal_continuation(province):
    s=new_campaign(11,extended=True)
    s=apply_command(s,'begin_reign',{})
    before=s.gold
    s=apply_command(s,'decide',{'agenda':s.agendas[0]['id'],'choice':'stewardship'})
    assert s.gold==before-25
    s=apply_command(s,'construction',{'province':province,'building':'granary'})
    assert s.gold==before-85
    assert s.places[province].construction or any(e['province']==province for e in s.edicts)
    if province!='sogut':
        option=next(x for x in view(s)['provinces'][province]['construction_options'] if x['id']=='granary')
        assert 'уже в пути' in option['reasons'][0]
    for _ in range(95):
        s=apply_command(s,'advance',{'days':1,'until_event':False})
        if 'granary' in s.places[province].buildings:break
    assert 'granary' in s.places[province].buildings
    assert s.places[province].construction is None
    assert any(r['kind']=='building' and 'завершены' in r['text'] for r in s.reports)
    assert next(x for x in view(s)['provinces'][province]['construction_options'] if x['id']=='granary')['reasons']
