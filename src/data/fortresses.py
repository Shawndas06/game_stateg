"""
Данные крепостей эпохи Османской экспансии (1299-1453)
Историческое размещение: Анатолия, Балканы
Координаты: x запад→восток, y север→юг (0..3000 x 0..1800)
Крепости ТОЛЬКО на суше, расстояние между ними ≥ 120 px
География: запад=Балканы/Эгейское, восток=Чёрное/центральная Анатолия
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Fortress:
    """Крепость на карте кампании"""
    id: str
    name: str
    name_ru: str
    x: int
    y: int
    faction: str
    base_garrison: int = 50
    is_capital: bool = False
    stage_trigger: Optional[str] = None
    description: str = ""
    fortification: float = 1.0


MAP_LOGICAL_WIDTH = 3000
MAP_LOGICAL_HEIGHT = 1800

# Историческая география (см. карты XIV в.):
# Запад: Балканы (Белград, София, Фессалоника), Эгейское море
# Центр: Фракия (Адрианополь, Галлиполи), Мраморное море, Бурса
# Восток: Константинополь (Босфор), Никомедия, центральная Анатолия (Кония)
FORTESSES_DATA = [
    # === БЕЕЛИК ОСМАНА I (северо-запад Анатолии, между Мраморным морем и внутренностью) ===
    Fortress("sogut", "Söğüt", "Сёгют", 760, 860, "ottoman", 80, is_capital=True),        # Первая столица, южнее Бурсы
    Fortress("bilecik", "Bilecik", "Биледжик", 700, 800, "ottoman", 50),                  # Между Сёгют и Бурсой
    Fortress("karacahisar", "Karacahisar", "Караджахисар", 800, 960, "ottoman", 60),      # Южнее, к Эскишехиру
    Fortress("yarhisar", "Yarhisar", "Ярхисар", 820, 800, "ottoman", 50),                 # Путь к византийским землям
    Fortress("inegol", "İnegöl", "Инегёль", 860, 860, "ottoman", 60),                     # Подступы к Бурсе
    Fortress("yenishehir", "Yenişehir", "Йенишехир", 920, 820, "ottoman", 70),            # Еленос, у границы Вифинии
    Fortress("koyunhisar", "Koyunhisar", "Койунхисар", 980, 760, "ottoman", 80),          # Бафейон (1302)

    # === ГЕРМИЯН (западная Анатолия, южнее османов) ===
    Fortress("kutahya", "Kütahya", "Кютахья", 540, 640, "germiyan", 120),                 # Столица Гермияна
    Fortress("afyon", "Afyon", "Афьон", 620, 540, "germiyan", 90),                        # Афьон-Карахисар
    Fortress("usak", "Uşak", "Ушак", 380, 560, "germiyan", 60),                           # Западнее

    # === КАРАМАН (центральная Анатолия — далеко от побережья) ===
    Fortress("konya", "Konya", "Кония", 1320, 720, "karaman", 200),                       # Столица Карамана, центр Анатолии
    Fortress("aksehir", "Akşehir", "Акшехир", 1000, 560, "karaman", 80),                  # Северо-запад от Коньи
    Fortress("beysehir", "Beyşehir", "Бейшехир", 1120, 660, "karaman", 70),               # У озера Бейшехир

    # === АЙДЫН (эгейское побережье, юго-запад) ===
    Fortress("smyrna", "Smyrna", "Смирна", 180, 720, "aydin", 150),                       # Измир, порт
    Fortress("ephesus", "Ephesus", "Эфес", 140, 820, "aydin", 90),                        # Эфес, южнее Смирны
    Fortress("aydin_city", "Aydın", "Айдын", 300, 660, "aydin", 100),                     # Внутри, у реки

    # === ВИЗАНТИЯ — Анатолия (северо-запад, у Мраморного моря) ===
    Fortress("bursa", "Prusa", "Пруса", 920, 920, "byzantine", 350, fortification=1.2, stage_trigger="sultanate"),  # Бурса, южный берег Мраморного
    Fortress("lopadion", "Lopadion", "Лопадион", 800, 720, "byzantine", 120),             # Улубад, у реки Риндак
    Fortress("nicaea", "Nicaea", "Никея", 1080, 860, "byzantine", 350, fortification=1.25),  # Изник, у озера
    Fortress("milingia", "Milingia", "Мелингия", 1020, 1000, "byzantine", 120),           # Мелингой
    Fortress("thebes", "Thebes", "Фивы", 1220, 920, "byzantine", 150),                    # Фие, южный берег залива
    Fortress("cius", "Cius", "Киос", 860, 800, "byzantine", 100),                         # Гемлик, порт Мраморного — северо-запад Бурсы
    Fortress("kalolimni", "Kalolimni", "Калолимни", 1100, 800, "byzantine", 80),          # Гёльджюк, у залива
    Fortress("nicomedia", "Nicomedia", "Никомедия", 1300, 640, "byzantine", 400, fortification=1.3),  # Измит, восточный берег Мраморного
    Fortress("acra", "Acra", "Акра", 1500, 420, "byzantine", 60),                         # Акча-Хисар, Чёрное море

    # === ВИЗАНТИЯ — Европа (Фракия, Балканы) ===
    Fortress("gallipoli", "Gallipoli", "Галлиполи", 780, 460, "byzantine", 150, fortification=1.2),   # Гелиболу, Дарданеллы
    Fortress("constantinople", "Constantinople", "Константинополь", 1140, 380, "byzantine", 500, fortification=1.5, stage_trigger="empire"),  # Босфор
    Fortress("selymbria", "Selymbria", "Селимврия", 1220, 440, "byzantine", 80),          # Силиври
    Fortress("adrianople", "Adrianople", "Адрианополь", 940, 340, "byzantine", 200, fortification=1.2),  # Эдирне, Фракия
    Fortress("thessalonica", "Thessalonica", "Фессалоника", 480, 420, "byzantine", 180, fortification=1.15),  # Солунь, северная Греция

    # === БОЛГАРИЯ ===
    Fortress("tarnovo", "Tarnovo", "Тырново", 1100, 220, "bulgaria", 150),                # Столица
    Fortress("sofia", "Sofia", "София", 780, 300, "bulgaria", 180),                       # София
    Fortress("plovdiv", "Plovdiv", "Пловдив", 860, 360, "bulgaria", 120),                 # Пловдив (Филиппополь) — западнее Константинополя
    Fortress("varna", "Varna", "Варна", 1380, 180, "bulgaria", 100),                      # Порт на Чёрном море

    # === СЕРБИЯ ===
    Fortress("belgrade", "Belgrade", "Белград", 360, 260, "serbia", 200),                 # Белград, Дунай
    Fortress("nis", "Niš", "Ниш", 620, 400, "serbia", 120),                               # Ниш
    Fortress("skopje", "Skopje", "Скопье", 520, 460, "serbia", 100),                      # Скопье
]


def get_fortress_by_id(fortress_id: str) -> Optional[Fortress]:
    for f in FORTESSES_DATA:
        if f.id == fortress_id:
            return f
    return None


def get_ottoman_starting_fortresses() -> list[Fortress]:
    return [f for f in FORTESSES_DATA if f.faction == "ottoman"]


def get_byzantine_fortresses() -> list[Fortress]:
    return [f for f in FORTESSES_DATA if f.faction == "byzantine"]
