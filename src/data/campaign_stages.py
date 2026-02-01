"""
Этапы кампании — упрощённо (без эволюции Бейлик→Султанат→Империя)
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


STAGES = {
    STAGE_BEYLIK: CampaignStage(
        id=STAGE_BEYLIK,
        name="Ottoman Beylik",
        name_ru="Османский беелик",
        year_start=1299,
        description="Бейлик на границе Византии. Осман I — основатель династии."
    ),
    STAGE_SULTANATE: CampaignStage(
        id=STAGE_SULTANATE,
        name="Ottoman Sultanate",
        name_ru="Османский султанат",
        year_start=1326,
        description="Султанат после захвата Бурсы. Орхан I."
    ),
    STAGE_EMPIRE: CampaignStage(
        id=STAGE_EMPIRE,
        name="Ottoman Empire",
        name_ru="Османская империя",
        year_start=1453,
        description="Империя после падения Константинополя."
    ),
}


def get_stage_by_fortress(fortress_id: str) -> str | None:
    """Этапы отключены — возвращаем None."""
    return None


def get_next_stage(current_stage: str) -> str | None:
    """Этапы отключены."""
    return None
