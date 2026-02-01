"""
Отрисовка карты кампании.

Ландшафт: земля, моря (в углах, не перекрывают крепости), реки, горы.
Иконки крепостей с цветами по фракциям.
"""

import os
import pygame

from src.map.fortress_renderer import draw_fortress_icon
from src.data.fortresses import FORTESSES_DATA, MAP_LOGICAL_WIDTH, MAP_LOGICAL_HEIGHT


MAP_OFFSET_X = 60
MAP_OFFSET_Y = 90
MAP_VIEW_WIDTH = 1800
MAP_VIEW_HEIGHT = 880

# Цвета — спокойные, читаемые
COLOR_LAND = (72, 110, 72)
COLOR_SEA = (40, 75, 120)
COLOR_SEA_EDGE = (55, 95, 150)
COLOR_RIVER = (50, 90, 140)
COLOR_MOUNTAIN = (88, 80, 68)
COLOR_MOUNTAIN_EDGE = (70, 64, 55)

# Путь к единственной текстуре травы (если есть)
TEXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "textures")
_texture_cache = {}


def _load_texture(name: str):
    if name in _texture_cache:
        return _texture_cache[name]
    path = os.path.join(TEXTURES_DIR, name)
    if os.path.exists(path):
        try:
            t = pygame.image.load(path).convert()
            _texture_cache[name] = t
            return t
        except Exception:
            pass
    return None


def _draw_tiled(surf: pygame.Surface, tex: pygame.Surface, ox: int, oy: int, scale: float):
    if tex is None:
        return
    tw, th = tex.get_size()
    w = int(MAP_LOGICAL_WIDTH * scale)
    h = int(MAP_LOGICAL_HEIGHT * scale)
    for ty in range(0, h + th, th):
        for tx in range(0, w + tw, tw):
            surf.blit(tex, (ox + tx, oy + ty))


def _draw_landscape(surface: pygame.Surface, ox: int, oy: int, scale: float) -> None:
    w, h = MAP_LOGICAL_WIDTH, MAP_LOGICAL_HEIGHT
    map_rect = pygame.Rect(int(ox), int(oy), int(w * scale), int(h * scale))

    # 1. Основа — земля (текстура или цвет)
    tex = _load_texture("floor_ground_grass.png")
    if tex:
        _draw_tiled(surface, tex, int(ox), int(oy), scale)
    else:
        surface.fill(COLOR_LAND, map_rect)

    # 2. Моря — только в углах, далеко от крепостей (мин. расстояние ~200)
    # Крепости: север y<700 (Константинополь 544, Варна 224, Синоп 480...), запад x<900, восток x>1700, юг y>1600
    seas = [
        # Чёрное море — далеко на северо-востоке (x>2600, y<500)
        [(2600, 50), (3400, 80), (4200, 200), (4500, 500), (4000, 700), (2800, 500), (2600, 250)],
        # Мраморное — компактно, центр ~(1780,710), крепости вокруг снаружи
        [(1680, 690), (1820, 685), (1840, 735), (1780, 755), (1710, 735)],
        # Эгейское — крайний запад (x<100)
        [(0, 700), (60, 800), (80, 1500), (40, 2200), (0, 2200)],
        # Средиземное — крайний юг (y>2250)
        [(1200, 2300), (2500, 2550), (3800, 2500), (4200, 2200), (3200, 2200), (1500, 2250)],
    ]
    for pts in seas:
        scr = [(int(ox + p[0] * scale), int(oy + p[1] * scale)) for p in pts]
        pygame.draw.polygon(surface, COLOR_SEA, scr)
        pygame.draw.polygon(surface, COLOR_SEA_EDGE, scr, 2)

    # 3. Реки — тонкие линии
    rivers = [
        [(850, 1050), (1200, 1150), (1500, 1100)],
        [(2100, 650), (2600, 700)],
    ]
    rw = max(4, int(10 * scale))
    for pts in rivers:
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            x0, y0 = ox + pts[i][0] * scale, oy + pts[i][1] * scale
            x1, y1 = ox + pts[i + 1][0] * scale, oy + pts[i + 1][1] * scale
            pygame.draw.line(surface, COLOR_RIVER, (x0, y0), (x1, y1), rw)

    # 4. Горы — мягкие эллипсы (без грубых текстур)
    mountains = [
        (2050, 950, 180, 100),
        (2850, 750, 150, 90),
        (1500, 2050, 200, 110),
        (650, 850, 120, 80),
        (1100, 450, 100, 70),
    ]
    for mx, my, rx, ry in mountains:
        cx = int(ox + mx * scale)
        cy = int(oy + my * scale)
        rw = int(rx * 2 * scale)
        rh = int(ry * 2 * scale)
        rect = pygame.Rect(cx - rw // 2, cy - rh // 2, rw, rh)
        pygame.draw.ellipse(surface, COLOR_MOUNTAIN, rect)
        pygame.draw.ellipse(surface, COLOR_MOUNTAIN_EDGE, rect, 1)

    # 5. Рамка карты
    pygame.draw.rect(surface, (60, 65, 75), map_rect, 2)


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

    _draw_landscape(surface, ox, oy, scale)

    is_capital_fn = getattr(game_state, "is_capital", lambda fid: False)
    get_owner = getattr(game_state, "get_fortress_owner", lambda fid: "")
    ai_sieges = {}
    for fid, ai in getattr(game_state, "ai_state", {}).items():
        for tid, s in ai.get("sieges", {}).items():
            ai_sieges[tid] = s

    for fortress in FORTESSES_DATA:
        fx = ox + fortress.x * scale
        fy = oy + fortress.y * scale
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


def screen_to_map(screen_x: int, screen_y: int, zoom: float, off_x: float, off_y: float) -> tuple[float, float]:
    map_x = (screen_x - MAP_OFFSET_X) / zoom + off_x
    map_y = (screen_y - MAP_OFFSET_Y) / zoom + off_y
    return map_x, map_y


def get_clicked_fortress(mouse_x: int, mouse_y: int, zoom: float, off_x: float, off_y: float):
    from src.map.fortress_renderer import get_fortress_at_pos
    return get_fortress_at_pos(mouse_x, mouse_y, zoom, off_x, off_y)
