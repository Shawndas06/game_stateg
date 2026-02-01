"""
Дипломатический движок — предложения мира, НПП и т.д.
Целевое государство оценивает, стоит ли принимать предложение.
Возможность подключения AI-модели для управления другими государствами.
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


# Оценщик предложений — можно заменить на AI-модель
EvaluatorFn = Callable[[str, str, str, object], tuple[bool, str]]


def _default_evaluator(
    proposer_id: str,
    target_id: str,
    proposal_type: str,
    game_state,
) -> tuple[bool, str]:
    """
    Оценка предложения целевым государством (встроенная логика).
    В будущем можно заменить на AI: evaluate_proposal = ai_evaluator.
    """
    rel = getattr(game_state, "byzantine_relation", RELATION_WAR)
    owned = len(game_state.owned_fortresses)
    byzantine_forts = sum(1 for f in getattr(game_state, "_byzantine_fortresses", [])
                         or _get_byzantine_fort_ids(game_state))
    # Византия владеет крепостями, не принадлежащими османам
    byz_fort_count = _count_byzantine_fortresses(game_state)

    if target_id != BYZANTINE_ID:
        return False, "Неизвестное государство"

    # Османы предлагают мир / НПП
    if proposal_type == PROPOSAL_PEACE:
        # Византия принимает, если: в войне И (османы сильны ИЛИ византия слаба)
        if rel == RELATION_WAR:
            # Османы захватили много — византия готова к миру
            if owned >= 10 or byz_fort_count <= 3:
                return True, "Византия согласна на мир."
            # Османы слабы — византия не уступит
            if owned <= 7 and byz_fort_count >= 6:
                return False, "Византия отвергла мир — считает себя сильнее."
            # Середина — 50% шанс
            import random
            if random.random() < 0.5:
                return True, "Византия согласна на мир."
            return False, "Византия отвергла мир."
        return False, "Уже в мире."

    if proposal_type == PROPOSAL_NAP:
        if rel == RELATION_WAR:
            # Аналогично миру, но чуть строже
            if owned >= 11 or byz_fort_count <= 2:
                return True, "Византия подписала договор о ненападении."
            if owned <= 6:
                return False, "Византия отвергла НПП."
            import random
            if random.random() < 0.4:
                return True, "Византия подписала НПП."
            return False, "Византия отвергла НПП."
        return False, "Уже есть договор или мир."

    if proposal_type == PROPOSAL_TRIBUTE:
        # Обложить данью — византия почти никогда не согласна добровольно
        if owned >= 12 and byz_fort_count <= 2:
            return True, "Византия согласна платить дань."
        return False, "Византия отвергла требование дани."

    if proposal_type == PROPOSAL_ALLIANCE:
        return False, "Византия не заключает союзы с османами."

    if proposal_type == PROPOSAL_WAR:
        # Объявление войны — всегда «принято»
        return True, "Война объявлена."

    return False, "Неизвестное предложение"


def _count_byzantine_fortresses(game_state) -> int:
    """Количество крепостей, принадлежащих Византии."""
    return len(getattr(game_state, "byzantine_owned", set()))


def _get_byzantine_fort_ids(game_state) -> set:
    from src.data.fortresses import FORTESSES_DATA
    return {f.id for f in FORTESSES_DATA if f.faction == "byzantine"}


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


def propose_peace(game_state) -> tuple[bool, str]:
    """Османы предлагают мир Византии."""
    return propose(OTTOMAN_ID, BYZANTINE_ID, PROPOSAL_PEACE, game_state)


def propose_nap(game_state) -> tuple[bool, str]:
    """Османы предлагают договор о ненападении."""
    return propose(OTTOMAN_ID, BYZANTINE_ID, PROPOSAL_NAP, game_state)


def propose_tribute(game_state) -> tuple[bool, str]:
    """Османы требуют дань."""
    return propose(OTTOMAN_ID, BYZANTINE_ID, PROPOSAL_TRIBUTE, game_state)


def propose_alliance(game_state) -> tuple[bool, str]:
    """Османы предлагают военный союз."""
    return propose(OTTOMAN_ID, BYZANTINE_ID, PROPOSAL_ALLIANCE, game_state)


def declare_war(game_state) -> tuple[bool, str]:
    """Объявить войну — всегда «принято»."""
    return propose(OTTOMAN_ID, BYZANTINE_ID, PROPOSAL_WAR, game_state)
