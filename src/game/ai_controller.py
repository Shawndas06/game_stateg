"""
ai_controller.py — логика хода AI для всех фракций (кроме игрока).

Реализует:
- Вспомогательные функции: владение крепостями фракции, гарнизоны, постройки, расстояние между крепостями.
- Выбор целей: вражеские крепости, сортировка по слабости/близости; учёт отношений (не атакует при peace/nap/alliance).
- Набор войск, сбор полевой армии в столице, начало осад и штурмы (с учётом личности фракции).
- Строительство зданий по очереди AI_BUILD_ORDER и прогресс строительства за ход.
- Дипломатические предложения AI игроку: торговля (_maybe_propose_trade), мир (_maybe_propose_peace), дань (_maybe_propose_tribute).
- process_faction_turn: один ход одной фракции; process_all_ai_turns: ходы всех AI фракций, возвращает список сообщений для уведомлений.
"""

import random
from src.data.fortresses import FORTESSES_DATA, get_fortress_by_id
from src.data.factions_data import AI_FACTION_IDS, FACTION_NAMES_RU
from src.data.ai_personalities import get_personality
from src.data.buildings_data import BUILDINGS_DATA, get_building


OTTOMAN_ID = "ottoman"

# Параметры осады и экономики AI (должны совпадать с game_state при необходимости)
SIEGE_ADJACENCY_DISTANCE = 720
SIEGE_TURNS_CAPITULATION = 3
AI_STARTING_GOLD = 120
HIRE_COST_PER_TROOP = 5
GOLD_PER_FORTRESS_PER_TURN = 15
UPKEEP_PER_TROOP = 1

# Очередь построек AI (стены, рынок, казармы, мечеть, алтарь, катапульты, стены II)
AI_BUILD_ORDER = ["walls_1", "market", "barracks", "mosque", "altar", "catapult_workshop", "walls_2"]


def _get_faction_owned(game_state, faction_id: str) -> set[str]:
    """Множество id крепостей, принадлежащих данной фракции."""
    return {fid for fid, o in game_state.fortress_owners.items() if o == faction_id}


def _get_faction_garrison(game_state, faction_id: str, fortress_id: str) -> int:
    """Число войск в гарнизоне крепости у данной фракции (из ai_state или базовый гарнизон)."""
    ai = game_state.ai_state.get(faction_id, {})
    g = ai.get("garrisons", {})
    if fortress_id in g:
        return g[fortress_id]
    f = get_fortress_by_id(fortress_id)
    return f.base_garrison if f else 50


def _get_ai_buildings(game_state, faction_id: str) -> dict:
    ai = game_state.ai_state.get(faction_id, {})
    return ai.get("fortress_buildings", {})


def _get_ai_build_progress(game_state, faction_id: str) -> dict:
    ai = game_state.ai_state.get(faction_id, {})
    return ai.get("fortress_build_progress", {})


def _distance(fid1: str, fid2: str) -> float:
    f1, f2 = get_fortress_by_id(fid1), get_fortress_by_id(fid2)
    if not f1 or not f2:
        return float("inf")
    return ((f1.x - f2.x) ** 2 + (f1.y - f2.y) ** 2) ** 0.5


def _get_adjacent_faction_fortresses(game_state, faction_id: str, target_id: str) -> list[str]:
    owned = _get_faction_owned(game_state, faction_id)
    return [fid for fid in owned if _distance(fid, target_id) <= SIEGE_ADJACENCY_DISTANCE]


def _ai_capture_fortress(game_state, attacker_faction: str, fortress_id: str, garrison: int) -> None:
    prev_owner = game_state.fortress_owners.get(fortress_id)
    if prev_owner == attacker_faction:
        return
    game_state.fortress_owners[fortress_id] = attacker_faction
    ai = game_state.ai_state.setdefault(attacker_faction, {})
    g = ai.get("garrisons", {})
    g[fortress_id] = garrison
    ai["garrisons"] = g
    if prev_owner and prev_owner in AI_FACTION_IDS:
        prev_ai = game_state.ai_state.get(prev_owner, {})
        pg = prev_ai.get("garrisons", {})
        pg.pop(fortress_id, None)
        prev_ai["garrisons"] = pg


