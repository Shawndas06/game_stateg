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
from src.map.map_renderer import draw_map, get_clicked_fortress, MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT


# === МЕНЮ ВХОДА ===

MENU_BTN_NEW_GAME = "new_game"
MENU_BTN_LOAD_GAME = "load_game"
MENU_BTN_SETTINGS = "settings"
MENU_BTN_EXIT = "exit"


def draw_main_menu(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    has_save: bool = False,
) -> list[tuple[pygame.Rect, str]]:
    """
    Рисует меню входа.
    Возвращает список (rect, action) для обработки кликов.
    has_save: есть ли сохранение (кнопка «Загрузить» активна/неактивна)
    """
    surface.fill(COLOR_UI_BG)

    # Заголовок
    title = "Османская кампания"
    subtitle = "Беелик → Султанат → Империя"
    title_surf = font_title.render(title, True, COLOR_UI_ACCENT)
    subtitle_surf = font.render(subtitle, True, COLOR_TEXT_DIM)
    title_rect = title_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 120)
    subtitle_rect = subtitle_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 85)
    surface.blit(title_surf, title_rect)
    surface.blit(subtitle_surf, subtitle_rect)

    # Кнопки
    button_actions = []
    btn_w, btn_h = 280, 50
    btn_y = SCREEN_HEIGHT // 2 - 35
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    spacing = 12

    # Новая игра
    rect_new = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_new)
    pygame.draw.rect(surface, COLOR_TEXT, rect_new, 2)
    surface.blit(font.render("Новая игра", True, COLOR_UI_BG),
                 font.render("Новая игра", True, COLOR_UI_BG).get_rect(center=rect_new.center))
    button_actions.append((rect_new, MENU_BTN_NEW_GAME))

    # Загрузить игру
    rect_load = pygame.Rect(btn_x, btn_y + btn_h + spacing, btn_w, btn_h)
    if has_save:
        pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_load)
        pygame.draw.rect(surface, COLOR_TEXT, rect_load, 2)
        surface.blit(font.render("Загрузить игру", True, COLOR_UI_BG),
                     font.render("Загрузить игру", True, COLOR_UI_BG).get_rect(center=rect_load.center))
        button_actions.append((rect_load, MENU_BTN_LOAD_GAME))
    else:
        pygame.draw.rect(surface, COLOR_UI_BG, rect_load)
        pygame.draw.rect(surface, COLOR_TEXT_DIM, rect_load, 2)
        surface.blit(font.render("Загрузить игру", True, COLOR_TEXT_DIM),
                     font.render("Загрузить игру", True, COLOR_TEXT_DIM).get_rect(center=rect_load.center))
        button_actions.append((rect_load, MENU_BTN_LOAD_GAME))

    # Настройки
    rect_settings = pygame.Rect(btn_x, btn_y + (btn_h + spacing) * 2, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_settings)
    pygame.draw.rect(surface, COLOR_TEXT, rect_settings, 2)
    surface.blit(font.render("Настройки", True, COLOR_UI_BG),
                 font.render("Настройки", True, COLOR_UI_BG).get_rect(center=rect_settings.center))
    button_actions.append((rect_settings, MENU_BTN_SETTINGS))

    # Выход
    rect_exit = pygame.Rect(btn_x, btn_y + (btn_h + spacing) * 3, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_exit)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_exit, 2)
    surface.blit(font.render("Выход", True, COLOR_UI_ACCENT),
                 font.render("Выход", True, COLOR_UI_ACCENT).get_rect(center=rect_exit.center))
    button_actions.append((rect_exit, MENU_BTN_EXIT))

    return button_actions


