#!/usr/bin/env python3
"""
main.py — точка входа и главный игровой цикл.

Реализует:
- Инициализацию Pygame, окна, шрифтов.
- Управление экранами: меню, настройки, игра.
- Обработку событий: клики по кнопкам, карте, крепостям; ввод текста (переименование, наместник); зум и панорама карты.
- Открытие/закрытие диалогов: осада, найм, столица, постройки, дипломатия, экономика, законы, предложения AI, победа/поражение.
- Вызов отрисовки текущего экрана и обновление кадра.

Запуск: python main.py
"""

import pygame
import sys

from src.game.game_state import GameState
from src.narrative.narrative_engine import get_next_narrative_event
from src.utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT


def get_screen_size() -> tuple[int, int]:
    """Текущий размер окна (для resize)."""
    try:
        return pygame.display.get_surface().get_size()
    except Exception:
        return SCREEN_WIDTH, SCREEN_HEIGHT
from src.ui.screens import (
    draw_victory_defeat_dialog,
    draw_main_menu,
    draw_build_dialog,
    draw_governor_dialog,
    draw_trade_proposal_dialog,
    draw_diplo_proposal_dialog,
    draw_settings_screen,
    get_menu_button_at_pos,
    get_top_bar_button_rects,
    MENU_BTN_NEW_GAME,
    MENU_BTN_LOAD_GAME,
    MENU_BTN_SETTINGS,
    MENU_BTN_EXIT,
    draw_main_screen,
    draw_narrative_dialog,
    is_end_turn_button_clicked,
    get_pause_menu_button_rect,
    draw_pause_popup,
    get_pause_button_at_pos,
    PAUSE_SAVE,
    PAUSE_EXIT,
    PAUSE_CLOSE,
    draw_siege_dialog,
    draw_hire_dialog,
    draw_capital_dialog,
    draw_rename_dialog,
    draw_diplomacy_dialog,
    draw_economy_dialog,
    draw_laws_dialog,
    SIEGE_CANCEL,
    HIRE_CANCEL,
    CAPITAL_CANCEL,
)
from src.map.map_renderer import get_clicked_fortress, MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT
from src.game.save_manager import save_game, load_game, has_save
from src.game.diplomacy_engine import propose_peace, propose_nap, propose_tribute, propose_alliance, propose_trade, declare_war
from src.audio.sound_manager import play_click, play_build, play_capture, play_diplomacy
from src.data.fortresses import get_fortress_by_id
from src.data.factions_data import FACTION_NAMES_RU


def get_fortress_name_ru(game_state, fortress_id: str) -> str:
    """Получить отображаемое имя крепости (с учётом переименований)"""
    if game_state and hasattr(game_state, "get_fortress_display_name"):
        return game_state.get_fortress_display_name(fortress_id)
    f = get_fortress_by_id(fortress_id)
    return f.name_ru if f else fortress_id


