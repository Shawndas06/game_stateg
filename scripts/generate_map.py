#!/usr/bin/env python3
"""
generate_map.py — генератор PNG-карты, согласованной с проекцией игры.

Идея: используем ту же `lonlat_to_map` и полигоны суши из `geography_land`,
поэтому крепости, спроецированные по lon/lat, автоматически попадают
на сушу/побережье без ручных смещений.

Результат сохраняется в `assets/map/generated_map.png`. Если файл существует,
`map_renderer` отдаёт ему приоритет перед старой картой.

Запуск:  python scripts/generate_map.py [--scale 0.5] [--out path.png]
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

# Делаем src импортируемым при запуске из корня
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.map.geography_land import (  # noqa: E402
    LAND_POLYGONS,
    MOUNTAIN_ELLIPSES,
    RIVER_LINES,
    is_land,
)
from src.map.geo_projection import (  # noqa: E402
    LAT_SPAN,
    LON_SPAN,
    LON_MIN,
    LON_MAX,
    LAT_MIN,
    LAT_MAX,
    MAP_LOGICAL_WIDTH,
    MAP_LOGICAL_HEIGHT,
    lonlat_to_map,
)


# ---- Палитра (тёплая средневековая карта) ----
COLOR_PARCHMENT = (228, 202, 158)        # фон суши
COLOR_PARCHMENT_DARK = (200, 168, 122)
COLOR_SEA_DEEP = (78, 116, 130)          # старо-морской сине-зелёный
COLOR_SEA_SHALLOW = (122, 158, 168)
COLOR_COAST_OUTLINE = (74, 56, 36)       # тёмный «чернильный» контур
COLOR_COAST_OUTLINE2 = (110, 84, 56)
COLOR_RIVER = (78, 110, 138)
COLOR_MOUNTAIN = (132, 102, 74)
COLOR_MOUNTAIN_HATCH = (96, 72, 52)
COLOR_GRID = (162, 132, 96)
COLOR_TITLE = (62, 44, 28)


def _project_poly(poly, scale: float) -> list[tuple[int, int]]:
    out = []
    for lon, lat in poly:
        mx, my = lonlat_to_map(lon, lat)
        out.append((int(mx * scale), int(my * scale)))
    return out


def _ocean_gradient(surf: pygame.Surface) -> None:
    w, h = surf.get_size()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(COLOR_SEA_DEEP[0] * (1 - t) + COLOR_SEA_SHALLOW[0] * t)
        g = int(COLOR_SEA_DEEP[1] * (1 - t) + COLOR_SEA_SHALLOW[1] * t)
        b = int(COLOR_SEA_DEEP[2] * (1 - t) + COLOR_SEA_SHALLOW[2] * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))


def _add_sea_noise(surf: pygame.Surface, density: float = 0.0008) -> None:
    """Лёгкая зернистость моря — тонкие точки, имитация бумаги."""
    w, h = surf.get_size()
    rng = random.Random(42)
    n = int(w * h * density)
    for _ in range(n):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        c = (
            min(255, COLOR_SEA_SHALLOW[0] + rng.randint(-12, 18)),
            min(255, COLOR_SEA_SHALLOW[1] + rng.randint(-12, 18)),
            min(255, COLOR_SEA_SHALLOW[2] + rng.randint(-12, 18)),
        )
        surf.set_at((x, y), c)


def _draw_compass_lines(surf: pygame.Surface, scale: float) -> None:
    """Едва заметные «портоланные» лучи от пары узлов — атмосфера старой карты."""
    w, h = surf.get_size()
    nodes = [(int(w * 0.32), int(h * 0.42)), (int(w * 0.66), int(h * 0.55))]
    for nx, ny in nodes:
        for k in range(16):
            ang = (math.pi * 2) * (k / 16.0)
            ex = int(nx + math.cos(ang) * w * 0.45)
            ey = int(ny + math.sin(ang) * h * 0.45)
            pygame.draw.aaline(surf, (140, 110, 78), (nx, ny), (ex, ey))
        pygame.draw.circle(surf, (140, 110, 78), (nx, ny), 3)


def _draw_land(surf: pygame.Surface, scale: float) -> None:
    # Сначала тёмный «теневой» контур чуть со смещением — даёт объём.
    for poly in LAND_POLYGONS:
        scr = _project_poly(poly, scale)
        if len(scr) < 3:
            continue
        shadow = [(x + 4, y + 5) for (x, y) in scr]
        pygame.draw.polygon(surf, (60, 44, 30), shadow)

    for poly in LAND_POLYGONS:
        scr = _project_poly(poly, scale)
        if len(scr) < 3:
            continue
        pygame.draw.polygon(surf, COLOR_PARCHMENT, scr)

    # Внутренняя «тёплая» окантовка побережья
    for poly in LAND_POLYGONS:
        scr = _project_poly(poly, scale)
        if len(scr) < 3:
            continue
        pygame.draw.polygon(surf, COLOR_PARCHMENT_DARK, scr, 6)

    # Чёткий чернильный контур побережья
    for poly in LAND_POLYGONS:
        scr = _project_poly(poly, scale)
        if len(scr) < 3:
            continue
        pygame.draw.polygon(surf, COLOR_COAST_OUTLINE, scr, 2)


def _draw_paper_grain(surf: pygame.Surface, density: float = 0.0006) -> None:
    """Зерно «старой бумаги» поверх суши."""
    w, h = surf.get_size()
    rng = random.Random(7)
    n = int(w * h * density)
    for _ in range(n):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        # точки только на суше — пробуем по цвету пикселя
        c = surf.get_at((x, y))
        if c[2] < 130:  # синий доминирует → море, пропускаем
            continue
        d = rng.choice([(218, 188, 140), (244, 222, 180), (200, 168, 120)])
        surf.set_at((x, y), d)


def _draw_rivers(surf: pygame.Surface, scale: float) -> None:
    rw = max(2, int(6 * scale))
    for pts in RIVER_LINES:
        if len(pts) < 2:
            continue
        scr = _project_poly(pts, scale)
        for k in range(len(scr) - 1):
            pygame.draw.line(surf, COLOR_RIVER, scr[k], scr[k + 1], rw)
            pygame.draw.line(surf, (140, 168, 188), scr[k], scr[k + 1], max(1, rw // 3))


def _draw_mountains(surf: pygame.Surface, scale: float) -> None:
    """Стилизованные горные «хребты» — короткие шевроны вдоль эллипсов."""
    rng = random.Random(91)
    for lon_c, lat_c, rx_d, ry_d in MOUNTAIN_ELLIPSES:
        cx_m, cy_m = lonlat_to_map(lon_c, lat_c)
        cx = int(cx_m * scale)
        cy = int(cy_m * scale)
        rx = max(20, int(rx_d / LON_SPAN * MAP_LOGICAL_WIDTH * scale))
        ry = max(14, int(ry_d / LAT_SPAN * MAP_LOGICAL_HEIGHT * scale))

        # Базовая «земляная» подложка
        rect = pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2)
        shade = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.ellipse(shade, (132, 102, 74, 90), shade.get_rect())
        surf.blit(shade, rect.topleft)

        # Шевроны — мелкие треугольники вдоль большой оси
        n = max(6, rx // 18)
        for i in range(n):
            t = (i + 0.5) / n
            x = rect.left + int(t * rect.width)
            ybase = rect.centery + rng.randint(-int(ry * 0.45), int(ry * 0.45))
            tw = max(6, int(rx / n * 0.85))
            th = max(5, int(ry * 0.35))
            apex = (x, ybase - th)
            l = (x - tw // 2, ybase + 2)
            r = (x + tw // 2, ybase + 2)
            pygame.draw.polygon(surf, COLOR_MOUNTAIN, [apex, l, r])
            pygame.draw.polygon(surf, COLOR_MOUNTAIN_HATCH, [apex, l, r], 1)


def _draw_grid(surf: pygame.Surface, scale: float) -> None:
    """Тонкая сетка lon/lat — ориентир."""
    w, h = surf.get_size()
    grid = pygame.Surface((w, h), pygame.SRCALPHA)
    color = (*COLOR_GRID, 70)
    for lon in range(int(LON_MIN), int(LON_MAX) + 1, 5):
        x, _ = lonlat_to_map(float(lon), (LAT_MIN + LAT_MAX) / 2)
        sx = int(x * scale)
        pygame.draw.line(grid, color, (sx, 0), (sx, h), 1)
    for lat in range(int(LAT_MIN), int(LAT_MAX) + 1, 2):
        _, y = lonlat_to_map((LON_MIN + LON_MAX) / 2, float(lat))
        sy = int(y * scale)
        pygame.draw.line(grid, color, (0, sy), (w, sy), 1)
    surf.blit(grid, (0, 0))


def _draw_labels(surf: pygame.Surface, scale: float) -> None:
    """Декоративные надписи морей/океанов."""
    pygame.font.init()
    try:
        big = pygame.font.SysFont("dejavuserif", max(28, int(64 * scale)), italic=True)
        small = pygame.font.SysFont("dejavuserif", max(18, int(34 * scale)), italic=True)
    except Exception:
        big = pygame.font.Font(None, max(30, int(70 * scale)))
        small = pygame.font.Font(None, max(20, int(36 * scale)))

    def _text(text, lon, lat, font):
        x, y = lonlat_to_map(lon, lat)
        ts = font.render(text, True, COLOR_TITLE)
        ts.set_alpha(160)
        surf.blit(ts, ts.get_rect(center=(int(x * scale), int(y * scale))))

    _text("MARE  MEDITERRANEUM", 17.0, 35.6, big)
    _text("Pontus Euxinus", 33.0, 43.6, small)
    _text("Mare Aegaeum", 25.0, 38.6, small)
    _text("Mare Adriaticum", 16.0, 42.6, small)
    _text("Mare Tyrrhenum", 11.5, 40.0, small)
    _text("ANATOLIA", 33.0, 39.0, big)
    _text("AEGYPTUS", 30.0, 27.0, big)
    _text("AFRICA", 6.0, 32.0, big)
    _text("HISPANIA", -4.0, 40.0, big)
    _text("THRACIA", 26.5, 42.5, small)


def _draw_border(surf: pygame.Surface) -> None:
    """Двойная рамка по периметру в стиле старых карт."""
    w, h = surf.get_size()
    pygame.draw.rect(surf, COLOR_TITLE, (0, 0, w, h), 5)
    pygame.draw.rect(surf, COLOR_PARCHMENT_DARK, (10, 10, w - 20, h - 20), 2)


def generate(scale: float = 0.5) -> pygame.Surface:
    out_w = max(800, int(MAP_LOGICAL_WIDTH * scale))
    out_h = max(480, int(MAP_LOGICAL_HEIGHT * scale))

    pygame.init()
    pygame.display.set_mode((1, 1))
    surf = pygame.Surface((out_w, out_h))

    _ocean_gradient(surf)
    _add_sea_noise(surf)
    _draw_compass_lines(surf, scale)
    _draw_land(surf, scale)
    _draw_paper_grain(surf)
    _draw_rivers(surf, scale)
    _draw_mountains(surf, scale)
    _draw_grid(surf, scale)
    _draw_labels(surf, scale)
    _draw_border(surf)

    return surf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=0.5,
                        help="Доля от логического размера карты (по умолчанию 0.5 → 4200×2520)")
    parser.add_argument("--out", type=str, default="assets/map/generated_map.png")
    args = parser.parse_args()

    target = ROOT / args.out
    target.parent.mkdir(parents=True, exist_ok=True)

    surf = generate(scale=args.scale)
    pygame.image.save(surf, str(target))
    print(f"OK  {target}  ({surf.get_width()}×{surf.get_height()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
