"""
screens.py — отрисовка всех экранов и диалогов игры.

Реализует:
- Победа/поражение: draw_victory_defeat_dialog.
- Главное меню: draw_main_menu (Новая игра, Загрузить, Настройки, Выход); get_menu_button_at_pos.
- Настройки: draw_settings_screen (оконный/полноэкранный, Назад).
- Верхняя панель: get_top_bar_button_rects (Ход, Дипломатия, Экономика, Законы).
- Главный экран игры: draw_main_screen (шапка с инфо, карта через map_renderer, нижняя панель с подсказкой и кнопкой «Следующий ход», блок лога действий AI).
- Нарратив: draw_narrative_dialog (событие с текстом и кнопками выбора).
- Меню паузы: get_pause_menu_button_rect, draw_pause_popup, get_pause_button_at_pos.
- Диалоги крепостей: draw_capital_dialog (столица, перевод в армию, полководец), draw_siege_dialog (осада/штурм), draw_hire_dialog (наём, постройки, наместник, столица, переименование).
- Постройки, наместник, переименование: draw_build_dialog, draw_governor_dialog, draw_rename_dialog.
- Предложения AI: draw_trade_proposal_dialog, draw_diplo_proposal_dialog.
- Дипломатия, экономика, законы: draw_diplomacy_dialog, draw_economy_dialog, draw_laws_dialog.
- Вспомогательные: is_end_turn_button_clicked, константы кнопок (MENU_BTN_*, PAUSE_*, SIEGE_CANCEL и т.д.).
"""

import pygame

from src.ui import draw_kit
from src.ui import game_assets
from src.utils.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_MAP_BACKGROUND,
    COLOR_UI_BG,
    COLOR_UI_BG_DEEP,
    COLOR_UI_PANEL,
    COLOR_UI_ACCENT,
    COLOR_UI_ACCENT_DIM,
    COLOR_UI_GOLD_LIGHT,
    COLOR_PARCHMENT,
    COLOR_PARCHMENT_SHADOW,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_SHADOW,
)
from src.map.map_renderer import draw_map, get_clicked_fortress, MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT


def _texture_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    cell: tuple[int, int],
) -> None:
    """Кнопка из спрайт-листа или запасной вариант из draw_kit."""
    tex = game_assets.get_button_sheet_cell(cell[0], cell[1])
    if tex is not None and game_assets.has_ui_buttons():
        draw_kit.draw_textured_button(surface, rect, label, font, tex)
    else:
        draw_kit.draw_primary_button(surface, rect, label, font, COLOR_UI_BG_DEEP, COLOR_UI_ACCENT, COLOR_UI_GOLD_LIGHT)


# Высота шапки игры — не наезжает на верхнюю полосу кнопок; текст в две строки.
HEADER_HEIGHT = 88
# Левая колонка статистики не заходит правее этой координаты X (оставляем место кнопкам «Ход…»).
TOP_BAR_BTN_COUNT = 5

def _header_stats_right_edge() -> int:
    btn_w, btn_h = 118, 40
    btn_x = SCREEN_WIDTH - btn_w * TOP_BAR_BTN_COUNT - 8 * (TOP_BAR_BTN_COUNT - 1) - 28
    return btn_x - 20


def _fit_stats_lines(
    line1: str,
    line2: str,
    color: tuple[int, int, int],
    max_width: int,
) -> tuple[pygame.Surface, pygame.Surface]:
    """Подобрать размер шрифта, чтобы обе строки помещались по ширине."""
    for size in (17, 15, 14, 13, 12):
        try:
            sf = pygame.font.SysFont("dejavusans", size)
        except Exception:
            sf = pygame.font.Font(None, size + 8)
        s1 = sf.render(line1, True, color)
        s2 = sf.render(line2, True, color)
        if s1.get_width() <= max_width and s2.get_width() <= max_width:
            return s1, s2
    try:
        sf = pygame.font.SysFont("dejavusans", 12)
    except Exception:
        sf = pygame.font.Font(None, 20)
    return sf.render(line1, True, color), sf.render(line2, True, color)


# === ПОБЕДА / ПОРАЖЕНИЕ ===


def draw_victory_defeat_dialog(
    surface: pygame.Surface,
    typ: str,
    message: str,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(230)
    overlay.fill(COLOR_SHADOW)
    surface.blit(overlay, (0, 0))
    popup_w, popup_h = 620, 300
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.drop_shadow(surface, popup_rect)
    accent = (88, 168, 108) if typ == "victory" else (190, 78, 88)
    parchment = game_assets.get_parchment_source()
    draw_kit.draw_parchment_backing(surface, popup_rect, parchment, COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, accent, popup_rect, 3, border_radius=10)
    draw_kit.draw_title_bar(surface, popup_rect, accent, width=5)
    title = "Победа" if typ == "victory" else "Поражение"
    surface.blit(font_title.render(title, True, (62, 48, 38)), (popup_x + 32, popup_y + 32))
    surface.blit(font.render(message, True, (46, 40, 36)), (popup_x + 32, popup_y + 100))
    buttons = []
    rect = pygame.Rect(popup_x + (popup_w - 160) // 2, popup_y + 225, 160, 52)
    _texture_button(surface, rect, "В меню", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect, "vd_menu"))
    return buttons


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
    full = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
    draw_kit.vertical_gradient(surface, full, COLOR_UI_BG_DEEP, COLOR_UI_BG)
    draw_kit.ornament_line(surface, SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT // 2 - 165, 360, COLOR_UI_ACCENT_DIM)

    scroll_rect = pygame.Rect(SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 - 210, 480, 500)
    draw_kit.draw_parchment_backing(surface, scroll_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)

    title = "Османская кампания"
    subtitle = "Беелик → Султанат → Империя"
    tag = "Пошаговая стратегия · XIII–XV века"
    title_surf = font_title.render(title, True, COLOR_UI_GOLD_LIGHT)
    subtitle_surf = font.render(subtitle, True, COLOR_UI_ACCENT)
    tag_surf = font.render(tag, True, COLOR_TEXT_DIM)
    title_rect = title_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 150)
    subtitle_rect = subtitle_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 110)
    tag_rect = tag_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 78)
    surface.blit(title_surf, title_rect)
    surface.blit(subtitle_surf, subtitle_rect)
    surface.blit(tag_surf, tag_rect)

    button_actions = []
    btn_w, btn_h = 300, 54
    btn_y = SCREEN_HEIGHT // 2 - 30
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    spacing = 14

    rect_new = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    _texture_button(surface, rect_new, "Новая игра", font, game_assets.BTN_CELL_MENU_PRIMARY)
    button_actions.append((rect_new, MENU_BTN_NEW_GAME))

    rect_load = pygame.Rect(btn_x, btn_y + btn_h + spacing, btn_w, btn_h)
    if has_save:
        _texture_button(surface, rect_load, "Загрузить игру", font, game_assets.BTN_CELL_MENU_PRIMARY)
        button_actions.append((rect_load, MENU_BTN_LOAD_GAME))
    else:
        draw_kit.draw_secondary_button(surface, rect_load, "Загрузить игру", font, COLOR_TEXT_DIM, COLOR_UI_ACCENT_DIM, COLOR_UI_BG)
        button_actions.append((rect_load, MENU_BTN_LOAD_GAME))

    rect_settings = pygame.Rect(btn_x, btn_y + (btn_h + spacing) * 2, btn_w, btn_h)
    _texture_button(surface, rect_settings, "Настройки", font, game_assets.BTN_CELL_ECONOMY)
    button_actions.append((rect_settings, MENU_BTN_SETTINGS))

    rect_exit = pygame.Rect(btn_x, btn_y + (btn_h + spacing) * 3, btn_w, btn_h)
    _texture_button(surface, rect_exit, "Выход", font, game_assets.BTN_CELL_MENU_SECOND)
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
    full = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
    draw_kit.vertical_gradient(surface, full, COLOR_UI_BG_DEEP, COLOR_UI_BG)

    title_surf = font_title.render("Настройки", True, COLOR_UI_GOLD_LIGHT)
    title_rect = title_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 120)
    surface.blit(title_surf, title_rect)

    buttons = []
    btn_w, btn_h = 240, 52
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    y = SCREEN_HEIGHT // 2 - 40
    spacing = 16

    rect_window = pygame.Rect(btn_x, y, btn_w, btn_h)
    if not fullscreen:
        draw_kit.draw_primary_button(surface, rect_window, "Оконный режим ✓", font, COLOR_UI_BG_DEEP, COLOR_UI_ACCENT, COLOR_UI_GOLD_LIGHT)
    else:
        draw_kit.draw_secondary_button(surface, rect_window, "Оконный режим", font, COLOR_TEXT, COLOR_UI_ACCENT_DIM, COLOR_UI_PANEL)
    buttons.append((rect_window, "settings_windowed"))

    rect_full = pygame.Rect(btn_x, y + btn_h + spacing, btn_w, btn_h)
    if fullscreen:
        draw_kit.draw_primary_button(surface, rect_full, "Полноэкранный ✓", font, COLOR_UI_BG_DEEP, COLOR_UI_ACCENT, COLOR_UI_GOLD_LIGHT)
    else:
        draw_kit.draw_secondary_button(surface, rect_full, "Полноэкранный", font, COLOR_TEXT, COLOR_UI_ACCENT_DIM, COLOR_UI_PANEL)
    buttons.append((rect_full, "settings_fullscreen"))

    rect_back = pygame.Rect(btn_x, y + (btn_h + spacing) * 2 + 24, btn_w, btn_h)
    draw_kit.draw_secondary_button(surface, rect_back, "Назад", font, COLOR_UI_ACCENT, COLOR_UI_ACCENT_DIM, COLOR_UI_BG_DEEP)
    buttons.append((rect_back, "settings_back"))

    return buttons


