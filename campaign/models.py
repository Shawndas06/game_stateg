from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from copy import deepcopy
import math
from typing import Any


@dataclass
class Province:
    id: str
    owner: str
    controller: str
    garrison: dict[str, int]
    walls: int
    loyalty: int = 75
    prosperity: int = 70
    buildings: list[str] = field(default_factory=list)
    construction: dict[str, Any] | None = None
    fortress_level: int = 1
    max_walls: int = 0


@dataclass
class Army:
    id: str
    faction: str
    location: str
    troops: dict[str, int]
    supply: int = 100
    morale: int = 100
    engines: int = 0
    order: dict[str, Any] | None = None

    @property
    def size(self) -> int:
        return sum(self.troops.values())


@dataclass
class Siege:
    province: str
    army_id: str
    supplies: int = 100
    morale: int = 100
    breached: bool = False
    mode: str = "blockade"


@dataclass
class Faction:
    id: str
    gold: int = 230
    food: int = 300
    manpower: int = 90
    legitimacy: int = 55
    arrears: int = 0
    knowledge: int = 0
    research: dict[str, Any] | None = None
    technologies: list[str] = field(default_factory=list)
    reforms: list[str] = field(default_factory=list)
    groups: dict[str, int] = field(default_factory=lambda: {"military": 55, "merchants": 50, "administration": 50})
    administrative_base: int = 3


@dataclass
class State:
    seed: int
    schema_version: int = 2
    rules_version: int = 2
    content_version: str = "mediterranean-2"
    revision: int = 0
    turn: int = 0
    capital: str = "sogut"
    ruler: str = "Осман"
    ruler_id: str = "osman"
    ruler_rank: int = 1
    provinces: dict[str, Province] = field(default_factory=dict)
    armies: dict[str, Army] = field(default_factory=dict)
    sieges: dict[str, Siege] = field(default_factory=dict)
    factions: dict[str, Faction] = field(default_factory=dict)
    treaties: dict[str, dict[str, Any]] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    shown_events: list[str] = field(default_factory=list)
    pending_event: str | None = "founding"
    log: list[dict[str, Any]] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    ending: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> State:
        from campaign.content import CAPITALS, CONTENT_VERSION, DYNASTY, FACTIONS, INITIAL_SEAFARERS, PLACES, PLACE_INDEX, PLACE_KINDS, RULES_VERSION
        legacy = (data.get("schema_version"), data.get("rules_version"), data.get("content_version")) == (1, 1, "bithynia-1")
        if not legacy and (data.get("schema_version"), data.get("rules_version"), data.get("content_version")) != (2, RULES_VERSION, CONTENT_VERSION):
            raise ValueError("Unsupported campaign version")
        values = deepcopy({f.name: data[f.name] for f in fields(cls) if f.name in data})
        values.update(schema_version=2, rules_version=RULES_VERSION, content_version=CONTENT_VERSION)
        if legacy:
            ruler = next((r for r in DYNASTY if r['name'] == values['ruler']), DYNASTY[0])
            values.update(ruler_id=ruler['id'], ruler_rank=ruler['rank'])
            if str(values.get('ending', '')).startswith('Первая глава завершена:'):
                values['ending'] = None
            for pid, _, _, _, owner, guards, walls, _ in PLACES:
                values['provinces'].setdefault(pid, asdict(Province(pid, owner, owner, {'militia': guards}, walls, fortress_level=int(walls > 0), max_walls=walls)))
            for fid in FACTIONS:
                if fid not in values['factions']:
                    values['factions'][fid] = asdict(Faction(fid, technologies=['ferries', 'convoys'] if fid in INITIAL_SEAFARERS else []))
                    home = CAPITALS[fid]
                    values['armies'][f'{fid}-1'] = asdict(Army(f'{fid}-1', fid, home, {'militia': 30, 'archers': 10}))
                if fid != 'ottoman':
                    values['factions'][fid]['administrative_base'] = max(3, math.ceil(sum(.25 if PLACE_KINDS[p[0]] == 'village' else 1 for p in PLACES if p[4] == fid)))
            for fid in INITIAL_SEAFARERS:
                for tech in ['ferries', 'convoys']:
                    if tech not in values['factions'][fid]['technologies']: values['factions'][fid]['technologies'].append(tech)
            for i, a in enumerate(FACTIONS):
                for b in list(FACTIONS)[i + 1:]:
                    values['treaties'].setdefault(':'.join(sorted((a, b))), {'status': 'peace', 'trade': False, 'envoys': {}})
        for pid, p in values['provinces'].items():
            p.setdefault('fortress_level', int(PLACE_INDEX[pid][6] > 0))
            p.setdefault('max_walls', max(p['walls'], PLACE_INDEX[pid][6] + (25 if 'walls' in p['buildings'] else 0)))
        for key, model in (("provinces", Province), ("armies", Army), ("sieges", Siege), ("factions", Faction)):
            values[key] = {k: model(**v) for k, v in values[key].items()}
        return cls(**values)
