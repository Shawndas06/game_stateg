"""
factions_data.py — идентификаторы и названия фракций (государств) на карте.

Реализует:
- FACTION_IDS: список всех фракций (игрок ottoman + AI).
- AI_FACTION_IDS: только AI-фракции (для циклов по противникам).
- FACTION_NAMES_RU: русские названия для отображения в UI.
"""

# Все фракции (игрок + AI)
FACTION_IDS = [
    "ottoman",
    "byzantine",
    "germiyan",
    "karaman",
    "aydin",
    "mentese",
    "saruhan",
    "candar",
    "hamid",
    "teke",
    "karasi",
    "bulgaria",
    "serbia",
    "hungary",
    "mamluk",
    "maghreb",
]

# AI-фракции (не игрок)
AI_FACTION_IDS = [f for f in FACTION_IDS if f != "ottoman"]

# Названия фракций (рус.)
FACTION_NAMES_RU = {
    "ottoman": "Османы",
    "byzantine": "Византия",
    "germiyan": "Гермиян",
    "karaman": "Караман",
    "aydin": "Айдын",
    "mentese": "Ментеше",
    "saruhan": "Сарухан",
    "candar": "Джандар",
    "hamid": "Хамид",
    "teke": "Теке",
    "karasi": "Карасы",
    "bulgaria": "Болгария",
    "serbia": "Сербия",
    "hungary": "Венгрия",
    "mamluk": "Мамлюки",
    "maghreb": "Магриб",
}
