"""
Дипломатический движок.

Обработка предложений: мир, война, дань, союз, НПП, торговля.
Целевое государство оценивает предложение (сила, легитимность, нарушения НПП).
Можно заменить встроенный оценщик на внешнюю AI-модель.
"""

from typing import Callable, Optional

BYZANTINE_ID = "byzantine"
OTTOMAN_ID = "ottoman"

RELATION_WAR = "war"
RELATION_PEACE = "peace"
RELATION_TRIBUTE = "tribute"
RELATION_ALLIANCE = "alliance"
RELATION_NAP = "nap"

PROPOSAL_PEACE = "peace"
PROPOSAL_WAR = "war"
PROPOSAL_TRIBUTE = "tribute"
PROPOSAL_ALLIANCE = "alliance"
PROPOSAL_NAP = "nap"
PROPOSAL_TRADE = "trade"


# Оценщик предложений — можно заменить на AI-модель
EvaluatorFn = Callable[[str, str, str, object], tuple[bool, str]]


def _count_faction_fortresses(game_state, faction_id: str) -> int:
    """Количество крепостей, принадлежащих фракции."""
    return sum(1 for fid, o in game_state.fortress_owners.items() if o == faction_id)


def _default_evaluator(
    proposer_id: str,
    target_id: str,
    proposal_type: str,
    game_state,
) -> tuple[bool, str]:
    """
    Оценка предложения целевым государством (встроенная логика).
    Работает для любой фракции (Византия, беилики и т.д.).
    """
    import random
    from src.data.factions_data import FACTION_NAMES_RU
    target_name = FACTION_NAMES_RU.get(target_id, target_id)
    rel = game_state.get_relation_with(target_id) if hasattr(game_state, "get_relation_with") else getattr(game_state, "byzantine_relation", RELATION_WAR)
    ottoman_forts = len(game_state.owned_fortresses)
    target_forts = _count_faction_fortresses(game_state, target_id)
    nap_violations = getattr(game_state, "nap_violations", 0)

    # Османы предлагают мир
    if proposal_type == PROPOSAL_PEACE:
        if rel == RELATION_WAR:
            if nap_violations > 0 and random.random() < 0.3:
                return False, f"{target_name} не доверяет — вы нарушали договоры."
            if ottoman_forts >= 10 or target_forts <= 3:
                return True, f"{target_name} согласна на мир."
            if ottoman_forts <= 5 and target_forts >= 6:
                return False, f"{target_name} отвергла мир — считает себя сильнее."
            peace_chance = 0.35 + legitimacy * 0.005 - nap_violations * 0.1
            if random.random() < max(0.1, peace_chance):
                return True, f"{target_name} согласна на мир."
            return False, f"{target_name} отвергла мир."
        return False, "Уже в мире."

    if proposal_type == PROPOSAL_NAP:
        if rel == RELATION_WAR:
            if nap_violations > 0 and random.random() < 0.4:
                return False, f"{target_name} помнит о нарушенных договорах."
            if ottoman_forts >= 9 or target_forts <= 2:
                return True, f"{target_name} подписала договор о ненападении."
            if ottoman_forts <= 4:
                return False, f"{target_name} отвергла НПП."
            nap_chance = 0.3 + legitimacy * 0.004 - nap_violations * 0.08
            if random.random() < max(0.05, nap_chance):
                return True, f"{target_name} подписала НПП."
            return False, f"{target_name} отвергла НПП."
        return False, "Уже есть договор или мир."

    if proposal_type == PROPOSAL_TRIBUTE:
        if ottoman_forts >= 10 and target_forts <= 2:
            return True, f"{target_name} согласна платить дань."
        return False, f"{target_name} отвергла требование дани."

    if proposal_type == PROPOSAL_ALLIANCE:
        if rel == RELATION_PEACE or rel == RELATION_NAP:
            if random.random() < 0.3:
                return True, f"{target_name} заключила военный союз."
        return False, f"{target_name} не заключает союз."

    if proposal_type == PROPOSAL_WAR:
        return True, "Война объявлена."

    if proposal_type == PROPOSAL_TRADE:
        if rel == RELATION_PEACE or rel == RELATION_NAP or rel == RELATION_ALLIANCE:
            return True, f"Торговое соглашение с {target_name} заключено."
        return False, f"Нужен мир или НПП для торговли с {target_name}."

    return False, "Неизвестное предложение"




# Глобальный оценщик — можно подменить на AI
_evaluator: Optional[EvaluatorFn] = None


def set_diplomacy_evaluator(fn: EvaluatorFn) -> None:
    """Установить функцию оценки (для подключения AI)."""
    global _evaluator
    _evaluator = fn


def propose(
    proposer_id: str,
    target_id: str,
    proposal_type: str,
    game_state,
) -> tuple[bool, str]:
    """
    Предложить мир / НПП / дань / союз.
    Возвращает (принято: bool, сообщение: str).
    """
    fn = _evaluator or _default_evaluator
    return fn(proposer_id, target_id, proposal_type, game_state)


def propose_to_faction(game_state, target_id: str, proposal_type: str) -> tuple[bool, str]:
    """Османы делают предложение выбранной фракции. Возвращает (принято, сообщение)."""
    return propose(OTTOMAN_ID, target_id, proposal_type, game_state)


def propose_peace(game_state, target_id: str = BYZANTINE_ID) -> tuple[bool, str]:
    """Османы предлагают мир."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_PEACE, game_state)


def propose_nap(game_state, target_id: str = BYZANTINE_ID) -> tuple[bool, str]:
    """Османы предлагают договор о ненападении."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_NAP, game_state)


def propose_tribute(game_state, target_id: str = BYZANTINE_ID) -> tuple[bool, str]:
    """Османы требуют дань."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_TRIBUTE, game_state)


def propose_alliance(game_state, target_id: str = BYZANTINE_ID) -> tuple[bool, str]:
    """Османы предлагают военный союз."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_ALLIANCE, game_state)


def propose_trade(game_state, target_id: str) -> tuple[bool, str]:
    """Заключить торговое соглашение (при мире/НПП)."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_TRADE, game_state)


def declare_war(game_state, target_id: str = BYZANTINE_ID) -> tuple[bool, str]:
    """Объявить войну."""
    return propose(OTTOMAN_ID, target_id, PROPOSAL_WAR, game_state)
