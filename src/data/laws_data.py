"""
Законы Османского государства.

Открываются по этапу кампании. Эффекты: доход, найм, upkeep, осада, торговля.
"""

from dataclasses import dataclass
from src.utils.constants import STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE


@dataclass
class Law:
    """Закон с описанием и эффектами"""
    id: str
    name_ru: str
    description: str
    # Минимальный этап для принятия
    required_stage: str
    # Плюсы (список строк)
    pros: list[str]
    # Минусы (список строк)
    cons: list[str]
    # Эффекты (опционально — для будущего)
    income_modifier: float = 1.0      # Множитель дохода
    garrison_modifier: float = 1.0    # Множитель гарнизона
    hire_cost_modifier: float = 1.0   # Множитель стоимости найма


# Исторически обоснованные законы Османов
LAWS_DATA = [
    # === БЕЕЛИК (1299+) ===
    Law(
        id="akhi_teşkilat",
        name_ru="Ахи-теşkilat (Цеха)",
        description="Ремесленные гильдии — основа экономики беелика.",
        required_stage=STAGE_BEYLIK,
        pros=["+15% дохода с крепостей", "Стабильность в городах"],
        cons=["Меньше контроля над ремеслом"],
    ),
    Law(
        id="gaza_ideology",
        name_ru="Идеология газа",
        description="Война против неверных как долг перед Аллахом.",
        required_stage=STAGE_BEYLIK,
        pros=["+10% к морали армии", "Легитимность завоеваний"],
        cons=["Сложнее заключить мир с христианами"],
    ),
    Law(
        id="uc_bey_system",
        name_ru="Удж-беи (Пограничные беи)",
        description="Назначать пограничных военачальников в приграничные крепости.",
        required_stage=STAGE_BEYLIK,
        pros=["Быстрее сбор армии у границ", "Автономия в обороне"],
        cons=["Риск сепаратизма"],
    ),
    Law(
        id="timar_draft",
        name_ru="Зачатки тимара",
        description="Земельные пожалования за военную службу.",
        required_stage=STAGE_BEYLIK,
        pros=["−20% стоимость найма", "Лояльность сипахов"],
        cons=["Меньше дохода в казну с земель"],
    ),

    # === СУЛТАНАТ (1326+) ===
    Law(
        id="devsirme",
        name_ru="Девширме",
        description="Набор христианских мальчиков в янычары.",
        required_stage=STAGE_SULTANATE,
        pros=["Элитные подразделения", "Верность султану"],
        cons=["Недовольство христиан", "+5% расходы на армию"],
    ),
    Law(
        id="kanunname",
        name_ru="Кануннаме",
        description="Свод законов — единые правила на всех землях.",
        required_stage=STAGE_SULTANATE,
        pros=["+20% доход", "Единая администрация"],
        cons=["Сопротивление местных элит"],
    ),
    Law(
        id="millet_system",
        name_ru="Система миллетов",
        description="Религиозная автономия общин (православные, армяне, иудеи).",
        required_stage=STAGE_SULTANATE,
        pros=["+10% доход", "Лояльность немусульман"],
        cons=["Меньше централизации"],
    ),
    Law(
        id="vezir_divan",
        name_ru="Диван и везиры",
        description="Совет при султане — централизованное управление.",
        required_stage=STAGE_SULTANATE,
        pros=["+15% доход", "Эффективное управление"],
        cons=["Риск заговоров везиров"],
    ),

    # === ИМПЕРИЯ (1453+) ===
    Law(
        id="timar_full",
        name_ru="Тимар (полная система)",
        description="Развитая система военно-ленных поместий.",
        required_stage=STAGE_EMPIRE,
        pros=["−30% стоимость найма", "Многочисленная конница"],
        cons=["Зависимость от сипахов"],
    ),
    Law(
        id="capitulations",
        name_ru="Капитуляции",
        description="Торговые привилегии для иностранных купцов.",
        required_stage=STAGE_EMPIRE,
        pros=["+25% доход с торговли", "Рост портов"],
        cons=["Уступка части суверенитета"],
    ),
    Law(
        id="devlet_ali",
        name_ru="Высокая Порта",
        description="Централизованная имперская бюрократия.",
        required_stage=STAGE_EMPIRE,
        pros=["+20% доход", "Контроль над провинциями"],
        cons=["Коррупция", "+10% расходы"],
    ),
]


def get_laws_for_stage(stage: str) -> list[Law]:
    """Законы, доступные на данном этапе"""
    stage_order = [STAGE_BEYLIK, STAGE_SULTANATE, STAGE_EMPIRE]
    stage_idx = stage_order.index(stage) if stage in stage_order else 0
    result = []
    for law in LAWS_DATA:
        req_idx = stage_order.index(law.required_stage) if law.required_stage in stage_order else 0
        if req_idx <= stage_idx:
            result.append(law)
    return result


# Эффекты законов (множители)
LAW_EFFECTS = {
    "akhi_teşkilat": {"income": 1.15},
    "gaza_ideology": {"assault_morale": 0.1},  # −10% шанс поражения при штурме
    "uc_bey_system": {"garrison_min": 0},
    "timar_draft": {"hire_cost": 0.8},
    "devsirme": {"upkeep": 1.05, "garrison_bonus": 5},
    "kanunname": {"income": 1.2},
    "millet_system": {"income": 1.1},
    "vezir_divan": {"income": 1.15},
    "timar_full": {"hire_cost": 0.7},
    "capitulations": {"trade_income": 1.25},
    "devlet_ali": {"income": 1.2, "upkeep": 1.1},
}
