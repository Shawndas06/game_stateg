"""
geo_projection.py — эквиректанглярная проекция карты «Восточное Средиземноморье».

Границы охватывают Иберию, Западную и Южную Европу, Балканы, Анатолию,
Левант, Египет и северную Африку до Атлантики (упрощённая игровая карта мира игры).
Логические координаты совпадают по размеру с прежней картой для сохранения UI.
"""

from __future__ import annotations

# Логический размер «мира». Соотношение 1.79 совпадает с PNG-картой (1440×804).
MAP_LOGICAL_WIDTH = 8400
MAP_LOGICAL_HEIGHT = 4690

# Границы в градусах. Карта охватывает всё Средиземноморье — от Атлантики до Каспия,
# от Дуная/Карпат до южного Египта.
LON_MIN = -10.0
LON_MAX = 44.0
LAT_MIN = 22.0
LAT_MAX = 46.0
LON_SPAN = LON_MAX - LON_MIN
LAT_SPAN = LAT_MAX - LAT_MIN


def _interp(value: float, points: tuple[tuple[float, float], ...]) -> float:
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= value <= x1:
            t = (value - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t
    return points[-1][1]


def _interp_reverse(value: float, points: tuple[tuple[float, float], ...]) -> float:
    rev = tuple(sorted(((y, x) for x, y in points), key=lambda p: p[0]))
    return _interp(value, rev)


# Калибровка под художественную карту generated_map.png (1440×804).
# Используется ПРОСТАЯ ЛИНЕЙНАЯ проекция: вся ширина 8400 логич. = lon -10..+44,
# вся высота 4690 логич. = lat 22..46. Так у нас минимум поверхностей для ошибок.
# Опорные точки взяты по анализу пиксельных данных PNG: Чёрное море при lat≈41 начинается
# у PNG x≈990, что соответствует lon≈27.5 (Varna), и далее линейно.
#
# Если какая-то крепость окажется не на месте — добавь промежуточную точку в таблицу
# и сместятся только окрестные крепости, остальные остаются на местах.

_LON_TO_X = (
    (-10.0,    0.0),
    ( 44.0, 8400.0),
)

_LAT_TO_Y = (
    # Откалибровано по фактическому положению суши на художественной карте:
    # AI нарисовал Анатолию ниже геогра­фической, поэтому северный берег Анатолии
    # на PNG примерно y≈259, а не y≈170 как при чисто-линейной проекции.
    (22.0, 4690.0),      # PNG y≈804 (нижний край)
    (30.0, 3150.0),      # PNG y≈540 — побережье Египта (Каир/Александрия)
    (36.0, 2300.0),      # PNG y≈394 — южное побережье Анатолии (Анталия) / Кипр
    (38.0, 1850.0),      # PNG y≈317 — западная Анатолия (Смирна/Бурса)
    (41.0, 1400.0),      # PNG y≈240 — Босфор/Константинополь, северное побережье Анатолии
    (44.0,  600.0),      # PNG y≈103 — Чёрное море северный берег / Крым
    (46.0,    0.0),      # PNG y=0 (верхний край)
)


# Глобальный сдвиг проекции: оставлены на нуле под новую (откалиброванную) карту.
# Менять только если PNG-карту заменили на другую и нужна общая корректировка.
PROJECTION_X_SHIFT = 0
PROJECTION_Y_SHIFT = 0


def lonlat_to_map(lon: float, lat: float) -> tuple[int, int]:
    """Долгота/широта → координаты на художественной PNG-карте."""
    lon = max(LON_MIN, min(LON_MAX, lon))
    lat = max(LAT_MIN, min(LAT_MAX, lat))
    x = _interp(lon, _LON_TO_X) + PROJECTION_X_SHIFT
    y = _interp(lat, _LAT_TO_Y) + PROJECTION_Y_SHIFT
    x = max(0, min(MAP_LOGICAL_WIDTH, x))
    y = max(0, min(MAP_LOGICAL_HEIGHT, y))
    return int(x), int(y)


def map_to_lonlat(mx: float, my: float) -> tuple[float, float]:
    """Логические координаты → долгота/широта."""
    lon = _interp_reverse(mx - PROJECTION_X_SHIFT, _LON_TO_X)
    lat = _interp_reverse(my - PROJECTION_Y_SHIFT, _LAT_TO_Y)
    return lon, lat
