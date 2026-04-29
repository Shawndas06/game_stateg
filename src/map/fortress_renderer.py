"""
fortress_renderer.py — иконки крепостей на карте и попадание курсора.

Визуал: PNG-пиксельарт (assets/ui/fortress_icon.png) и цветное кольцо фракции;
при отсутствии файла — упрощённый векторный силуэт.
"""

import math
import pygame
from typing import Optional

from src.data.fortresses import Fortress, FORTESSES_DATA
from src.ui import game_assets
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
    COLOR_MAMLUK,
    COLOR_MAGHREB,
)


def _shade(c: tuple[int, int, int], m: float) -> tuple[int, int, int]:
    return (min(255, int(c[0] * m)), min(255, int(c[1] * m)), min(255, int(c[2] * m)))


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
        "mamluk": COLOR_MAMLUK,
        "maghreb": COLOR_MAGHREB,
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
    """Рисует МАРКЕР владельца поверх уже нарисованной на карте крепости.

    Сама пиктограмма замка/города отрисована на художественной карте, поэтому
    игра рисует только тонкое цветное кольцо (фракция-владелец) + корону столицы
    + индикатор осады + подпись.
    """
    x, y = offset_x, offset_y
    size = max(10, int(FORTRESS_ICON_SIZE * scale * 0.55))
    half = size // 2

    if is_besieged:
        ring_color = COLOR_BESIEGED
    elif is_owned:
        ring_color = COLOR_OWNED
    else:
        faction = owner_faction if owner_faction else fortress.faction
        ring_color = _get_faction_color(faction, False)

    # Тонкое кольцо вокруг нарисованного на карте замка — маркер владельца
    r_outer = half + 2
    ring_w = max(2, int(2 * scale))
    pygame.draw.circle(surface, ring_color, (int(x), int(y)), r_outer, width=ring_w)
    # Тёмная контурная обводка для контраста на пергаменте
    pygame.draw.circle(surface, (42, 36, 28), (int(x), int(y)), r_outer + 1, width=1)

    if is_besieged:
        # Пунктирная вторая красная кайма — наглядно, что идёт осада
        for ang in range(0, 360, 30):
            rad = math.radians(ang)
            tx = int(x + math.cos(rad) * (r_outer + 4))
            ty = int(y + math.sin(rad) * (r_outer + 4))
            pygame.draw.circle(surface, COLOR_BESIEGED, (tx, ty), 2)

    if is_capital:
        crown_y = y - r_outer - 6
        pygame.draw.polygon(
            surface,
            (235, 200, 88),
            [
                (x, crown_y - 4),
                (x + 6, crown_y + 4),
                (x - 6, crown_y + 4),
            ],
        )
        pygame.draw.polygon(
            surface,
            (90, 60, 20),
            [
                (x, crown_y - 4),
                (x + 6, crown_y + 4),
                (x - 6, crown_y + 4),
            ],
            1,
        )

    rect = pygame.Rect(int(x - r_outer - 2), int(y - r_outer - 2), (r_outer + 2) * 2, (r_outer + 2) * 2)

    show_label = font is not None and (scale >= 0.55 or is_capital or is_owned or fortress.faction == "ottoman")
    if show_label:
        name = display_name if display_name else fortress.name_ru
        if is_capital and not name.startswith("★"):
            name = "★ " + name
        max_chars = 9 if scale < 0.75 else 12
        if len(name) > max_chars:
            name = name[: max_chars - 1].rstrip() + "…"
        fsize = max(9, int(12 * scale))
        try:
            small_font = pygame.font.SysFont("dejavusans", fsize)
        except Exception:
            small_font = font
        pad = pygame.Surface((small_font.size(name)[0] + 7, small_font.get_height() + 3), pygame.SRCALPHA)
        pad.fill((38, 32, 26, 190))
        tx = small_font.render(name, True, (248, 244, 236))
        tr = tx.get_rect(centerx=int(x), top=int(y + half + 3))
        surface.blit(pad, (tr.left - 4, tr.top - 2))
        surface.blit(tx, tr)

    return rect


def get_fortress_at_pos(
    mouse_x: int,
    mouse_y: int,
    zoom: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> Optional[Fortress]:
    from src.map.map_renderer import screen_to_map

    map_x, map_y = screen_to_map(mouse_x, mouse_y, zoom, offset_x, offset_y)
    click_radius = 62

    for fortress in FORTESSES_DATA:
        dx = map_x - fortress.x
        dy = map_y - fortress.y
        if dx * dx + dy * dy <= click_radius * click_radius:
            return fortress
    return None
