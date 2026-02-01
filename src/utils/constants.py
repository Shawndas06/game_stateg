"""
Константы игры — экран, цвета, размеры
"""

# Размеры окна (увеличено для карты мира)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Цвета (R, G, B)
COLOR_MAP_BACKGROUND = (34, 45, 55)
COLOR_OWNED = (34, 139, 34)      # Османские территории - тёмно-зелёный
COLOR_ENEMY = (139, 0, 0)        # Византия - тёмно-красный
COLOR_BESIEGED = (180, 100, 30)  # Осада в процессе - оранжевый
COLOR_NEUTRAL = (128, 128, 128)  # Нейтральные
COLOR_UI_BG = (45, 55, 72)
COLOR_UI_ACCENT = (180, 140, 80)
COLOR_TEXT = (240, 240, 230)
COLOR_TEXT_DIM = (160, 160, 150)

# Размеры крепостей (маленькие иконки — экономия места)
FORTRESS_ICON_SIZE = 26
FORTRESS_SPACING = 100

# Цвета фракций
COLOR_GERMIYAN = (100, 80, 60)
COLOR_KARAMAN = (120, 60, 40)
COLOR_AYDIN = (80, 100, 60)
COLOR_BULGARIA = (80, 60, 100)
COLOR_SERBIA = (60, 80, 100)

# Этапы кампании
STAGE_BEYLIK = "beylik"           # Османский беелик (до Бурсы)
STAGE_SULTANATE = "sultanate"     # Османский султанат (после Бурсы)
STAGE_EMPIRE = "empire"           # Османская империя (после Константинополя)
