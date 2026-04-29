"""
constants.py — глобальные константы игры.

Палитра карты — приглушённые «пергаментные» тона фракций (близко к историческим картам).
"""

# --- Размеры окна ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# --- Карта (фон вне карты / швы — тёплый тёмный тон под пергаментную карту) ---
COLOR_MAP_BACKGROUND = (26, 22, 18)
COLOR_OWNED = (72, 98, 78)
COLOR_ENEMY = (118, 76, 76)
COLOR_BESIEGED = (148, 108, 62)
COLOR_NEUTRAL = (96, 100, 94)

# --- Интерфейс ---
COLOR_UI_BG = (32, 38, 54)
COLOR_UI_BG_DEEP = (22, 26, 38)
COLOR_UI_PANEL = (40, 46, 64)
COLOR_UI_ACCENT = (212, 168, 88)
COLOR_UI_ACCENT_DIM = (160, 124, 68)
COLOR_UI_GOLD_LIGHT = (235, 210, 160)
COLOR_PARCHMENT = (232, 218, 188)
COLOR_PARCHMENT_SHADOW = (180, 160, 130)
COLOR_TEXT = (245, 242, 235)
COLOR_TEXT_DIM = (165, 172, 188)
COLOR_SHADOW = (8, 10, 18)

# --- Иконки крепостей ---
FORTRESS_ICON_SIZE = 26
FORTRESS_SPACING = 100

# --- Фракции (земляные, приглушённые) ---
COLOR_GERMIYAN = (92, 78, 68)
COLOR_KARAMAN = (98, 82, 68)
COLOR_AYDIN = (78, 92, 74)
COLOR_BULGARIA = (88, 78, 98)
COLOR_SERBIA = (78, 88, 96)
COLOR_HUNGARY = (104, 82, 72)
COLOR_MENTESE = (84, 94, 80)
COLOR_SARUHAN = (96, 88, 76)
COLOR_CANDAR = (78, 88, 96)
COLOR_HAMID = (96, 80, 92)
COLOR_TEKE = (78, 96, 90)
COLOR_KARASI = (92, 88, 78)
COLOR_MAMLUK = (112, 98, 76)
COLOR_MAGHREB = (96, 82, 92)

# --- Этапы кампании ---
STAGE_BEYLIK = "beylik"
STAGE_SULTANATE = "sultanate"
STAGE_EMPIRE = "empire"
