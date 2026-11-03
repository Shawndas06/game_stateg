"""
fortresses.py — крепости кампании с реальными координатами (WGS84).

x, y в логических единицах карты вычисляются из lon/lat через geo_projection (эквиректанглярная проекция).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.map.geo_projection import lonlat_to_map


@dataclass
class Fortress:
    """Крепость: географические координаты и производные x, y для игровой логики и отрисовки."""
    id: str
    name: str
    name_ru: str
    lon: float
    lat: float
    faction: str
    base_garrison: int = 50
    is_capital: bool = False
    description: str = ""
    fortification: float = 1.0
    x: int = field(init=False)
    y: int = field(init=False)

    def __post_init__(self) -> None:
        # Если для крепости задана ручная позиция (откалибрована по художке) —
        # она имеет приоритет над геопроекцией и любыми offset'ами.
        manual = MANUAL_FORTRESS_POSITIONS.get(self.id)
        if manual is not None:
            self.x, self.y = manual
            return
        self.x, self.y = lonlat_to_map(self.lon, self.lat)
        dx, dy = FORTRESS_MAP_OFFSETS.get(self.id, (0, 0))
        self.x += dx
        self.y += dy


# === MANUAL_FORTRESS_POSITIONS START ===
# Ручные позиции в логических пикселях, откалиброванные по нарисованным иконкам
# крепостей на художественной карте через scripts/calibrate_fortresses.py.
# Имеют АБСОЛЮТНЫЙ приоритет над lon/lat-проекцией и FORTRESS_MAP_OFFSETS.
# Заполняется автоматически через scripts/apply_fortress_positions.py.
MANUAL_FORTRESS_POSITIONS: dict[str, tuple[int, int]] = {}
# === MANUAL_FORTRESS_POSITIONS END ===


# Точечные смещения для крепостей, которые при чистой геопроекции попадают в синюю
# заливку моря на художественной PNG-карте (используются только если нет ручной
# калибровки). Применяются ТОЛЬКО к id, отсутствующим в MANUAL_FORTRESS_POSITIONS.
FORTRESS_MAP_OFFSETS: dict[str, tuple[int, int]] = {
    # МИНИМАЛЬНЫЕ корректировки: сдвигаем ТОЛЬКО те крепости, которые при чистой
    # геопроекции попадают в синюю заливку моря на художественной карте. Сдвиг —
    # до ближайшего пикселя суши, без растаскивания плотных групп.
    # Все остальные 68 крепостей стоят на своих ИСТОРИЧЕСКИХ координатах без смещений.
    # Визуальное разведение слипшихся иконок выполняется в map_renderer на этапе
    # отрисовки (force-directed layout), не затрагивая логические позиции.
    'balikesir'       : (  +69,   +66),  # с залива Эдремит на материк
    'gallipoli'       : (  -76,   +58),  # с пролива Дарданеллы на сушу полуострова
    'varna'           : (  -58,   -68),  # с Чёрного моря на берег
    'alexandria'      : ( +214,  -186),  # на видимый кусок дельты Нила
    'tunis'           : (  -42,   -30),  # с Тунисского залива на материк
    'tripoli_maghreb' : ( +144,  -151),  # на ливийское побережье
}


# Координаты городов — приближённые современные/исторические центры (игровая абстракция).

FORTESSES_DATA = [
    # === ОСМАНЫ === (1299 г. — только Сёгют, остальные византийские пограничные форты)
    Fortress("sogut", "Söğüt", "Сёгют", 30.179, 39.792, "ottoman", 80, is_capital=True),
    # Биледжик, Караджахисар, Ярхисар, Инегёль, Йенишехир, Койунхисар — византийские
    # форты, которые Осман I захватит постепенно в 1299–1326 гг. На старте они НЕ
    # принадлежат османам.
    Fortress("bilecik", "Bilecik", "Биледжик", 29.979, 40.143, "byzantine", 50),
    Fortress("karacahisar", "Karacahisar", "Караджахисар", 30.561, 39.903, "byzantine", 60),
    Fortress("yarhisar", "Yarhisar", "Ярхисар", 29.651, 40.238, "byzantine", 50),
    Fortress("inegol", "İnegöl", "Инегёль", 29.513, 40.078, "byzantine", 60),
    Fortress("yenishehir", "Yenişehir", "Йенишехир", 29.651, 40.268, "byzantine", 70),
    Fortress("koyunhisar", "Koyunhisar", "Койунхисар", 30.094, 40.593, "byzantine", 80),
    # === ГЕРМИЯН ===
    Fortress("kutahya", "Kütahya", "Кютахья", 29.983, 39.418, "germiyan", 120),
    Fortress("afyon", "Afyon", "Афьон", 30.538, 38.764, "germiyan", 90),
    Fortress("usak", "Uşak", "Ушак", 29.407, 38.682, "germiyan", 60),
    Fortress("simav", "Simav", "Симав", 29.982, 39.088, "germiyan", 50),
    # === КАРАМАН ===
    Fortress("konya", "Konya", "Кония", 32.484, 37.871, "karaman", 200),
    Fortress("aksehir", "Akşehir", "Акшехир", 31.416, 38.357, "karaman", 80),
    Fortress("beysehir", "Beyşehir", "Бейшехир", 31.724, 37.676, "karaman", 70),
    Fortress("nigde", "Niğde", "Нигде", 34.685, 37.969, "karaman", 100),
    Fortress("larende", "Karaman", "Ларинда", 33.215, 37.181, "karaman", 90),
    # === АЙДЫН ===
    Fortress("smyrna", "Smyrna", "Смирна", 27.142, 38.423, "aydin", 150),
    Fortress("ephesus", "Selçuk", "Эфес", 27.367, 37.950, "aydin", 90),
    Fortress("aydin_city", "Aydın", "Айдын", 27.836, 37.844, "aydin", 100),
    Fortress("tyrha", "Tire", "Тирха", 27.731, 38.088, "aydin", 60),
    # === МЕНТЕШЕ ===
    Fortress("mugla", "Muğla", "Мугла", 28.367, 37.215, "mentese", 100),
    Fortress("milas", "Milas", "Милас", 27.780, 37.316, "mentese", 80),
    Fortress("peçin", "Peçin", "Печин", 29.032, 37.103, "mentese", 70),
    # === САРУХАН ===
    Fortress("manisa", "Manisa", "Маниса", 27.429, 38.614, "saruhan", 120),
    Fortress("nif", "Kemalpaşa", "Ниф", 27.417, 38.428, "saruhan", 60),
    Fortress("gordes", "Gördes", "Гёрдес", 27.601, 38.961, "saruhan", 70),
    # === ДЖАНДАР ===
    Fortress("kastamonu", "Kastamonu", "Кастамону", 33.776, 41.376, "candar", 150),
    Fortress("sinop", "Sinop", "Синоп", 35.155, 42.027, "candar", 120),
    Fortress("cankiri", "Çankırı", "Чанкыры", 33.615, 40.601, "candar", 80),
    # === ХАМИД ===
    Fortress("isparta", "Isparta", "Испарта", 30.553, 37.765, "hamid", 100),
    Fortress("egirdir", "Eğirdir", "Эгирдир", 30.848, 37.874, "hamid", 80),
    Fortress("ulusuborga", "Uluborlu", "Улуборлу", 30.142, 38.079, "hamid", 60),
    # === ТЕКЕ ===
    Fortress("antalya", "Antalya", "Анталья", 30.713, 36.896, "teke", 130),
    Fortress("alanya", "Alanya", "Аланья", 31.999, 36.544, "teke", 100),
    Fortress("korkuteli", "Korkuteli", "Коркутели", 29.636, 37.066, "teke", 70),
    # === КАРАСЫ ===
    Fortress("balikesir", "Balıkesir", "Балыкесир", 27.886, 39.647, "karasi", 120),
    Fortress("bergama", "Bergama", "Бергама", 27.176, 39.118, "karasi", 90),
    Fortress("edremit", "Edremit", "Эдремит", 27.024, 39.596, "karasi", 70),
    # === ВИЗАНТИЯ — Анатолия и Мраморное ===
    Fortress("bursa", "Prusa", "Пруса", 29.061, 40.182, "byzantine", 350, fortification=1.2),
    Fortress("lopadion", "Lopadion", "Лопадион", 28.908, 40.038, "byzantine", 120),
    Fortress("nicaea", "Nicaea", "Никея", 29.721, 40.428, "byzantine", 350, fortification=1.25),
    Fortress("milingia", "Miletus", "Милет", 27.278, 37.531, "byzantine", 150),
    Fortress("thebes", "Athens", "Афины", 23.727, 37.984, "byzantine", 150),
    Fortress("cius", "Cius", "Киос", 29.088, 40.433, "byzantine", 100),
    Fortress("kalolimni", "Mudanya", "Калолимни", 28.882, 40.375, "byzantine", 80),
    Fortress("nicomedia", "Nicomedia", "Никомедия", 29.916, 40.765, "byzantine", 400, fortification=1.3),
    Fortress("acra", "Trebizond", "Трапезунд", 39.720, 41.003, "byzantine", 60),
    # === ВИЗАНТИЯ — Балканы и Константинополь ===
    Fortress("gallipoli", "Gallipoli", "Галлиполи", 26.676, 40.413, "byzantine", 150, fortification=1.2),
    Fortress("constantinople", "Constantinople", "Константинополь", 28.978, 41.008, "byzantine", 500, fortification=1.5),
    Fortress("selymbria", "Selymbria", "Селимврия", 28.246, 41.073, "byzantine", 80),
    Fortress("adrianople", "Adrianople", "Адрианополь", 26.556, 41.677, "byzantine", 200, fortification=1.2),
    Fortress("thessalonica", "Thessalonica", "Фессалоника", 22.944, 40.640, "byzantine", 180, fortification=1.15),
    # === БОЛГАРИЯ ===
    Fortress("tarnovo", "Tarnovo", "Тырново", 25.656, 43.081, "bulgaria", 150),
    Fortress("sofia", "Sofia", "София", 23.321, 42.698, "bulgaria", 180),
    Fortress("plovdiv", "Plovdiv", "Пловдив", 24.745, 42.136, "bulgaria", 120),
    Fortress("varna", "Varna", "Варна", 27.911, 43.214, "bulgaria", 100),
    Fortress("vidin", "Vidin", "Видин", 22.872, 43.991, "bulgaria", 80),
    # === СЕРБИЯ ===
    Fortress("belgrade", "Belgrade", "Белград", 20.448, 44.786, "serbia", 200),
    Fortress("nis", "Niš", "Ниш", 21.896, 43.321, "serbia", 120),
    Fortress("skopje", "Skopje", "Скопье", 21.432, 41.998, "serbia", 100),
    Fortress("prizren", "Prizren", "Призрен", 20.739, 42.213, "serbia", 70),
    # === ВЕНГРИЯ ===
    Fortress("buda", "Buda", "Буда", 19.040, 47.498, "hungary", 250),
    Fortress("visegrad", "Visegrád", "Вышеград", 18.910, 47.785, "hungary", 100),
    Fortress("szeged", "Szeged", "Сегед", 20.148, 46.253, "hungary", 80),
    # === МАМЛЮКИ (Египет и Левант) ===
    Fortress("cairo", "Cairo", "Каир", 31.235, 30.044, "mamluk", 400, is_capital=True),
    Fortress("alexandria", "Alexandria", "Александрия", 29.918, 31.200, "mamluk", 280),
    Fortress("damascus", "Damascus", "Дамаск", 36.276, 33.511, "mamluk", 320),
    Fortress("aleppo", "Aleppo", "Алеппо", 37.156, 36.203, "mamluk", 300),
    Fortress("jerusalem", "Jerusalem", "Иерусалим", 35.234, 31.776, "mamluk", 180),
    # === МАГРИБ ===
    Fortress("tunis", "Tunis", "Тунис", 10.181, 36.806, "maghreb", 220, is_capital=True),
    Fortress("tripoli_maghreb", "Tripoli", "Триполи", 13.191, 32.887, "maghreb", 160),
    Fortress("algiers", "Algiers", "Алжир", 3.058, 36.753, "maghreb", 200),
    Fortress("fez", "Fez", "Фес", -4.999, 34.033, "maghreb", 180),
    Fortress("marrakech", "Marrakech", "Марракеш", -8.008, 31.629, "maghreb", 150),
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
