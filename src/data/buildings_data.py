"""
Здания и улучшения крепостей.

Мечеть, рынок, казармы, катапульты, медресе, стены, алтарь.
Эффекты: доход, укрепления, найм, гарнизон, торговля, осада.
"""

from dataclasses import dataclass
from typing import Optional

from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class Building:
    """Здание в крепости"""
    id: str
    name_ru: str
    description: str
    cost: int
    turns_to_build: int
    required_stage: str
    # Эффекты: income_plus, income_mult, fortification, siege_bonus, hire_bonus
    income_plus: int = 0
    income_mult: float = 1.0
    fortification: float = 0.0
    siege_bonus: float = 0.0  # Бонус к осаде (катапульты)
    hire_bonus: float = 0.0
    garrison_bonus: int = 0
    trade_bonus: float = 0.0


BUILDINGS_DATA = [
    Building("walls_1", "Укрепления I", "Каменные стены", 80, 2, STAGE_BEYLIK, fortification=0.1),
    Building("walls_2", "Укрепления II", "Двойные стены", 200, 3, STAGE_SULTANATE, fortification=0.2),
    Building("walls_3", "Укрепления III", "Цитадель", 400, 4, STAGE_EMPIRE, fortification=0.3),
    Building("mosque", "Мечеть", "Центр веры и культуры", 150, 3, STAGE_BEYLIK, income_plus=3, income_mult=1.05),
    Building("mosque_great", "Большая мечеть", "Улемы и медресе", 350, 4, STAGE_SULTANATE, income_plus=8, income_mult=1.1),
    Building("market", "Рынок", "Торговля и ремесло", 100, 2, STAGE_BEYLIK, income_plus=2, trade_bonus=0.1),
    Building("market_grand", "Большой базар", "Караван-сарай", 250, 3, STAGE_SULTANATE, income_plus=6, trade_bonus=0.25),
    Building("barracks", "Казармы", "Набор войск", 120, 2, STAGE_BEYLIK, hire_bonus=-0.1),
    Building("barracks_elite", "Элитные казармы", "Янычары", 300, 4, STAGE_SULTANATE, hire_bonus=-0.2, garrison_bonus=20),
    Building("catapult_workshop", "Мастерская катапульт", "Осадные орудия", 180, 3, STAGE_BEYLIK, siege_bonus=0.15),
    Building("catapult_grand", "Мастерская требушетов", "Тяжёлые орудия", 400, 5, STAGE_SULTANATE, siege_bonus=0.3),
    Building("university", "Медресе", "Учёные и писцы", 220, 4, STAGE_SULTANATE, income_plus=5, income_mult=1.08),
    Building("university_grand", "Высшее медресе", "Академия наук", 500, 6, STAGE_EMPIRE, income_plus=12, income_mult=1.15),
    Building("altar", "Алтарь газа", "Святилище войны", 100, 2, STAGE_BEYLIK, fortification=0.05),
]


def get_building(building_id: str) -> Optional[Building]:
    for b in BUILDINGS_DATA:
        if b.id == building_id:
            return b
    return None
