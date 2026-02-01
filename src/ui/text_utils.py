"""
text_utils.py — вспомогательные функции для отображения текста в UI.

Реализует:
- wrap_text(font, text, max_width): разбивает текст на строки по словам, чтобы ширина не превышала max_width пикселей.
- truncate_text(font, text, max_width): обрезает строку до max_width с добавлением «…» при необходимости.
"""

import pygame


def wrap_text(
    font: pygame.font.Font,
    text: str,
    max_width: int,
) -> list[str]:
    """Разбить текст на строки, не превышающие max_width пикселей."""
    words = text.split()
    lines = []
    current = []
    for w in words:
        test = " ".join(current + [w])
        w_px = font.size(test)[0]
        if w_px <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def truncate_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Обрезать текст до max_width, добавляя '…' при необходимости."""
    if font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + "…")[0] > max_width:
        text = text[:-1]
    return (text or "") + "…"
