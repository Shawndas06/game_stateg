"""
Этапы кампании: Беелик → Султанат → Империя
Чёткая сюжетная логика перехода состояний
"""

from dataclasses import dataclass
from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class CampaignStage:
    """Этап кампании с описанием"""
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
        description="Маленький бейлик на границе Византии. Осман I объявил независимость от сельджуков."
    ),
    STAGE_SULTANATE: CampaignStage(
        id=STAGE_SULTANATE,
        name="Ottoman Sultanate",
        name_ru="Османский султанат",
        year_start=1326,
        description="Падение Бурсы — первая столица. Орхан I провозглашает султанат."
    ),
    STAGE_EMPIRE: CampaignStage(
        id=STAGE_EMPIRE,
        name="Ottoman Empire",
        name_ru="Османская империя",
        year_start=1453,
        description="Падение Константинополя. Мехмед II — Кайзер-и Рум. Новая эра."
    ),
}


# Триггеры: какая крепость переводит в какой этап
STAGE_TRIGGERS = {
    "sultanate": "bursa",   # Захват Бурсы → Султанат
    "empire": "constantinople",  # Захват Константинополя → Империя
}


def get_next_stage(current_stage: str) -> str | None:
    """Получить следующий этап кампании"""
    order = [STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE]
    idx = order.index(current_stage) if current_stage in order else -1
    if idx >= 0 and idx < len(order) - 1:
        return order[idx + 1]
    return None


def get_stage_by_fortress(fortress_id: str) -> str | None:
    """Какой этап активируется при захвате этой крепости"""
    for stage, fid in STAGE_TRIGGERS.items():
        if fid == fortress_id:
            return stage
    return None