def get_top_bar_button_rects() -> list[tuple[pygame.Rect, str]]:
    """Прямоугольники кнопок Ход, Дипломатия, Экономика, Законы, Династия в правом верхнем углу."""
    btn_w, btn_h = 118, 40
    btn_y = (HEADER_HEIGHT - btn_h) // 2
    btn_x = SCREEN_WIDTH - btn_w * TOP_BAR_BTN_COUNT - 8 * (TOP_BAR_BTN_COUNT - 1) - 28
    return [
        (pygame.Rect(btn_x, btn_y, btn_w, btn_h), "top_turn"),
        (pygame.Rect(btn_x + btn_w + 8, btn_y, btn_w, btn_h), "top_diplomacy"),
        (pygame.Rect(btn_x + (btn_w + 8) * 2, btn_y, btn_w, btn_h), "top_economy"),
        (pygame.Rect(btn_x + (btn_w + 8) * 3, btn_y, btn_w, btn_h), "top_laws"),
        (pygame.Rect(btn_x + (btn_w + 8) * 4, btn_y, btn_w, btn_h), "top_dynasty"),
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
    header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT)
    draw_kit.vertical_gradient(surface, header_rect, COLOR_UI_PANEL, COLOR_UI_BG)

    menu_btn_rect = pygame.Rect(12, (HEADER_HEIGHT - 48) // 2, 48, 48)
    draw_kit.draw_secondary_button(surface, menu_btn_rect, "☰", font_title, COLOR_UI_ACCENT, COLOR_UI_ACCENT_DIM, COLOR_UI_BG_DEEP)

    btn_w, btn_h = 118, 40
    btn_y = (HEADER_HEIGHT - btn_h) // 2
    btn_x = SCREEN_WIDTH - btn_w * TOP_BAR_BTN_COUNT - 8 * (TOP_BAR_BTN_COUNT - 1) - 28
    turn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    _texture_button(surface, turn_rect, "Ход", font, game_assets.BTN_CELL_TURN)

    diplomacy_rect = pygame.Rect(btn_x + btn_w + 8, btn_y, btn_w, btn_h)
    _texture_button(surface, diplomacy_rect, "Дипломатия", font, game_assets.BTN_CELL_DIPLOMACY)

    economy_rect = pygame.Rect(btn_x + (btn_w + 8) * 2, btn_y, btn_w, btn_h)
    _texture_button(surface, economy_rect, "Экономика", font, game_assets.BTN_CELL_ECONOMY)

    laws_rect = pygame.Rect(btn_x + (btn_w + 8) * 3, btn_y, btn_w, btn_h)
    _texture_button(surface, laws_rect, "Законы", font, game_assets.BTN_CELL_LAWS)

    dynasty_rect = pygame.Rect(btn_x + (btn_w + 8) * 4, btn_y, btn_w, btn_h)
    _texture_button(surface, dynasty_rect, "Династия", font, game_assets.BTN_CELL_DYNASTY)

    pygame.draw.line(surface, COLOR_UI_ACCENT_DIM, (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 2)

    stage_info = game_state.get_stage_info()
    gold = getattr(game_state, "gold", 0)
    field_army = getattr(game_state, "field_army", 0)
    garrison_total = sum(game_state._get_garrison(fid) for fid in game_state.owned_fortresses)
    troops_total = garrison_total + field_army
    legitimacy = getattr(game_state, "legitimacy", 50)
    sultan_h = getattr(game_state, "sultan_health", 80)
    line1 = f"{stage_info.name_ru}   ·   {game_state.year} г.   ·   Ход {game_state.turn}   ·   Золото: {gold}"
    line2 = f"Армия: {field_army}   ·   Войска: {troops_total}   ·   Легит.: {legitimacy}   ·   Здор.: {sultan_h}"
    stats_left = 74
    sultan_badge = game_assets.get_sultan_portrait_circle(game_assets.SULTAN_BADGE_SIZE)
    if sultan_badge is not None:
        bx = game_assets.SULTAN_BADGE_X
        by = (HEADER_HEIGHT - sultan_badge.get_height()) // 2
        surface.blit(sultan_badge, (bx, by))
        stats_left = bx + sultan_badge.get_width() + 12
    max_stats_w = _header_stats_right_edge() - stats_left
    surf1, surf2 = _fit_stats_lines(line1, line2, COLOR_UI_GOLD_LIGHT, max(200, max_stats_w))
    ty = (HEADER_HEIGHT - surf1.get_height() - surf2.get_height() - 4) // 2
    surface.blit(surf1, (stats_left, ty))
    surface.blit(surf2, (stats_left, ty + surf1.get_height() + 4))

    # Полоса между шапкой и картой (убирает «щель» при увеличенной шапке)
    if MAP_OFFSET_Y > HEADER_HEIGHT:
        seam = pygame.Rect(0, HEADER_HEIGHT, SCREEN_WIDTH, MAP_OFFSET_Y - HEADER_HEIGHT)
        pygame.draw.rect(surface, COLOR_MAP_BACKGROUND, seam)

    # Карта (zoom, pan)
    draw_map(surface, game_state, font, map_zoom, map_offset_x, map_offset_y)

    footer_rect = pygame.Rect(0, SCREEN_HEIGHT - 82, SCREEN_WIDTH, 82)
    draw_kit.vertical_gradient(surface, footer_rect, COLOR_UI_BG, COLOR_UI_PANEL)
    pygame.draw.line(surface, COLOR_UI_ACCENT_DIM, (0, SCREEN_HEIGHT - 82), (SCREEN_WIDTH, SCREEN_HEIGHT - 82), 2)

    btn_rect = pygame.Rect(SCREEN_WIDTH - 198, SCREEN_HEIGHT - 68, 182, 52)
    _texture_button(surface, btn_rect, "Следующий ход", font, game_assets.BTN_CELL_NEXT_TURN)

    log_box_w, log_box_h = 420, 92
    log_box_x = SCREEN_WIDTH - log_box_w - 24

    turn = getattr(game_state, "turn", 0)
    if turn <= 2:
        hint = "Подсказка: Соберите армию в столице (Сёгют). Крепость → «Перевести в армию». Карту двигайте ЛКМ по морю/суше; колёсико — масштаб."
    else:
        hint = "Столица (★) → армия. Крепости → найм / осада. Колёсико — масштаб, ЛКМ на карте — двигать карту."
    hint_max_w = max(280, log_box_x - 70)
    hint_lines = _wrap_text(hint, font, hint_max_w)
    hy = SCREEN_HEIGHT - 58
    for hl in hint_lines[:2]:
        hint_line = font.render(hl, True, COLOR_TEXT_DIM)
        surface.blit(hint_line, (22, hy))
        hy += 22

    notifs = getattr(game_state, "notifications", [])[-4:]
    log_box_y = SCREEN_HEIGHT - 80 - log_box_h - 12
    log_bg = pygame.Surface((log_box_w, log_box_h))
    log_bg.set_alpha(240)
    log_bg.fill(COLOR_UI_PANEL)
    surface.blit(log_bg, (log_box_x, log_box_y))
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, (log_box_x, log_box_y, log_box_w, log_box_h), 2, border_radius=6)
    try:
        log_font = pygame.font.SysFont("dejavusans", 16)
    except Exception:
        log_font = font
    ny = log_box_y + 12
    for _, msg in reversed(notifs):
        line = (msg[:52] + "…") if len(msg) > 52 else msg
        ns = log_font.render(line, True, COLOR_TEXT)
        surface.blit(ns, (log_box_x + 14, ny))
        ny += 20
    if not notifs:
        ns = log_font.render("Действия AI появятся после хода.", True, COLOR_TEXT_DIM)
        surface.blit(ns, (log_box_x + 14, log_box_y + 36))


def draw_narrative_dialog(
    surface: pygame.Surface,
    event,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list:
    """
    Рисует диалоговое окно нарративного события.
    Возвращает список (rect, choice) для обработки кликов.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(215)
    overlay.fill(COLOR_SHADOW)
    surface.blit(overlay, (0, 0))

    dialog_w = 880
    dialog_h = 520
    dialog_x = (SCREEN_WIDTH - dialog_w) // 2
    dialog_y = (SCREEN_HEIGHT - dialog_h) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
    draw_kit.drop_shadow(surface, dialog_rect)
    parchment = game_assets.get_parchment_source()
    draw_kit.draw_parchment_backing(surface, dialog_rect, parchment, COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, dialog_rect, 3, border_radius=12)
    draw_kit.draw_title_bar(surface, dialog_rect, COLOR_UI_ACCENT_DIM, width=5)

    title_surf = font_title.render(event.title, True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (dialog_x + 32, dialog_y + 28))

    body_rect = pygame.Rect(dialog_x + 24, dialog_y + 78, dialog_w - 48, 260)
    pygame.draw.rect(surface, (30, 27, 24), body_rect, border_radius=8)
    pygame.draw.rect(surface, COLOR_UI_GOLD_LIGHT, body_rect, 2, border_radius=8)
    body_lines = _wrap_text(event.body, font, body_rect.width - 36)
    y_offset = body_rect.top + 18
    for line in body_lines[:8]:
        line_surf = font.render(line, True, COLOR_TEXT)
        surface.blit(line_surf, (body_rect.left + 18, y_offset))
        y_offset += 26

    try:
        small = pygame.font.SysFont("dejavusans", 14)
    except Exception:
        small = font

    button_rects = []
    btn_y = dialog_y + dialog_h - 118
    btn_w = min(400, (dialog_w - 80 - 24) // max(1, len(event.choices)))
    btn_h = 46
    spacing = 16
    total_btn_width = len(event.choices) * btn_w + (len(event.choices) - 1) * spacing
    start_x = dialog_x + (dialog_w - total_btn_width) // 2

    try:
        btn_font_choice = pygame.font.SysFont("dejavusans", 16)
    except Exception:
        btn_font_choice = font
    max_text_w = btn_w - 22

    for i, choice in enumerate(event.choices):
        btn_x = start_x + i * (btn_w + spacing)
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        label = choice.text
        while (
            len(label) > 3
            and btn_font_choice.render(label + "…", True, (0, 0, 0)).get_width() > max_text_w
        ):
            label = label[:-1]
        if btn_font_choice.render(label, True, (0, 0, 0)).get_width() > max_text_w:
            label = label.rstrip() + "…"
        _texture_button(surface, btn_rect, label, btn_font_choice, game_assets.BTN_CELL_MENU_PRIMARY)
        if choice.consequence:
            cx = btn_x + btn_w // 2
            cons_lines = _wrap_text(choice.consequence, small, btn_w + 40)
            cy = btn_y + btn_h + 6
            for cl in cons_lines[:2]:
                cons = small.render(cl, True, COLOR_TEXT)
                surface.blit(cons, cons.get_rect(centerx=cx, top=cy))
                cy += 16

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
    btn_rect = pygame.Rect(SCREEN_WIDTH - 198, SCREEN_HEIGHT - 68, 182, 52)
    return btn_rect.collidepoint(mouse_pos)


# === КНОПКА МЕНЮ И POPUP ===

PAUSE_SAVE = "pause_save"
PAUSE_EXIT = "pause_exit"
PAUSE_CLOSE = "pause_close"


def get_pause_menu_button_rect() -> pygame.Rect:
    """Прямоугольник кнопки меню (☰) в левом верхнем углу"""
    return pygame.Rect(12, (HEADER_HEIGHT - 48) // 2, 48, 48)


def draw_pause_popup(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """
    Рисует окно паузы в центре экрана с тремя кнопками.
    Возвращает список (rect, action) для обработки кликов.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(215)
    overlay.fill(COLOR_SHADOW)
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 480, 340
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.drop_shadow(surface, popup_rect)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)

    title_surf = font_title.render("Меню", True, (54, 42, 32))
    surface.blit(title_surf, (popup_x + 32, popup_y + 28))

    button_actions = []
    btn_w, btn_h = 300, 54
    btn_x = (SCREEN_WIDTH - btn_w) // 2
    start_y = popup_y + 96
    spacing = 18

    labels = [
        ("Сохранить игру", PAUSE_SAVE),
        ("Выйти в главное меню", PAUSE_EXIT),
        ("Закрыть", PAUSE_CLOSE),
    ]

    for i, (label, action) in enumerate(labels):
        btn_rect = pygame.Rect(btn_x, start_y + i * (btn_h + spacing), btn_w, btn_h)
        if action != PAUSE_CLOSE:
            _texture_button(surface, btn_rect, label, font, game_assets.BTN_CELL_MENU_PRIMARY)
        else:
            _texture_button(surface, btn_rect, label, font, game_assets.BTN_CELL_MENU_SECOND)
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

    popup_w, popup_h = 640, 500
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)

    field_army = getattr(game_state, "field_army", 0)
    commander = getattr(game_state, "field_army_commander", None)
    commanders = getattr(game_state, "commanders", []) or []

    title_surf = font_title.render(f"Столица: {fortress_name_ru}", True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 28, popup_y + 22))
    army_surf = font.render(f"Походная армия: {field_army} воинов  |  Полководец: {commander or '—'}", True, COLOR_TEXT)
    surface.blit(army_surf, (popup_x + 28, popup_y + 58))
    hint_surf = font.render("Заберите войска из крепостей в походную армию:", True, COLOR_TEXT_DIM)
    surface.blit(hint_surf, (popup_x + 28, popup_y + 86))

    buttons = []
    if commanders:
        surface.blit(font.render("Полководец:", True, COLOR_TEXT_DIM), (popup_x + 28, popup_y + 116))
        for i, c in enumerate(commanders[:4]):
            rect = pygame.Rect(popup_x + 150 + i * 105, popup_y + 112, 98, 32)
            sel = commander == c
            draw_kit.draw_secondary_button(surface, rect, c[:9], font, COLOR_UI_BG_DEEP if sel else COLOR_TEXT, COLOR_UI_GOLD_LIGHT, COLOR_UI_ACCENT if sel else COLOR_UI_PANEL)
            buttons.append((rect, f"set_commander:{c}"))

    # Область списка крепостей (фиксированная высота, не выходит за границы)
    list_top = popup_y + 158
    list_bottom = popup_y + popup_h - 58  # Место для кнопок внизу
    row_height = 48  # Достаточно для название + кнопки в ряд
    max_visible_rows = max(1, (list_bottom - list_top) // row_height)

    other = game_state.get_other_owned_fortresses(game_state.capital_id)
    row_idx = 0

    for source_id, garrison in other:
        if garrison <= 1:
            continue
        if row_idx >= max_visible_rows:
            break
        row_y = list_top + row_idx * row_height
        name_ru = get_fortress_name_ru(source_id)
        row_rect = pygame.Rect(popup_x + 24, row_y - 4, popup_w - 48, row_height - 6)
        pygame.draw.rect(surface, (28, 25, 23), row_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, row_rect, 1, border_radius=6)
        row_surf = font.render(f"{name_ru} ({garrison})", True, COLOR_TEXT)
        surface.blit(row_surf, (popup_x + 36, row_y + 6))
        btn_y_row = row_y + 2

        btn_x = popup_x + 250
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
            draw_kit.draw_secondary_button(surface, rect, f"+{amt}", font, COLOR_UI_BG_DEEP, COLOR_UI_GOLD_LIGHT, COLOR_UI_ACCENT)
            buttons.append((rect, f"capital_transfer:{source_id}:{amt}"))
            btn_x += 60
        row_idx += 1

    # Кнопки внизу — фиксированная позиция, не перекрываются
    btn_y = popup_y + popup_h - 52
    rect_rename = pygame.Rect(popup_x + 28, btn_y, 180, 42)
    _texture_button(surface, rect_rename, "Переименовать", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_rename, "capital_rename"))

    rect_cancel = pygame.Rect(popup_x + popup_w - 168, btn_y, 140, 42)
    _texture_button(surface, rect_cancel, "Закрыть", font, game_assets.BTN_CELL_MENU_SECOND)
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

    popup_w, popup_h = 640, 440
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)

    defender = game_state.get_defender_garrison(fortress_id)
    effective_defender = game_state.get_effective_defender(fortress_id, 0)
    siege_info = game_state.sieges_in_progress.get(fortress_id)
    field_army = getattr(game_state, "field_army", 0)
    adjacent = game_state.get_adjacent_owned_fortresses(fortress_id)

    title_surf = font_title.render(f"Осада: {fortress_name_ru}", True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 28, popup_y + 24))
    def_surf = font.render(f"Гарнизон защитников: {defender}  |  Ваша армия: {field_army}", True, COLOR_TEXT)
    surface.blit(def_surf, (popup_x + 28, popup_y + 62))

    buttons = []
    btn_h = 40
    y = popup_y + 104

    # Проверяем, враг ли это (любая не-османская крепость)
    if not game_state.is_fortress_enemy(fortress_id):
        body_surf = font.render("Это ваша крепость! Осаждать не нужно.", True, COLOR_TEXT_DIM)
        surface.blit(body_surf, (popup_x + 28, y))
        y += 50
    elif siege_info:
        supplies = getattr(siege_info, "defender_supplies", 3)
        catapults = getattr(siege_info, "catapults", 0)
        cat_text = f", Катапульт: {catapults}" if catapults else ""
        siege_turns = 3 - siege_info.turns_remaining
        body = f"Осада. Атакующих: {siege_info.attacker_troops}{cat_text}. Снабжение: {supplies}. Ходов: {siege_info.turns_remaining}"
        body_surf = font.render(body, True, COLOR_TEXT)
        surface.blit(body_surf, (popup_x + 28, y))
        y += 35
        eff_siege = game_state._get_effective_defender(fortress_id, max(0, siege_turns))
        assault_needed = int(eff_siege * 1.5)
        siege_troops = siege_info.attacker_troops
        can_assault = (field_army >= assault_needed or siege_troops >= assault_needed) and siege_turns > 0
        if can_assault:
            rect = pygame.Rect(popup_x + 28, y, 190, btn_h)
            _texture_button(surface, rect, "Штурм ослабленной крепости", font, game_assets.BTN_CELL_MENU_SECOND)
            buttons.append((rect, f"siege_field:{assault_needed}:assault"))
        y += 50
    elif not adjacent:
        for line in _wrap_text("Нет своих крепостей рядом. Армия не может достичь цели.", font, popup_w - 56):
            surface.blit(font.render(line, True, COLOR_TEXT_DIM), (popup_x + 28, y))
            y += 24
    elif field_army <= defender:
        for line in _wrap_text("Соберите армию в столице (Сёгют). Для осады нужно больше войск, чем гарнизон защитников.", font, popup_w - 56):
            surface.blit(font.render(line, True, COLOR_TEXT_DIM), (popup_x + 28, y))
            y += 24
    else:
        body_surf = font.render("Отправить армию (собрана в столице):", True, COLOR_TEXT)
        surface.blit(body_surf, (popup_x + 28, y))
        y += 35

        # Варианты: мин (defender+1), 50%, 75%, вся армия
        amounts = set()
        if field_army > defender:
            amounts.add(defender + 1)
        amounts.add(max(defender + 1, field_army // 2))
        amounts.add(max(defender + 1, field_army * 3 // 4))
        amounts.add(field_army)
        amounts = sorted([a for a in amounts if defender < a <= field_army])

        btn_x = popup_x + 28
        for amt in amounts:
            if amt <= defender:
                continue
            rect = pygame.Rect(btn_x, y, 118, btn_h)
            _texture_button(surface, rect, f"{amt} в осаду", font, game_assets.BTN_CELL_MENU_PRIMARY)
            buttons.append((rect, f"siege_field:{amt}:siege"))
            btn_x += 126

        assault_needed = int(effective_defender * 1.5)
        if field_army >= assault_needed:
            rect = pygame.Rect(btn_x, y, 104, btn_h)
            _texture_button(surface, rect, "Штурм", font, game_assets.BTN_CELL_MENU_SECOND)
            buttons.append((rect, f"siege_field:{assault_needed}:assault"))
        y += 50

    # Закрыть
    rect_cancel = pygame.Rect(popup_x + popup_w - 168, popup_y + popup_h - 58, 140, 44)
    _texture_button(surface, rect_cancel, "Закрыть", font, game_assets.BTN_CELL_MENU_SECOND)
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
    """Окно крепости: найм войск (по типу), постройки, наместник."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 640, 500
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)

    garrison = game_state._get_garrison(fortress_id)
    gold = game_state.gold
    field_army = getattr(game_state, "field_army", 0)
    mods = game_state._get_law_modifiers() if hasattr(game_state, "_get_law_modifiers") else {"hire_cost": 1.0}
    from src.data.troops_data import get_troops_for_stage, get_troop_type

    troops = get_troops_for_stage(game_state.stage)
    governor = (game_state.fortress_governors or {}).get(fortress_id, "")
    buildings = (game_state.fortress_buildings or {}).get(fortress_id, set())
    build_prog = (game_state.fortress_build_progress or {}).get(fortress_id)

    title_surf = font_title.render(f"Крепость: {fortress_name_ru}", True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 28, popup_y + 22))
    surface.blit(font.render(f"Гарнизон: {garrison} | Золото: {gold}", True, COLOR_TEXT), (popup_x + 28, popup_y + 58))
    unrest = (game_state.fortress_unrest or {}).get(fortress_id, 0)
    gov_text = f"Наместник: {governor or '—'}"
    if unrest > 0:
        gov_text += f"  |  Недовольство: {unrest}%"
    surface.blit(font.render(gov_text, True, COLOR_TEXT_DIM), (popup_x + 28, popup_y + 82))
    if buildings:
        from src.data.buildings_data import get_building
        names = []
        for bid in list(buildings)[:4]:
            b = get_building(bid)
            names.append(b.name_ru[:10] if b else bid[:8])
        surface.blit(font.render(f"Здания: {', '.join(names)}", True, COLOR_TEXT_DIM), (popup_x + 28, popup_y + 104))
    if build_prog:
        bid, left = build_prog
        from src.data.buildings_data import get_building
        b = get_building(bid)
        bname = b.name_ru if b else bid
        surface.blit(font.render(f"Строится: {bname} ({left} ход.)", True, COLOR_UI_ACCENT), (popup_x + 28, popup_y + 126))

    buttons = []
    y = popup_y + 150
    hire_mult = 1.0
    from src.data.buildings_data import get_building
    for bid in (game_state.fortress_buildings or {}).get(fortress_id, set()):
        b = get_building(bid)
        if b and getattr(b, "hire_bonus", 0):
            hire_mult += b.hire_bonus
    for t in troops[:6]:
        tt = get_troop_type(t.id)
        if not tt:
            continue
        cost_per = max(1, int(tt.cost * mods["hire_cost"] * hire_mult))
        row_rect = pygame.Rect(popup_x + 24, y - 5, popup_w - 48, 32)
        pygame.draw.rect(surface, (28, 25, 23), row_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, row_rect, 1, border_radius=6)
        surface.blit(font.render(f"{tt.name_ru} ({cost_per})", True, COLOR_TEXT), (popup_x + 36, y + 3))
        for j, amt in enumerate([5, 15, 30]):
            rect = pygame.Rect(popup_x + 340 + j * 64, y - 2, 58, 28)
            cost = amt * cost_per
            ok = gold >= cost
            if ok:
                draw_kit.draw_secondary_button(surface, rect, f"+{amt}", font, COLOR_UI_BG_DEEP, COLOR_UI_GOLD_LIGHT, COLOR_UI_ACCENT)
            else:
                draw_kit.draw_secondary_button(surface, rect, f"+{amt}", font, COLOR_TEXT_DIM, COLOR_UI_ACCENT_DIM, COLOR_UI_PANEL)
            buttons.append((rect, f"hire_amount:{amt}:{t.id}"))
        y += 38

    btn_y = popup_y + popup_h - 54
    btn_h = 42
    btn_w = 104
    x = popup_x + 24
    rect_build = pygame.Rect(x, btn_y, btn_w, btn_h)
    _texture_button(surface, rect_build, "Строить", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_build, f"fort_build:{fortress_id}"))
    x += btn_w + 10
    rect_gov = pygame.Rect(x, btn_y, btn_w, btn_h)
    _texture_button(surface, rect_gov, "Наместник", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_gov, f"fort_governor:{fortress_id}"))
    x += btn_w + 10
    if fortress_id != game_state.capital_id:
        rect_capital = pygame.Rect(x, btn_y, btn_w, btn_h)
        _texture_button(surface, rect_capital, "Столица", font, game_assets.BTN_CELL_MENU_PRIMARY)
        buttons.append((rect_capital, f"make_capital:{fortress_id}"))
        x += btn_w + 10
    rect_cancel = pygame.Rect(x, btn_y, btn_w, btn_h)
    _texture_button(surface, rect_cancel, "Закрыть", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_cancel, HIRE_CANCEL))
    x += btn_w + 10
    rect_rename = pygame.Rect(x, btn_y, btn_w, btn_h)
    _texture_button(surface, rect_rename, "Имя", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_rename, f"hire_rename:{fortress_id}"))

    commander = getattr(game_state, "field_army_commander", None)
    commanders = getattr(game_state, "commanders", []) or []
    if commanders and field_army > 0:
        surface.blit(font.render("Полководец:", True, COLOR_TEXT_DIM), (popup_x + 28, btn_y - 32))
        for i, c in enumerate(commanders[:4]):
            rect = pygame.Rect(popup_x + 150 + i * 96, btn_y - 36, 88, 28)
            sel = commander == c
            draw_kit.draw_secondary_button(surface, rect, c[:7], font, COLOR_UI_BG_DEEP if sel else COLOR_TEXT, COLOR_UI_GOLD_LIGHT, COLOR_UI_ACCENT if sel else COLOR_UI_PANEL)
            buttons.append((rect, f"set_commander:{c}"))

    return buttons


def draw_build_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    fortress_id: str,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """Окно постройки зданий."""
    from src.data.buildings_data import BUILDINGS_DATA, get_building
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    popup_w, popup_h = 560, 500
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    pygame.draw.rect(surface, COLOR_UI_BG, (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)
    surface.blit(font_title.render(f"Постройка: {fortress_name_ru}", True, COLOR_UI_ACCENT), (popup_x + 20, popup_y + 12))
    surface.blit(font.render(f"Золото: {game_state.gold}", True, COLOR_TEXT), (popup_x + 20, popup_y + 45))
    built = (game_state.fortress_buildings or {}).get(fortress_id, set())
    in_progress = (game_state.fortress_build_progress or {}).get(fortress_id)
    buttons = []
    y = popup_y + 75
    rect_close = pygame.Rect((popup_w - 100) // 2 + popup_x, popup_y + popup_h - 50, 100, 40)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_close)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_close, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT), font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_close.center))
    buttons.append((rect_close, "build_close"))
    for b in BUILDINGS_DATA[:12]:
        if b.required_stage == "sultanate" and game_state.stage == "beylik":
            continue
        if b.required_stage == "empire" and game_state.stage in ("beylik", "sultanate"):
            continue
        name_text = f"{b.name_ru} — {b.cost} зол."
        if b.id in built:
            surface.blit(font.render(f"✓ {b.name_ru} (построено)", True, COLOR_TEXT_DIM), (popup_x + 20, y))
        elif in_progress and in_progress[0] == b.id:
            surface.blit(font.render(f"... {b.name_ru} (строится)", True, COLOR_UI_ACCENT), (popup_x + 20, y))
        elif game_state.gold >= b.cost and fortress_id not in (game_state.fortress_build_progress or {}):
            surface.blit(font.render(name_text, True, COLOR_TEXT), (popup_x + 20, y))
            rect = pygame.Rect(popup_x + 360, y - 4, 95, 28)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 2)
            surface.blit(font.render("Строить", True, COLOR_UI_BG), font.render("Строить", True, COLOR_UI_BG).get_rect(center=rect.center))
            buttons.append((rect, f"build_{b.id}"))
        else:
            surface.blit(font.render(name_text, True, COLOR_TEXT_DIM), (popup_x + 20, y))
        y += 30
    return buttons


def draw_governor_dialog(
    surface: pygame.Surface,
    fortress_name_ru: str,
    fortress_id: str,
    current_text: str,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """Окно назначения наместника."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    popup_w, popup_h = 480, 240
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    pygame.draw.rect(surface, COLOR_UI_BG, (popup_x, popup_y, popup_w, popup_h))
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)
    surface.blit(font_title.render(f"Наместник: {fortress_name_ru}", True, COLOR_UI_ACCENT), (popup_x + 20, popup_y + 15))
    input_rect = pygame.Rect(popup_x + 20, popup_y + 60, popup_w - 40, 40)
    pygame.draw.rect(surface, (60, 65, 80), input_rect)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, input_rect, 2)
    surface.blit(font.render(current_text[:30] if current_text else "Имя наместника...", True, COLOR_TEXT if current_text else COLOR_TEXT_DIM), (input_rect.x + 10, input_rect.y + 10))
    buttons = []
    rect_ok = pygame.Rect(popup_x + popup_w // 2 - 110, popup_y + 130, 90, 40)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_ok)
    pygame.draw.rect(surface, COLOR_TEXT, rect_ok, 2)
    surface.blit(font.render("OK", True, COLOR_UI_BG), font.render("OK", True, COLOR_UI_BG).get_rect(center=rect_ok.center))
    buttons.append((rect_ok, "governor_ok"))
    rect_cancel = pygame.Rect(popup_x + popup_w // 2 + 10, popup_y + 130, 90, 40)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_cancel)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_cancel, 2)
    surface.blit(font.render("Отмена", True, COLOR_UI_ACCENT), font.render("Отмена", True, COLOR_UI_ACCENT).get_rect(center=rect_cancel.center))
    buttons.append((rect_cancel, "governor_cancel"))
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

    popup_w, popup_h = 500, 240
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)

    title_surf = font_title.render(f"Переименовать: {fortress_name_ru}", True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 24, popup_y + 20))

    input_rect = pygame.Rect(popup_x + 24, popup_y + 68, popup_w - 48, 45)
    pygame.draw.rect(surface, (28, 25, 23), input_rect, border_radius=6)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, input_rect, 2, border_radius=6)
    display_text = current_text if current_text else "Введите новое имя..."
    text_color = COLOR_TEXT if current_text else COLOR_TEXT_DIM
    text_surf = font.render(display_text[:40], True, text_color)
    surface.blit(text_surf, (input_rect.x + 10, input_rect.y + 12))

    buttons = []
    rect_ok = pygame.Rect(popup_x + popup_w // 2 - 130, popup_y + 130, 100, 45)
    _texture_button(surface, rect_ok, "OK", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_ok, "rename_ok"))

    rect_cancel = pygame.Rect(popup_x + popup_w // 2 - 20, popup_y + 130, 100, 45)
    _texture_button(surface, rect_cancel, "Отмена", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_cancel, "rename_cancel"))

    return buttons


# === ДИПЛОМАТИЧЕСКОЕ ПРЕДЛОЖЕНИЕ ОТ AI (мир, дань, союз) ===


def draw_diplo_proposal_dialog(
    surface: pygame.Surface,
    faction_name_ru: str,
    proposal_type: str,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    texts = {"peace": "предлагает мир", "tribute": "согласна платить дань", "alliance": "предлагает союз"}
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    popup_w, popup_h = 480, 240
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)
    surface.blit(font_title.render(f"{faction_name_ru} {texts.get(proposal_type, proposal_type)}", True, (52, 40, 32)), (popup_x + 20, popup_y + 30))
    surface.blit(font.render("Принять или отклонить предложение.", True, (42, 38, 34)), (popup_x + 20, popup_y + 80))
    buttons = []
    rect_yes = pygame.Rect(popup_x + 80, popup_y + 130, 130, 48)
    _texture_button(surface, rect_yes, "Принять", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_yes, "diplo_accept"))
    rect_no = pygame.Rect(popup_x + 230, popup_y + 130, 140, 48)
    _texture_button(surface, rect_no, "Отклонить", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_no, "diplo_decline"))
    return buttons


