"""
draw_kit.py — общие приёмы отрисовки UI: градиенты, тени, кнопки, рамки.

Используется экранами для единого «османского» оформления без внешних ассетов.
"""

from __future__ import annotations

import pygame
import hashlib


def vertical_gradient(surface: pygame.Surface, rect: pygame.Rect, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    """Заливка вертикальным градиентом в пределах rect."""
    h = max(1, rect.height)
    for y in range(rect.height):
        t = y / h
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        pygame.draw.line(surface, (r, g, b), (rect.left, rect.top + y), (rect.right - 1, rect.top + y))


def drop_shadow(surface: pygame.Surface, rect: pygame.Rect, blur: int = 4, alpha: int = 90) -> None:
    """Мягкая тень под панелью."""
    sh = pygame.Surface((rect.width + blur * 2, rect.height + blur * 2), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, alpha), (blur, blur, rect.width, rect.height), border_radius=6)
    surface.blit(sh, (rect.x - blur, rect.y - blur + 3))


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    border_width: int = 2,
    inner_highlight: tuple[int, int, int] | None = None,
) -> None:
    """Плоская панель с рамкой и лёгкой верхней засветкой."""
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, border_width, border_radius=8)
    if inner_highlight:
        inset = rect.inflate(-6, -6)
        pygame.draw.line(surface, inner_highlight, (inset.left + 4, inset.top + 2), (inset.right - 4, inset.top + 2), 1)


def draw_title_bar(surface: pygame.Surface, rect: pygame.Rect, accent: tuple[int, int, int], width: int = 4) -> None:
    """Декоративная полоса сверху панели."""
    bar = pygame.Rect(rect.left + 12, rect.top + 10, rect.width - 24, width)
    pygame.draw.rect(surface, accent, bar, border_radius=2)


def draw_primary_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    fg: tuple[int, int, int],
    bg: tuple[int, int, int],
    border: tuple[int, int, int],
) -> None:
    drop_shadow(surface, rect, blur=3, alpha=80)
    vertical_gradient(surface, rect, (min(255, bg[0] + 24), min(255, bg[1] + 20), min(255, bg[2] + 12)), bg)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)
    pygame.draw.rect(surface, (255, 235, 170), rect.inflate(-6, -6), 1, border_radius=6)
    txt = font.render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=rect.center))


def draw_secondary_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    fg: tuple[int, int, int],
    accent: tuple[int, int, int],
    bg: tuple[int, int, int],
) -> None:
    drop_shadow(surface, rect, blur=2, alpha=55)
    vertical_gradient(surface, rect, (min(255, bg[0] + 14), min(255, bg[1] + 12), min(255, bg[2] + 8)), bg)
    pygame.draw.rect(surface, accent, rect, 2, border_radius=8)
    txt = font.render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=rect.center))


