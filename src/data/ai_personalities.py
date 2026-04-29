"""
ai_personalities.py — типы личности AI-фракций для вариативности поведения.

Реализует:
- Словарь AI_PERSONALITY: faction_id -> "aggressive" | "peaceful" | "trade" | "defensive".
- get_personality(faction_id): возвращает тип личности (по умолчанию "aggressive").
Используется в ai_controller: aggressive — чаще атакует; peaceful — реже атакует, предлагает мир; trade — чаще предлагает торговлю; defensive — строит укрепления, реже атакует.
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
    "mamluk": "defensive",
    "maghreb": "trade",
}

def get_personality(faction_id: str) -> str:
    """Вернуть тип личности фракции для AI (aggressive/peaceful/trade/defensive)."""
    return AI_PERSONALITY.get(faction_id, "aggressive")