def draw_settings_screen(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    fullscreen: bool,
) -> list[tuple[pygame.Rect, str]]:
    """
    Экран настроек: оконный режим / полноэкранный.
    Возвращает список (rect, action).
    """
    surface.fill(COLOR_UI_BG)

    title_surf = font_title.render("Настройки", True, COLOR_UI_ACCENT)
    title_rect = title_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 120)
    surface.blit(title_surf, title_rect)

    buttons = []
    btn_w, btn_h = 220, 50
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    y = SCREEN_HEIGHT // 2 - 40
    spacing = 15

    # Оконный режим
    rect_window = pygame.Rect(btn_x, y, btn_w, btn_h)
    c = COLOR_UI_ACCENT if not fullscreen else COLOR_UI_BG
    pygame.draw.rect(surface, c, rect_window)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_window, 2)
    txt = "Оконный режим" + (" ✓" if not fullscreen else "")
    surface.blit(font.render(txt, True, COLOR_UI_BG if not fullscreen else COLOR_UI_ACCENT),
                 font.render(txt, True, COLOR_UI_BG).get_rect(center=rect_window.center))
    buttons.append((rect_window, "settings_windowed"))

    # Полноэкранный
    rect_full = pygame.Rect(btn_x, y + btn_h + spacing, btn_w, btn_h)
    c = COLOR_UI_ACCENT if fullscreen else COLOR_UI_BG
    pygame.draw.rect(surface, c, rect_full)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_full, 2)
    txt = "Полноэкранный" + (" ✓" if fullscreen else "")
    surface.blit(font.render(txt, True, COLOR_UI_BG if fullscreen else COLOR_UI_ACCENT),
                 font.render(txt, True, COLOR_UI_BG).get_rect(center=rect_full.center))
    buttons.append((rect_full, "settings_fullscreen"))

    # Назад
    rect_back = pygame.Rect(btn_x, y + (btn_h + spacing) * 2 + 20, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_back)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_back, 2)
    surface.blit(font.render("Назад", True, COLOR_UI_ACCENT),
                 font.render("Назад", True, COLOR_UI_ACCENT).get_rect(center=rect_back.center))
    buttons.append((rect_back, "settings_back"))

    return buttons


def get_top_bar_button_rects() -> list[tuple[pygame.Rect, str]]:
    """Прямоугольники кнопок Дипломатия, Экономика, Законы в правом верхнем углу"""
    btn_w, btn_h = 115, 38
    btn_y = 16
    btn_x = SCREEN_WIDTH - btn_w * 3 - 25
    return [
        (pygame.Rect(btn_x, btn_y, btn_w, btn_h), "top_diplomacy"),
        (pygame.Rect(btn_x + btn_w + 8, btn_y, btn_w, btn_h), "top_economy"),
        (pygame.Rect(btn_x + (btn_w + 8) * 2, btn_y, btn_w, btn_h), "top_laws"),
    ]


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
    map_zoom: float = 0.6,
    map_offset_x: float = 0.0,
    map_offset_y: float = 0.0,
) -> None:
    """
    Рисует главный экран: карта + панель информации.
    """
    # Панель сверху — этап кампании, год, ход
    header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 70)
    pygame.draw.rect(surface, COLOR_UI_BG, header_rect)
    pygame.draw.line(surface, COLOR_UI_ACCENT, (0, 70), (SCREEN_WIDTH, 70), 2)

    # Кнопка меню в левом верхнем углу (≡)
    menu_btn_rect = pygame.Rect(10, 10, 45, 45)
    pygame.draw.rect(surface, COLOR_UI_BG, menu_btn_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, menu_btn_rect, 2)
    menu_icon = font.render("≡", True, COLOR_UI_ACCENT)
    surface.blit(menu_icon, menu_icon.get_rect(center=menu_btn_rect.center))

    # Кнопки справа: Дипломатия, Экономика, Законы
    btn_w, btn_h = 115, 38
    btn_y = 16
    btn_x = SCREEN_WIDTH - btn_w * 3 - 25
    diplomacy_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, diplomacy_rect)
    pygame.draw.rect(surface, COLOR_TEXT, diplomacy_rect, 2)
    surface.blit(font.render("Дипломатия", True, COLOR_UI_BG),
                 font.render("Дипломатия", True, COLOR_UI_BG).get_rect(center=diplomacy_rect.center))

    economy_rect = pygame.Rect(btn_x + btn_w + 8, btn_y, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, economy_rect)
    pygame.draw.rect(surface, COLOR_TEXT, economy_rect, 2)
    surface.blit(font.render("Экономика", True, COLOR_UI_BG),
                 font.render("Экономика", True, COLOR_UI_BG).get_rect(center=economy_rect.center))

    laws_rect = pygame.Rect(btn_x + (btn_w + 8) * 2, btn_y, btn_w, btn_h)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, laws_rect)
    pygame.draw.rect(surface, COLOR_TEXT, laws_rect, 2)
    surface.blit(font.render("Законы", True, COLOR_UI_BG),
                 font.render("Законы", True, COLOR_UI_BG).get_rect(center=laws_rect.center))

    # Заголовок — этап, год, ход, золото, армия
    stage_info = game_state.get_stage_info()
    gold = getattr(game_state, "gold", 0)
    field_army = getattr(game_state, "field_army", 0)
    title_text = f"{stage_info.name_ru}  |  {game_state.year} г.  |  Ход {game_state.turn}  |  Золото: {gold}  |  Армия: {field_army}"
    title_surf = font_title.render(title_text, True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (70, 20))

    # Карта (zoom, pan)
    draw_map(surface, game_state, font, map_zoom, map_offset_x, map_offset_y)

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
    hint = "Столица (★) → армия. Крепости → найм, столица, переименование. Вражеская → осада. Колёсико — зум, ЛКМ — панорама."
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


