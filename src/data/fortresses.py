"""
Данные крепостей эпохи Османской экспансии (1299-1453)
Все крепости Анатолии и Балкан с историческими координатами
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Fortress:
    """Крепость на карте кампании"""
    id: str
    name: str
    name_ru: str
    # Позиция на карте (x, y) - большое расстояние между крепостями
    x: int
    y: int
    # Принадлежность: ottoman, byzantine, neutral
    faction: str
    # Ключевые крепости для сюжета
    is_capital: bool = False
    # Триггер перехода: sultanate (Бурса), empire (Константинополь)
    stage_trigger: Optional[str] = None
    # Описание для нарратива
    description: str = ""


# Крепости с исторически большими расстояниями друг от друга
# Координаты в пикселях на карте 1200x600
FORTESSES_DATA = [
    # === АНАТОЛИЯ - Начальные территории ===
    Fortress(
        id="sogut",
        name="Söğüt",
        name_ru="Сёгют",
        x=180, y=320,
        faction="ottoman",
        is_capital=True,
        description="Колыбель Османского беелика. Осман I провозгласил независимость в 1299 году."
    ),
    Fortress(
        id="bilecik",
        name="Bilecik",
        name_ru="Биледжик",
        x=240, y=280,
        faction="ottoman",
        description="Одна из первых крепостей, захваченных Османом I."
    ),
    Fortress(
        id="inyegol",
        name="İnegöl",
        name_ru="Инегёль",
        x=320, y=300,
        faction="ottoman",
        description="Ключевая крепость на пути к Бурсе."
    ),
    # === БУРСА - Переход в Султанат ===
    Fortress(
        id="bursa",
        name="Bursa",
        name_ru="Бурса",
        x=420, y=260,
        faction="byzantine",
        stage_trigger="sultanate",
        description="Византийская Пруса. Падение крепости — восхождение Османского Султаната (1326)."
    ),
    Fortress(
        id="nizaea",
        name="Nicaea",
        name_ru="Никея",
        x=480, y=220,
        faction="byzantine",
        description="Древняя Никея — одна из важнейших византийских крепостей Анатолии."
    ),
    Fortress(
        id="nicomedia",
        name="Nicomedia",
        name_ru="Никомедия",
        x=560, y=200,
        faction="byzantine",
        description="Столица Византии до Константинополя. Изумит."
    ),
    # === ПРОЛИВЫ И ГАЛЛИПОЛИ ===
    Fortress(
        id="gallipoli",
        name="Gallipoli",
        name_ru="Галлиполи",
        x=580, y=380,
        faction="byzantine",
        description="Ключ к проливам. Первая османская крепость в Европе (1354)."
    ),
    Fortress(
        id="tzympe",
        name="Tzympe",
        name_ru="Цимпа",
        x=540, y=360,
        faction="byzantine",
        description="Крепость у пролива Дарданеллы."
    ),
    # === БАЛКАНЫ - Фракия ===
    Fortress(
        id="adrianople",
        name="Adrianople",
        name_ru="Адрианополь",
        x=680, y=340,
        faction="byzantine",
        description="Эдирне. Станет второй османской столицей в Европе (1361)."
    ),
    Fortress(
        id="philippopolis",
        name="Philippopolis",
        name_ru="Пловдив",
        x=720, y=420,
        faction="neutral",
        description="Филиппополь — ворота в глубинные Балканы."
    ),
    Fortress(
        id="thessaloniki",
        name="Thessaloniki",
        name_ru="Салоники",
        x=640, y=480,
        faction="neutral",
        description="Второй по величине город Византии."
    ),
    # === КОНСТАНТИНОПОЛЬ ===
    Fortress(
        id="constantinople",
        name="Constantinople",
        name_ru="Константинополь",
        x=620, y=260,
        faction="byzantine",
        stage_trigger="empire",
        description="Новый Рим. Падение в 1453 — рождение Османской Империи."
    ),
    Fortress(
        id="heraclea",
        name="Heraclea",
        name_ru="Гераклея",
        x=500, y=320,
        faction="byzantine",
        description="Крепость на Мраморном море."
    ),
]


def get_fortress_by_id(fortress_id: str) -> Optional[Fortress]:
    """Получить крепость по ID"""
    for f in FORTESSES_DATA:
        if f.id == fortress_id:
            return f
    return None


def get_ottoman_starting_fortresses() -> list[Fortress]:
    """Крепости, принадлежащие Османам в начале игры"""
    return [f for f in FORTESSES_DATA if f.faction == "ottoman"]


def get_byzantine_fortresses() -> list[Fortress]:
    """Византийские крепости"""
    return [f for f in FORTESSES_DATA if f.faction == "byzantine"]
