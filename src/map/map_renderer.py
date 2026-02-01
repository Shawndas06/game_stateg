"""
Отрисовка карты кампании
Карта Анатолии и Балкан с крепостями
"""

import pygame

from src.utils.constants import COLOR_MAP_BACKGROUND, SCREEN_WIDTH, SCREEN_HEIGHT
from src.map.fortress_renderer import draw_fortress_icon, get_fortress_at_pos
from src.data.fortresses import FORTESSES_DATA


# Область карты (центрирована)
MAP_OFFSET_X = 80
MAP_OFFSET_Y = 120
MAP_WIDTH = 1000
MAP_HEIGHT = 500


def draw_map(
    surface: pygame.Surface,
    game_state,
    font: pygame.font.Font,
) -> None:
    """
    Рисует карту кампании с крепостями.
    """
    # Фон карты — тёмный
    map_rect = pygame.Rect(MAP_OFFSET_X, MAP_OFFSET_Y, MAP_WIDTH, MAP_HEIGHT)
    pygame.draw.rect(surface, COLOR_MAP_BACKGROUND, map_rect)
    pygame.draw.rect(surface, (80, 80, 90), map_rect, 2)

    # Линии "соединяют" соседние крепости (схематично)
    # Просто рисуем карту как фон

    # Рисуем все крепости
    for fortress in FORTESSES_DATA:
        is_owned = game_state.is_fortress_owned(fortress.id)
        draw_fortress_icon(
            surface,
            fortress,
            is_owned,
            font=font,
            offset_x=MAP_OFFSET_X,
            offset_y=MAP_OFFSET_Y,
        )


def get_clicked_fortress(mouse_x: int, mouse_y: int):
    """Проверить клик по крепости (используется в UI)"""
    return get_fortress_at_pos(mouse_x, mouse_y, MAP_OFFSET_X, MAP_OFFSET_Y)
