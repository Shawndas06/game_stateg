from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Person:
    id: str
    name: str
    born: int
    location: str
    role: str
    historical: bool = False
    approximate_birth: bool = True
    status: str = 'active'
    health: int = 100
    skills: dict[str, int] = field(default_factory=lambda: {'command': 30, 'stewardship': 30, 'siege': 20, 'logistics': 30})
    experience: dict[str, int] = field(default_factory=dict)
    trust: int = 55
    ambition: int = 30
    wealth: int = 0
    memories: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    travel: dict[str, Any] | None = None
    wounded_until: int = 0
    faction: str = "ottoman"


@dataclass
class Cohort:
    id: str
    troop: str
    count: int
    origin: str
    sponsor: str = 'crown'
    service: str = 'retinue'
    training: int = 0


@dataclass
class Place:
    id: str
    owner: str
    controller: str
    garrison: list[Cohort]
    walls: int
    max_walls: int
    fortress_level: int
    grain: int = 2500
    reserve: int = 80
    prosperity: int = 65
    loyalty: int = 65
    governor: str | None = None
    buildings: list[str] = field(default_factory=list)
    construction: dict[str, Any] | None = None
    training: list[dict[str, Any]] = field(default_factory=list)
    tax: str = 'customary'
    grant: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    unrest: int = 0
    occupied_since: int | None = None
    seized_gold: int = 0


@dataclass
class Army:
    id: str
    faction: str
    location: str
    cohorts: list[Cohort]
    commander: str | None
    deputy: str | None = None
    grain: int = 2400
    morale: int = 90
    engines: int = 0
    mission: dict[str, Any] | None = None
    travel: dict[str, Any] | None = None
    funds: int = 0
    posture: str = 'rear'
    deputy_officer: str = ''
    service_return: bool = False

    @property
    def size(self) -> int:
        return sum(c.count for c in self.cohorts)


@dataclass
class Polity:
    gold: int = 180
    arrears: int = 0
    income: int = 0
    expense: int = 0
    target: str | None = None
    rally: str | None = None
    plan: str = 'guard'
    doctrine: str = 'defense'
    shipping: bool = False
    intelligence: dict[str, dict] = field(default_factory=dict)
    last_war: int = 0


@dataclass
class RulerState:
    seed: int
    scenario: str = 'ruler_v1'
    schema_version: int = 3
    rules_version: int = 3
    content_version: str = 'ruler-chapter-1'
    revision: int = 0
    day: int = 0
    capital: str = 'sogut'
    ruler_id: str = 'osman'
    regent: str | None = 'hasan'
    gold: int = 230
    arrears: int = 0
    counter: int = 0
    archive_seq: int = 0
    places: dict[str, Place] = field(default_factory=dict)
    people: dict[str, Person] = field(default_factory=dict)
    armies: dict[str, Army] = field(default_factory=dict)
    relations: dict[str, dict[str, Any]] = field(default_factory=dict)
    sieges: dict[str, dict[str, Any]] = field(default_factory=dict)
    couriers: list[dict[str, Any]] = field(default_factory=list)
    transports: dict[str, dict[str, Any]] = field(default_factory=dict)
    obligations: dict[str, dict[str, Any]] = field(default_factory=dict)
    appointments: list[dict[str, Any]] = field(default_factory=list)
    edicts: list[dict[str, Any]] = field(default_factory=list)
    agendas: list[dict[str, Any]] = field(default_factory=list)
    shown: list[str] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)
    institutions: dict[str, dict[str, Any]] = field(default_factory=dict)
    reports: list[dict[str, Any]] = field(default_factory=list)
    knowledge: dict[str, dict[str, Any]] = field(default_factory=dict)
    outbox: list[dict[str, Any]] = field(default_factory=list)
    merchant: dict[str, Any] = field(default_factory=lambda: {'gold': 220, 'grain': 9000, 'location': 'kutahya', 'warehouses': {}})
    hazards: dict[str, int] = field(default_factory=dict)
    ending: str | None = None
    polities: dict[str, Polity] = field(default_factory=dict)
    foreign_cargo: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RulerState:
        if (data.get('schema_version'), data.get('rules_version'), data.get('content_version')) not in [(3, 3, 'ruler-chapter-1'), (4, 4, 'ruler-campaign-2')]:
            raise ValueError('Unsupported ruler scenario version')
        from copy import deepcopy
        values = deepcopy(data)
        for k in ['places', 'armies']:
            field_name = 'garrison' if k == 'places' else 'cohorts'
            for value in values[k].values():
                value[field_name] = [Cohort(**c) for c in value[field_name]]
        values['places'] = {k: Place(**v) for k, v in values['places'].items()}
        values['armies'] = {k: Army(**v) for k, v in values['armies'].items()}
        values['people'] = {k: Person(**v) for k, v in values['people'].items()}
        values['polities'] = {k: Polity(**v) for k, v in values.get('polities', {}).items()}
        return cls(**values)
