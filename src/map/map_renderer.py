"""
Отрисовка карты кампании
Анатолия и Балканы: вода, реки, горы, равнины с текстурами
Zoom и pan мышью
"""

import os
import pygame
import math

from src.utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from src.map.fortress_renderer import draw_fortress_icon
from src.data.fortresses import FORTESSES_DATA, MAP_LOGICAL_WIDTH, MAP_LOGICAL_HEIGHT


MAP_OFFSET_X = 60
MAP_OFFSET_Y = 90
MAP_VIEW_WIDTH = 1800
MAP_VIEW_HEIGHT = 880

# Цвета (fallback при отсутствии текстур)
COLOR_SEA = (30, 60, 100)
COLOR_SEA_DEEP = (20, 45, 80)
COLOR_RIVER = (50, 90, 140)
COLOR_PLAIN = (55, 95, 55)
COLOR_HILLS = (75, 110, 65)
COLOR_MOUNTAINS = (90, 95, 85)

# Путь к текстурам (относительно корня проекта)
TEXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "textures")

# Кэш загруженных текстур
_texture_cache = {}


def _load_texture(name: str):
    """Загрузить текстуру с кэшированием."""
    if name in _texture_cache:
        return _texture_cache[name]
    path = os.path.join(TEXTURES_DIR, name)
    if os.path.exists(path):
        try:
            tex = pygame.image.load(path).convert_alpha()
            _texture_cache[name] = tex
            return tex
        except Exception:
            pass
    return None


def _draw_tiled_texture(surface: pygame.Surface, tex: pygame.Surface, ox: int, oy: int, scale: float) -> None:
    """Заполнить область тайлами текстуры."""
    if tex is None:
        return
    tw, th = tex.get_size()
    if tw <= 0 or th <= 0:
        return
    w, h = int(MAP_LOGICAL_WIDTH * scale), int(MAP_LOGICAL_HEIGHT * scale)
    for ty in range(0, h + th, th):
        for tx in range(0, w + tw, tw):
            rect = pygame.Rect(ox + tx, oy + ty, tw, th)
            surface.blit(tex, rect)


