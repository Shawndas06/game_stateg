"""
map_renderer.py — географическая карта Средиземноморья.

Фон: текстура пергамента (assets/map/mediterranean_parchment.png), масштабируется под логический мир.
При отсутствии файла — прежний процедурный рельеф.

Порядок слоёв: пергамент → (опционально процедура) → иконки крепостей.
"""

from __future__ import annotations

import math
from pathlib import Path
import pygame

from src.map.fortress_renderer import draw_fortress_icon
from src.map.geography_land import (
    LAND_POLYGONS,
    MOUNTAIN_ELLIPSES,
    RIVER_LINES,
    is_land,
)
from src.map.geo_projection import (
    LAT_SPAN,
    LON_SPAN,
    MAP_LOGICAL_HEIGHT,
    MAP_LOGICAL_WIDTH,
    lonlat_to_map,
    map_to_lonlat,
)
from src.data.fortresses import FORTESSES_DATA
from src.utils.constants import (
    COLOR_OWNED,
    COLOR_ENEMY,
    COLOR_GERMIYAN,
    COLOR_KARAMAN,
    COLOR_AYDIN,
    COLOR_BULGARIA,
    COLOR_SERBIA,
    COLOR_HUNGARY,
    COLOR_MENTESE,
    COLOR_SARUHAN,
    COLOR_CANDAR,
    COLOR_HAMID,
    COLOR_TEKE,
    COLOR_KARASI,
    COLOR_NEUTRAL,
    COLOR_MAMLUK,
    COLOR_MAGHREB,
)


# Минимальное расстояние между иконками крепостей в логических пикселях.
# Если ближе — добавляется визуальный сдвиг по спирали, чтобы они не накладывались.
_MIN_ICON_DIST = 95
_FORTRESS_VISUAL_OFFSET: dict[str, tuple[int, int]] = {}


