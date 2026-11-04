"""Historic landing rights, local harbour works and paid carrier services."""
from campaign.content import PLACE_INDEX
from campaign.world import PORT_ACCESS

PORT_COST, PORT_DAYS, PORT_WORKERS = 120, 120, 12

def landing(pid):
    # Includes documented river ports and towns served by an outlying harbour.
    return bool(PLACE_INDEX[pid][7])

def harbour(s, pid):
    p=s.places[pid]
    return landing(pid) and 'harbor' in p.buildings and p.owner==p.controller

def navigation(s):
    return 'navigation' in s.flags.get('statecraft',{}).get('skills',{}).get('ottoman',[])

def status(s,p):
    if not landing(p.id):return None
    return {'name':'Оборудованный порт' if 'harbor' in p.buildings else 'Историческая пристань',
            'developed':'harbor' in p.buildings,'operational':p.owner==p.controller,
            'access':PORT_ACCESS.get(p.id,'Морская пристань у прибрежного поселения'),
            'description':'Причалы, склады и местные перевозчики. Организованный порт открывает службу морских перевозок; содержание — 3 монеты за 30 дней.'}