def _get_enemy_fortresses_smart(game_state, faction_id: str) -> list[tuple[str, str, float, int]]:
    """
    Список вражеских крепостей для данной фракции: (fortress_id, owner, distance_to_capital, defender_count).
    Учитывает отношения: при peace/nap/alliance не включает крепости игрока.
    Сортировка: сначала слабые и близкие цели.
    """
    rel = game_state.get_relation_with(faction_id)
    attack_ottoman = rel not in ("peace", "nap", "alliance")
    owned = _get_faction_owned(game_state, faction_id)
    capital = game_state.ai_state.get(faction_id, {}).get("capital") or (list(owned)[0] if owned else None)
    enemies = []
    for fid, owner in game_state.fortress_owners.items():
        if owner == faction_id:
            continue
        if owner == "ottoman" and not attack_ottoman:
            continue
        if owner not in AI_FACTION_IDS and owner != "ottoman":
            continue
        adjacent = _get_adjacent_faction_fortresses(game_state, faction_id, fid)
        if not adjacent:
            continue
        defender = game_state._get_garrison(fid)
        dist = _distance(capital, fid) if capital else 500
        enemies.append((fid, owner, dist, defender))
    enemies.sort(key=lambda x: (x[3], x[2]))
    return enemies


def _maybe_propose_trade(game_state, faction_id: str) -> bool:
    personality = get_personality(faction_id)
    rel = game_state.get_relation_with(faction_id)
    if rel not in ("peace", "nap", "alliance"):
        return False
    if faction_id in game_state.trade_partners:
        return False
    chance = 0.08 if personality == "trade" else (0.04 if personality == "peaceful" else 0.02)
    if random.random() < chance:
        game_state.trade_proposals_pending.append((faction_id,))
        return True
    return False


def _maybe_propose_peace(game_state, faction_id: str) -> bool:
    personality = get_personality(faction_id)
    if personality == "aggressive":
        return False
    rel = game_state.get_relation_with(faction_id)
    if rel != "war":
        return False
    ottoman_forts = len(game_state.owned_fortresses)
    faction_forts = len(_get_faction_owned(game_state, faction_id))
    if ottoman_forts >= faction_forts + 3 and random.random() < 0.15:
        game_state.ai_diplomacy_proposals.append((faction_id, "peace"))
        return True
    return False


def _maybe_propose_tribute(game_state, faction_id: str) -> bool:
    rel = game_state.get_relation_with(faction_id)
    if rel != "war":
        return False
    ottoman_forts = len(game_state.owned_fortresses)
    faction_forts = len(_get_faction_owned(game_state, faction_id))
    if ottoman_forts >= 12 and faction_forts <= 3 and random.random() < 0.1:
        game_state.ai_diplomacy_proposals.append((faction_id, "tribute"))
        return True
    return False


def _ai_build(game_state, faction_id: str, owned: set, gold: int) -> tuple[int, bool]:
    ai = game_state.ai_state.get(faction_id, {})
    buildings = {}
    for k, v in ai.get("fortress_buildings", {}).items():
        buildings[k] = set(v) if isinstance(v, (list, set)) else set()
    progress = dict(ai.get("fortress_build_progress", {}))
    for fid in list(owned):
        if fid in progress:
            continue
        built = buildings.get(fid, set())
        for bid in AI_BUILD_ORDER[:5]:
            if bid in built:
                continue
            b = get_building(bid)
            if not b or b.cost > gold:
                continue
            gold -= b.cost
            progress[fid] = (bid, b.turns_to_build)
            ai["fortress_build_progress"] = progress
            ai["fortress_buildings"] = buildings
            return gold, True
    return gold, False


def _ai_process_build_progress(game_state, faction_id: str) -> None:
    ai = game_state.ai_state.get(faction_id, {})
    progress = dict(ai.get("fortress_build_progress", {}))
    buildings = {}
    for k, v in ai.get("fortress_buildings", {}).items():
        buildings[k] = set(v) if isinstance(v, (list, set)) else set()
    for fid in list(progress.keys()):
        bid, left = progress[fid]
        left -= 1
        if left <= 0:
            del progress[fid]
            if fid not in buildings:
                buildings[fid] = set()
            buildings[fid].add(bid)
        else:
            progress[fid] = (bid, left)
    ai["fortress_build_progress"] = progress
    ai["fortress_buildings"] = buildings


