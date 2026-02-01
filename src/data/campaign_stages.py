"""
Этапы кампании — эволюция Бейлик → Султанат → Империя
Триггеры: захват Бурсы, захват Константинополя
"""

from dataclasses import dataclass
from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class CampaignStage:
    """Этап кампании"""
    id: str
    name: str
    name_ru: str
    year_start: int
    description: str
    trigger_fortress: str | None = None  # Крепость для перехода


STAGES = {
    STAGE_BEYLIK: CampaignStage(
        id=STAGE_BEYLIK,
        name="Ottoman Beylik",
        name_ru="Османский беелик",
        year_start=1299,
        description="Бейлик на границе Византии. Осман I — основатель династии.",
        trigger_fortress=None,
    ),
    STAGE_SULTANATE: CampaignStage(
        id=STAGE_SULTANATE,
        name="Ottoman Sultanate",
        name_ru="Османский султанат",
        year_start=1326,
        description="Султанат после захвата Бурсы. Орхан I.",
        trigger_fortress="bursa",
    ),
    STAGE_EMPIRE: CampaignStage(
        id=STAGE_EMPIRE,
        name="Ottoman Empire",
        name_ru="Османская империя",
        year_start=1453,
        description="Империя после падения Константинополя.",
        trigger_fortress="constantinople",
    ),
}


def get_stage_by_fortress(fortress_id: str) -> str | None:
    """Этап, разблокируемый захватом крепости."""
    for stage_id, s in STAGES.items():
        if s.trigger_fortress == fortress_id:
            return stage_id
    return None


def get_next_stage(current_stage: str) -> str | None:
    """Следующий этап после текущего."""
    order = [STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE]
    try:
        i = order.index(current_stage)
        if i + 1 < len(order):
            return order[i + 1]
    except ValueError:
        pass
    return None
