"""Chapter one content. Dates/coordinates and design abstractions stay separate."""

from campaign.world import CROSSINGS, DYNASTY, FORTRESS_PROJECT, LAND_CHAINS, REGIONS, SEA_CHAINS, WORLD_FACTIONS, WORLD_PLACES, chain_edges

CONTENT_VERSION = "mediterranean-2"
RULES_VERSION = 2
FACTIONS = {"ottoman": "Османы", "byzantine": "Византия", "germiyan": "Гермиян"}
# Military numbers and income are balance values, not historical population estimates.
# The chapter starts in spring 1299, before the year's frontier conquests.
PLACES = [
    ("sogut", "Сёгют", 30.179, 39.792, "ottoman", 45, 30, False),
    ("karacahisar", "Караджахисар", 30.561, 39.903, "ottoman", 30, 45, False),
    ("bilecik", "Биледжик", 29.979, 40.143, "byzantine", 32, 40, False),
    ("yarhisar", "Ярхисар", 29.651, 40.238, "byzantine", 25, 35, False),
    ("inegol", "Инегёль", 29.513, 40.078, "byzantine", 35, 40, False),
    ("yenishehir", "Йенишехир", 29.651, 40.268, "byzantine", 30, 35, False),
    ("koyunhisar", "Койунхисар", 30.094, 40.593, "byzantine", 40, 40, False),
    ("bursa", "Бурса", 29.061, 40.182, "byzantine", 110, 90, False),
    ("nicaea", "Никея", 29.721, 40.428, "byzantine", 95, 85, False),
    ("mudanya", "Муданья", 28.882, 40.375, "byzantine", 40, 45, True),
    ("cius", "Киос", 29.088, 40.433, "byzantine", 45, 45, True),
    ("nicomedia", "Никомедия", 29.916, 40.765, "byzantine", 100, 85, True),
    ("kutahya", "Кютахья", 29.983, 39.418, "germiyan", 70, 65, False),
]
# Explicit strategic corridors, not pixel-distance adjacency. One edge per season.
ROADS = [
    ("sogut", "karacahisar"), ("sogut", "bilecik"), ("sogut", "inegol"),
    ("sogut", "kutahya"), ("karacahisar", "kutahya"),
    ("bilecik", "yarhisar"), ("bilecik", "koyunhisar"),
    ("yarhisar", "yenishehir"), ("yarhisar", "inegol"),
    ("inegol", "bursa"), ("yenishehir", "bursa"), ("yenishehir", "nicaea"),
    ("koyunhisar", "nicaea"), ("koyunhisar", "nicomedia"),
    ("bursa", "mudanya"), ("bursa", "cius"), ("cius", "nicaea"),
    ("mudanya", "cius"), ("nicaea", "nicomedia"),
]
FACTIONS.update(WORLD_FACTIONS)
PLACES += WORLD_PLACES
ROADS = sorted({tuple(sorted(edge)) for edge in ROADS + chain_edges(LAND_CHAINS) + CROSSINGS + chain_edges(SEA_CHAINS)})
PLACE_INDEX = {p[0]: p for p in PLACES}
assert len(PLACE_INDEX) == len(PLACES), "Duplicate place ID"
ROUTE_TYPES = {tuple(sorted(edge)): "ferry" for edge in CROSSINGS}
ROUTE_TYPES.update({tuple(sorted(edge)): "sea" for edge in chain_edges(SEA_CHAINS)})
INITIAL_SEAFARERS = {p[4] for p in PLACES if p[7]} - {"ottoman"}
ADJACENCY = {pid: sorted(b if a == pid else a for a, b in ROADS if pid in (a, b)) for pid in PLACE_INDEX}
PLACE_KINDS = {p[0]: "village" if p[6] == 0 else "city" if p[7] or p[5] >= 55 else "fortress" for p in PLACES}
CAPITALS = {fid: next(p[0] for p in PLACES if p[4] == fid) for fid in FACTIONS}
CAPITALS.update({"ottoman": "sogut", "byzantine": "constantinople", "germiyan": "kutahya", "genoa": "genoa_city", "venice": "venice_city", "mamluk": "cairo"})
TROOPS = {
    "militia": {"name": "Ополчение", "cost": 2, "upkeep": 1, "power": 8},
    "archers": {"name": "Лучники", "cost": 4, "upkeep": 2, "power": 12},
    "cavalry": {"name": "Конница", "cost": 6, "upkeep": 3, "power": 16},
}
BUILDINGS = {
    "market": {"name": "Рынок", "cost": 75, "turns": 2, "description": "+8 золота за сезон"},
    "granary": {"name": "Зернохранилище", "cost": 60, "turns": 2, "description": "+12 продовольствия, +20 к запасам при обороне"},
    "walls": {"name": "Укрепления", "cost": 80, "turns": 3, "description": "+25 целостности стен"},
    "workshop": {"name": "Осадная мастерская", "cost": 90, "turns": 3, "requires": "siege_camp", "description": "Позволяет оснастить находящуюся здесь армию орудиями"},
}
TECHNOLOGIES = {
    "drill": {"name": "Обучение отрядов", "branch": "Военное дело", "cost": 60, "requires": [], "description": "+15% силы пехоты"},
    "combined_arms": {"name": "Взаимодействие войск", "branch": "Военное дело", "cost": 100, "requires": ["drill"], "description": "+10% силы смешанной армии"},
    "siege_camp": {"name": "Осадный лагерь", "branch": "Инженерия", "cost": 60, "requires": [], "description": "Открывает мастерскую; ускоряет осадные работы"},
    "trebuchets": {"name": "Организация метательных машин", "branch": "Инженерия", "cost": 100, "requires": ["siege_camp", "stores"], "description": "Усиливает доставленные осадные орудия"},
    "stores": {"name": "Организация запасов", "branch": "Хозяйство", "cost": 60, "requires": [], "description": "+10 продовольствия с каждого владения"},
    "irrigation": {"name": "Улучшение землепользования", "branch": "Хозяйство", "cost": 100, "requires": ["stores"], "description": "+15 продовольствия с каждого владения"},
    "scribes": {"name": "Подготовка писцов", "branch": "Управление", "cost": 60, "requires": [], "description": "+1 административная способность, +2 знания за сезон"},
    "land_register": {"name": "Земельный учёт", "branch": "Управление", "cost": 100, "requires": ["scribes"], "description": "+4 налога с каждого владения"},
    "ferries": {"name": "Организация переправ", "branch": "Морское дело", "cost": 60, "requires": [], "description": "Открывает переправы (10 золота) и морские переходы (20); +6 дохода при владении портом"},
    "convoys": {"name": "Снабжение побережья", "branch": "Морское дело", "cost": 100, "requires": ["ferries", "stores"], "description": "Открывает морские пути снабжения; +15 снабжения армии в своём порту"},
}
REFORMS = {
    "tolerance": {"name": "Гарантии местным общинам", "cost": 45, "description": "Лояльность завоёванных городов растёт быстрее; военная знать недовольна"},
    "tax_register": {"name": "Единый сбор податей", "cost": 55, "requires": "scribes", "description": "+6 налога с владения; при введении −10 местной лояльности"},
    "provincial_offices": {"name": "Провинциальные канцелярии", "cost": 180, "requires": "land_register", "description": "+12 административной способности; +8 расходов за сезон"},
}

