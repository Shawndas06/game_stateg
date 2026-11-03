"""
diplomacy_data.py — константы дипломатических отношений (используются в diplomacy_engine и game_state).

Реализует:
- Состояния отношений: RELATION_WAR, RELATION_PEACE, RELATION_TRIBUTE, RELATION_ALLIANCE, RELATION_NAP.
- BYZANTINE_ID — идентификатор Византии (для обратной совместимости; в игре отношения есть со всеми фракциями).
"""

# Состояния отношений с фракцией
RELATION_WAR = "war"
RELATION_PEACE = "peace"
RELATION_TRIBUTE = "tribute"      # дань (игрок получает от вассала)
RELATION_ALLIANCE = "alliance"    # военный союз
RELATION_NAP = "nap"              # договор о ненападении

BYZANTINE_ID = "byzantine"
