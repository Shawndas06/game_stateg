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
    get_menu_button_at_pos,
    MENU_BTN_NEW_GAME,
    MENU_BTN_EXIT,
    draw_main_screen,
    draw_narrative_dialog,
    is_end_turn_button_clicked,
)
from src.map.map_renderer import get_clicked_fortress


def main():
    pygame.init()
    pygame.display.set_caption("Османская кампания — Беелик → Султанат → Империя")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # Шрифты — SysFont для кроссплатформенности
    font_title = pygame.font.SysFont("dejavusans", 24)
    font = pygame.font.SysFont("dejavusans", 18)

    # Состояние: "menu" или "game"
    screen_state = "menu"
    menu_buttons = []  # Кэш кнопок меню для кликов

    # Состояние игры (создаётся при переходе из меню)
    game_state = None
    active_dialog_event = None
    active_dialog_buttons = []  # [(rect, choice), ...]

    running = True
    while running:
        # === ОБРАБОТКА СОБЫТИЙ ===
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()

                if screen_state == "menu":
                    # Клик по кнопке меню
                    action = get_menu_button_at_pos(mouse_pos, menu_buttons)
                    if action == MENU_BTN_NEW_GAME:
                        screen_state = "game"
                        game_state = GameState()
                        active_dialog_event = get_next_narrative_event(
                            game_state.stage, game_state.turn, game_state.shown_events
                        )
                        active_dialog_buttons = []
                    elif action == MENU_BTN_EXIT:
                        running = False
                        break
                    continue

                if active_dialog_event and game_state:
                    # Клик по кнопке выбора в диалоге
                    for btn_rect, choice in active_dialog_buttons:
                        if btn_rect.collidepoint(mouse_pos):
                            game_state.shown_events.add(active_dialog_event.id)
                            active_dialog_event = None
                            active_dialog_buttons = []
                            break
                elif game_state:
                    # Кнопка "Следующий ход"
                    if is_end_turn_button_clicked(mouse_pos):
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
                        # Клик по крепости — пока только выбор (захват через отдельную механику)
                        fortress = get_clicked_fortress(*mouse_pos)
                        # TODO: механика захвата крепостей (осада, армия и т.д.)
                        if fortress and not game_state.is_fortress_owned(fortress.id):
                            pass  # Пока клик не захватывает

        # === ОТРИСОВКА ===
        screen.fill((30, 35, 45))

        if screen_state == "menu":
            menu_buttons = draw_main_menu(screen, font_title, font)
        else:
            draw_main_screen(screen, game_state, font_title, font)
            if active_dialog_event:
                active_dialog_buttons = draw_narrative_dialog(
                    screen, active_dialog_event, font_title, font
                )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