# === ТОРГОВОЕ ПРЕДЛОЖЕНИЕ ОТ AI ===


def draw_trade_proposal_dialog(
    surface: pygame.Surface,
    faction_name_ru: str,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
) -> list[tuple[pygame.Rect, str]]:
    """AI предлагает торговать."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    popup_w, popup_h = 460, 220
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)
    surface.blit(font_title.render(f"{faction_name_ru} предлагает торговать", True, (52, 40, 32)), (popup_x + 20, popup_y + 25))
    surface.blit(font.render("Принять торговое соглашение?", True, (42, 38, 34)), (popup_x + 20, popup_y + 65))
    buttons = []
    rect_yes = pygame.Rect(popup_x + 55, popup_y + 108, 130, 48)
    _texture_button(surface, rect_yes, "Принять", font, game_assets.BTN_CELL_MENU_PRIMARY)
    buttons.append((rect_yes, "trade_accept"))
    rect_no = pygame.Rect(popup_x + 215, popup_y + 108, 140, 48)
    _texture_button(surface, rect_no, "Отклонить", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_no, "trade_decline"))
    return buttons


# === ДИПЛОМАТИЯ ===

def draw_diplomacy_dialog(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    selected_faction_id: str | None = None,
) -> list[tuple[pygame.Rect, str]]:
    """
    Окно дипломатии. Сначала выбор государства, затем действие (мир, война, дань, союз, НПП, торговля).
    selected_faction_id: None — список государств; иначе — действия для выбранного государства.
    """
    from src.data.factions_data import AI_FACTION_IDS, FACTION_NAMES_RU

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 620, 500
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, (popup_x, popup_y, popup_w, popup_h), 3)

    buttons = []
    rel_names = {"war": "Война", "peace": "Мир", "tribute": "Дань", "alliance": "Союз", "nap": "НПП"}

    if selected_faction_id is None:
        # Шаг 1: выбор государства
        title_surf = font_title.render("Дипломатия — выберите государство", True, (52, 40, 32))
        surface.blit(title_surf, (popup_x + 28, popup_y + 22))
        y = popup_y + 68
        col_w = (popup_w - 96) // 2
        for i, fid in enumerate(AI_FACTION_IDS):
            name = FACTION_NAMES_RU.get(fid, fid)
            row, col = i // 2, i % 2
            rect = pygame.Rect(popup_x + 28 + col * (col_w + 16), y + row * 48, col_w, 42)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect)
            pygame.draw.rect(surface, COLOR_TEXT, rect, 2)
            surface.blit(font.render(name, True, COLOR_UI_BG),
                         font.render(name, True, COLOR_UI_BG).get_rect(center=rect.center))
            buttons.append((rect, f"diplo_select:{fid}"))
    else:
        # Шаг 2: действия для выбранного государства
        target_name = FACTION_NAMES_RU.get(selected_faction_id, selected_faction_id)
        rel = game_state.get_relation_with(selected_faction_id) if hasattr(game_state, "get_relation_with") else "war"
        rel_name = rel_names.get(rel, rel)
        title_surf = font_title.render(f"Дипломатия: {target_name}", True, (52, 40, 32))
        surface.blit(title_surf, (popup_x + 28, popup_y + 22))
        mini = game_assets.get_sultan_portrait_circle(52)
        if mini is not None:
            surface.blit(mini, (popup_x + popup_w - mini.get_width() - 24, popup_y + 16))
        status_surf = font.render(f"Отношения: {rel_name}", True, (42, 38, 34))
        surface.blit(status_surf, (popup_x + 28, popup_y + 58))

        y = popup_y + 98
        options = [
            ("Мир", f"diplo_peace:{selected_faction_id}"),
            ("Объявить войну", f"diplo_war:{selected_faction_id}"),
            ("Обложить данью", f"diplo_tribute:{selected_faction_id}"),
            ("Военный союз", f"diplo_alliance:{selected_faction_id}"),
            ("Договор о ненападении", f"diplo_nap:{selected_faction_id}"),
            ("Торговое соглашение", f"diplo_trade:{selected_faction_id}"),
        ]
        for label, action in options:
            rect = pygame.Rect(popup_x + 48, y, popup_w - 96, 44)
            pygame.draw.rect(surface, COLOR_UI_ACCENT if not label.startswith("Объявить") else COLOR_UI_BG, rect)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, rect, 2)
            surface.blit(font.render(label, True, COLOR_UI_BG if not label.startswith("Объявить") else COLOR_UI_ACCENT),
                         font.render(label, True, COLOR_UI_BG).get_rect(center=rect.center))
            buttons.append((rect, action))
            y += 50

        rect_back = pygame.Rect(popup_x + 48, y + 12, 130, 42)
        pygame.draw.rect(surface, COLOR_UI_BG, rect_back)
        pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_back, 2)
        surface.blit(font.render("← Назад", True, COLOR_UI_ACCENT),
                     font.render("← Назад", True, COLOR_UI_ACCENT).get_rect(center=rect_back.center))
        buttons.append((rect_back, "diplo_back"))

    rect_close = pygame.Rect((SCREEN_WIDTH - 100) // 2, popup_y + popup_h - 50, 100, 40)
    pygame.draw.rect(surface, COLOR_UI_BG, rect_close)
    pygame.draw.rect(surface, COLOR_UI_ACCENT, rect_close, 2)
    surface.blit(font.render("Закрыть", True, COLOR_UI_ACCENT),
                 font.render("Закрыть", True, COLOR_UI_ACCENT).get_rect(center=rect_close.center))
    buttons.append((rect_close, "diplo_close"))

    msg = getattr(game_state, "_diplomacy_message", None)
    if msg:
        msg_surf = font.render(msg, True, (150, 200, 150))
        msg_rect = msg_surf.get_rect(centerx=popup_x + popup_w // 2, bottom=popup_y + popup_h - 58)
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
    Окно экономики — доходы (крепости, дань, торговля), расходы, законы.
    """
    from src.game.game_state import (
        GOLD_PER_FORTRESS_PER_TURN, UPKEEP_PER_TROOP,
        TRIBUTE_GOLD_PER_TURN, TRADE_GOLD_PER_TURN,
    )
    from src.data.factions_data import FACTION_NAMES_RU

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 580, 460
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=10)
    surface.set_clip(popup_rect)

    gold = getattr(game_state, "gold", 0)
    fort_count = len(game_state.owned_fortresses)
    mods = game_state._get_law_modifiers() if hasattr(game_state, "_get_law_modifiers") else {"income": 1.0, "upkeep": 1.0, "trade_income": 1.0}
    from src.data.buildings_data import get_building
    income = 0
    for fid in game_state.owned_fortresses:
        inc = GOLD_PER_FORTRESS_PER_TURN
        for bid in (game_state.fortress_buildings or {}).get(fid, set()):
            b = get_building(bid)
            if b:
                inc = int(inc * (b.income_mult or 1.0)) + (b.income_plus or 0)
        income += max(inc, GOLD_PER_FORTRESS_PER_TURN)
    income = int(income * mods["income"])
    tribute_count = sum(1 for fid in getattr(game_state, "ai_state", {}) if game_state.get_relation_with(fid) == "tribute")
    tribute_income = tribute_count * TRIBUTE_GOLD_PER_TURN
    trade_count = len(getattr(game_state, "trade_partners", set()))
    trade_income = int(trade_count * TRADE_GOLD_PER_TURN * mods["trade_income"])
    garrison_total = sum(game_state._get_garrison(fid) for fid in game_state.owned_fortresses)
    field_army = getattr(game_state, "field_army", 0)
    troops_total = garrison_total + field_army
    upkeep = int(troops_total * UPKEEP_PER_TROOP * mods["upkeep"])
    net = income + tribute_income + trade_income - upkeep
    is_winter = game_state.turn % 4 == 0
    if is_winter:
        income = int(income * 0.85)
        net = income + tribute_income + trade_income - upkeep

    title_surf = font_title.render("Экономика", True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 28, popup_y + 22))
    surface.blit(font.render(f"Казна: {gold} золота", True, COLOR_TEXT), (popup_x + 28, popup_y + 58))
    surface.blit(font.render(f"Крепостей: {fort_count}", True, COLOR_TEXT), (popup_x + 28, popup_y + 82))
    y_line = popup_y + 100
    surface.blit(font.render("─ Доходы ─", True, COLOR_UI_ACCENT), (popup_x + 20, y_line))
    y_line += 24
    inc_text = f"Крепости ({fort_count}): +{income}" + (" (зима −15%)" if is_winter else "")
    surface.blit(font.render(inc_text, True, COLOR_TEXT), (popup_x + 30, y_line))
    y_line += 22
    if tribute_count > 0:
        surface.blit(font.render(f"Дань (вассалы {tribute_count}): +{tribute_income}", True, COLOR_TEXT), (popup_x + 30, y_line))
        y_line += 22
    if trade_count > 0:
        surface.blit(font.render(f"Торговля ({trade_count}): +{trade_income}", True, COLOR_TEXT), (popup_x + 30, y_line))
        y_line += 22
    y_line += 6
    surface.blit(font.render("─ Расходы ─", True, COLOR_UI_ACCENT), (popup_x + 20, y_line))
    y_line += 24
    surface.blit(font.render(f"Содержание войск ({troops_total}): −{upkeep}", True, COLOR_TEXT), (popup_x + 30, y_line))
    y_line += 28
    surface.blit(font.render(f"Итого за ход: {'+' if net >= 0 else ''}{net} золота", True, COLOR_UI_ACCENT), (popup_x + 20, y_line))

    surface.set_clip(None)
    rect_close = pygame.Rect(popup_x + (popup_w - 140) // 2, popup_y + popup_h - 56, 140, 42)
    _texture_button(surface, rect_close, "Закрыть", font, game_assets.BTN_CELL_MENU_SECOND)
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

    popup_w, popup_h = 760, 620
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


# === ФАМИЛЬНОЕ ДРЕВО ОСМАНОВ ===

DYNASTY_CLOSE = "dynasty_close"
DYNASTY_SCROLL_UP = "dynasty_scroll_up"
DYNASTY_SCROLL_DOWN = "dynasty_scroll_down"


def draw_dynasty_dialog(
    surface: pygame.Surface,
    game_state,
    font_title: pygame.font.Font,
    font: pygame.font.Font,
    scroll: int = 0,
) -> list[tuple[pygame.Rect, str]]:
    """Окно с фамильным древом османской династии.

    Слева — вертикальный список султанов с медальонами-портретами,
    справа — биография выбранного (по умолчанию текущий правитель).
    """
    from src.data.dynasty_data import DYNASTY_DATA, get_current_sultan, year_from_turn

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(210)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    popup_w, popup_h = 980, 640
    popup_x = (SCREEN_WIDTH - popup_w) // 2
    popup_y = (SCREEN_HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    draw_kit.draw_parchment_backing(surface, popup_rect, game_assets.get_parchment_source(), COLOR_UI_BG_DEEP)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, popup_rect, 3, border_radius=12)

    title = "Династия Османов"
    title_surf = font_title.render(title, True, COLOR_UI_GOLD_LIGHT)
    surface.blit(title_surf, (popup_x + 28, popup_y + 22))

    year = getattr(game_state, "year", None)
    if year is None:
        year = year_from_turn(getattr(game_state, "turn", 0))
    current = get_current_sultan(year)
    sub = font.render(f"Текущий год: {year} · Правит: {current.name_ru} ({current.epithet})", True, COLOR_TEXT)
    surface.blit(sub, (popup_x + 28, popup_y + 64))

    # Левая колонка — вертикальный список султанов
    list_x = popup_x + 24
    list_y = popup_y + 100
    list_w = 360
    list_h = popup_h - 100 - 70
    list_rect = pygame.Rect(list_x, list_y, list_w, list_h)
    pygame.draw.rect(surface, (28, 25, 23), list_rect, border_radius=8)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, list_rect, 2, border_radius=8)

    row_h = 86
    visible_rows = list_h // row_h
    total = len(DYNASTY_DATA)
    max_scroll = max(0, total - visible_rows)
    scroll = max(0, min(scroll, max_scroll))

    buttons: list[tuple[pygame.Rect, str]] = []
    rendered = DYNASTY_DATA[scroll: scroll + visible_rows]

    try:
        small = pygame.font.SysFont("dejavusans", 14)
    except Exception:
        small = font

    surface.set_clip(list_rect)
    for i, sultan in enumerate(rendered):
        ry = list_y + 4 + i * row_h
        row_rect = pygame.Rect(list_x + 6, ry, list_w - 12, row_h - 6)
        is_current = sultan.id == current.id
        if is_current:
            pygame.draw.rect(surface, (62, 50, 30), row_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_UI_GOLD_LIGHT, row_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, (40, 36, 32), row_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, row_rect, 1, border_radius=6)

        # Портрет-медальон
        portrait_rect = pygame.Rect(row_rect.left + 8, row_rect.top + 6, 64, 64)
        draw_kit.draw_sultan_portrait(surface, portrait_rect, sultan.id, is_current=is_current)

        # Имя и годы
        name_color = COLOR_UI_GOLD_LIGHT if is_current else COLOR_TEXT
        name_surf = font.render(sultan.name_ru, True, name_color)
        surface.blit(name_surf, (row_rect.left + 84, row_rect.top + 8))
        years_surf = font.render(f"{sultan.reign_start}–{sultan.reign_end}", True, COLOR_TEXT_DIM)
        surface.blit(years_surf, (row_rect.left + 84, row_rect.top + 30))
        epi_surf = small.render(sultan.epithet, True, COLOR_UI_ACCENT)
        surface.blit(epi_surf, (row_rect.left + 84, row_rect.top + 54))

        buttons.append((row_rect, f"dynasty_select:{sultan.id}"))
    surface.set_clip(None)

    # Кнопки прокрутки
    if max_scroll > 0:
        scroll_up_rect = pygame.Rect(list_x + list_w - 36, list_y + 4, 32, 28)
        scroll_dn_rect = pygame.Rect(list_x + list_w - 36, list_y + list_h - 32, 32, 28)
        for r, label, act in (
            (scroll_up_rect, "▲", DYNASTY_SCROLL_UP),
            (scroll_dn_rect, "▼", DYNASTY_SCROLL_DOWN),
        ):
            pygame.draw.rect(surface, COLOR_UI_BG_DEEP, r, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, r, 1, border_radius=4)
            ts = font.render(label, True, COLOR_UI_GOLD_LIGHT)
            surface.blit(ts, ts.get_rect(center=r.center))
            buttons.append((r, act))

    # Правая колонка — биография выбранного / текущего
    selected_id = getattr(game_state, "_dynasty_selected", None) or current.id
    selected = next((s for s in DYNASTY_DATA if s.id == selected_id), current)

    bio_x = list_x + list_w + 24
    bio_y = list_y
    bio_w = popup_x + popup_w - bio_x - 24
    bio_h = list_h
    bio_rect = pygame.Rect(bio_x, bio_y, bio_w, bio_h)
    pygame.draw.rect(surface, (30, 27, 24), bio_rect, border_radius=8)
    pygame.draw.rect(surface, COLOR_UI_ACCENT_DIM, bio_rect, 2, border_radius=8)

    # Большой портрет
    big_portrait = pygame.Rect(bio_rect.left + 24, bio_rect.top + 22, 156, 156)
    draw_kit.draw_sultan_portrait(surface, big_portrait, selected.id, is_current=(selected.id == current.id))

    # Имя и эпитет
    name_big = font_title.render(selected.name_ru, True, COLOR_UI_GOLD_LIGHT)
    surface.blit(name_big, (big_portrait.right + 22, bio_rect.top + 28))
    epi_big = font.render(selected.epithet, True, COLOR_UI_ACCENT)
    surface.blit(epi_big, (big_portrait.right + 22, bio_rect.top + 70))
    years_big = font.render(f"Годы правления: {selected.reign_start}–{selected.reign_end}", True, COLOR_TEXT)
    surface.blit(years_big, (big_portrait.right + 22, bio_rect.top + 100))
    parent = next((s for s in DYNASTY_DATA if s.id == selected.parent_id), None)
    parent_label = parent.name_ru if parent else "—"
    par_big = font.render(f"Отец: {parent_label}", True, COLOR_TEXT_DIM)
    surface.blit(par_big, (big_portrait.right + 22, bio_rect.top + 128))

    # Биография (перенос по словам)
    bio_text_y = bio_rect.top + 200
    bio_text_w = bio_rect.width - 48
    bio_lines = _wrap_text(selected.bio, font, bio_text_w)
    for line in bio_lines[:10]:
        ls = font.render(line, True, COLOR_TEXT)
        surface.blit(ls, (bio_rect.left + 24, bio_text_y))
        bio_text_y += 26

    # Преемственность — стрелка от родителя
    if parent:
        link = small.render(f"↳ Сын {parent.name_ru}", True, COLOR_UI_ACCENT_DIM)
        surface.blit(link, (bio_rect.left + 24, bio_rect.bottom - 36))

    # Кнопка закрытия
    rect_close = pygame.Rect(popup_x + (popup_w - 160) // 2, popup_y + popup_h - 56, 160, 42)
    _texture_button(surface, rect_close, "Закрыть", font, game_assets.BTN_CELL_MENU_SECOND)
    buttons.append((rect_close, DYNASTY_CLOSE))

    return buttons
