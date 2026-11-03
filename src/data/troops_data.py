"""
troops_data.py — типы войск по этапу кампании (исторические названия).

Реализует:
- Класс TroopType: id, название, стоимость найма, содержание (upkeep), множитель силы, требуемый этап.
- TROOPS_DATA: ополченцы, конница, лучники, гази (Бейлик); азапы, сипахи, янычары, акынджи (Султанат); тимариоты, капыкулу, топчу (Империя).
- get_troops_for_stage(stage): список типов войск, доступных на данном этапе.
- get_troop_type(troop_id): поиск по id.
"""

from dataclasses import dataclass
from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class TroopType:
    """Один тип войск: стоимость найма (cost), содержание за ход (upkeep), множитель силы в бою (strength), этап появления (required_stage)."""
    id: str
    name_ru: str
    cost: int
    upkeep: float
    strength: float
    required_stage: str


TROOPS_DATA = [
    TroopType("militia", "Ополченцы", 3, 0.8, 0.8, STAGE_BEYLIK),
    TroopType("cavalry", "Конница", 7, 1.2, 1.2, STAGE_BEYLIK),
    TroopType("archers", "Лучники", 5, 1.0, 1.0, STAGE_BEYLIK),
    TroopType("ghazi", "Гази", 4, 0.9, 0.95, STAGE_BEYLIK),
    TroopType("azaps", "Азапы", 6, 1.0, 1.1, STAGE_SULTANATE),
    TroopType("sipahi", "Сипахи", 9, 1.3, 1.3, STAGE_SULTANATE),
    TroopType("janissaries", "Янычары", 12, 1.5, 1.5, STAGE_SULTANATE),
    TroopType("akinci", "Акынджи", 8, 1.1, 1.2, STAGE_SULTANATE),
    TroopType("timariot", "Тимариоты", 10, 1.2, 1.25, STAGE_EMPIRE),
    TroopType("kapikulu", "Капыкулу", 14, 1.6, 1.6, STAGE_EMPIRE),
    TroopType("topcu", "Топчу", 11, 1.4, 1.35, STAGE_EMPIRE),
]


def get_troops_for_stage(stage: str) -> list[TroopType]:
    """Вернуть список типов войск, доступных на данном этапе (бейлик/султанат/империя)."""
    order = {STAGE_BEYLIK: 0, STAGE_SULTANATE: 1, STAGE_EMPIRE: 2}
    s = order.get(stage, 0)
    return [t for t in TROOPS_DATA if order.get(t.required_stage, 0) <= s]


def get_troop_type(troop_id: str) -> TroopType | None:
    """Вернуть тип войск по id или None."""
    for t in TROOPS_DATA:
        if t.id == troop_id:
            return t
    return None
