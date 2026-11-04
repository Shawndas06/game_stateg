"""Versioned scenario dispatch; legacy snapshots never enter the new rules."""
from campaign import engine as legacy
from campaign.models import State
from campaign.ruler.models import RulerState
from campaign.ruler import engine as ruler


def load_state(data):
    return RulerState.from_dict(data) if data.get('scenario')=='ruler_v1' else State.from_dict(data)


def new_campaign(seed,scenario='legacy',campaign_mode='chapter'):
    if scenario=='ruler_v1':return ruler.new_campaign(seed,extended=campaign_mode in ['long','realm'],living=campaign_mode=='realm')
    if scenario=='legacy':return legacy.new_campaign(seed)
    raise legacy.RuleError('Неизвестный сценарий')


def apply_command(state,kind,payload):
    return ruler.apply_command(state,kind,payload) if isinstance(state,RulerState) else legacy.apply_command(state,kind,payload)


def view(state):
    return ruler.view(state) if isinstance(state,RulerState) else legacy.view(state)
