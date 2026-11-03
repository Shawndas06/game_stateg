"""
game_assets.py — загрузка и кэш PNG-ассетов (крепость, кнопки, пергамент, портрет султана).

Пути: assets/ui/*.png относительно корня проекта.
"""

from __future__ import annotations

from pathlib import Path
import pygame

_ROOT = Path(__file__).resolve().parents[2]
_UI_DIR = _ROOT / "assets" / "ui"

# --- Портрет в шапке главного экрана ---
SULTAN_BADGE_X = 68
SULTAN_BADGE_SIZE = 64

_fortress_src: pygame.Surface | bool | None = None
_fort_scaled: dict[int, pygame.Surface] = {}
_button_sheet: pygame.Surface | bool | None = None
_button_cells: dict[tuple[int, int], pygame.Surface] = {}
_parchment_src: pygame.Surface | bool | None = None
_sultan_src: pygame.Surface | bool | None = None
_sultan_circle: dict[int, pygame.Surface] = {}


def _path(name: str) -> Path:
    return _UI_DIR / name


def has_fortress_icon() -> bool:
    return _path("fortress_icon.png").is_file()


def has_ui_buttons() -> bool:
    return _path("ui_buttons.png").is_file()


def has_parchment() -> bool:
    return _path("parchment_panel.png").is_file()


def has_sultan_portrait() -> bool:
    return _path("sultan_portrait.png").is_file()


def get_fortress_icon_source() -> pygame.Surface | None:
    """Исходная иконка крепости с альфой или None."""
    global _fortress_src
    if _fortress_src is False:
        return None
    if _fortress_src is None:
        p = _path("fortress_icon.png")
        try:
            _fortress_src = pygame.image.load(str(p)).convert_alpha()
        except Exception:
            _fortress_src = False
            return None
    return _fortress_src  # type: ignore[return-value]


def get_fortress_icon_scaled(size: int) -> pygame.Surface | None:
    """Иконка крепости масштабированная до size×size."""
    src = get_fortress_icon_source()
    if src is None:
        return None
    s = max(16, min(320, int(size)))
    if s not in _fort_scaled:
        _fort_scaled[s] = pygame.transform.smoothscale(src, (s, s))
    return _fort_scaled[s]


def _get_button_sheet() -> pygame.Surface | None:
    global _button_sheet
    if _button_sheet is False:
        return None
    if _button_sheet is None:
        p = _path("ui_buttons.png")
        try:
            _button_sheet = pygame.image.load(str(p)).convert_alpha()
        except Exception:
            _button_sheet = False
            return None
    return _button_sheet  # type: ignore[return-value]


def get_button_sheet_cell(row: int, col: int) -> pygame.Surface | None:
    """
    Ячейка сетки 4×2 (ряд сверху вниз 0..3, колонка 0..1).
    Ряд 0 — светлый / акцент; ряд 1 — «основное действие» и дипломатия; ряд 3 — экономика и законы.
    """
    sheet = _get_button_sheet()
    if sheet is None:
        return None
    key = (row, col)
    if key not in _button_cells:
        sw = sheet.get_width() // 2
        sh = sheet.get_height() // 4
        x, y = col * sw, row * sh
        try:
            sub = sheet.subsurface((x, y, sw, sh)).copy()
            _button_cells[key] = sub
        except Exception:
            return None
    return _button_cells[key]


def get_parchment_source() -> pygame.Surface | None:
    global _parchment_src
    if _parchment_src is False:
        return None
    if _parchment_src is None:
        p = _path("parchment_panel.png")
        try:
            img = pygame.image.load(str(p)).convert_alpha()
            _parchment_src = img
        except Exception:
            _parchment_src = False
            return None
    return _parchment_src  # type: ignore[return-value]


def _get_sultan_source() -> pygame.Surface | None:
    global _sultan_src
    if _sultan_src is False:
        return None
    if _sultan_src is None:
        p = _path("sultan_portrait.png")
        try:
            _sultan_src = pygame.image.load(str(p)).convert_alpha()
        except Exception:
            _sultan_src = False
            return None
    return _sultan_src  # type: ignore[return-value]


def get_sultan_portrait_circle(diameter: int) -> pygame.Surface | None:
    """Портрет султана для шапки (чёрные углы убраны colorkey, золотистая окантовка)."""
    src = _get_sultan_source()
    if src is None:
        return None
    d = max(24, min(160, int(diameter)))
    if d in _sultan_circle:
        return _sultan_circle[d]
    sq = pygame.transform.smoothscale(src, (d, d)).convert()
    sq.set_colorkey((0, 0, 0))
    pad = 6
    out = pygame.Surface((d + pad * 2, d + pad * 2), pygame.SRCALPHA)
    cx = out.get_width() // 2
    cy = out.get_height() // 2
    rr = min(cx, cy) - 3
    pygame.draw.circle(out, (148, 118, 72, 255), (cx, cy), rr + 2, width=5)
    out.blit(sq, (pad, pad))
    pygame.draw.circle(out, (220, 188, 120, 255), (cx, cy), rr, width=2)
    _sultan_circle[d] = out
    return out


# Пресеты ячеек кнопок (ряд, колонка) под русские подписи
BTN_CELL_TURN = (0, 0)
BTN_CELL_NEXT_TURN = (1, 0)
BTN_CELL_DIPLOMACY = (1, 1)
BTN_CELL_ECONOMY = (3, 0)
BTN_CELL_LAWS = (3, 1)
BTN_CELL_MENU_PRIMARY = (1, 0)
BTN_CELL_MENU_SECOND = (3, 1)
BTN_CELL_DYNASTY = (0, 1)