def _compute_visual_offsets() -> None:
    """Один раз: распределить тесные крепости по кругу/спирали.

    Алгоритм: проходим крепости в порядке data, для каждой проверяем
    последние уже расставленные. Если в радиусе MIN_ICON_DIST есть соседи,
    добавляем сдвиг по углу (фан вокруг центра кластера).
    """
    placed: list[tuple[str, float, float]] = []  # (id, x_visual, y_visual)
    cluster_count: dict[tuple[int, int], int] = {}  # для подсчёта мест в одной точке

    for f in FORTESSES_DATA:
        bx, by = float(f.x), float(f.y)
        # Найти ближайшего уже размещённого
        neighbors = [(pid, px, py) for (pid, px, py) in placed
                     if (px - bx) ** 2 + (py - by) ** 2 < (_MIN_ICON_DIST * 1.6) ** 2]
        if not neighbors:
            placed.append((f.id, bx, by))
            _FORTRESS_VISUAL_OFFSET[f.id] = (0, 0)
            continue
        # Ключ кластера — округлённая исходная точка ближайшего соседа
        nb = min(neighbors, key=lambda t: (t[1] - bx) ** 2 + (t[2] - by) ** 2)
        key = (int(nb[1]) // 30, int(nb[2]) // 30)
        idx = cluster_count.get(key, 1)
        cluster_count[key] = idx + 1
        # Веер: чередуем по углу, шаг радиуса растёт каждый виток.
        angle = (idx * 137.508) * math.pi / 180.0  # «золотой» угол → равномерное распределение
        radius = _MIN_ICON_DIST * (0.85 + 0.18 * (idx // 6))
        dx = int(math.cos(angle) * radius)
        dy = int(math.sin(angle) * radius)
        _FORTRESS_VISUAL_OFFSET[f.id] = (dx, dy)
        placed.append((f.id, bx + dx, by + dy))


_compute_visual_offsets()


def get_fortress_visual_offset(fid: str) -> tuple[int, int]:
    return _FORTRESS_VISUAL_OFFSET.get(fid, (0, 0))


MAP_OFFSET_X = 60
MAP_OFFSET_Y = 96
MAP_VIEW_WIDTH = 1800
MAP_VIEW_HEIGHT = 880

# Океан и суша — спокойные «реальные» тона, без кислотности
COLOR_SEA_DEEP = (26, 52, 88)
COLOR_SEA_SHALLOW = (42, 76, 112)
COLOR_LAND_BASE = (118, 124, 94)

COLOR_RIVER = (58, 108, 138)
COLOR_MOUNTAIN = (96, 90, 78)
COLOR_MOUNTAIN_EDGE = (74, 70, 62)
COLOR_COAST_OUTLINE = (88, 96, 76)

# Кэш исходной и отмасштабированной текстуры (размер зависит только от zoom).
_PARCHMENT_SOURCE: pygame.Surface | bool | None = None
_PARCHMENT_SCALED: pygame.Surface | None = None
_PARCHMENT_SCALED_WH: tuple[int, int] | None = None

TERRITORY_COLORS = {
    "ottoman": COLOR_OWNED,
    "byzantine": COLOR_ENEMY,
    "germiyan": COLOR_GERMIYAN,
    "karaman": COLOR_KARAMAN,
    "aydin": COLOR_AYDIN,
    "mentese": COLOR_MENTESE,
    "saruhan": COLOR_SARUHAN,
    "candar": COLOR_CANDAR,
    "hamid": COLOR_HAMID,
    "teke": COLOR_TEKE,
    "karasi": COLOR_KARASI,
    "bulgaria": COLOR_BULGARIA,
    "serbia": COLOR_SERBIA,
    "hungary": COLOR_HUNGARY,
    "mamluk": COLOR_MAMLUK,
    "maghreb": COLOR_MAGHREB,
}


def _get_territory_color(faction_id: str):
    return TERRITORY_COLORS.get(faction_id, COLOR_NEUTRAL)


def _political_tint(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Смешиваем цвет фракции с базовым тоном суши — меньше «радуги»."""
    r, g, b = rgb
    br, bg, bb = COLOR_LAND_BASE
    t = 0.68
    return (
        int(r * t + br * (1 - t)),
        int(g * t + bg * (1 - t)),
        int(b * t + bb * (1 - t)),
    )


def _lonlat_poly_to_screen(poly: list[tuple[float, float]], ox: float, oy: float, scale: float) -> list[tuple[int, int]]:
    out = []
    for lon, lat in poly:
        mx, my = lonlat_to_map(lon, lat)
        out.append((int(ox + mx * scale), int(oy + my * scale)))
    return out


def _draw_ocean_gradient(surface: pygame.Surface, ox: int, oy: int, scale: float) -> None:
    w = int(MAP_LOGICAL_WIDTH * scale)
    h = int(MAP_LOGICAL_HEIGHT * scale)
    for row in range(h):
        t = row / max(1, h - 1)
        r = int(COLOR_SEA_DEEP[0] * (1 - t) + COLOR_SEA_SHALLOW[0] * t)
        g = int(COLOR_SEA_DEEP[1] * (1 - t) + COLOR_SEA_SHALLOW[1] * t)
        b = int(COLOR_SEA_DEEP[2] * (1 - t) + COLOR_SEA_SHALLOW[2] * t)
        pygame.draw.line(surface, (r, g, b), (ox, oy + row), (ox + w, oy + row))


def _draw_land_mass(surface: pygame.Surface, ox: float, oy: float, scale: float) -> None:
    for poly in LAND_POLYGONS:
        scr = _lonlat_poly_to_screen(poly, ox, oy, scale)
        if len(scr) >= 3:
            pygame.draw.polygon(surface, COLOR_LAND_BASE, scr)
            pygame.draw.polygon(surface, COLOR_COAST_OUTLINE, scr, 2)


def _draw_territory(surface: pygame.Surface, game_state, ox: float, oy: float, scale: float) -> None:
    """Политическая окраска: только ячейки суши (центр в полигоне суши)."""
    cell = 46
    nx = int(math.ceil(MAP_LOGICAL_WIDTH / cell))
    ny = int(math.ceil(MAP_LOGICAL_HEIGHT / cell))
    get_owner = getattr(game_state, "get_fortress_owner", lambda fid: "")

    for i in range(nx):
        for j in range(ny):
            cx = i * cell + cell // 2
            cy = j * cell + cell // 2
            lon, lat = map_to_lonlat(float(cx), float(cy))
            if not is_land(lon, lat):
                continue
            best_fid = None
            best_d2 = float("inf")
            for f in FORTESSES_DATA:
                d2 = (f.x - cx) ** 2 + (f.y - cy) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best_fid = f.id
            owner = get_owner(best_fid) if best_fid else ""
            if not owner:
                owner = next((ff.faction for ff in FORTESSES_DATA if ff.id == best_fid), "")
            color = _political_tint(_get_territory_color(owner))
            sx = int(ox + i * cell * scale)
            sy = int(oy + j * cell * scale)
            cw = int(cell * scale) + 1
            ch = int(cell * scale) + 1
            surface.fill(color, (sx, sy, cw, ch))


def _draw_rivers(surface: pygame.Surface, ox: float, oy: float, scale: float) -> None:
    rw = max(3, int(8 * scale))
    for pts in RIVER_LINES:
        if len(pts) < 2:
            continue
        scr = [_lonlat_poly_to_screen([p], ox, oy, scale)[0] for p in pts]
        for k in range(len(scr) - 1):
            pygame.draw.line(surface, COLOR_RIVER, scr[k], scr[k + 1], rw)


def _draw_mountains(surface: pygame.Surface, ox: float, oy: float, scale: float) -> None:
    for lon_c, lat_c, rx_d, ry_d in MOUNTAIN_ELLIPSES:
        mx, my = lonlat_to_map(lon_c, lat_c)
        rx_map = rx_d / LON_SPAN * MAP_LOGICAL_WIDTH * scale
        ry_map = ry_d / LAT_SPAN * MAP_LOGICAL_HEIGHT * scale
        cx = int(ox + mx * scale)
        cy = int(oy + my * scale)
        rw = max(18, int(rx_map * 2))
        rh = max(14, int(ry_map * 2))
        rect = pygame.Rect(cx - rw // 2, cy - rh // 2, rw, rh)
        pygame.draw.ellipse(surface, COLOR_MOUNTAIN, rect)
        pygame.draw.ellipse(surface, COLOR_MOUNTAIN_EDGE, rect, 1)


def _get_parchment_source() -> pygame.Surface | None:
    """Загружает PNG один раз; при ошибке возвращает None (fallback на процедурную карту).

    Приоритет: assets/map/generated_map.png (создаётся scripts/generate_map.py
    и согласован с проекцией крепостей). Если его нет — старая
    assets/map/mediterranean_parchment.png. Если и её нет — None.
    """
    global _PARCHMENT_SOURCE
    if _PARCHMENT_SOURCE is False:
        return None
    if _PARCHMENT_SOURCE is not None:
        return _PARCHMENT_SOURCE  # type: ignore[return-value]
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "assets" / "map" / "generated_map.png",
        root / "assets" / "map" / "mediterranean_parchment.png",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            img = pygame.image.load(str(path)).convert()
            _PARCHMENT_SOURCE = img
            return img
        except Exception:
            continue
    _PARCHMENT_SOURCE = False
    return None


def _draw_parchment_background(surface: pygame.Surface, ox: float, oy: float, scale: float) -> bool:
    """Рисует стилизованную карту; True если текстура есть, False — нужен процедурный fallback."""
    src = _get_parchment_source()
    if src is None:
        return False
    w = max(1, int(MAP_LOGICAL_WIDTH * scale))
    h = max(1, int(MAP_LOGICAL_HEIGHT * scale))
    global _PARCHMENT_SCALED, _PARCHMENT_SCALED_WH
    if _PARCHMENT_SCALED_WH != (w, h) or _PARCHMENT_SCALED is None:
        _PARCHMENT_SCALED = pygame.transform.smoothscale(src, (w, h))
        _PARCHMENT_SCALED_WH = (w, h)
    surface.blit(_PARCHMENT_SCALED, (int(ox), int(oy)))
    return True


def draw_map(
    surface: pygame.Surface,
    game_state,
    font: pygame.font.Font,
    map_zoom: float = 1.0,
    map_offset_x: float = 0.0,
    map_offset_y: float = 0.0,
) -> None:
    scale = map_zoom
    ox = MAP_OFFSET_X - map_offset_x * scale
    oy = MAP_OFFSET_Y - map_offset_y * scale

    map_rect = pygame.Rect(MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT)
    clip_save = surface.get_clip()
    surface.set_clip(map_rect)

    if not _draw_parchment_background(surface, ox, oy, scale):
        _draw_ocean_gradient(surface, int(ox), int(oy), scale)
        _draw_land_mass(surface, ox, oy, scale)
        if game_state is not None:
            _draw_territory(surface, game_state, ox, oy, scale)
        _draw_rivers(surface, ox, oy, scale)
        _draw_mountains(surface, ox, oy, scale)

    map_rect_screen = pygame.Rect(int(ox), int(oy), int(MAP_LOGICAL_WIDTH * scale), int(MAP_LOGICAL_HEIGHT * scale))
    pygame.draw.rect(surface, (62, 52, 42), map_rect_screen, 2, border_radius=4)
    pygame.draw.line(surface, (110, 96, 78), (map_rect_screen.left + 3, map_rect_screen.top + 2),
                     (map_rect_screen.right - 4, map_rect_screen.top + 2), 1)

    if game_state is not None:
        is_capital_fn = getattr(game_state, "is_capital", lambda fid: False)
        get_owner = getattr(game_state, "get_fortress_owner", lambda fid: "")
        ai_sieges = {}
        for fid, ai in getattr(game_state, "ai_state", {}).items():
            for tid, s in ai.get("sieges", {}).items():
                ai_sieges[tid] = s

        for fortress in FORTESSES_DATA:
            vdx, vdy = get_fortress_visual_offset(fortress.id)
            fx = ox + (fortress.x + vdx) * scale
            fy = oy + (fortress.y + vdy) * scale
            if fx < -80 or fy < -80 or fx > MAP_OFFSET_X + MAP_VIEW_WIDTH + 80 or fy > MAP_OFFSET_Y + MAP_VIEW_HEIGHT + 80:
                continue
            is_owned = game_state.is_fortress_owned(fortress.id)
            is_besieged = fortress.id in game_state.sieges_in_progress or fortress.id in ai_sieges
            is_capital = is_owned and is_capital_fn(fortress.id)
            name = game_state.get_fortress_display_name(fortress.id) if hasattr(game_state, "get_fortress_display_name") else fortress.name_ru
            owner = get_owner(fortress.id) or fortress.faction
            draw_fortress_icon(
                surface, fortress, is_owned,
                is_besieged=is_besieged, is_capital=is_capital,
                display_name=name, font=font,
                offset_x=int(fx), offset_y=int(fy), scale=scale, owner_faction=owner,
            )

    surface.set_clip(clip_save)


def get_max_map_offset(zoom: float) -> tuple[float, float]:
    """Максимальное смещение карты при zoom (чтобы не уезжать за пределы мира)."""
    vw = MAP_VIEW_WIDTH / zoom
    vh = MAP_VIEW_HEIGHT / zoom
    return max(0.0, MAP_LOGICAL_WIDTH - vw), max(0.0, MAP_LOGICAL_HEIGHT - vh)


def screen_to_map(screen_x: int, screen_y: int, zoom: float, off_x: float, off_y: float) -> tuple[float, float]:
    map_x = (screen_x - MAP_OFFSET_X) / zoom + off_x
    map_y = (screen_y - MAP_OFFSET_Y) / zoom + off_y
    return map_x, map_y


def get_clicked_fortress(mouse_x: int, mouse_y: int, zoom: float, off_x: float, off_y: float):
    from src.map.fortress_renderer import get_fortress_at_pos
    return get_fortress_at_pos(mouse_x, mouse_y, zoom, off_x, off_y)