def process_faction_turn(game_state, faction_id: str) -> list[str]:
    messages = []
    owned = _get_faction_owned(game_state, faction_id)
    if not owned:
        return messages

    personality = get_personality(faction_id)
    ai = game_state.ai_state.setdefault(faction_id, {})
    gold = ai.get("gold", AI_STARTING_GOLD)
    garrisons = dict(ai.get("garrisons", {}))
    field_army = ai.get("field_army", 0)
    sieges = dict(ai.get("sieges", {}))

    _ai_process_build_progress(game_state, faction_id)

    gold += len(owned) * GOLD_PER_FORTRESS_PER_TURN
    troops = sum(garrisons.get(fid, _get_faction_garrison(game_state, faction_id, fid)) for fid in owned) + field_army
    gold -= troops * UPKEEP_PER_TROOP
    gold = max(0, gold)

    ai["gold"] = gold
    ai["garrisons"] = garrisons
    ai["field_army"] = field_army
    ai["sieges"] = sieges

    for fid in list(sieges.keys()):
        s = sieges[fid]
        s["turns_remaining"] = s.get("turns_remaining", SIEGE_TURNS_CAPITULATION) - 1
        if s["turns_remaining"] <= 0:
            del sieges[fid]
            surv = max(50, int(s.get("attacker_troops", 100) * 0.9))
            _ai_capture_fortress(game_state, faction_id, fid, surv)
            f = get_fortress_by_id(fid)
            messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} захватила {f.name_ru if f else fid}")

    if personality in ("defensive", "trade") and gold >= 100:
        gold, built = _ai_build(game_state, faction_id, owned, gold)
        if built:
            ai["gold"] = gold

    hire_chance = 0.6 if personality == "aggressive" else (0.5 if personality == "defensive" else 0.35)
    if gold >= HIRE_COST_PER_TROOP * 20 and random.random() < hire_chance:
        forts = [fid for fid in owned if _get_faction_garrison(game_state, faction_id, fid) < 180]
        if forts:
            weak = min(forts, key=lambda f: _get_faction_garrison(game_state, faction_id, f))
            count = min(35, gold // HIRE_COST_PER_TROOP)
            cost = count * HIRE_COST_PER_TROOP
            if cost <= gold:
                gold -= cost
                cur = garrisons.get(weak, get_fortress_by_id(weak).base_garrison if get_fortress_by_id(weak) else 50)
                garrisons[weak] = cur + count
                ai["gold"] = gold
                ai["garrisons"] = garrisons

    capital = ai.get("capital") or (list(owned)[0] if owned else None)
    cap_garrison = garrisons.get(capital, get_fortress_by_id(capital).base_garrison if capital and get_fortress_by_id(capital) else 50)
    gather_chance = 0.55 if personality == "aggressive" else 0.4
    if cap_garrison > 70 and field_army < 120 and random.random() < gather_chance:
        transfer = min(80, cap_garrison - 40)
        garrisons[capital] = cap_garrison - transfer
        field_army += transfer
        ai["field_army"] = field_army
        ai["garrisons"] = garrisons

    if _maybe_propose_trade(game_state, faction_id):
        messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} предлагает торговать")
    if _maybe_propose_peace(game_state, faction_id):
        messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} предлагает мир")
    if _maybe_propose_tribute(game_state, faction_id):
        messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} согласна платить дань")

    attack_chance = 0.75 if personality == "aggressive" else (0.5 if personality == "defensive" else 0.35)
    enemy_forts = _get_enemy_fortresses_smart(game_state, faction_id)
    ottoman_troops = sum(game_state._get_garrison(f) for f in game_state.owned_fortresses) + game_state.field_army
    faction_troops = sum(garrisons.get(f, _get_faction_garrison(game_state, faction_id, f)) for f in owned) + field_army

    if field_army > 45 and not sieges and enemy_forts and random.random() < attack_chance:
        for target_id, owner, dist, defender in enemy_forts[:6]:
            if field_army <= defender + 20:
                continue
            if owner == "ottoman" and faction_troops < ottoman_troops * 0.6:
                continue
            troop_count = min(field_army, defender + 60)
            field_army -= troop_count
            sieges[target_id] = {
                "target_fortress_id": target_id,
                "attacker_troops": troop_count,
                "turns_remaining": SIEGE_TURNS_CAPITULATION,
            }
            ai["field_army"] = field_army
            ai["sieges"] = sieges
            f = get_fortress_by_id(target_id)
            messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} осадила {f.name_ru if f else target_id}")
            break

    return messages


def process_all_ai_turns(game_state) -> list[str]:
    random.shuffle(AI_FACTION_IDS)
    msgs = []
    for fid in AI_FACTION_IDS:
        msgs.extend(process_faction_turn(game_state, fid))
    return msgs
