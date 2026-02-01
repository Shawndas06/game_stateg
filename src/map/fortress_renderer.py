"""
Отрисовка крепостей на карте
Иконки крепостей с большим расстоянием друг от друга
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
)


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
) -> pygame.Rect:
    """
    Рисует иконку крепости на карте.
    Османские — зелёные, византийские — красные, осада — оранжевые, нейтральные — серые.
    """
    x = fortress.x + offset_x
    y = fortress.y + offset_y

    # Цвет по состоянию
    if is_owned:
        color = COLOR_OWNED
    elif is_besieged:
        color = COLOR_BESIEGED
    elif fortress.faction == "byzantine":
        color = COLOR_ENEMY
    else:
        color = COLOR_NEUTRAL

    # Основание иконки — квадрат/башня
    half = FORTRESS_ICON_SIZE // 2
    rect = pygame.Rect(x - half, y - half, FORTRESS_ICON_SIZE, FORTRESS_ICON_SIZE)

    # Заливка "башни"
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, (255, 255, 255), rect, 2)

    # Крыша башни (треугольник)
    roof_points = [
        (x, y - half - 10),
        (x - half - 5, y - half),
        (x + half + 5, y - half),
    ]
    pygame.draw.polygon(surface, color, roof_points)
    pygame.draw.polygon(surface, (255, 255, 255), roof_points, 1)

    # Название крепости под иконкой (★ для столицы)
    if font:
        name = display_name if display_name is not None else fortress.name_ru
        if is_capital:
            name = "★ " + name
        text_surf = font.render(name, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(centerx=x, top=y + half + 4)
        surface.blit(text_surf, text_rect)

    return rect


def get_fortress_at_pos(mouse_x: int, mouse_y: int, offset_x: int = 0, offset_y: int = 0) -> Optional[Fortress]:
    """
    Определить, по какой крепости кликнули.
    """
    half = FORTRESS_ICON_SIZE // 2
    click_radius = half + 20  # Увеличиваем область клика

    for fortress in FORTESSES_DATA:
        fx = fortress.x + offset_x
        fy = fortress.y + offset_y
        dx = mouse_x - fx
        dy = mouse_y - fy
        if dx * dx + dy * dy <= click_radius * click_radius:
            return fortress
    return None