def main():
    # --- Инициализация Pygame и окна ---
    pygame.init()
    pygame.display.set_caption("Османская кампания — Беелик → Султанат → Империя")
    fullscreen = False
    flags = pygame.RESIZABLE
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    clock = pygame.time.Clock()
    font_title = pygame.font.SysFont("dejavusans", 24)
    font = pygame.font.SysFont("dejavusans", 18)

    # --- Состояние экрана и меню ---
    screen_state = "menu"  # "menu" | "settings" | "game"
    menu_buttons = []
    settings_buttons = []

    # --- Состояние игры и диалогов ---
    game_state = None
    victory_defeat_state = None   # ("victory"|"defeat", message) или None
    active_dialog_event = None   # текущее нарративное событие
    active_dialog_buttons = []
    pause_popup_open = False
    pause_popup_buttons = []

    # --- Выбранная крепость и кнопки её диалога ---
    selected_fortress = None
    fortress_dialog_buttons = []

    # --- Состояние модальных диалогов (постройка, наместник, переименование, предложения AI) ---
    rename_state = None          # (fortress_id, current_text) или None
    rename_dialog_buttons = []
    build_dialog_state = None    # (fortress_id,) или None
    governor_dialog_state = None
    trade_proposal_state = None  # ("trade", faction_id) или ("diplo", (faction_id, relation)) или None
    build_dialog_buttons = []
    governor_dialog_buttons = []
    trade_proposal_buttons = []

    # --- Верхняя панель: Дипломатия, Экономика, Законы ---
    diplomacy_open = False
    diplomacy_selected_faction = None  # сначала выбор государства, затем действие
    economy_open = False
    laws_open = False
    top_dialog_buttons = []

    # --- Карта: масштаб и смещение при перетаскивании ---
    map_zoom = 0.6
    map_offset_x = 0.0
    map_offset_y = 0.0
    map_panning = False
    pan_start = (0, 0, 0.0, 0.0)  # (mouse_x, mouse_y, offset_x, offset_y) в начале перетаскивания

    running = True
    while running:
        # ========== Обработка событий ==========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            # --- Ввод текста в диалоге наместника (до общей обработки кликов) ---
            if governor_dialog_state and event.type == pygame.KEYDOWN:
                fortress_id, text = governor_dialog_state
                if event.key == pygame.K_ESCAPE:
                    governor_dialog_state = None
                elif event.key == pygame.K_RETURN:
                    if text.strip():
                        game_state.appoint_governor(fortress_id, text)
                    governor_dialog_state = None
                elif event.key == pygame.K_BACKSPACE:
                    governor_dialog_state = (fortress_id, text[:-1])
                elif event.unicode and len(text) < 25 and event.unicode.isprintable():
                    governor_dialog_state = (fortress_id, text + event.unicode)
                continue

            # --- Ввод текста для переименования крепости ---
            if rename_state and event.type == pygame.KEYDOWN:
                fortress_id, text = rename_state
                if event.key == pygame.K_ESCAPE:
                    rename_state = None
                elif event.key == pygame.K_RETURN:
                    if text.strip():
                        game_state.rename_fortress(fortress_id, text)
                    rename_state = None
                    selected_fortress = get_fortress_by_id(fortress_id) if fortress_id else None
                elif event.key == pygame.K_BACKSPACE:
                    rename_state = (fortress_id, text[:-1])
                elif event.unicode and len(text) < 30 and event.unicode.isprintable():
                    rename_state = (fortress_id, text + event.unicode)
                continue

            # --- Зум карты колёсиком мыши (только на экране игры, без открытых диалогов) ---
            if event.type == pygame.MOUSEWHEEL and screen_state == "game" and game_state:
                if not (pause_popup_open or active_dialog_event or rename_state or diplomacy_open or economy_open or laws_open):
                    zoom_delta = 1.1 if event.y > 0 else 0.9
                    map_zoom = max(0.35, min(1.5, map_zoom * zoom_delta))
                continue

            # --- Клик левой кнопкой мыши: определение цели и выполнение действия ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()

                if screen_state == "menu":
                    action = get_menu_button_at_pos(mouse_pos, menu_buttons)
                    if action == MENU_BTN_NEW_GAME:
                        play_click()
                        screen_state = "game"
                        game_state = GameState()
                        active_dialog_event = get_next_narrative_event(
                            game_state.stage, game_state.turn, game_state.shown_events
                        )
                        active_dialog_buttons = []
                    elif action == MENU_BTN_LOAD_GAME and has_save():
                        play_click()
                        loaded = load_game()
                        if loaded is not None:
                            screen_state = "game"
                            game_state = loaded
                            active_dialog_event = None
                            active_dialog_buttons = []
                    elif action == MENU_BTN_SETTINGS:
                        play_click()
                        screen_state = "settings"
                        settings_buttons = draw_settings_screen(screen, font_title, font, fullscreen)
                    elif action == MENU_BTN_EXIT:
                        play_click()
                        running = False
                        break
                    continue

                # --- Настройки: оконный/полноэкранный режим, назад ---
                if screen_state == "settings":
                    for rect, act in settings_buttons:
                        if rect.collidepoint(mouse_pos):
                            play_click()
                            if act == "settings_windowed":
                                fullscreen = False
                                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                            elif act == "settings_fullscreen":
                                fullscreen = True
                                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                                                 pygame.FULLSCREEN | pygame.HWSURFACE)
                            elif act == "settings_back":
                                screen_state = "menu"
                            if act != "settings_back":
                                settings_buttons = draw_settings_screen(screen, font_title, font, fullscreen)
                            break
                    continue

                # --- Диалог победы/поражения: кнопка «В меню» ---
                if victory_defeat_state:
                    popup_w, popup_h = 560, 260
                    popup_x = (SCREEN_WIDTH - popup_w) // 2
                    popup_y = (SCREEN_HEIGHT - popup_h) // 2
                    vd_btn_rect = pygame.Rect(popup_x + (popup_w - 120) // 2, popup_y + 185, 120, 48)
                    if vd_btn_rect.collidepoint(mouse_pos):
                        play_click()
                        screen_state = "menu"
                        game_state = None
                        victory_defeat_state = None
                        active_dialog_event = None
                        selected_fortress = None
                    continue
                # --- Предложение AI (торговля или дипломатия): принять/отклонить ---
                if trade_proposal_state and game_state:
                    for rect, act in trade_proposal_buttons:
                        if rect.collidepoint(mouse_pos):
                            play_click()
                            typ = trade_proposal_state[0]
                            if typ == "trade":
                                fid = trade_proposal_state[1]
                                if act == "trade_accept":
                                    game_state.trade_partners.add(fid)
                                    play_diplomacy()
                            elif typ == "diplo":
                                fid, prop = trade_proposal_state[1]
                                if act == "diplo_accept":
                                    game_state.ai_state.setdefault(fid, {})["relation"] = prop
                                    if fid == "byzantine":
                                        game_state.byzantine_relation = prop
                                    play_diplomacy()
                            trade_proposal_state = None
                            break
                    continue
                if governor_dialog_state and game_state:
                    for rect, act in governor_dialog_buttons:
                        if rect.collidepoint(mouse_pos):
                            fid, text = governor_dialog_state
                            if act == "governor_ok" and text.strip():
                                game_state.appoint_governor(fid, text)
                            governor_dialog_state = None
                            break
                    continue
                if build_dialog_state and game_state:
                    for rect, act in build_dialog_buttons:
                        if rect.collidepoint(mouse_pos):
                            fid = build_dialog_state[0]
                            if act == "build_close":
                                build_dialog_state = None
                            elif act.startswith("build_") and act != "build_close":
                                bid = act[6:]
                                ok, _ = game_state.build_building(fid, bid)
                                if ok:
                                    play_build()
                                    build_dialog_state = None
                            break
                    continue
                # Диалог переименования
                if rename_state and game_state:
                    for rect, action in rename_dialog_buttons:
                        if rect.collidepoint(mouse_pos):
                            fortress_id, text = rename_state
                            if action == "rename_ok" and text.strip():
                                game_state.rename_fortress(fortress_id, text)
                            rename_state = None
                            selected_fortress = get_fortress_by_id(fortress_id) if fortress_id else None
                            break
                    continue

                # --- Диалоги верхней панели: Дипломатия, Экономика, Законы ---
                if (diplomacy_open or economy_open or laws_open) and game_state:
                    for rect, action in top_dialog_buttons:
                        if rect.collidepoint(mouse_pos):
                            if action == "diplo_close" or action == "econ_close" or action == "laws_close":
                                diplomacy_open = economy_open = laws_open = False
                                diplomacy_selected_faction = None
                                if hasattr(game_state, "_diplomacy_message"):
                                    delattr(game_state, "_diplomacy_message")
                            elif action == "diplo_back":
                                diplomacy_selected_faction = None
                            elif action.startswith("diplo_select:"):
                                diplomacy_selected_faction = action.split(":", 1)[1]
                            elif action.startswith("diplo_peace:"):
                                target_id = action.split(":", 1)[1]
                                ok, msg = propose_peace(game_state, target_id)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.ai_state.setdefault(target_id, {})["relation"] = "peace"
                                    if target_id == "byzantine":
                                        game_state.byzantine_relation = "peace"
                            elif action.startswith("diplo_war:"):
                                target_id = action.split(":", 1)[1]
                                _, msg = declare_war(game_state, target_id)
                                game_state._diplomacy_message = msg
                                game_state.ai_state.setdefault(target_id, {})["relation"] = "war"
                                if target_id == "byzantine":
                                    game_state.byzantine_relation = "war"
                            elif action.startswith("diplo_tribute:"):
                                target_id = action.split(":", 1)[1]
                                ok, msg = propose_tribute(game_state, target_id)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.ai_state.setdefault(target_id, {})["relation"] = "tribute"
                                    if target_id == "byzantine":
                                        game_state.byzantine_relation = "tribute"
                            elif action.startswith("diplo_alliance:"):
                                target_id = action.split(":", 1)[1]
                                ok, msg = propose_alliance(game_state, target_id)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.ai_state.setdefault(target_id, {})["relation"] = "alliance"
                                    if target_id == "byzantine":
                                        game_state.byzantine_relation = "alliance"
                            elif action.startswith("diplo_nap:"):
                                target_id = action.split(":", 1)[1]
                                ok, msg = propose_nap(game_state, target_id)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.ai_state.setdefault(target_id, {})["relation"] = "nap"
                                    if target_id == "byzantine":
                                        game_state.byzantine_relation = "nap"
                            elif action.startswith("diplo_trade:"):
                                target_id = action.split(":", 1)[1]
                                ok, msg = propose_trade(game_state, target_id)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.trade_partners.add(target_id)
                            elif action.startswith("law_enact:"):
                                law_id = action.split(":")[1]
                                game_state.enacted_laws.add(law_id)
                            break
                    continue

                # --- Диалог выбранной крепости: осада (вражеская), найм (своя), столица ---
                if selected_fortress and game_state and not pause_popup_open and not active_dialog_event and not rename_state and not (diplomacy_open or economy_open or laws_open):
                    for rect, action in fortress_dialog_buttons:
                        if not rect.collidepoint(mouse_pos):
                            continue

                        if action == SIEGE_CANCEL or action == HIRE_CANCEL or action == CAPITAL_CANCEL:
                            play_click()
                            selected_fortress = None
                            break

                        if action == "capital_rename":
                            rename_state = (game_state.capital_id, game_state.get_fortress_display_name(game_state.capital_id))
                            break

                        if action.startswith("hire_rename:"):
                            fid = action.split(":")[1]
                            rename_state = (fid, game_state.get_fortress_display_name(fid))
                            break

                        if action.startswith("make_capital:"):
                            fid = action.split(":")[1]
                            ok, _ = game_state.set_capital(fid)
                            if ok:
                                selected_fortress = get_fortress_by_id(fid)
                            break

                        if action.startswith("set_commander:"):
                            c = action.split(":", 1)[1]
                            game_state.set_commander(c)
                            break
                        if action.startswith("capital_transfer:"):
                            parts = action.split(":")
                            if len(parts) >= 3:
                                source_id, amount_str = parts[1], parts[2]
                                game_state.transfer_to_field_army(source_id, int(amount_str))
                            break

                        if action.startswith("siege_field:"):
                            parts = action.split(":")
                            if len(parts) >= 3:
                                amount_str, mode = parts[1], parts[2]
                                target_id = selected_fortress.id
                                target_owner = game_state.get_fortress_owner(target_id)
                                if target_owner and target_owner != "ottoman":
                                    rel = game_state.get_relation_with(target_owner)
                                    if rel == "nap":
                                        game_state.nap_violations += 1
                                        game_state.legitimacy = max(0, getattr(game_state, "legitimacy", 50) - 10)
                                    if rel != "war":
                                        game_state.ai_state.setdefault(target_owner, {})["relation"] = "war"
                                        if target_owner == "byzantine":
                                            game_state.byzantine_relation = "war"
                                if mode == "siege":
                                    ok, _ = game_state.start_siege_from_field_army(target_id, int(amount_str))
                                    if ok:
                                        play_click()
                                        selected_fortress = None
                                elif mode == "assault":
                                    ok, _ = game_state.assault_from_field_army(target_id, int(amount_str))
                                    if ok:
                                        play_capture()
                                        selected_fortress = None
                                        won, msg = game_state.check_victory()
                                        if won:
                                            victory_defeat_state = ("victory", msg)
                                            break
                                        next_ev = get_next_narrative_event(
                                            game_state.stage, game_state.turn, game_state.shown_events
                                        )
                                        if next_ev:
                                            active_dialog_event = next_ev
                                            active_dialog_buttons = draw_narrative_dialog(
                                                screen, next_ev, font_title, font
                                            )
                            break

                        if action.startswith("hire_amount:"):
                            parts = action.split(":")
                            count = int(parts[1])
                            troop_type = parts[2] if len(parts) >= 3 else "militia"
                            game_state.hire_troops(selected_fortress.id, count, troop_type)
                            break
                        if action.startswith("fort_build:"):
                            fid = action.split(":")[1]
                            build_dialog_state = (fid,)
                            break
                        if action.startswith("fort_governor:"):
                            fid = action.split(":")[1]
                            governor_dialog_state = (fid, (game_state.fortress_governors or {}).get(fid, ""))
                            break
                    continue

                # --- Меню паузы: сохранить, выйти в меню, закрыть ---
                if pause_popup_open and game_state:
                    action = get_pause_button_at_pos(mouse_pos, pause_popup_buttons)
                    if action == PAUSE_SAVE:
                        save_game(game_state)
                        pause_popup_open = False
                    elif action == PAUSE_EXIT:
                        screen_state = "menu"
                        game_state = None
                        active_dialog_event = None
                        selected_fortress = None
                        rename_state = None
                        pause_popup_open = False
                    elif action == PAUSE_CLOSE:
                        pause_popup_open = False
                    continue

                # --- Нарративное событие: клик по варианту выбора ---
                if active_dialog_event and game_state:
                    for btn_rect, choice in active_dialog_buttons:
                        if btn_rect.collidepoint(mouse_pos):
                            game_state.shown_events.add(active_dialog_event.id)
                            active_dialog_event = None
                            active_dialog_buttons = []
                            break
                    continue

                # --- Игровой экран: кнопки верхней панели, меню паузы, «Следующий ход», клик по карте/крепости ---
                if game_state and not pause_popup_open and not active_dialog_event and not rename_state and not (diplomacy_open or economy_open or laws_open):
                    top_clicked = None
                    for rect, action in get_top_bar_button_rects():
                        if rect.collidepoint(mouse_pos):
                            top_clicked = action
                            break
                    if top_clicked == "top_turn":
                        play_click()
                        captured = game_state.next_turn()
                        if captured:
                            play_capture()
                        won, msg = game_state.check_victory()
                        if won:
                            victory_defeat_state = ("victory", msg)
                            continue
                        lost, msg = game_state.check_defeat()
                        if lost:
                            victory_defeat_state = ("defeat", msg)
                            continue
                        if game_state.ai_diplomacy_proposals and not trade_proposal_state:
                            trade_proposal_state = ("diplo", game_state.ai_diplomacy_proposals.pop(0))
                        elif game_state.trade_proposals_pending:
                            trade_proposal_state = ("trade", game_state.trade_proposals_pending.pop(0))
                        next_ev = get_next_narrative_event(
                            game_state.stage, game_state.turn, game_state.shown_events
                        )
                        if next_ev:
                            active_dialog_event = next_ev
                            active_dialog_buttons = draw_narrative_dialog(
                                screen, next_ev, font_title, font
                            )
                    elif top_clicked == "top_diplomacy":
                        play_diplomacy()
                        diplomacy_open = True
                        diplomacy_selected_faction = None
                        economy_open = laws_open = False
                    elif top_clicked == "top_economy":
                        economy_open = True
                        diplomacy_open = laws_open = False
                    elif top_clicked == "top_laws":
                        laws_open = True
                        diplomacy_open = economy_open = False
                    elif get_pause_menu_button_rect().collidepoint(mouse_pos):
                        pause_popup_open = True
                        pause_popup_buttons = draw_pause_popup(screen, font_title, font)
                    elif is_end_turn_button_clicked(mouse_pos):
                        play_click()
                        captured = game_state.next_turn()
                        if captured:
                            play_capture()
                        won, msg = game_state.check_victory()
                        if won:
                            victory_defeat_state = ("victory", msg)
                            continue
                        lost, msg = game_state.check_defeat()
                        if lost:
                            victory_defeat_state = ("defeat", msg)
                            continue
                        if game_state.ai_diplomacy_proposals and not trade_proposal_state:
                            trade_proposal_state = ("diplo", game_state.ai_diplomacy_proposals.pop(0))
                        elif game_state.trade_proposals_pending:
                            trade_proposal_state = ("trade", game_state.trade_proposals_pending.pop(0))
                        next_ev = get_next_narrative_event(
                            game_state.stage, game_state.turn, game_state.shown_events
                        )
                        if next_ev:
                            active_dialog_event = next_ev
                            active_dialog_buttons = draw_narrative_dialog(
                                screen, next_ev, font_title, font
                            )
                    else:
                        map_rect = pygame.Rect(MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT)
                        if map_rect.collidepoint(mouse_pos):
                            map_panning = True
                            pan_start = (mouse_pos[0], mouse_pos[1], map_offset_x, map_offset_y)
                        else:
                            fortress = get_clicked_fortress(mouse_pos[0], mouse_pos[1], map_zoom, map_offset_x, map_offset_y)
                            if fortress:
                                selected_fortress = fortress

            # --- Конец перетаскивания карты: если движение было маленьким — считаем кликом по крепости ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if map_panning:
                    mx, my = pygame.mouse.get_pos()
                    dx = abs(mx - pan_start[0])
                    dy = abs(my - pan_start[1])
                    if dx < 5 and dy < 5 and game_state and not (pause_popup_open or active_dialog_event or rename_state or diplomacy_open or economy_open or laws_open):
                        map_rect = pygame.Rect(MAP_OFFSET_X, MAP_OFFSET_Y, MAP_VIEW_WIDTH, MAP_VIEW_HEIGHT)
                        if map_rect.collidepoint(mx, my):
                            fortress = get_clicked_fortress(mx, my, map_zoom, map_offset_x, map_offset_y)
                            if fortress:
                                selected_fortress = fortress
                    map_panning = False

            # --- Перетаскивание карты: обновление смещения в пределах границ ---
            if event.type == pygame.MOUSEMOTION and map_panning:
                mx, my = pygame.mouse.get_pos()
                dx = (mx - pan_start[0]) / map_zoom
                dy = (my - pan_start[1]) / map_zoom
                map_offset_x = pan_start[2] - dx
                map_offset_y = pan_start[3] - dy
                map_offset_x = max(0, min(1400, map_offset_x))
                map_offset_y = max(0, min(700, map_offset_y))

        # ========== Отрисовка текущего экрана ==========
        screen.fill((30, 35, 45))

        if screen_state == "menu":
            menu_buttons = draw_main_menu(
                screen, font_title, font, has_save=has_save()
            )
        elif screen_state == "settings":
            settings_buttons = draw_settings_screen(screen, font_title, font, fullscreen)
        else:
            draw_main_screen(screen, game_state, font_title, font, map_zoom, map_offset_x, map_offset_y)
            if active_dialog_event:
                active_dialog_buttons = draw_narrative_dialog(
                    screen, active_dialog_event, font_title, font
                )
            if pause_popup_open:
                pause_popup_buttons = draw_pause_popup(screen, font_title, font)

            if victory_defeat_state:
                vd_typ, vd_msg = victory_defeat_state
                draw_victory_defeat_dialog(screen, vd_typ, vd_msg, font_title, font)

            if diplomacy_open:
                top_dialog_buttons = draw_diplomacy_dialog(screen, game_state, font_title, font, diplomacy_selected_faction)
            elif economy_open:
                top_dialog_buttons = draw_economy_dialog(screen, game_state, font_title, font)
            elif laws_open:
                top_dialog_buttons = draw_laws_dialog(screen, game_state, font_title, font)

            if rename_state:
                fortress_id, text = rename_state
                name = game_state.get_fortress_display_name(fortress_id)
                rename_dialog_buttons = draw_rename_dialog(
                    screen, name, fortress_id, text, font_title, font
                )
            elif trade_proposal_state:
                typ = trade_proposal_state[0]
                if typ == "trade":
                    fid = trade_proposal_state[1]
                    name = FACTION_NAMES_RU.get(fid, fid)
                    trade_proposal_buttons = draw_trade_proposal_dialog(screen, name, font_title, font)
                else:
                    fid, prop = trade_proposal_state[1]
                    name = FACTION_NAMES_RU.get(fid, fid)
                    trade_proposal_buttons = draw_diplo_proposal_dialog(screen, name, prop, font_title, font)
            elif build_dialog_state:
                fid = build_dialog_state[0]
                build_dialog_buttons = draw_build_dialog(
                    screen, get_fortress_name_ru(game_state, fid), fid, game_state, font_title, font
                )
            elif governor_dialog_state:
                fid, text = governor_dialog_state
                governor_dialog_buttons = draw_governor_dialog(
                    screen, get_fortress_name_ru(game_state, fid), fid, text, font_title, font
                )
            elif selected_fortress:
                get_name = lambda fid: get_fortress_name_ru(game_state, fid)
                if selected_fortress.id == game_state.capital_id:
                    fortress_dialog_buttons = draw_capital_dialog(
                        screen,
                        get_name(selected_fortress.id),
                        game_state,
                        font_title,
                        font,
                        get_name,
                    )
                elif game_state.is_fortress_owned(selected_fortress.id):
                    fortress_dialog_buttons = draw_hire_dialog(
                        screen,
                        get_name(selected_fortress.id),
                        selected_fortress.id,
                        game_state,
                        font_title,
                        font,
                    )
                else:
                    fortress_dialog_buttons = draw_siege_dialog(
                        screen,
                        get_name(selected_fortress.id),
                        selected_fortress.id,
                        game_state,
                        font_title,
                        font,
                        get_name,
                    )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
