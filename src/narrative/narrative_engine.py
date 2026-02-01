"""
Движок нарратива — события, выборы, сюжет
В стиле Suzerain: текст, решения, последствия
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
    Получить следующее нарративное событие для показа.
    События показываются по одному, в порядке trigger_after_turn.
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
