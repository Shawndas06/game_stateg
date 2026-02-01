"""
Данные фракций — все государства на карте
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
}
