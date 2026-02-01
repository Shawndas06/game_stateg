"""
Личности фракций AI — агрессивные, мирные, торговые
Влияет на решения о войне, строительстве, дипломатии
"""
# aggressive: часто атакует, редко мирится
# peaceful: редко атакует, предлагает мир
# trade: часто торгует, строит рынки
# defensive: строит укрепления, мало атакует

AI_PERSONALITY = {
    "byzantine": "defensive",
    "germiyan": "aggressive",
    "karaman": "aggressive",
    "aydin": "trade",
    "mentese": "peaceful",
    "saruhan": "aggressive",
    "candar": "defensive",
    "hamid": "peaceful",
    "teke": "trade",
    "karasi": "aggressive",
    "bulgaria": "defensive",
    "serbia": "peaceful",
    "hungary": "aggressive",
}

def get_personality(faction_id: str) -> str:
    return AI_PERSONALITY.get(faction_id, "aggressive")