def _draw_landscape(surface: pygame.Surface, ox: int, oy: int, scale: float) -> None:
    """Ландшафт: равнины с текстурами, моря, реки, горы."""
    w, h = MAP_LOGICAL_WIDTH, MAP_LOGICAL_HEIGHT

    # 1. Основа — травяная текстура (Kenney floor_ground_grass)
    tex_grass = _load_texture("floor_ground_grass.png")
    tex_dirt = _load_texture("floor_ground_dirt.png")
    tex_sand = _load_texture("floor_ground_sand.png")

    if tex_grass:
        _draw_tiled_texture(surface, tex_grass, int(ox), int(oy), scale)
    else:
        # Fallback: сетка цветов
        step = 120
        for gy in range(0, h + step, step):
            for gx in range(0, w + step, step):
                v = (gx * 7 + gy * 13) % 25
                c = (COLOR_PLAIN[0] + v, COLOR_PLAIN[1] + v // 2, COLOR_PLAIN[2] + v)
                rect = pygame.Rect(int(ox + gx * scale), int(oy + gy * scale),
                                   int(step * 1.2 * scale), int(step * 1.2 * scale))
                pygame.draw.rect(surface, c, rect)

    # 2. Вариация — участки земли/песка (внутренние районы, сухие зоны)
    if tex_dirt or tex_sand:
        step = 400
        for gy in range(200, h, step):
            for gx in range(800, w, step):
                v = (gx + gy) % 3
                if v == 0 and tex_dirt:
                    sub = pygame.Surface((int(step * scale), int(step * scale)))
                    for sy in range(0, int(step * scale), tex_dirt.get_height()):
                        for sx in range(0, int(step * scale), tex_dirt.get_width()):
                            sub.blit(tex_dirt, (sx, sy))
                    surface.blit(sub, (int(ox + gx * scale), int(oy + gy * scale)))
                elif v == 1 and tex_sand:
                    sub = pygame.Surface((int(step * 0.6 * scale), int(step * 0.6 * scale)))
                    for sy in range(0, sub.get_height(), tex_sand.get_height()):
                        for sx in range(0, sub.get_width(), tex_sand.get_width()):
                            sub.blit(tex_sand, (sx, sy))
                    surface.blit(sub, (int(ox + gx * scale), int(oy + gy * scale)))

    # 3. Моря — полигоны (НЕ накрывают крепости)
    # Мраморное: компактно, берега свободны для Nicomedia, Kalolimni, Kios, Bursa
    seas = [
        ([(900, 500), (1050, 460), (1160, 500), (1180, 600), (1040, 700), (900, 660), (850, 580)]),
        ([(1420, 80), (2000, 120), (2600, 280), (2500, 600), (1680, 520), (1480, 280)]),
        ([(0, 600), (80, 560), (140, 620), (100, 1000), (0, 1000)]),
    ]
    for pts in seas:
        screen_pts = [(int(ox + p[0] * scale), int(oy + p[1] * scale)) for p in pts]
        pygame.draw.polygon(surface, COLOR_SEA, screen_pts)
        pygame.draw.polygon(surface, COLOR_SEA_DEEP, screen_pts, 2)

    # 4. Реки
    rivers = [
        [(380, 620), (520, 700), (660, 680), (820, 760)],
        [(1400, 520), (1700, 580), (1900, 540)],
        [(2000, 320), (2300, 400), (2500, 480)],
    ]
    for pts in rivers:
        if len(pts) < 2:
            continue
        screen_pts = [(ox + p[0] * scale, oy + p[1] * scale) for p in pts]
        for i in range(len(screen_pts) - 1):
            pygame.draw.line(surface, COLOR_RIVER, screen_pts[i], screen_pts[i + 1], max(2, int(6 * scale)))

    # 5. Горы — вдали от крепостей (центральная Анатолия)
    mountains = [
        (1100, 1100, 90), (1400, 1200, 80), (1800, 1000, 85),
        (1600, 1400, 70), (800, 1300, 65),
    ]
    for mx, my, r in mountains:
        cx, cy = ox + mx * scale, oy + my * scale
        rr = int(r * scale)
        pygame.draw.circle(surface, COLOR_MOUNTAINS, (int(cx), int(cy)), rr)
        pygame.draw.circle(surface, COLOR_HILLS, (int(cx), int(cy)), rr, 2)

    # 6. Граница карты
    border = pygame.Rect(int(ox), int(oy), int(w * scale), int(h * scale))
    pygame.draw.rect(surface, (70, 75, 85), border, 2)


def draw_map(
    surface: pygame.Surface,
    game_state,
    font: pygame.font.Font,
    map_zoom: float = 1.0,
    map_offset_x: float = 0.0,
    map_offset_y: float = 0.0,
) -> None:
    """Рисует карту с zoom и pan."""
    scale = map_zoom
    ox = MAP_OFFSET_X - map_offset_x * scale
    oy = MAP_OFFSET_Y - map_offset_y * scale

    map_rect = pygame.Rect(MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT)
    clip = surface.get_clip()
    surface.set_clip(map_rect)

    _draw_landscape(surface, ox, oy, scale)

    is_capital_fn = getattr(game_state, "is_capital", lambda fid: False)
    byzantine_sieges = getattr(game_state, "byzantine_sieges", {})
    for fortress in FORTESSES_DATA:
        fx = ox + fortress.x * scale
        fy = oy + fortress.y * scale
        if fx < -50 or fy < -50 or fx > MAP_OFFSET_X + MAP_VIEW_WIDTH + 50 or fy > MAP_OFFSET_Y + MAP_VIEW_HEIGHT + 50:
            continue
        is_owned = game_state.is_fortress_owned(fortress.id)
        is_besieged = (
            fortress.id in game_state.sieges_in_progress
            or fortress.id in byzantine_sieges
        )
        is_capital = is_owned and is_capital_fn(fortress.id)
        name = game_state.get_fortress_display_name(fortress.id) if hasattr(game_state, "get_fortress_display_name") else fortress.name_ru
        draw_fortress_icon(
            surface,
            fortress,
            is_owned,
            is_besieged=is_besieged,
            is_capital=is_capital,
            display_name=name,
            font=font,
            offset_x=int(fx),
            offset_y=int(fy),
            scale=scale,
        )

    surface.set_clip(clip)


def screen_to_map(screen_x: int, screen_y: int, zoom: float, off_x: float, off_y: float) -> tuple[float, float]:
    """Экранные координаты → логические координаты карты."""
    map_x = (screen_x - MAP_OFFSET_X) / zoom + off_x
    map_y = (screen_y - MAP_OFFSET_Y) / zoom + off_y
    return map_x, map_y


def get_clicked_fortress(mouse_x: int, mouse_y: int, zoom: float, off_x: float, off_y: float):
    """Проверить клик по крепости с учётом zoom/pan."""
    from src.map.fortress_renderer import get_fortress_at_pos
    return get_fortress_at_pos(mouse_x, mouse_y, zoom, off_x, off_y)
