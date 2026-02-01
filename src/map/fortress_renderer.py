"""
Отрисовка крепостей на карте.

Иконки с цветом по владельцу, подписи, масштабирование.
"""

import pygame
from typing import Optional

from src.data.fortresses import Fortress, FORTESSES_DATA
from src.utils.constants import (
    FORTRESS_ICON_SIZE,
    COLOR_OWNED,
    COLOR_ENEMY,
    COLOR_BESIEGED,
    COLOR_NEUTRAL,
    COLOR_TEXT,
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
)


def _get_faction_color(faction: str, is_owned: bool) -> tuple:
    if is_owned:
        return COLOR_OWNED
    colors = {
        "byzantine": COLOR_ENEMY,
        "germiyan": COLOR_GERMIYAN,
        "karaman": COLOR_KARAMAN,
        "aydin": COLOR_AYDIN,
        "bulgaria": COLOR_BULGARIA,
        "serbia": COLOR_SERBIA,
        "hungary": COLOR_HUNGARY,
        "mentese": COLOR_MENTESE,
        "saruhan": COLOR_SARUHAN,
        "candar": COLOR_CANDAR,
        "hamid": COLOR_HAMID,
        "teke": COLOR_TEKE,
        "karasi": COLOR_KARASI,
    }
    return colors.get(faction, COLOR_NEUTRAL)


def draw_fortress_icon(
    surface: pygame.Surface,
    fortress: Fortress,
    is_owned: bool,
    is_besieged: bool = False,
    is_capital: bool = False,
    display_name: Optional[str] = None,
    font: Optional[pygame.font.Font] = None,
    offset_x: int = 0,
    offset_y: int = 0,
    scale: float = 1.0,
    owner_faction: Optional[str] = None,
) -> pygame.Rect:
    """Рисует иконку крепости. owner_faction — текущий владелец (для цвета)."""
    x, y = offset_x, offset_y
    size = max(16, int(FORTRESS_ICON_SIZE * scale))
    half = size // 2

    if is_owned:
        color = COLOR_OWNED
    elif is_besieged:
        color = COLOR_BESIEGED
    else:
        faction = owner_faction if owner_faction else fortress.faction
        color = _get_faction_color(faction, False)

    rect = pygame.Rect(int(x - half), int(y - half), size, size)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, (255, 255, 255), rect, 1)

    roof_points = [
        (x, y - half - 6),
        (x - half - 3, y - half),
        (x + half + 3, y - half),
    ]
    pygame.draw.polygon(surface, color, roof_points)
    pygame.draw.polygon(surface, (255, 255, 255), roof_points, 1)

    if font:
        name = display_name if display_name else fortress.name_ru
        if is_capital:
            name = "★ " + name
        max_chars = 9 if scale < 0.75 else 11
        if len(name) > max_chars:
            name = name[:max_chars - 1].rstrip() + "…"
        fsize = max(10, int(14 * scale))
        try:
            small_font = pygame.font.SysFont("dejavusans", fsize)
        except Exception:
            small_font = font
        text_surf = small_font.render(name, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(centerx=int(x), top=int(y + half + 2))
        surface.blit(text_surf, text_rect)

    return rect


def get_fortress_at_pos(
    mouse_x: int,
    mouse_y: int,
    zoom: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> Optional[Fortress]:
    """Определить крепость по клику с учётом zoom/pan."""
    from src.map.map_renderer import screen_to_map

    map_x, map_y = screen_to_map(mouse_x, mouse_y, zoom, offset_x, offset_y)
    click_radius = 88  # в логических единицах карты (масштаб 1.6×)

    for fortress in FORTESSES_DATA:
        dx = map_x - fortress.x
        dy = map_y - fortress.y
        if dx * dx + dy * dy <= click_radius * click_radius:
            return fortress
    return None