# === КНОПКА МЕНЮ И POPUP ===

PAUSE_SAVE = "pause_save"
PAUSE_EXIT = "pause_exit"
PAUSE_CLOSE = "pause_close"


def get_pause_menu_button_rect() -> pygame.Rect:
    """Прямоугольник кнопки меню (≡) в левом верхнем углу"""
    return pygame.Rect(10, 10, 45, 45)


def draw_pause_popup(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Рисует окно паузы в центре экрана с тремя кнопками.
    Возвращает список (rect, action) для обработки кликов.
    """
    # Полупрозрачный фон
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    # Окно в центре
    popup_w, popup_h = 400, 280
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(surface, COLOR_UI_BG, popup_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, popup_rect, 3)

    # Заголовок
    title_surf = font_title.render("Меню", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 20))

    # Три кнопки
    button_actions = []
    btn_w, btn_h = 240, 50
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    start_y = popup_y + 80
    spacing = 15

    labels = [
        ("Сохранить игру", PAUSE_SAVE),
        ("Выйти", PAUSE_EXIT),
        ("Закрыть", PAUSE_CLOSE),
    ]

    for i, (label, action) in enumerate(labels):
        btn_rect = pygame.Rect(btn_x, start_y + i * (btn_h + spacing), btn_w, btn_h)
        pygame.draw.rect(surface, COLOR_UI_ACCENT if action != PAUSE_CLOSE else COLOR_UI_BG, btn_rect)
        pygame.draw.rect(surface, COLOR_UI_ACCENT, btn_rect, 2)
        btn_text = font.render(label, True, COLOR_UI_BG if action != PAUSE_CLOSE else COLOR_UI_ACCENT)
        surface.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
        button_actions.append((btn_rect, action))

    return button_actions


def get_pause_button_at_pos(mouse_pos: tuple[int, int], buttons: list) -> str | None:
    """Проверить клик по кнопке popup. Возвращает action или None."""
    for rect, action in buttons:
        if rect.collidepoint(mouse_pos):
            return action
    return None


# === ДИАЛОГ СТОЛИЦЫ (сбор армии) ===

CAPITAL_TRANSFER = "capital_transfer"  # capital_transfer:source_id:amount
CAPITAL_CANCEL = "capital_cancel"


def draw_capital_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    get_fortress_name_ru,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно столицы — сбор походной армии из других крепостей.
    Список крепостей с прокруткой — ограниченная область, кнопки фиксированы внизу.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 520, 480
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(surface, COLOR_UI_BG, popup_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, popup_rect, 3)

    field_army = getattr(game_state, "field_army", 0)

    title_surf = font_title.render(f"Столица: {fortress_name_ru}", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 12))
    army_surf = font.render(f"Походная армия: {field_army} воинов", True, COLOR_TEXT)
    surface.blit(army_surf, (popup_x + 20, popup_y + 40))
    hint_surf = font.render("Заберите войска из крепостей в армию:", True, COLOR_TEXT_DIM)
    surface.blit(hint_surf, (popup_x + 20, popup_y + 65))

    # Область списка крепостей (фиксированная высота, не выходит за границы)
    list_top = popup_y + 88
    list_bottom = popup_y + popup_h - 58  # Место для кнопок внизу
    row_height = 48  # Достаточно для название + кнопки в ряд
    max_visible_rows = max(1, (list_bottom - list_top) // row_height)

    buttons = []
    other = game_state.get_other_owned_fortresses(game_state.capital_id)
    row_idx = 0

    for source_id, garrison in other:
        if garrison <= 1:
            continue
        if row_idx >= max_visible_rows:
            break
        row_y = list_top + row_idx * row_height
        name_ru = get_fortress_name_ru(source_id)
        row_surf = font.render(f"{name_ru} ({garrison}):", True, COLOR_TEXT_DIM)
        surface.blit(row_surf, (popup_x + 20, row_y))
        btn_y_row = row_y + 2

        btn_x = popup_x + 180
        options = []
        for amt in [25, 50, 75]:
            if 1 <= amt < garrison:
                options.append(amt)
        options.append(max(1, garrison - 1))
        options = sorted(set(options))

        for amt in options:
            if btn_x + 58 > popup_x + popup_w - 20:
                break
            rect = pygame.Rect(btn_x, btn_y_row, 56, 28)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 1)
            txt = font.render(f"+{amt}", True, COLOR_UI_BG)
            surface.blit(txt, txt.get_rect(center=rect.center))
            buttons.append((rect, f"capital_transfer:{source_id}:{amt}"))
            btn_x += 60
        row_idx += 1

    # Кнопки внизу — фиксированная позиция, не перекрываются
    btn_y = popup_y + popup_h - 52
    rect_rename = pygame.Rect(popup_x + 20, btn_y, 140, 42)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_rename)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_rename, 2)
    surface.blit(font.render("Переименовать", True, COLOR_UI_ACCENT),
                 font.render("Переименовать", True, COLOR_UI_ACCENT).get_rect(center=rect_rename.center))
    buttons.append((rect_rename, "capital_rename"))

    rect_cancel = pygame.Rect(popup_x + (popup_w - 120) // 2, btn_y, 120, 42)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_cancel)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_cancel, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_cancel.center))
    buttons.append((rect_cancel, CAPITAL_CANCEL))

    return buttons


# === ДИАЛОГ ОСАДЫ ===

SIEGE_START = "siege_start"
SIEGE_ASSAULT = "siege_assault"
SIEGE_CANCEL = "siege_cancel"
SIEGE_SELECT = "siege_select"  # siege_field:amount:mode


def draw_siege_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    fortress_id: str,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    get_fortress_name_ru,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно осады крепости. Выбор крепости-источника и количества войск.
    Возвращает (rect, action). action: "siege_select:source_id:amount" или SIEGE_CANCEL.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 500, 420
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(surface, COLOR_UI_BG, popup_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, popup_rect, 3)

    defender = game_state.get_defender_garrison(fortress_id)
    effective_defender = game_state.get_effective_defender(fortress_id)
    siege_info = game_state.sieges_in_progress.get(fortress_id)
    field_army = getattr(game_state, "field_army", 0)
    adjacent = game_state.get_adjacent_owned_fortresses(fortress_id)

    title_surf = font_title.render(f"Осада: {fortress_name_ru}", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 15))
    def_surf = font.render(f"Гарнизон защитников: {defender}  |  Ваша армия: {field_army}", True, COLOR_TEXT)
    surface.blit(def_surf, (popup_x + 20, popup_y + 45))

    buttons = []
    btn_h = 36
    y = popup_y + 75

    if fortress_id not in getattr(game_state, "byzantine_owned", set()):
        body_surf = font.render("Только византийские крепости можно осаждать. Другие государства — в будущих обновлениях.", True, COLOR_TEXT_DIM)
        surface.blit(body_surf, (popup_x + 20, y))
        y += 50
    elif siege_info:
        body = f"Осада в процессе. Атакующих: {siege_info.attacker_troops}. Ходов до капитуляции: {siege_info.turns_remaining}"
        body_surf = font.render(body, True, COLOR_TEXT)
        surface.blit(body_surf, (popup_x + 20, y))
        y += 50
    elif not adjacent:
        body_surf = font.render("Нет своих крепостей рядом. Армия не может достичь цели.", True, COLOR_TEXT_DIM)
        surface.blit(body_surf, (popup_x + 20, y))
        y += 40
    elif field_army <= defender:
        body_surf = font.render("Соберите армию в столице (Сёгют)! Нужно больше защитников.", True, COLOR_TEXT_DIM)
        surface.blit(body_surf, (popup_x + 20, y))
        y += 40
    else:
        body_surf = font.render("Отправить армию (собрана в столице):", True, COLOR_TEXT)
        surface.blit(body_surf, (popup_x + 20, y))
        y += 35

        # Варианты: мин (defender+1), 50%, 75%, вся армия
        amounts = set()
        if field_army > defender:
            amounts.add(defender + 1)
        amounts.add(max(defender + 1, field_army // 2))
        amounts.add(max(defender + 1, field_army * 3 // 4))
        amounts.add(field_army)
        amounts = sorted([a for a in amounts if defender < a <= field_army])

        btn_x = popup_x + 40
        for amt in amounts:
            if amt <= defender:
                continue
            rect = pygame.Rect(btn_x, y, 95, btn_h)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 1)
            txt = font.render(f"{amt} осада", True, COLOR_UI_BG)
            surface.blit(txt, txt.get_rect(center=rect.center))
            buttons.append((rect, f"siege_field:{amt}:siege"))
            btn_x += 102

        assault_needed = int(effective_defender * 1.5)
        if field_army >= assault_needed:
            rect = pygame.Rect(btn_x, y, 90, btn_h)
            pygame.draw.rect(surface, (180, 60, 40), rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 1)
            txt = font.render("Штурм", True, COLOR_TEXT)
            surface.blit(txt, txt.get_rect(center=rect.center))
            buttons.append((rect, f"siege_field:{assault_needed}:assault"))
        y += 50

    # Закрыть
    rect_cancel = pygame.Rect((SCREEN_WIDTH - 120) // 2, popup_y + popup_h - 55, 120, 45)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_cancel)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_cancel, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_cancel.center))
    buttons.append((rect_cancel, SIEGE_CANCEL))

    return buttons


# === ДИАЛОГ НАЙМА ВОЙСК ===

HIRE_CONFIRM = "hire_confirm"
HIRE_CANCEL = "hire_cancel"
HIRE_AMOUNT = "hire_amount"  # hire_amount:count


def draw_hire_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    fortress_id: str,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно найма войск в крепости.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 420, 280
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(surface, COLOR_UI_BG, popup_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, popup_rect, 3)

    garrison = game_state._get_garrison(fortress_id)
    gold = game_state.gold
    cost_per = 5

    title_surf = font_title.render(f"Крепость: {fortress_name_ru}", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 15))
    g_surf = font.render(f"Гарнизон: {garrison} воинов", True, COLOR_TEXT)
    surface.blit(g_surf, (popup_x + 20, popup_y + 50))
    gold_surf = font.render(f"Золото: {gold} (найм: {cost_per} за воина)", True, COLOR_TEXT)
    surface.blit(gold_surf, (popup_x + 20, popup_y + 75))

    surface.blit(font.render("Нанять воинов:", True, COLOR_TEXT), (popup_x + 20, popup_y + 105))

    buttons = []
    amounts = [10, 25, 50, 100]
    btn_w, btn_h = 70, 38
    hire_y = popup_y + 135
    start_x = popup_x + 20
    for i, amt in enumerate(amounts):
        cost = amt * cost_per
        rect = pygame.Rect(start_x + i * (btn_w + 10), hire_y, btn_w, btn_h)
        if gold >= cost:
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            txt = font.render(f"+{amt}", True, COLOR_UI_BG)
        else:
            pygame.draw.rect(surface, COLOR_UI_BG, rect)
            pygame.draw.rect(surface, COLOR_TEXT_DIM, rect, 2)
            txt = font.render(f"+{amt}", True, COLOR_TEXT_DIM)
        surface.blit(txt, txt.get_rect(center=rect.center))
        buttons.append((rect, f"hire_amount:{amt}"))

    # Нижний ряд: [Столица] [Закрыть] [Переименовать] — без наложения
    btn_y = popup_y + popup_h - 48
    btn_h = 38
    if fortress_id != game_state.capital_id:
        rect_capital = pygame.Rect(popup_x + 15, btn_y, 125, btn_h)
        pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_capital)
        pygame.draw.rect(surface, COLOR_TEXT, rect_capital, 2)
        surface.blit(font.render("Столица сюда", True, COLOR_UI_BG),
                     font.render("Столица сюда", True, COLOR_UI_BG).get_rect(center=rect_capital.center))
        buttons.append((rect_capital, f"make_capital:{fortress_id}"))

    rect_cancel = pygame.Rect(popup_x + (popup_w - 95) // 2, btn_y, 95, btn_h)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_cancel)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_cancel, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_cancel.center))
    buttons.append((rect_cancel, HIRE_CANCEL))

    rect_rename = pygame.Rect(popup_x + popup_w - 130, btn_y, 115, btn_h)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_rename)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_rename, 2)
    surface.blit(font.render("Переимен.", True, COLOR_UI_ACCENT),
                 font.render("Переимен.", True, COLOR_UI_ACCENT).get_rect(center=rect_rename.center))
    buttons.append((rect_rename, f"hire_rename:{fortress_id}"))

    return buttons


def draw_rename_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    fortress_id: str,
    current_text: str,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно переименования крепости. current_text — текущий ввод.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 450, 200
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    pygame.draw.rect(surface, COLOR_UI_BG, popup_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, popup_rect, 3)

    title_surf = font_title.render(f"Переименовать: {fortress_name_ru}", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 15))

    input_rect = pygame.Rect(popup_x + 20, popup_y + 60, popup_w - 40, 45)
    pygame.draw.rect(surface, (60, 65, 80), input_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, input_rect, 2)
    display_text = current_text if current_text else "Введите новое имя..."
    text_color = COLOR_TEXT if current_text else COLOR_TEXT_DIM
    text_surf = font.render(display_text[:40], True, text_color)
    surface.blit(text_surf, (input_rect.x + 10, input_rect.y + 12))

    buttons = []
    rect_ok = pygame.Rect(popup_x + popup_w // 2 - 130, popup_y + 130, 100, 45)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_ok)
    pygame.draw.rect(surface, COLOR_TEXT, rect_ok, 2)
    surface.blit(font.render("OK", True, COLOR_UI_BG), font.render("OK", True, COLOR_UI_BG).get_rect(center=rect_ok.center))
    buttons.append((rect_ok, "rename_ok"))

    rect_cancel = pygame.Rect(popup_x + popup_w // 2 - 20, popup_y + 130, 100, 45)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_cancel)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_cancel, 2)
    surface.blit(font.render("Отмена", True, COLOR_UI_ACCENT),
                 font.render("Отмена", True, COLOR_UI_ACCENT).get_rect(center=rect_cancel.center))
    buttons.append((rect_cancel, "rename_cancel"))

    return buttons


# === ДИПЛОМАТИЯ ===

def draw_diplomacy_dialog(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно дипломатии — Византия: мир, война, дань, союз, НПП.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 520, 400
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    pygame.draw.rect(surface, COLOR_UI_BG, (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)

    rel = getattr(game_state, "byzantine_relation", "war")
    rel_names = {"war": "Война", "peace": "Мир", "tribute": "Дань", "alliance": "Союз", "nap": "НПП"}
    rel_name = rel_names.get(rel, rel)
    title_surf = font_title.render("Дипломатия: Византия", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 15))
    status_surf = font.render(f"Отношения: {rel_name}", True, COLOR_TEXT)
    surface.blit(status_surf, (popup_x + 20, popup_y + 50))

    buttons = []
    y = popup_y + 95
    options = [
        ("Мир", "diplo_peace"),
        ("Объявить войну", "diplo_war"),
        ("Обложить данью", "diplo_tribute"),
        ("Военный союз", "diplo_alliance"),
        ("Договор о ненападении", "diplo_nap"),
    ]
    for label, action in options:
        rect = pygame.Rect(popup_x + 40, y, popup_w - 80, 42)
        pygame.draw.rect(surface, COLOR_UI_ACCENT if not label.startswith("Объявить") else COLOR_UI_BG, rect)
        pygame.draw.rect(surface, COLOR_UI_ACCENT, rect, 2)
        surface.blit(font.render(label, True, COLOR_UI_BG if not label.startswith("Объявить") else COLOR_UI_ACCENT),
                     font.render(label, True, COLOR_UI_BG).get_rect(center=rect.center))
        buttons.append((rect, action))
        y += 50

    rect_close = pygame.Rect((SCREEN_WIDTH - 100) // 2, popup_y + popup_h - 52, 100, 42)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_close)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_close, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_close.center))
    buttons.append((rect_close, "diplo_close"))

    # Сообщение о результате (если есть)
    msg = getattr(game_state, "_diplomacy_message", None)
    if msg:
        msg_surf = font.render(msg, True, (150, 200, 150))
        msg_rect = msg_surf.get_rect(centerx=popup_x + popup_w // 2, bottom=popup_y + popup_h - 60)
        surface.blit(msg_surf, msg_rect)

    return buttons


# === ЭКОНОМИКА ===

def draw_economy_dialog(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно экономики — доходы, расходы на следующий ход, крепости.
    """
    from src.game.game_state import GOLD_PER_FORTRESS_PER_TURN, UPKEEP_PER_TROOP

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 520, 420
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    pygame.draw.rect(surface, COLOR_UI_BG, (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)

    gold = getattr(game_state, "gold", 0)
    fort_count = len(game_state.owned_fortresses)
    income_per = GOLD_PER_FORTRESS_PER_TURN
    income = fort_count * income_per
    garrison_total = sum(game_state._get_garrison(fid) for fid in game_state.owned_fortresses)
    field_army = getattr(game_state, "field_army", 0)
    troops_total = garrison_total + field_army
    upkeep_per = UPKEEP_PER_TROOP
    upkeep = troops_total * upkeep_per
    net = income - upkeep

    title_surf = font_title.render("Экономика", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 15))
    surface.blit(font.render(f"Казна: {gold} золота", True, COLOR_TEXT), (popup_x + 20, popup_y + 50))
    surface.blit(font.render(f"Крепостей: {fort_count}", True, COLOR_TEXT), (popup_x + 20, popup_y + 78))
    surface.blit(font.render("─ Доходы ─", True, COLOR_UI_ACCENT), (popup_x + 20, popup_y + 112))
    surface.blit(font.render(f"С крепостей ({fort_count} × {income_per}): +{income}", True, COLOR_TEXT), (popup_x + 30, popup_y + 140))
    surface.blit(font.render("─ Расходы ─", True, COLOR_UI_ACCENT), (popup_x + 20, popup_y + 175))
    surface.blit(font.render(f"Содержание войск ({troops_total} × {upkeep_per}): −{upkeep}", True, COLOR_TEXT), (popup_x + 30, popup_y + 203))
    surface.blit(font.render(f"Итого за ход: {'+' if net >= 0 else ''}{net} золота", True, COLOR_UI_ACCENT), (popup_x + 20, popup_y + 248))

    rect_close = pygame.Rect((SCREEN_WIDTH - 100) // 2, popup_y + popup_h - 52, 100, 42)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_close)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_close, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_close.center))
    return [(rect_close, "econ_close")]


# === ЗАКОНЫ ===

def draw_laws_dialog(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно законов — принятые и доступные для принятия.
    Текст не выходит за границы, не накладывается на кнопки.
    """
    from src.data.laws_data import get_laws_for_stage
    from src.ui.text_utils import truncate_text

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 680, 560
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    pygame.draw.rect(surface, COLOR_UI_BG, (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)

    stage = game_state.stage
    enacted = getattr(game_state, "enacted_laws", set())
    available = get_laws_for_stage(stage)

    title_surf = font_title.render("Законы", True, COLOR_UI_ACCENT)
    surface.blit(title_surf, (popup_x + 20, popup_y + 12))
    intro = "Принятие законов — плюсы и минусы. Новые законы открываются по мере расширения."
    surface.blit(font.render(intro, True, COLOR_TEXT_DIM), (popup_x + 20, popup_y + 45))

    # Область текста: слева от кнопки "Принять" (ширина 105), отступ 15
    text_max_w = popup_w - 145
    btn_x = popup_x + popup_w - 125

    buttons = []
    y = popup_y + 78
    for law in available[:8]:
        is_enacted = law.id in enacted
        row_h = 62

        name = f"{'[✓] ' if is_enacted else ''}{law.name_ru}"
        surface.blit(font.render(name, True, COLOR_UI_ACCENT if is_enacted else COLOR_TEXT),
                     (popup_x + 20, y))

        pros_str = "+ " + "; ".join(law.pros[:2])
        cons_str = "− " + "; ".join(law.cons[:2])
        pros_short = truncate_text(font, pros_str, text_max_w)
        cons_short = truncate_text(font, cons_str, text_max_w)
        surface.blit(font.render(pros_short, True, (120, 200, 120)), (popup_x + 25, y + 22))
        surface.blit(font.render(cons_short, True, (200, 120, 120)), (popup_x + 25, y + 40))

        if not is_enacted:
            rect = pygame.Rect(btn_x, y + 12, 100, 36)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 2)
            surface.blit(font.render("Принять", True, COLOR_UI_BG),
                         font.render("Принять", True, COLOR_UI_BG).get_rect(center=rect.center))
            buttons.append((rect, f"law_enact:{law.id}"))
        y += row_h

    rect_close = pygame.Rect((SCREEN_WIDTH - 100) // 2, popup_y + popup_h - 52, 100, 40)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_close)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_close, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_close.center))
    buttons.append((rect_close, "laws_close"))

    return buttons
