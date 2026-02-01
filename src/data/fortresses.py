"""
Данные крепостей эпохи Османской экспансии (1299-1453)
Историческое размещение: Анатолия, Балканы
Координаты: x запад→восток, y север→юг (0..4800 x 0..2880)
Минимальное расстояние между крепостями: 140 px (логические единицы)
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
    description: str = ""
    fortification: float = 1.0


# Логический размер карты (масштаб 1.6×)
MAP_LOGICAL_WIDTH = 4800
MAP_LOGICAL_HEIGHT = 2880

# Историческая география.
FORTESSES_DATA = [
    # === ОСМАНЫ (северо-запад Анатолии) ===
    Fortress("sogut", "Söğüt", "Сёгют", 1184, 1440, "ottoman", 80, is_capital=True),
    Fortress("bilecik", "Bilecik", "Биледжик", 1056, 1312, "ottoman", 50),
    Fortress("karacahisar", "Karacahisar", "Караджахисар", 1312, 1600, "ottoman", 60),
    Fortress("yarhisar", "Yarhisar", "Ярхисар", 1280, 1248, "ottoman", 50),
    Fortress("inegol", "İnegöl", "Инегёль", 1408, 1440, "ottoman", 60),
    Fortress("yenishehir", "Yenişehir", "Йенишехир", 1536, 1280, "ottoman", 70),
    Fortress("koyunhisar", "Koyunhisar", "Койунхисар", 1632, 1152, "ottoman", 80),

    # === ГЕРМИЯН ===
    Fortress("kutahya", "Kütahya", "Кютахья", 800, 992, "germiyan", 120),
    Fortress("afyon", "Afyon", "Афьон", 960, 800, "germiyan", 90),
    Fortress("usak", "Uşak", "Ушак", 544, 864, "germiyan", 60),
    Fortress("simav", "Simav", "Симав", 704, 1056, "germiyan", 50),

    # === КАРАМАН ===
    Fortress("konya", "Konya", "Кония", 2144, 1216, "karaman", 200),
    Fortress("aksehir", "Akşehir", "Акшехир", 1568, 832, "karaman", 80),
    Fortress("beysehir", "Beyşehir", "Бейшехир", 1824, 1120, "karaman", 70),
    Fortress("nigde", "Niğde", "Нигде", 2336, 1312, "karaman", 100),
    Fortress("larende", "Larende", "Ларинда", 2080, 1344, "karaman", 90),

    # === АЙДЫН (эгейское побережье) ===
    Fortress("smyrna", "Smyrna", "Смирна", 256, 1088, "aydin", 150),
    Fortress("ephesus", "Ephesus", "Эфес", 192, 1376, "aydin", 90),
    Fortress("aydin_city", "Aydın", "Айдын", 512, 992, "aydin", 100),
    Fortress("tyrha", "Tyrha", "Тирха", 352, 1280, "aydin", 60),

    # === МЕНТЕШЕ (юго-запад) ===
    Fortress("mugla", "Muğla", "Мугла", 320, 1568, "mentese", 100),
    Fortress("milas", "Milas", "Милас", 448, 1440, "mentese", 80),
    Fortress("peçin", "Peçin", "Печин", 384, 1504, "mentese", 70),

    # === САРУХАН (запад) ===
    Fortress("manisa", "Manisa", "Маниса", 608, 1184, "saruhan", 120),
    Fortress("nif", "Nif", "Ниф", 544, 1344, "saruhan", 60),
    Fortress("gordes", "Gördes", "Гёрдес", 736, 1088, "saruhan", 70),

    # === ДЖАНДАР/КАНДАР (Чёрное море) ===
    Fortress("kastamonu", "Kastamonu", "Кастамону", 1888, 768, "candar", 150),
    Fortress("sinop", "Sinop", "Синоп", 2208, 480, "candar", 120),
    Fortress("cankiri", "Çankırı", "Чанкыры", 1728, 896, "candar", 80),

    # === ХАМИД (центральная Анатолия) ===
    Fortress("isparta", "Isparta", "Испарта", 1248, 1376, "hamid", 100),
    Fortress("egirdir", "Eğirdir", "Эгирдир", 1440, 1184, "hamid", 80),
    Fortress("ulusuborga", "Uluborlu", "Улуборлу", 1184, 1280, "hamid", 60),

    # === ТЕКЕ (юг, Анталья) ===
    Fortress("antalya", "Antalya", "Анталья", 1024, 1728, "teke", 130),
    Fortress("alanya", "Alanya", "Аланья", 1536, 1696, "teke", 100),
    Fortress("korkuteli", "Korkuteli", "Коркутели", 1152, 1600, "teke", 70),

    # === КАРАСЫ (северо-запад Анатолии) ===
    Fortress("balikesir", "Balıkesir", "Балыкесир", 864, 1088, "karasi", 120),
    Fortress("bergama", "Bergama", "Бергама", 480, 1088, "karasi", 90),
    Fortress("edremit", "Edremit", "Эдремит", 576, 992, "karasi", 70),

    # === ВИЗАНТИЯ — Анатолия ===
    Fortress("bursa", "Prusa", "Пруса", 1536, 1536, "byzantine", 350, fortification=1.2),
    Fortress("lopadion", "Lopadion", "Лопадион", 1216, 1088, "byzantine", 120),
    Fortress("nicaea", "Nicaea", "Никея", 1792, 1440, "byzantine", 350, fortification=1.25),
    Fortress("milingia", "Milingia", "Мелингия", 1664, 1664, "byzantine", 120),
    Fortress("thebes", "Thebes", "Фивы", 1984, 1536, "byzantine", 150),
    Fortress("cius", "Cius", "Киос", 1408, 1180, "byzantine", 100),
    Fortress("kalolimni", "Kalolimni", "Калолимни", 1824, 1344, "byzantine", 80),
    Fortress("nicomedia", "Nicomedia", "Никомедия", 2112, 960, "byzantine", 400, fortification=1.3),
    Fortress("acra", "Acra", "Акра", 2432, 608, "byzantine", 60),

    # === ВИЗАНТИЯ — Европа ===
    Fortress("gallipoli", "Gallipoli", "Галлиполи", 1184, 672, "byzantine", 150, fortification=1.2),
    Fortress("constantinople", "Constantinople", "Константинополь", 1856, 544, "byzantine", 500, fortification=1.5),
    Fortress("selymbria", "Selymbria", "Селимврия", 1984, 640, "byzantine", 80),
    Fortress("adrianople", "Adrianople", "Адрианополь", 1568, 480, "byzantine", 200, fortification=1.2),
    Fortress("thessalonica", "Thessalonica", "Фессалоника", 704, 608, "byzantine", 180, fortification=1.15),

    # === БОЛГАРИЯ ===
    Fortress("tarnovo", "Tarnovo", "Тырново", 1792, 288, "bulgaria", 150),
    Fortress("sofia", "Sofia", "София", 1184, 416, "bulgaria", 180),
    Fortress("plovdiv", "Plovdiv", "Пловдив", 1088, 512, "bulgaria", 120),
    Fortress("varna", "Varna", "Варна", 2240, 224, "bulgaria", 100),
    Fortress("vidin", "Vidin", "Видин", 960, 320, "bulgaria", 80),

    # === СЕРБИЯ ===
    Fortress("belgrade", "Belgrade", "Белград", 512, 352, "serbia", 200),
    Fortress("nis", "Niš", "Ниш", 928, 576, "serbia", 120),
    Fortress("skopje", "Skopje", "Скопье", 768, 672, "serbia", 100),
    Fortress("prizren", "Prizren", "Призрен", 640, 768, "serbia", 70),

    # === ВЕНГРИЯ ===
    Fortress("buda", "Buda", "Буда", 384, 224, "hungary", 250),
    Fortress("visegrad", "Visegrád", "Вышеград", 512, 160, "hungary", 100),
    Fortress("szeged", "Szeged", "Сегед", 672, 320, "hungary", 80),
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
