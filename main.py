#!/usr/bin/env python3
"""
Османская кампания — Desktop Strategy Game
Беелик → Султанат → Империя

Запуск: python main.py
"""

import pygame
import sys

from src.game.game_state import GameState
from src.narrative.narrative_engine import get_next_narrative_event
from src.utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from src.ui.screens import (
    draw_main_menu,
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
from src.game.diplomacy_engine import propose_peace, propose_nap, propose_tribute, propose_alliance, declare_war
from src.data.fortresses import get_fortress_by_id


def get_fortress_name_ru(game_state, fortress_id: str) -> str:
    """Получить отображаемое имя крепости (с учётом переименований)"""
    if game_state and hasattr(game_state, "get_fortress_display_name"):
        return game_state.get_fortress_display_name(fortress_id)
    f = get_fortress_by_id(fortress_id)
    return f.name_ru if f else fortress_id


def main():
    pygame.init()
    pygame.display.set_caption("Османская кампания — Беелик → Султанат → Империя")

    fullscreen = False
    flags = pygame.RESIZABLE
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("dejavusans", 24)
    font = pygame.font.SysFont("dejavusans", 18)

    screen_state = "menu"
    menu_buttons = []
    settings_buttons = []

    game_state = None
    active_dialog_event = None
    active_dialog_buttons = []
    pause_popup_open = False
    pause_popup_buttons = []

    selected_fortress = None
    fortress_dialog_buttons = []

    # Диалог переименования: (fortress_id, current_text) или None
    rename_state = None
    rename_dialog_buttons = []

    # Диалоги: Дипломатия, Экономика, Законы
    diplomacy_open = False
    economy_open = False
    laws_open = False
    top_dialog_buttons = []

    # Карта: zoom и pan
    map_zoom = 0.55
    map_offset_x = 0.0
    map_offset_y = 0.0
    map_panning = False
    pan_start = (0, 0, 0.0, 0.0)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # Ввод текста для переименования
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

            if event.type == pygame.MOUSEWHEEL and screen_state == "game" and game_state:
                if not (pause_popup_open or active_dialog_event or rename_state or diplomacy_open or economy_open or laws_open):
                    zoom_delta = 1.1 if event.y > 0 else 0.9
                    map_zoom = max(0.35, min(1.5, map_zoom * zoom_delta))
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()

                if screen_state == "menu":
                    action = get_menu_button_at_pos(mouse_pos, menu_buttons)
                    if action == MENU_BTN_NEW_GAME:
                        screen_state = "game"
                        game_state = GameState()
                        active_dialog_event = get_next_narrative_event(
                            game_state.stage, game_state.turn, game_state.shown_events
                        )
                        active_dialog_buttons = []
                    elif action == MENU_BTN_LOAD_GAME and has_save():
                        loaded = load_game()
                        if loaded is not None:
                            screen_state = "game"
                            game_state = loaded
                            active_dialog_event = None
                            active_dialog_buttons = []
                    elif action == MENU_BTN_SETTINGS:
                        screen_state = "settings"
                        settings_buttons = draw_settings_screen(screen, font_title, font, fullscreen)
                    elif action == MENU_BTN_EXIT:
                        running = False
                        break
                    continue

                if screen_state == "settings":
                    for rect, act in settings_buttons:
                        if rect.collidepoint(mouse_pos):
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

                # Диалоги Дипломатия / Экономика / Законы
                if (diplomacy_open or economy_open or laws_open) and game_state:
                    for rect, action in top_dialog_buttons:
                        if rect.collidepoint(mouse_pos):
                            if action == "diplo_close" or action == "econ_close" or action == "laws_close":
                                diplomacy_open = economy_open = laws_open = False
                                if hasattr(game_state, "_diplomacy_message"):
                                    delattr(game_state, "_diplomacy_message")
                            elif action == "diplo_peace":
                                ok, msg = propose_peace(game_state)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.byzantine_relation = "peace"
                            elif action == "diplo_war":
                                _, msg = declare_war(game_state)
                                game_state._diplomacy_message = msg
                                game_state.byzantine_relation = "war"
                            elif action == "diplo_tribute":
                                ok, msg = propose_tribute(game_state)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.byzantine_relation = "tribute"
                            elif action == "diplo_alliance":
                                ok, msg = propose_alliance(game_state)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.byzantine_relation = "alliance"
                            elif action == "diplo_nap":
                                ok, msg = propose_nap(game_state)
                                game_state._diplomacy_message = msg
                                if ok:
                                    game_state.byzantine_relation = "nap"
                            elif action.startswith("law_enact:"):
                                law_id = action.split(":")[1]
                                game_state.enacted_laws.add(law_id)
                            break
                    continue

                # Диалог осады, найма или столицы
                if selected_fortress and game_state and not pause_popup_open and not active_dialog_event and not rename_state and not (diplomacy_open or economy_open or laws_open):
                    for rect, action in fortress_dialog_buttons:
                        if not rect.collidepoint(mouse_pos):
                            continue

                        if action == SIEGE_CANCEL or action == HIRE_CANCEL or action == CAPITAL_CANCEL:
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
                                if mode == "siege":
                                    ok, _ = game_state.start_siege_from_field_army(target_id, int(amount_str))
                                    if ok:
                                        selected_fortress = None
                                elif mode == "assault":
                                    ok, _ = game_state.assault_from_field_army(target_id, int(amount_str))
                                    if ok:
                                        selected_fortress = None
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
                            count = int(action.split(":")[1])
                            game_state.hire_troops(selected_fortress.id, count)
                            break
                    continue

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

                if active_dialog_event and game_state:
                    for btn_rect, choice in active_dialog_buttons:
                        if btn_rect.collidepoint(mouse_pos):
                            game_state.shown_events.add(active_dialog_event.id)
                            active_dialog_event = None
                            active_dialog_buttons = []
                            break
                    continue

                if game_state and not pause_popup_open and not active_dialog_event and not rename_state and not (diplomacy_open or economy_open or laws_open):
                    # Кнопки сверху: Дипломатия, Экономика, Законы
                    top_clicked = None
                    for rect, action in get_top_bar_button_rects():
                        if rect.collidepoint(mouse_pos):
                            top_clicked = action
                            break
                    if top_clicked == "top_diplomacy":
                        diplomacy_open = True
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
                        game_state.next_turn()
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

            if event.type == pygame.MOUSEMOTION and map_panning:
                mx, my = pygame.mouse.get_pos()
                dx = (mx - pan_start[0]) / map_zoom
                dy = (my - pan_start[1]) / map_zoom
                map_offset_x = pan_start[2] - dx
                map_offset_y = pan_start[3] - dy
                map_offset_x = max(0, min(1400, map_offset_x))
                map_offset_y = max(0, min(700, map_offset_y))

        # === ОТРИСОВКА ===
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

            if diplomacy_open:
                top_dialog_buttons = draw_diplomacy_dialog(screen, game_state, font_title, font)
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
