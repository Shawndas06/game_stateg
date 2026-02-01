"""
Состояние игры — центральный хранилище данных кампании
Чистая бизнес-логика, без UI
"""

from dataclasses import dataclass, field
from typing import Optional

from src.data.fortresses import Fortress, FORTESSES_DATA, get_fortress_by_id
from src.data.campaign_stages import (
    get_next_stage,
    get_stage_by_fortress,
    STAGES,
)
from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class GameState:
    """
    Текущее состояние кампании.
    Османский беелик → Султанат (Бурса) → Империя (Константинополь)
    """
    # Текущий этап кампании
    stage: str = STAGE_BEYLIK
    # Текущий год (начинаем 1299)
    year: int = 1299
    # Номер хода
    turn: int = 0
    # Захваченные крепости (id) — в начале только османские
    owned_fortresses: set[str] = field(default_factory=lambda: {
        f.id for f in FORTESSES_DATA if f.faction == "ottoman"
    })
    # Показанные нарративные события (id) — чтобы не показывать повторно
    shown_events: set[str] = field(default_factory=set)
    # Текущее нарративное событие (если открыто диалоговое окно)
    active_narrative_event_id: Optional[str] = None

    def capture_fortress(self, fortress_id: str) -> bool:
        """
        Захватить крепость. Возвращает True, если произошёл переход этапа.
        """
        fortress = get_fortress_by_id(fortress_id)
        if not fortress or fortress_id in self.owned_fortresses:
            return False

        self.owned_fortresses.add(fortress_id)

        # Проверка перехода этапа
        new_stage = get_stage_by_fortress(fortress_id)
        if new_stage:
            self.stage = new_stage
            return True
        return False

    def get_stage_info(self):
        """Информация о текущем этапе"""
        return STAGES.get(self.stage, STAGES[STAGE_BEYLIK])

    def is_fortress_owned(self, fortress_id: str) -> bool:
        return fortress_id in self.owned_fortresses

    def next_turn(self):
        """Следующий ход"""
        self.turn += 1
        # Год примерно каждые 3 хода
        if self.turn % 3 == 0:
            self.year += 1
