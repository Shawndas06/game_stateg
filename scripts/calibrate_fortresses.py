"""Интерактивный калибратор позиций крепостей на художественной карте.

Запуск:
    ./.venv/bin/python scripts/calibrate_fortresses.py

Управление:
    ЛКМ           — поставить выбранную крепость в эту точку, перейти к следующей
    ПКМ           — пропустить (оставить старые координаты)
    стрелки ←/→   — переключиться между крепостями вручную
    Backspace     — отменить последний клик и вернуться к предыдущей
    S             — сохранить и выйти
    Esc           — выйти без сохранения
    Ctrl+колесо   — зум на карту в окне

Результат: scripts/fortress_positions.json — словарь fortress_id -> [x, y] в
логических пикселях (8400×4690), которые сразу можно подставить в Fortress(...).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data.fortresses import FORTESSES_DATA  # type: ignore

MAP_PATH = ROOT / "assets" / "map" / "generated_map.png"
OUT_PATH = ROOT / "scripts" / "fortress_positions.json"

WIN_W, WIN_H = 1600, 900
SCALE_LOGICAL = 8400 / 1440  # logical px per PNG px (current projection scale)


def main() -> None:
    pygame.init()
    if not MAP_PATH.exists():
        print(f"Карта не найдена: {MAP_PATH}")
        sys.exit(1)

    raw = pygame.image.load(str(MAP_PATH))
    map_w, map_h = raw.get_size()
    print(f"Карта: {map_w}×{map_h} PNG-px, лог.шкала ≈ {SCALE_LOGICAL:.3f}")

    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Калибратор крепостей")
    font = pygame.font.SysFont("DejaVu Sans", 18, bold=True)
    font_sm = pygame.font.SysFont("DejaVu Sans", 14)

    # Состояние
    positions: dict[str, tuple[int, int]] = {}
    if OUT_PATH.exists():
        try:
            saved = json.loads(OUT_PATH.read_text())
            positions = {k: tuple(v) for k, v in saved.items()}
            print(f"Загружено {len(positions)} ранее сохранённых позиций")
        except Exception as e:
            print(f"Не смог прочесть {OUT_PATH}: {e}")

    fortresses = list(FORTESSES_DATA)
    idx = 0
    # стартуем на первой неразмеченной
    while idx < len(fortresses) and fortresses[idx].id in positions:
        idx += 1
    if idx >= len(fortresses):
        idx = 0

    # Зум / пан карты в окне
    zoom = min((WIN_W - 320) / map_w, WIN_H / map_h)
    pan_x, pan_y = 0.0, 0.0
    dragging = False
    drag_from: tuple[int, int] | None = None

    history: list[tuple[int, str | None]] = []  # (idx, prev_value_or_None)
    clock = pygame.time.Clock()
    running = True

    def screen_to_png(sx: int, sy: int) -> tuple[int, int]:
        px = int((sx - pan_x) / zoom)
        py = int((sy - pan_y) / zoom)
        return px, py

    def png_to_screen(px: int, py: int) -> tuple[int, int]:
        return int(px * zoom + pan_x), int(py * zoom + pan_y)

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_s:
                    OUT_PATH.write_text(json.dumps(positions, indent=2, ensure_ascii=False))
                    print(f"Сохранено {len(positions)} позиций → {OUT_PATH}")
                    running = False
                elif ev.key == pygame.K_RIGHT:
                    idx = (idx + 1) % len(fortresses)
                elif ev.key == pygame.K_LEFT:
                    idx = (idx - 1) % len(fortresses)
                elif ev.key == pygame.K_BACKSPACE and history:
                    last_idx, prev = history.pop()
                    fid = fortresses[last_idx].id
                    if prev is None:
                        positions.pop(fid, None)
                    else:
                        positions[fid] = tuple(prev)
                    idx = last_idx
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if mx >= WIN_W - 320:
                    continue  # клик в правую панель — игнор
                if ev.button == 1:  # ЛКМ — поставить
                    px, py = screen_to_png(mx, my)
                    if 0 <= px < map_w and 0 <= py < map_h:
                        fid = fortresses[idx].id
                        prev = positions.get(fid)
                        history.append((idx, list(prev) if prev else None))
                        positions[fid] = (px, py)
                        # автопрыжок к следующей неразмеченной
                        nxt = idx + 1
                        while nxt < len(fortresses) and fortresses[nxt].id in positions:
                            nxt += 1
                        if nxt < len(fortresses):
                            idx = nxt
                elif ev.button == 3:  # ПКМ — пропустить
                    idx = (idx + 1) % len(fortresses)
                elif ev.button == 2:  # СКМ — пан
                    dragging = True
                    drag_from = (mx, my)
                elif ev.button == 4:  # колесо вверх
                    old = zoom
                    zoom = min(zoom * 1.15, 8.0)
                    pan_x = mx - (mx - pan_x) * (zoom / old)
                    pan_y = my - (my - pan_y) * (zoom / old)
                elif ev.button == 5:  # колесо вниз
                    old = zoom
                    zoom = max(zoom / 1.15, 0.2)
                    pan_x = mx - (mx - pan_x) * (zoom / old)
                    pan_y = my - (my - pan_y) * (zoom / old)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 2:
                dragging = False
                drag_from = None
            elif ev.type == pygame.MOUSEMOTION and dragging and drag_from:
                dx = ev.pos[0] - drag_from[0]
                dy = ev.pos[1] - drag_from[1]
                pan_x += dx
                pan_y += dy
                drag_from = ev.pos
            elif ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(ev.size, pygame.RESIZABLE)

        # Отрисовка
        screen.fill((30, 30, 40))
        scaled = pygame.transform.smoothscale(
            raw, (max(1, int(map_w * zoom)), max(1, int(map_h * zoom)))
        )
        screen.blit(scaled, (pan_x, pan_y))

        # Все уже размеченные — зелёные точки
        for fid, (px, py) in positions.items():
            sx, sy = png_to_screen(px, py)
            pygame.draw.circle(screen, (0, 220, 90), (sx, sy), 6, 2)
            lbl = font_sm.render(fid, True, (0, 220, 90))
            screen.blit(lbl, (sx + 8, sy - 6))

        # Текущая выбранная — красное мигающее перекрестие
        cur = fortresses[idx]
        if cur.id in positions:
            px, py = positions[cur.id]
            sx, sy = png_to_screen(px, py)
            pygame.draw.circle(screen, (255, 80, 80), (sx, sy), 14, 3)

        # Правая панель
        panel = pygame.Rect(screen.get_width() - 320, 0, 320, screen.get_height())
        pygame.draw.rect(screen, (20, 20, 30), panel)
        y0 = 16

        def put(text: str, color=(230, 230, 230), f=font) -> int:
            nonlocal y0
            surf = f.render(text, True, color)
            screen.blit(surf, (panel.x + 12, y0))
            y0 += surf.get_height() + 4
            return y0

        put(f"[{idx + 1}/{len(fortresses)}]  {cur.name_ru}", (255, 220, 100))
        put(f"id: {cur.id}", (180, 180, 200), font_sm)
        put(f"фракция: {cur.faction}", (180, 180, 200), font_sm)
        put(f"lon/lat: {cur.lon:.2f}, {cur.lat:.2f}", (160, 160, 180), font_sm)
        y0 += 8
        put(f"Размечено: {len(positions)} / {len(fortresses)}", (200, 200, 200), font_sm)
        y0 += 12
        put("ЛКМ — поставить", (180, 180, 180), font_sm)
        put("ПКМ — пропустить", (180, 180, 180), font_sm)
        put("←/→ — навигация", (180, 180, 180), font_sm)
        put("Backspace — назад", (180, 180, 180), font_sm)
        put("СКМ-drag — пан", (180, 180, 180), font_sm)
        put("Колесо — зум", (180, 180, 180), font_sm)
        put("S — сохранить и выйти", (255, 200, 100), font_sm)
        put("Esc — выйти без сохранения", (255, 100, 100), font_sm)

        # Список оставшихся
        y0 += 16
        put("Очередь:", (200, 200, 200), font_sm)
        for i in range(idx + 1, min(idx + 18, len(fortresses))):
            f = fortresses[i]
            color = (120, 120, 120) if f.id in positions else (200, 200, 200)
            put(f"  {f.name_ru}", color, font_sm)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