def ornament_line(surface: pygame.Surface, x: int, y: int, width: int, color: tuple[int, int, int]) -> None:
    """Тонкая декоративная линия с короткими засечками."""
    pygame.draw.line(surface, color, (x, y), (x + width, y), 2)
    for dx in (0, width // 2, width):
        pygame.draw.line(surface, color, (x + dx, y - 4), (x + dx, y + 4), 1)


def scale_surface_contain(src: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    """Масштаб целиком вписать в прямоугольник."""
    iw, ih = src.get_width(), src.get_height()
    if iw < 1 or ih < 1:
        return src
    scale = min(max_w / iw, max_h / ih)
    nw = max(1, int(iw * scale))
    nh = max(1, int(ih * scale))
    return pygame.transform.smoothscale(src, (nw, nh))


def draw_parchment_backing(
    surface: pygame.Surface,
    rect: pygame.Rect,
    parchment: pygame.Surface | None,
    letterbox_fill: tuple[int, int, int],
) -> None:
    """Фон под текст: пергамент по центру + заполнение полей."""
    drop_shadow(surface, rect, blur=5, alpha=110)
    vertical_gradient(surface, rect, (44, 39, 34), letterbox_fill)
    pygame.draw.rect(surface, (192, 154, 86), rect, 2, border_radius=10)
    pygame.draw.rect(surface, (245, 218, 150), rect.inflate(-8, -8), 1, border_radius=8)


def draw_textured_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    texture: pygame.Surface | None,
    fg: tuple[int, int, int] = (252, 248, 242),
    outline: tuple[int, int, int] = (28, 22, 18),
    max_font_sizes: tuple[int, ...] = (17, 15, 14, 13, 12, 11),
) -> None:
    """Единая кнопка: спокойный тёмный фон, золотая рамка и читаемая русская подпись."""
    drop_shadow(surface, rect, blur=3, alpha=85)
    base_top = (86, 72, 56)
    base_bottom = (42, 36, 34)
    vertical_gradient(surface, rect, base_top, base_bottom)
    pygame.draw.rect(surface, (198, 158, 86), rect, 2, border_radius=9)
    pygame.draw.rect(surface, (238, 210, 142), rect.inflate(-6, -6), 1, border_radius=7)
    glow = pygame.Surface((rect.width - 10, max(1, rect.height // 3)), pygame.SRCALPHA)
    glow.fill((255, 236, 170, 32))
    surface.blit(glow, (rect.left + 5, rect.top + 4))

    family = "dejavusans"
    surf = None
    used_size = max_font_sizes[-1]
    for sz in max_font_sizes:
        try:
            f = pygame.font.SysFont(family, sz)
        except Exception:
            f = font
        test = f.render(label, True, fg)
        if test.get_width() <= rect.width - 10 and test.get_height() <= rect.height - 6:
            surf = test
            used_size = sz
            break
    if surf is None:
        try:
            f = pygame.font.SysFont(family, max_font_sizes[-1])
        except Exception:
            f = font
        used_size = max_font_sizes[-1]
        surf = f.render(label, True, fg)

    cx, cy = rect.center
    pos = surf.get_rect(center=(cx, cy))
    try:
        olf = pygame.font.SysFont(family, used_size)
        outline_surf = olf.render(label, True, outline)
    except Exception:
        outline_surf = font.render(label, True, outline)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surface.blit(outline_surf, (pos.x + ox, pos.y + oy))
    surface.blit(surf, pos)


def _seed_color(seed: str, base: tuple[int, int, int], spread: int = 28) -> tuple[int, int, int]:
    """Детерминированный сдвиг базового цвета по seed (id султана)."""
    h = hashlib.md5(seed.encode("utf-8")).digest()
    r = max(0, min(255, base[0] + (h[0] % (2 * spread + 1)) - spread))
    g = max(0, min(255, base[1] + (h[1] % (2 * spread + 1)) - spread))
    b = max(0, min(255, base[2] + (h[2] % (2 * spread + 1)) - spread))
    return (r, g, b)


def draw_sultan_portrait(
    surface: pygame.Surface,
    rect: pygame.Rect,
    seed: str,
    is_current: bool = False,
) -> None:
    """Процедурный стилизованный портрет султана: тюрбан + халат + лицо-силуэт.

    Используется как заглушка вместо PNG, чтобы окно династии было живым.
    seed — id султана, чтобы цвета были стабильными между запусками.
    is_current — выделяет текущего правителя золотой рамкой.
    """
    portrait = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pw, ph = rect.width, rect.height

    # Фон-овал (бронзовый медальон)
    bg_top = _seed_color(seed + "_bg", (74, 56, 40), spread=12)
    bg_bot = _seed_color(seed + "_bg2", (44, 32, 24), spread=10)
    for y in range(ph):
        t = y / max(1, ph)
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        pygame.draw.line(portrait, (r, g, b), (0, y), (pw, y))

    # Плечи / халат
    robe_color = _seed_color(seed + "_robe", (140, 60, 38), spread=40)
    robe_dark = (max(0, robe_color[0] - 30), max(0, robe_color[1] - 30), max(0, robe_color[2] - 30))
    shoulders = [
        (int(pw * 0.10), ph),
        (int(pw * 0.22), int(ph * 0.78)),
        (int(pw * 0.50), int(ph * 0.70)),
        (int(pw * 0.78), int(ph * 0.78)),
        (int(pw * 0.90), ph),
    ]
    pygame.draw.polygon(portrait, robe_color, shoulders)
    pygame.draw.polygon(portrait, robe_dark, shoulders, 2)
    # Воротник-V
    collar = [
        (int(pw * 0.42), int(ph * 0.74)),
        (int(pw * 0.50), int(ph * 0.92)),
        (int(pw * 0.58), int(ph * 0.74)),
    ]
    pygame.draw.polygon(portrait, (240, 220, 170), collar)

    # Лицо
    skin = _seed_color(seed + "_skin", (210, 178, 140), spread=10)
    face_rect = pygame.Rect(int(pw * 0.32), int(ph * 0.36), int(pw * 0.36), int(ph * 0.40))
    pygame.draw.ellipse(portrait, skin, face_rect)
    # Тень под подбородком
    shadow_rect = pygame.Rect(face_rect.left + 2, face_rect.bottom - 8, face_rect.width - 4, 8)
    sh = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    sh.fill((0, 0, 0, 60))
    portrait.blit(sh, shadow_rect.topleft)
    # Глаза-точки
    eye_y = face_rect.top + int(face_rect.height * 0.45)
    eye_dx = int(face_rect.width * 0.22)
    cx = face_rect.centerx
    pygame.draw.circle(portrait, (40, 30, 22), (cx - eye_dx, eye_y), max(1, pw // 70))
    pygame.draw.circle(portrait, (40, 30, 22), (cx + eye_dx, eye_y), max(1, pw // 70))
    # Борода
    beard_color = _seed_color(seed + "_beard", (40, 28, 20), spread=8)
    beard_pts = [
        (face_rect.left + 8, face_rect.top + int(face_rect.height * 0.62)),
        (cx, face_rect.bottom + 4),
        (face_rect.right - 8, face_rect.top + int(face_rect.height * 0.62)),
        (face_rect.right - 14, face_rect.top + int(face_rect.height * 0.78)),
        (cx, face_rect.bottom - 2),
        (face_rect.left + 14, face_rect.top + int(face_rect.height * 0.78)),
    ]
    pygame.draw.polygon(portrait, beard_color, beard_pts)

    # Тюрбан (две дуги + перо/султанка)
    turban_color = _seed_color(seed + "_turban", (240, 232, 218), spread=12)
    turban_shadow = (max(0, turban_color[0] - 30), max(0, turban_color[1] - 30), max(0, turban_color[2] - 30))
    turban_rect = pygame.Rect(int(pw * 0.22), int(ph * 0.10), int(pw * 0.56), int(ph * 0.38))
    pygame.draw.ellipse(portrait, turban_color, turban_rect)
    fold_rect = pygame.Rect(turban_rect.left + 6, turban_rect.top + int(turban_rect.height * 0.55),
                            turban_rect.width - 12, int(turban_rect.height * 0.30))
    pygame.draw.ellipse(portrait, turban_shadow, fold_rect, 2)
    # Кокарда / султанка
    plume_color = _seed_color(seed + "_plume", (200, 160, 70), spread=20)
    plume_rect = pygame.Rect(turban_rect.centerx - 4, turban_rect.top - 8, 8, 18)
    pygame.draw.rect(portrait, plume_color, plume_rect, border_radius=3)
    pygame.draw.circle(portrait, plume_color, (turban_rect.centerx, turban_rect.top - 8), 4)

    # Овальная маска по форме медальона
    mask = pygame.Surface((pw, ph), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
    portrait.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    surface.blit(portrait, rect.topleft)

    # Рамка-медальон
    frame_color = (235, 200, 110) if is_current else (170, 130, 70)
    pygame.draw.ellipse(surface, frame_color, rect, 3)
    if is_current:
        pygame.draw.ellipse(surface, (255, 240, 190), rect.inflate(-6, -6), 1)


def draw_unit_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    troop_id: str,
) -> None:
    """Стилизованная иконка-щит юнита: фон + символ оружия в зависимости от типа.

    Использует troop_id для подбора цвета и иконки. Без внешних PNG.
    """
    icon = pygame.Surface(rect.size, pygame.SRCALPHA)
    w, h = rect.size

    palette = {
        "militia":     ((132, 110, 80), (74, 60, 42),  "spear"),
        "cavalry":     ((128, 76, 60),  (74, 40, 30),  "lance"),
        "archers":     ((96, 116, 84),  (52, 70, 46),  "bow"),
        "ghazi":       ((150, 96, 60),  (88, 50, 30),  "saber"),
        "azaps":       ((110, 96, 70),  (60, 50, 36),  "axe"),
        "sipahi":      ((92, 72, 134),  (50, 38, 78),  "lance"),
        "janissaries": ((180, 168, 140),(96, 88, 70),  "musket"),
        "akinci":      ((140, 96, 64),  (78, 52, 32),  "saber"),
        "timariot":    ((96, 110, 90),  (52, 64, 50),  "lance"),
        "kapikulu":    ((80, 64, 110),  (40, 32, 60),  "saber"),
        "topcu":       ((70, 70, 70),   (32, 32, 32),  "cannon"),
    }
    base, dark, weapon = palette.get(troop_id, ((110, 90, 70), (60, 48, 36), "spear"))

    # Щит (трапеция → овал внизу)
    shield = [
        (int(w * 0.10), int(h * 0.05)),
        (int(w * 0.90), int(h * 0.05)),
        (int(w * 0.90), int(h * 0.55)),
        (int(w * 0.50), int(h * 0.95)),
        (int(w * 0.10), int(h * 0.55)),
    ]
    pygame.draw.polygon(icon, base, shield)
    pygame.draw.polygon(icon, dark, shield, 2)

    cx, cy = w // 2, int(h * 0.50)
    fg = (240, 230, 200)

    if weapon == "spear":
        pygame.draw.line(icon, fg, (cx, int(h * 0.18)), (cx, int(h * 0.78)), 2)
        pygame.draw.polygon(icon, fg, [(cx, int(h * 0.10)), (cx - 4, int(h * 0.22)), (cx + 4, int(h * 0.22))])
    elif weapon == "lance":
        pygame.draw.line(icon, fg, (int(w * 0.20), int(h * 0.78)), (int(w * 0.82), int(h * 0.18)), 3)
        pygame.draw.polygon(icon, fg, [(int(w * 0.82), int(h * 0.18)),
                                       (int(w * 0.74), int(h * 0.20)),
                                       (int(w * 0.80), int(h * 0.28))])
    elif weapon == "bow":
        pygame.draw.arc(icon, fg, pygame.Rect(int(w * 0.22), int(h * 0.20), int(w * 0.56), int(h * 0.50)), 1.4, 4.9, 3)
        pygame.draw.line(icon, fg, (cx - 1, int(h * 0.20)), (cx - 1, int(h * 0.70)), 1)
        pygame.draw.line(icon, fg, (int(w * 0.30), cy), (int(w * 0.74), cy), 1)
    elif weapon == "saber":
        pygame.draw.arc(icon, fg, pygame.Rect(int(w * 0.22), int(h * 0.18), int(w * 0.56), int(h * 0.62)), 0.2, 2.4, 3)
        pygame.draw.line(icon, fg, (int(w * 0.30), int(h * 0.78)), (int(w * 0.36), int(h * 0.86)), 2)
    elif weapon == "axe":
        pygame.draw.line(icon, fg, (cx, int(h * 0.20)), (cx, int(h * 0.78)), 2)
        pygame.draw.polygon(icon, fg, [(cx, int(h * 0.30)), (int(w * 0.74), int(h * 0.22)),
                                       (int(w * 0.74), int(h * 0.46)), (cx, int(h * 0.40))])
    elif weapon == "musket":
        pygame.draw.line(icon, fg, (int(w * 0.22), int(h * 0.78)), (int(w * 0.82), int(h * 0.22)), 3)
        pygame.draw.rect(icon, (90, 60, 30), pygame.Rect(int(w * 0.18), int(h * 0.74), int(w * 0.16), int(h * 0.10)))
    elif weapon == "cannon":
        pygame.draw.rect(icon, fg, pygame.Rect(int(w * 0.18), int(h * 0.42), int(w * 0.60), int(h * 0.18)), border_radius=3)
        pygame.draw.circle(icon, dark, (int(w * 0.30), int(h * 0.66)), 6)
        pygame.draw.circle(icon, dark, (int(w * 0.66), int(h * 0.66)), 6)

    surface.blit(icon, rect.topleft)

