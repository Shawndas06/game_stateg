"""
Нарративные события в стиле Suzerain
Сюжетная линия: решения, последствия, атмосфера
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class NarrativeChoice:
    """Вариант выбора в нарративном событии"""
    text: str
    effect: str  # Описание эффекта
    consequence: str = ""  # Что произойдёт


@dataclass
class NarrativeEvent:
    """Нарративное событие — текст + выборы"""
    id: str
    title: str
    body: str
    choices: list[NarrativeChoice] = field(default_factory=list)
    # Когда показывать: stage, turn_range
    trigger_stage: str | None = None
    trigger_after_turn: int = 0


# === СОБЫТИЯ НАЧАЛА (Беелик) ===
EVENT_START = NarrativeEvent(
    id="start",
    title="1299 — Рождение беелика",
    body="Осман-бей, вы объявили независимость от сельджукского султаната. "
         "Ваш беелик — лишь горстка земель у границ Византии. Но Сёгют — начало великого пути. "
         "Византия слабеет. Время расширять границы.",
    choices=[
        NarrativeChoice("Готовиться к походу на Бурсу", "military", "Соберём армию и двинемся к стенам Прусы."),
        NarrativeChoice("Укрепить границы", "defense", "Организуем оборону владений."),
    ],
    trigger_stage="beylik",
    trigger_after_turn=0,
)

EVENT_BURSA_APPROACH = NarrativeEvent(
    id="bursa_approach",
    title="Путь к Бурсе",
    body="Бурса — жемчужина Византии в Анатолии. Город-крепость, осада которого может занять годы. "
         "Но её падение изменит всё: Орхан провозгласит султанат, а Бурса станет первой столицей.",
    choices=[
        NarrativeChoice("Начать осаду Бурсы", "siege_bursa", "Долгая осада, но награда велика."),
        NarrativeChoice("Сначала захватить Никею", "siege_nicaea", "Ослабим византийцев по периметру."),
    ],
    trigger_stage="beylik",
    trigger_after_turn=5,
)

# === СОБЫТИЯ СУЛТАНАТА ===
EVENT_BURSA_FALLEN = NarrativeEvent(
    id="bursa_fallen",
    title="1326 — Падение Бурсы",
    body="Стены пали. Орхан I вступает в город. Осман-гази похоронен в Бурсе по его завещанию. "
         "Бейлик стал Султанатом. Новая эра началась.",
    choices=[
        NarrativeChoice("Продолжить экспансию", "expand", "Европа и Азия ждут."),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=0,
)

EVENT_GALLIPOLI = NarrativeEvent(
    id="gallipoli",
    title="1354 — Землетрясение в Галлиполи",
    body="Землетрясение разрушило византийские укрепления Галлиполи. "
         "Сулейман-паша занял крепость — первая османская цитадель в Европе. "
         "Двери на Балканы открыты.",
    choices=[
        NarrativeChoice("Переправить войска в Европу", "europe", "Адрианополь — следующая цель."),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=3,
)

# === СОБЫТИЯ ИМПЕРИИ ===
EVENT_CONSTANTINOPLE_FALLEN = NarrativeEvent(
    id="constantinople_fallen",
    title="1453 — Падение Константинополя",
    body="53 дня осады. Пушки. Последний император пал у стен. "
         "Мехмед II въезжает в город как Кайзер-и Рум — Цезарь Рима. "
         "Константинополь стал Стамбулом. Османская Империя — преемница Рима.",
    choices=[
        NarrativeChoice("Новая эра империи", "empire", "История пишется заново."),
    ],
    trigger_stage="empire",
    trigger_after_turn=0,
)

# Все события для выборки по этапу и ходу
NARRATIVE_EVENTS = [
    EVENT_START,
    EVENT_BURSA_APPROACH,
    EVENT_BURSA_FALLEN,
    EVENT_GALLIPOLI,
    EVENT_CONSTANTINOPLE_FALLEN,
]


def get_events_for_stage(stage: str, current_turn: int) -> list[NarrativeEvent]:
    """Получить события для текущего этапа и хода"""
    result = []
    for ev in NARRATIVE_EVENTS:
        if ev.trigger_stage == stage and ev.trigger_after_turn <= current_turn:
            result.append(ev)
    return result
