"""
narrative_engine.py — выбор и показ нарративных событий по этапу и ходу.

Реализует:
- get_next_narrative_event(stage, turn, shown_events): из NARRATIVE_EVENTS выбирает события с подходящим trigger_stage и trigger_after_turn <= turn, ещё не показанные (id не в shown_events); возвращает одно с минимальным trigger_after_turn или None.
- process_choice(choice): возвращает словарь с effect и consequence выбора (для возможной будущей обработки последствий).
"""

from typing import Optional

from src.data.narrative_data import (
    NarrativeEvent,
    NarrativeChoice,
    NARRATIVE_EVENTS,
    EVENT_START,
)


def get_next_narrative_event(
    stage: str,
    turn: int,
    shown_events: set[str],
) -> Optional[NarrativeEvent]:
    """
    Вернуть следующее нарративное событие для показа: подходит по этапу и ходу, ещё не показывалось.
    Среди подходящих выбирается с минимальным trigger_after_turn.
    """
    candidates = []
    for ev in NARRATIVE_EVENTS:
        if ev.id in shown_events:
            continue
        if ev.trigger_stage != stage:
            continue
        if ev.trigger_after_turn > turn:
            continue
        candidates.append(ev)

    # Сортируем по trigger_after_turn
    candidates.sort(key=lambda e: e.trigger_after_turn)
    return candidates[0] if candidates else None


def process_choice(choice: NarrativeChoice) -> dict:
    """
    Обработка выбора игрока. Возвращает эффект.
    """
    return {"effect": choice.effect, "consequence": choice.consequence}
