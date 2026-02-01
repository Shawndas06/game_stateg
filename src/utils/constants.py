"""
Константы игры — экран, цвета, размеры
"""

# Размеры окна (увеличено для большой карты)
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

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

# Размеры крепостей на карте
FORTRESS_ICON_SIZE = 48
FORTRESS_SPACING = 120  # Расстояние между крепостями (большое)

# Этапы кампании
STAGE_BEYLIK = "beylik"           # Османский беелик (до Бурсы)
STAGE_SULTANATE = "sultanate"     # Османский султанат (после Бурсы)
STAGE_EMPIRE = "empire"           # Османская империя (после Константинополя)