# Choices persist as flags; future events read those flags and actual world state.
EVENTS = {
    "founding": {
        "title": "Первый диван", "speaker": "Осман • правитель", "body": "Две крепости и небольшие поселения ещё не делают государство. Военные беи требуют похода, купцы — безопасности дорог. Каким будет первый приказ?",
        "choices": [
            {"id": "frontier", "text": "Дать пограничным беям военный мандат", "hint": "−30 золота; −15 резерва; +15 ополченцев; знать +10, купцы −5"},
            {"id": "merchants", "text": "Заключить договор с купцами", "hint": "+60 золота сейчас; обязательство вернуть 90 через 8 сезонов; купцы +10"},
            {"id": "stewardship", "text": "Начать с запасов и управления", "hint": "−25 золота; +80 продовольствия; +15 знаний"},
        ],
    },
    "merchant_debt": {
        "title": "Цена первого договора", "speaker": "Представитель купцов", "body": "Наши деньги помогли вашему первому походу. Пришёл срок возвращать долг. От вашего ответа зависит доверие к обещаниям правителя.",
        "choices": [
            {"id": "repay", "text": "Вернуть обещанные 90 золотых", "hint": "−90 золота; купцы +15; долг закрыт"},
            {"id": "privileges", "text": "Передать часть пошлин вместо денег", "hint": "−8 дохода каждый сезон; купцы +5; знать −5"},
            {"id": "refuse", "text": "Отказаться от обязательства", "hint": "Купцы −25; легитимность −10; при поддержке купцов ниже 40 торговля остановится"},
        ],
    },
    "first_city": {
        "title": "Город после осады", "speaker": "Совет • управление", "body": "Ключи от ворот у вас. Но кому достанутся дома, подати и право суда? Гарнизон удержит ворота — доверие жителей придётся заслужить.",
        "choices": [
            {"id": "charter", "text": "Подтвердить местные права", "hint": "−25 золота; +25 лояльности оккупированным городам; знать −5"},
            {"id": "plunder", "text": "Раздать добычу войску", "hint": "+65 золота; −20 лояльности; хозяйство −20; знать +10"},
        ],
    },
    "local_petition": {
        "title": "Исполните данное слово", "speaker": "Старейшины города", "body": "Вы обещали сохранить наш суд. Теперь пограничный бей требует заменить старейшин его людьми. Чьё слово сильнее — грамота правителя или заслуги военачальника?",
        "choices": [
            {"id": "honour", "text": "Защитить выданную грамоту", "hint": "+15 местной лояльности; знать −10; легитимность +5"},
            {"id": "revoke", "text": "Уступить военным беям", "hint": "−25 местной лояльности; знать +10; легитимность −5"},
        ],
    },
    "military_claim": {
        "title": "Мандат требует награды", "speaker": "Пограничные беи", "body": "Мы собирали людей по вашему первому приказу. Теперь новые города приносят доход. Беи требуют постоянной доли податей.",
        "choices": [
            {"id": "grant", "text": "Закрепить долю за военными", "hint": "−6 дохода за сезон; знать +15; легитимность +5"},
            {"id": "centralize", "text": "Оставить подати в казне", "hint": "Знать −20; администрация +10"},
        ],
    },
    "bursa": {
        "title": "Ключи от Бурсы", "speaker": "Диван • итог первой главы", "body": "Бурса под вашим контролем. У стен завершился поход, но не борьба за государство. Какой порядок вы установите в новом центре?",
        "choices": [
            {"id": "capital", "text": "Перенести двор и начать интеграцию", "hint": "−60 золота; столица в Бурсе; лояльность +20; легитимность +15"},
            {"id": "frontier_capital", "text": "Сохранить двор в Сёгюте", "hint": "Знать +10; легитимность +10; средства остаются на дальнейшие решения"},
        ],
    },
    "succession": {
        "title": "Передача власти", "speaker": "Совет • династия", "body": "Осман больше не может вести дела. Орхан готов принять власть, но беи требуют подтверждения своих прав. Государство должно пережить смену правителя.",
        "choices": [
            {"id": "oath", "text": "Получить присягу, подтвердив обязательства", "hint": "−40 золота; Орхан наследует власть; знать +10"},
            {"id": "authority", "text": "Передать власть без уступок", "hint": "Орхан наследует власть; легитимность −10; знать −15"},
        ],
    },
}

for ruler in DYNASTY[2:]:
    EVENTS[f"accession_{ruler['id']}"] = {
        "title": f"Новый правитель: {ruler['name']}",
        "speaker": "Диван • наследование власти",
        "body": f"Двор готов принести присягу. {ruler['name']} принимает державу вместе с её войнами, договорами и долгами." + (" С этого правления можно возводить новые крепости в своих поселениях." if ruler['rank'] == 3 else ""),
        "choices": [
            {"id": "oath", "text": "Подтвердить обязательства перед беями", "hint": "−40 золота; знать +10; новый правитель вступает на престол"},
            {"id": "authority", "text": "Принять власть без уступок", "hint": "Легитимность −10; знать −15; новый правитель вступает на престол"},
        ],
    }
