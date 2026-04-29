#!/usr/bin/env python3
"""
Генерация PNG панели UI в стиле пергамента с деревянным обрамлением и золотым орнаментом.
Запуск: python scripts/generate_parchment_panel.py

Результат: assets/ui/panel_parchment_800x400.png
"""

from __future__ import annotations

import argparse
import math
import os
import random

import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _feather_corner_rgba(surf: pygame.Surface, corner: str, radius: int) -> None:
    w, h = surf.get_size()
    for cy in range(radius):
        for cx in range(radius):
            d = math.sqrt(cx * cx + cy * cy)
            if d >= radius:
                continue
            alpha_scale = d / radius
            if corner == "tl":
                px, py = cx, cy
            elif corner == "tr":
                px, py = w - 1 - cx, cy
            elif corner == "bl":
                px, py = cx, h - 1 - cy
            else:
                px, py = w - 1 - cx, h - 1 - cy
            if not (0 <= px < w and 0 <= py < h):
                continue
            r0, g0, b0, a0 = surf.get_at((px, py))
            a1 = int(a0 * (0.35 + 0.65 * alpha_scale))
            surf.set_at((px, py), (r0, g0, b0, a1))


def generate_panel(width: int, height: int, seed: int = 42) -> pygame.Surface:
    random.seed(seed)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    top = (56, 50, 40)
    bottom = (74, 64, 50)
    for y in range(height):
        t = y / max(1, height - 1)
        c = _lerp_rgb(top, bottom, t)
        pygame.draw.line(surf, c + (255,), (0, y), (width, y))

    # Лёгкий шум пергамента
    for _ in range(2200):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        r, g, b, a = surf.get_at((x, y))
        d = random.randint(-7, 7)
        surf.set_at((x, y), (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)), a))

    bw = max(18, width // 32)
    wood_dark = (58, 40, 30)
    wood_mid = (88, 62, 42)
    pygame.draw.rect(surf, wood_dark, (0, 0, width, bw))
    pygame.draw.rect(surf, wood_dark, (0, height - bw, width, bw))
    pygame.draw.rect(surf, wood_dark, (0, 0, bw, height))
    pygame.draw.rect(surf, wood_dark, (width - bw, 0, bw, height))
    for yy in range(5, bw - 2, 5):
        pygame.draw.line(surf, wood_mid, (4, yy), (width - 4, yy), 1)
    for yy in range(height - bw + 5, height - 4, 5):
        pygame.draw.line(surf, wood_mid, (4, yy), (width - 4, yy), 1)

    gx0 = bw + 10
    gy0 = bw + 10
    gx1 = width - bw - 10
    gy1 = height - bw - 10

    inner = pygame.Rect(gx0 + 18, gy0 + 22, gx1 - gx0 - 36, gy1 - gy0 - 44)
    pygame.draw.rect(surf, (208, 192, 168, 248), inner)
    pygame.draw.rect(surf, (132, 108, 78, 230), inner, 2)

    gold = (176, 138, 68)
    gold_hi = (210, 175, 110)
    gold_lo = (112, 84, 44)
    pygame.draw.rect(surf, gold, (gx0, gy0, gx1 - gx0, gy1 - gy0), 4)
    pygame.draw.rect(surf, gold_lo, (gx0 + 6, gy0 + 6, gx1 - gx0 - 12, gy1 - gy0 - 12), 1)

    # Угловые медальоны
    r_med = 24
    for cx, cy in [(gx0 + r_med + 4, gy0 + r_med + 4), (gx1 - r_med - 4, gy0 + r_med + 4), (gx1 - r_med - 4, gy1 - r_med - 4), (gx0 + r_med + 4, gy1 - r_med - 4)]:
        pygame.draw.circle(surf, gold_hi, (cx, cy), r_med, 2)
        pygame.draw.circle(surf, gold_lo, (cx, cy), r_med - 6, 1)

    # Тонкий орнамент — линии и «греческий» ключ фрагменты
    step = 44
    for x in range(gx0 + 50, gx1 - 50, step):
        pygame.draw.line(surf, gold_hi, (x, gy0 + 14), (x + 22, gy0 + 14), 2)
        pygame.draw.line(surf, gold_hi, (x, gy1 - 14), (x + 22, gy1 - 14), 2)

    for corner in ("tl", "tr", "bl", "br"):
        _feather_corner_rgba(surf, corner, 28)

    return surf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--w", type=int, default=800)
    parser.add_argument("--h", type=int, default=400)
    parser.add_argument("--out", type=str, default="assets/ui/panel_parchment_800x400.png")
    args = parser.parse_args()

    pygame.init()
    panel = generate_panel(args.w, args.h)
    out_path = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pygame.image.save(panel, out_path)
    pygame.quit()
    print(out_path)


if __name__ == "__main__":
    main()
