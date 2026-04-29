"""
narrative_data.py — сюжетные события в духе Suzerain (текст + выборы с последствиями).

Поле choice.effect — строка-ключ для GameState.apply_narrative_choice.
"""

from dataclasses import dataclass, field


@dataclass
class NarrativeChoice:
    """Один вариант выбора: текст, ключ эффекта, подпись последствия для игрока."""
    text: str
    effect: str
    consequence: str = ""


@dataclass
class NarrativeEvent:
    """Нарративное событие и условия показа (этап и минимальный номер хода)."""
    id: str
    title: str
    body: str
    choices: list[NarrativeChoice] = field(default_factory=list)
    trigger_stage: str | None = None
    trigger_after_turn: int = 0


# === БЕЙЛИК ===

EVENT_START = NarrativeEvent(
    id="start",
    title="1299 — Рождение беелика",
    body="Вы отделились от распадающегося Румского султаната: Сёгют — узел дорог между степью и христианским миром. "
         "Византийские темы истощены войной с болгарами и сербами; анатолийские бейлики спорят за наследие сельджуков. "
         "Гази готовы к рейдам, но казна мала, а соседи не дремлют. Первый выбор задаёт тон всей кампании.",
    choices=[
        NarrativeChoice(
            "Собрать дань с крестьян и вооружить гази",
            "start_military",
            "−30 золота на оружие и провиант; +4 легитимности среди воинов.",
        ),
        NarrativeChoice(
            "Укрепить башни и запасы в Сёгюте",
            "start_defense",
            "−18 золота на ремонт стен; +7 легитимности как заботливого правителя.",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=0,
)

EVENT_VIZIER_MEMO = NarrativeEvent(
    id="vizier_intrigue",
    title="Грамота визиря",
    body="Эмир из соседнего бейлика шлёт заигрывания: он предлагает «совместную охрану границ», но ваши советники шепчут — "
         "за этим скрывается попытка подсадить своих людей при вашем диване. Торговцы жалуются на произвол сборщиков подати.",
    choices=[
        NarrativeChoice(
            "Расчистить сборщиков и заплатить лояльным племенам",
            "vizier_reward_loyal",
            "−12 золота; +9 легитимности.",
        ),
        NarrativeChoice(
            "Жёсткий аудит и конфискации у коррупционеров",
            "vizier_audit",
            "+28 золота в казну; −6 легитимности (страх и зависть).",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=2,
)

EVENT_COUNCIL_FEAST = NarrativeEvent(
    id="council_feast",
    title="Совет беков",
    body="Зимний совет в палатке: спорят, тянуть ли войско на Никомедию или копить силы до весны. "
         "Старейшины требуют пиров и подарков; улемы напоминают о шариате и справедливости к подданным.",
    choices=[
        NarrativeChoice(
            "Устроить пир и раздать трофеи — сплотить элиту",
            "council_feast",
            "−22 золота; +6 легитимности.",
        ),
        NarrativeChoice(
            "Отказаться от пира; деньги в казармы",
            "council_barracks",
            "−8 золота; к походной армии +10 воинов (новобранцы).",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=4,
)

EVENT_BURSA_APPROACH = NarrativeEvent(
    id="bursa_approach",
    title="Пруса на горизонте",
    body="Бурса (Пруса) — богатый узел шёлкового пути и ключ к Босфору. Византийский гарнизон устал; "
         "но стены всё ещё высоки, а осадная машина требует времени. Румелийские хроники будут помнить, как вы назвали цель.",
    choices=[
        NarrativeChoice(
            "Главный удар — на Бурсу, как завещал отец Осман",
            "siege_bursa",
            "+5 легитимности; фокус на столице султаната.",
        ),
        NarrativeChoice(
            "Сначала отрезать Никею — ослабить тыл врага",
            "siege_nicaea",
            "+24 золота (грабёж/контрибуция); −3 легитимности.",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=6,
)

EVENT_NOMAD_AUX = NarrativeEvent(
    id="nomad_auxiliaries",
    title="Тюркменские отряды",
    body="Кочевники предлагают услуги: они знают тропы через Улу-Даг и не боятся зимних перевалов. "
         "Но их верность длится ровно один сезон, а жалованье требуют золотом.",
    choices=[
        NarrativeChoice(
            "Нанять конные полки на рейд к Мармаре",
            "nomad_hire",
            "−42 золота; +18 воинов к походной армии.",
        ),
        NarrativeChoice(
            "Отказаться — не кормить чужих хищников",
            "nomad_refuse",
            "+7 легитимности (справедливость перед подданными).",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=9,
)

EVENT_TRADE_ROUTES = NarrativeEvent(
    id="nicaea_trade",
    title="Караван из Никеи",
    body="Греческие и армянские купцы просят охраны на тракте; за это готовы платить пошлину в вашу казну. "
         "Жёсткий контроль границ увеличит сбор, но разозлит местных спекулянтов.",
    choices=[
        NarrativeChoice(
            "Выдать охранные грамоты и собирать пошлину",
            "trade_permit",
            "+38 золота; −4 легитимности (резкий рост тарифов).",
        ),
        NarrativeChoice(
            "Умеренная пошлина и суд для споров купцов",
            "trade_balance",
            "+22 золота; +5 легитимности.",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=12,
)

EVENT_ORTHODOX_MILLET = NarrativeEvent(
    id="orthodox_millet",
    title="Христианские общины",
    body="Епископ из захваченного района просит не трогать церкви и давать суд по обычаю — «миллет» до официального оформления. "
         "Строгость понравится гази; милость укрепит налоговую базу.",
    choices=[
        NarrativeChoice(
            "Гарантировать богослужение за повышенную дань",
            "millet_tolerate",
            "+32 золота; +4 легитимности.",
        ),
        NarrativeChoice(
            "Не уступать — порядок превыше привычек подданных",
            "millet_strict",
            "+10 легитимности среди мусульманской элиты; −25 золота на подавление беспорядков.",
        ),
    ],
    trigger_stage="beylik",
    trigger_after_turn=15,
)

# === СУЛТАНАТ ===

EVENT_BURSA_FALLEN = NarrativeEvent(
    id="bursa_fallen",
    title="1326 — Бурса открыта",
    body="Стены сдались. Орхан объявляет столицу здесь; прах Османа переносят в город, как он завещал. "
         "Титул «султан» ещё звучит дерзко для соседей — но теперь вы говорите с миром языком государя, а не удельного бея.",
    choices=[
        NarrativeChoice(
            "Объявить масштабный поход на оставшиеся темы",
            "expand_aggressive",
            "+35 золота с трофеев; +6 легитимности.",
        ),
        NarrativeChoice(
            "Закрепиться: налоговая реформа и дороги",
            "expand_consolidate",
            "+12 легитимности; −20 золота на администрацию.",
        ),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=0,
)

EVENT_SUCCESSION = NarrativeEvent(
    id="succession_shadow",
    title="Тень престолонаследия",
    body="Хронисты уже пишут о распрях между сыновьями. Один фракция дворца тянет на жёсткую дисциплину наследования, "
         "другая — на милость к младшим и раздачу земель, как в персидских сказаниях.",
    choices=[
        NarrativeChoice(
            "Поддержать «законный» титул старшего — единая воля",
            "succession_elder",
            "+11 легитимности.",
        ),
        NarrativeChoice(
            "Купить лояльность дарениями и должностями",
            "succession_bribes",
            "−28 золота; +6 легитимности.",
        ),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=2,
)

EVENT_GALLIPOLI = NarrativeEvent(
    id="gallipoli",
    title="1354 — Землетрясение у Галлиполи",
    body="Стихия разрывает византийские укрепления у пролива. Сулейман занимает бастион — первый ваш гарнизон в Европе. "
         "Флот Константинополя в шоке; генуэзские капитаны пересчитывают риски контрабанды.",
    choices=[
        NarrativeChoice(
            "Срочно перебросить резервы на Балканы",
            "gallipoli_push",
            "+15 воинов в полевую армию; −18 золота на перевоз.",
        ),
        NarrativeChoice(
            "Укрепить плацдарм и торговать с морем",
            "gallipoli_fortify",
            "+26 золота; +5 легитимности.",
        ),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=5,
)

EVENT_RUMELIA = NarrativeEvent(
    id="rumelia_horizon",
    title="Румелия зовёт",
    body="Сербские и болгарские боляры спорят, с кем союз выгоднее — с вами или с Венгрией. "
         "Жестокий рейд принесёт золото и страх; дипломатия удержит фронт ценой престижа.",
    choices=[
        NarrativeChoice(
            "Наказать приграничье быстрым набегом",
            "rumelia_raid",
            "+44 золота; −7 легитимности.",
        ),
        NarrativeChoice(
            "Отправить послов с даром и угрозой вежливо",
            "rumelia_diplomacy",
            "+9 легитимности; −14 золота на подарки.",
        ),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=8,
)

EVENT_JANISSARY = NarrativeEvent(
    id="janissary_seed",
    title="Дьяруль-ахад и деўширме",
    body="Улемы спорят о каноничности воинов из числа подданных. Кадı — талантливый везир — предлагает систему, "
         "что позже назовут янычарами: дисциплина против племенных связей.",
    choices=[
        NarrativeChoice(
            "Заложить лагерь подготовки и платить рыцарям-наставникам",
            "janissary_invest",
            "−55 золота; +14 легитимности.",
        ),
        NarrativeChoice(
            "Двигаться постепенно — лишь казармы и порядок",
            "janissary_slow",
            "−22 золота; +7 легитимности.",
        ),
    ],
    trigger_stage="sultanate",
    trigger_after_turn=11,
)

# === ИМПЕРИЯ ===

EVENT_CONSTANTINOPLE_FALLEN = NarrativeEvent(
    id="constantinople_fallen",
    title="1453 — Стены Царьграда",
    body="Пушки Урбана бьют по Феодосиевым валам. Последний Константин пал среди своих. Мехмед въезжает не как завоеватель кочевников, "
         "а как кайзер-и Рум. Айя-София слышит новый зов; мир переосмысливает карту.",
    choices=[
        NarrativeChoice(
            "Объявить амнистию и сохранить инфраструктуру города",
            "conquest_mercy",
            "+90 золота из казны Византии; +18 легитимности.",
        ),
        NarrativeChoice(
            "Жёсткая смена элит; конфискации для новой армии",
            "conquest_harsh",
            "+130 золота; +8 легитимности.",
        ),
    ],
    trigger_stage="empire",
    trigger_after_turn=0,
)

EVENT_HEIR_OF_ROME = NarrativeEvent(
    id="heir_of_rome",
    title="Преемник Рима?",
    body="Латинские писатели ругают «турецкого варвара»; восточные хроники сравнивают вас с Киосроями. "
         "Италия дрожит; Мамлюкский султан шлёт копии писем, где вы — брат по власти над людьми Книги.",
    choices=[
        NarrativeChoice(
            "Подчеркнуть исламский характер империи",
            "rome_islamic",
            "+13 легитимности.",
        ),
        NarrativeChoice(
            "Выдать грамоты христианским общинам города",
            "rome_dhimmi",
            "+42 золота стабильного дохода от общин (единовременно); +6 легитимности.",
        ),
    ],
    trigger_stage="empire",
    trigger_after_turn=2,
)

EVENT_IMPERIAL_CODE = NarrativeEvent(
    id="imperial_code",
    title="Канун и канцелярия",
    body="Границы выросли вчерашним днём; без свода законов провинции начнут судить каждый по-своему. "
         "Шейх аль-ислам ждёт вашего слова о балансе шариата и государственной рации.",
    choices=[
        NarrativeChoice(
            "Финансировать редкий свод и школу кадı",
            "code_majesty",
            "−70 золота; +16 легитимности.",
        ),
        NarrativeChoice(
            "Узкий свод указов — сначала армия и налог",
            "code_pragmatic",
            "−38 золота; +9 легитимности.",
        ),
    ],
    trigger_stage="empire",
    trigger_after_turn=5,
)

NARRATIVE_EVENTS = [
    EVENT_START,
    EVENT_VIZIER_MEMO,
    EVENT_COUNCIL_FEAST,
    EVENT_BURSA_APPROACH,
    EVENT_NOMAD_AUX,
    EVENT_TRADE_ROUTES,
    EVENT_ORTHODOX_MILLET,
    EVENT_BURSA_FALLEN,
    EVENT_SUCCESSION,
    EVENT_GALLIPOLI,
    EVENT_RUMELIA,
    EVENT_JANISSARY,
    EVENT_CONSTANTINOPLE_FALLEN,
    EVENT_HEIR_OF_ROME,
    EVENT_IMPERIAL_CODE,
]


def get_events_for_stage(stage: str, current_turn: int) -> list[NarrativeEvent]:
    """События для этапа и хода (вспомогательно)."""
    result = []
    for ev in NARRATIVE_EVENTS:
        if ev.trigger_stage == stage and ev.trigger_after_turn <= current_turn:
            result.append(ev)
    return result
