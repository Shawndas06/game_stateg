from campaign.content import PLACES, MAP_SIZES
from campaign.engine import catalog


def test_all_settlements_have_display_scale_without_moving_their_coordinates():
    places=catalog()['places']
    assert len(places)==len(PLACES)==len(MAP_SIZES)
    for site,original in zip(places,PLACES):
        assert site['id']==original[0] and (site['lon'],site['lat'])==original[2:4]
        assert site['map_size'] in {'small','medium','large'}
    sizes={p['id']:p['map_size'] for p in places}
    assert sizes['sogut']=='small' and sizes['karacahisar']=='medium'
    assert sizes['bursa']=='medium' and sizes['constantinople']=='large'
    assert sizes['cairo']=='large' and sizes['domanic']=='small'
