"""
Данные крепостей эпохи Османской экспансии (1299-1453)
Северо-западная Анатолия — Византия и беелик Османа I
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Fortress:
    """Крепость на карте кампании"""
    id: str
    name: str
    name_ru: str
    # Позиция на карте (x, y) — большое расстояние между крепостями
    x: int
    y: int
    # Принадлежность: ottoman, byzantine
    faction: str
    # Базовый гарнизон — для византийских это защитники, для османских — начальный гарнизон
    base_garrison: int = 50
    # Ключевые крепости для сюжета
    is_capital: bool = False
    # Триггер перехода: sultanate (Бурса)
    stage_trigger: Optional[str] = None
    # Описание для нарратива
    description: str = ""


# Координаты на карте: x — запад→восток, y — север→юг
# Большие расстояния между крепостями (100-150 px)
# Карта: ~1400x650 px
FORTESSES_DATA = [
    # === БЕЕЛИК ОСМАНА I ===
    Fortress(
        id="sogut",
        name="Söğüt",
        name_ru="Сёгют",
        x=180, y=420,
        faction="ottoman",
        base_garrison=80,
        is_capital=True,
        description="Первая столица беелика, укреплённое поселение. Осман I провозгласил независимость в 1299 году."
    ),
    Fortress(
        id="karacahisar",
        name="Karacahisar",
        name_ru="Караджахисар",
        x=320, y=500,
        faction="ottoman",
        base_garrison=60,
        description="Крепость около Эскишехира. Одна из первых османских цитаделей."
    ),
    Fortress(
        id="bilecik",
        name="Bilecik",
        name_ru="Биледжик",
        x=250, y=350,
        faction="ottoman",
        base_garrison=50,
        description="Одна из первых крепостей, захваченных Османом I."
    ),
    Fortress(
        id="yarhisar",
        name="Yarhisar",
        name_ru="Ярхисар",
        x=350, y=380,
        faction="ottoman",
        base_garrison=50,
        description="Крепость на пути к византийским землям."
    ),
    Fortress(
        id="inegol",
        name="İnegöl",
        name_ru="Инегёль",
        x=420, y=420,
        faction="ottoman",
        base_garrison=60,
        description="Ключевая крепость на подступах к Бурсе."
    ),
    Fortress(
        id="yenishehir",
        name="Yenişehir",
        name_ru="Йенишехир",
        x=480, y=380,
        faction="ottoman",
        base_garrison=70,
        description="Еленос. Османская крепость у границы с Вифинией."
    ),
    Fortress(
        id="koyunhisar",
        name="Koyunhisar",
        name_ru="Койунхисар",
        x=550, y=350,
        faction="ottoman",
        base_garrison=80,
        description="Бафейон. Место битвы при Бафее (1302) — первая крупная победа османов над византийцами."
    ),

    # === ВИЗАНТИЙСКАЯ ИМПЕРИЯ (северо-западная Анатолия) ===
    Fortress(
        id="nicomedia",
        name="Nicomedia",
        name_ru="Никомедия",
        x=950, y=180,
        faction="byzantine",
        base_garrison=400,
        description="Измит. Крупнейший город-крепость в регионе, центр византийской власти в Вифинии."
    ),
    Fortress(
        id="nicaea",
        name="Nicaea",
        name_ru="Никея",
        x=820, y=300,
        faction="byzantine",
        base_garrison=350,
        description="Изник. Древняя Никея — одна из важнейших византийских крепостей Анатолии."
    ),
    Fortress(
        id="bursa",
        name="Prusa",
        name_ru="Пруса",
        x=700, y=400,
        faction="byzantine",
        base_garrison=350,
        stage_trigger="sultanate",
        description="Бурса. Падение крепости — восхождение Османского Султаната (1326)."
    ),
    Fortress(
        id="thebes",
        name="Thebes",
        name_ru="Фивы",
        x=880, y=320,
        faction="byzantine",
        base_garrison=150,
        description="Фие. Крепость на южном берегу Никомедийского залива."
    ),
    Fortress(
        id="lopadion",
        name="Lopadion",
        name_ru="Лопадион",
        x=580, y=250,
        faction="byzantine",
        base_garrison=120,
        description="Улубад. Крепость на реке Риндак (Муданья)."
    ),
    Fortress(
        id="cius",
        name="Cius",
        name_ru="Киос",
        x=780, y=220,
        faction="byzantine",
        base_garrison=100,
        description="Гемлик. Порт на Мраморном море."
    ),
    Fortress(
        id="kalolimni",
        name="Kalolimni",
        name_ru="Калолимни",
        x=920, y=250,
        faction="byzantine",
        base_garrison=80,
        description="Гёльджюк. Укрепление у залива."
    ),
    Fortress(
        id="milingia",
        name="Milingia",
        name_ru="Мелингия",
        x=850, y=400,
        faction="byzantine",
        base_garrison=120,
        description="Мелингой. Крепость в Вифинии."
    ),
    Fortress(
        id="acra",
        name="Acra",
        name_ru="Акра",
        x=1000, y=100,
        faction="byzantine",
        base_garrison=60,
        description="Акча-Хисар. Укрепление на Чёрном море."
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
