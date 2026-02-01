"""
Экраны игры — главное меню, карта, диалоги
"""

import pygame

from src.utils.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_UI_BG,
    COLOR_UI_ACCENT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
)
from src.map.map_renderer import draw_map, get_clicked_fortress, MAP_OFFSET_X, MAP_OFFSET_Y


# === МЕНЮ ВХОДА ===

MENU_BTN_NEW_GAME = "new_game"
MENU_BTN_EXIT = "exit"


def draw_main_menu(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Рисует меню входа.
    Возвращает список (rect, action) для обработки кликов.
    """
    surface.fill(COLOR_UI_BG)

    # Заголовок
    title = "Османская кампания"
    subtitle = "Беелик → Султанат → Империя"
    title_surf = font_title.render(title, True, COLOR_UI_ACCENT)
    subtitle_surf = font.render(subtitle, True, COLOR_TEXT_DIM)
    title_rect = title_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 80)
    subtitle_rect = subtitle_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 45)
    surface.blit(title_surf, title_rect)
    surface.blit(subtitle_surf, subtitle_rect)

    # Кнопки
    button_actions = []
    btn_w, btn_h = 280, 55
    btn_y = SCREEN_HEIGHT // 2
    btn_x = (SCREEN_WIDTH - btn_w) // 2

    # Новая игра
    rect_new = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_new)
    pygame.draw.rect(surface, COLOR_TEXT, rect_new, 2)
    text_new = font.render("Новая игра", True, COLOR_UI_BG)
    surface.blit(text_new, text_new.get_rect(center=rect_new.center))
    button_actions.append((rect_new, MENU_BTN_NEW_GAME))

    # Выход
    rect_exit = pygame.Rect(btn_x, btn_y + 75, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_exit)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_exit, 2)
    text_exit = font.render("Выход", True, COLOR_UI_ACCENT)
    surface.blit(text_exit, text_exit.get_rect(center=rect_exit.center))
    button_actions.append((rect_exit, MENU_BTN_EXIT))

    return button_actions


def get_menu_button_at_pos(mouse_pos: tuple[int, int], buttons: list) -> str | None:
    """Проверить клик по кнопке меню. Возвращает action или None."""
    for rect, action in buttons:
        if rect.collidepoint(mouse_pos):
            return action
    return None


def draw_main_screen(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> None:
    """
    Рисует главный экран: карта + панель информации.
    """
    # Панель сверху — этап кампании, год, ход
    header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 70)
    pygame.draw.rect(surface, COLOR_UI_BG, header_rect)
    pygame.draw.line(surface, COLOR_UI_ACCENT, (0, 70), (SCREEN_WIDTH, 70), 2)

    stage_info = game_state.get_stage_info()
    title_text = f"{stage_info.name_ru}  |  {game_state.year} г.  |  Ход {game_state.turn}"
    title_surf = font_title.render(title_text, True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (20, 20))

    # Карта
    draw_map(surface, game_state, font)

    # Панель снизу — информация и кнопки
    footer_rect = pygame.Rect(0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 80)
    pygame.draw.rect(surface, COLOR_UI_BG, footer_rect)
    pygame.draw.line(surface, COLOR_UI_ACCENT, (0, SCREEN_HEIGHT - 80), (SCREEN_WIDTH, SCREEN_HEIGHT - 80), 2)

    # Кнопка "Следующий ход"
    btn_rect = pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 65, 160, 50)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, btn_rect)
    pygame.draw.rect(surface, COLOR_TEXT, btn_rect, 2)
    btn_text = font.render("Следующий ход", True, COLOR_UI_BG)
    btn_text_rect = btn_text.get_rect(center=btn_rect.center)
    surface.blit(btn_text, btn_text_rect)

    # Подсказка
    hint = "Зелёные — ваши крепости, красные — Византия. Захват крепостей — через механику осады (в разработке)."
    hint_surf = font.render(hint, True, COLOR_TEXT_DIM)
    surface.blit(hint_surf, (20, SCREEN_HEIGHT - 55))


def draw_narrative_dialog(
    surface: pygame.Surface,
    event,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[pygame.Rect]:
    """
    Рисует диалоговое окно нарративного события.
    Возвращает список rect для кнопок выбора (для обработки кликов).
    """
    # Полупрозрачный фон
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    # Окно диалога
    dialog_w = 700
    dialog_h = 400
    dialog_x = (SCREEN_WIDTH - dialog_w) // 2
    dialog_y = (SCREEN_HEIGHT - dialog_h) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
    pygame.draw.rect(surface, COLOR_UI_BG, dialog_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, dialog_rect, 3)

    # Заголовок
    title_surf = font_title.render(event.title, True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (dialog_x + 20, dialog_y + 15))

    # Текст события (с переносом строк)
    body_lines = _wrap_text(event.body, font, dialog_w - 40)
    y_offset = dialog_y + 60
    for line in body_lines:
        line_surf = font.render(line, True, COLOR_TEXT)
        surface.blit(line_surf, (dialog_x + 20, y_offset))
        y_offset += 28

    # Кнопки выбора
    button_rects = []
    btn_y = dialog_y + dialog_h - 80
    btn_w = 200
    btn_h = 45
    spacing = 20
    total_btn_width = len(event.choices) * btn_w + (len(event.choices) - 1) * spacing
    start_x = dialog_x + (dialog_w - total_btn_width) // 2

    for i, choice in enumerate(event.choices):
        btn_x = start_x + i * (btn_w + spacing)
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, COLOR_UI_ACCENT, btn_rect)
        pygame.draw.rect(surface, COLOR_TEXT, btn_rect, 1)

        # Текст кнопки (сокращённый)
        btn_label = choice.text[:25] + "..." if len(choice.text) > 25 else choice.text
        btn_text_surf = font.render(btn_label, True, COLOR_UI_BG)
        btn_text_rect = btn_text_surf.get_rect(center=btn_rect.center)
        surface.blit(btn_text_surf, btn_text_rect)
        button_rects.append((btn_rect, choice))

    return button_rects


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Перенос текста по словам"""
    words = text.split()
    lines = []
    current_line = []
    current_width = 0

    for word in words:
        test_line = " ".join(current_line + [word])
        test_surf = font.render(test_line, True, (255, 255, 255))
        if test_surf.get_width() <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def is_end_turn_button_clicked(mouse_pos: tuple[int, int]) -> bool:
    """Проверить клик по кнопке «Следующий ход»"""
    btn_rect = pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 65, 160, 50)
    return btn_rect.collidepoint(mouse_pos)
