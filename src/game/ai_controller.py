"""
AI для всех государств — умный, атакует всех врагов (игрок + другие AI).
Предлагает торговлю. Захватывает крепости.
"""

import random
from src.data.fortresses import FORTESSES_DATA, get_fortress_by_id
from src.data.factions_data import AI_FACTION_IDS, FACTION_NAMES_RU


OTTOMAN_ID = "ottoman"

SIEGE_ADJACENCY_DISTANCE = 720
SIEGE_TURNS_CAPITULATION = 3
AI_STARTING_GOLD = 120
HIRE_COST_PER_TROOP = 5
GOLD_PER_FORTRESS_PER_TURN = 15
UPKEEP_PER_TROOP = 1


def _get_faction_owned(game_state, faction_id: str) -> set[str]:
    return {fid for fid, o in game_state.fortress_owners.items() if o == faction_id}


def _get_faction_garrison(game_state, faction_id: str, fortress_id: str) -> int:
    ai = game_state.ai_state.get(faction_id, {})
    g = ai.get("garrisons", {})
    if fortress_id in g:
        return g[fortress_id]
    f = get_fortress_by_id(fortress_id)
    return f.base_garrison if f else 50


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


def _get_enemy_fortresses(game_state, faction_id: str) -> list[tuple[str, str]]:
    """Вражеские крепости: (fortress_id, owner). Османов не атакуем при peace/nap/alliance."""
    rel = game_state.get_relation_with(faction_id)
    attack_ottoman = rel not in ("peace", "nap", "alliance")
    enemies = []
    for fid, owner in game_state.fortress_owners.items():
        if owner == faction_id:
            continue
        if owner == "ottoman" and attack_ottoman:
            enemies.append((fid, owner))
        elif owner in AI_FACTION_IDS:
            enemies.append((fid, owner))
    return enemies


def _maybe_propose_trade(game_state, faction_id: str) -> bool:
    """AI редко предлагает торг — в основном атакует и развивается."""
    rel = game_state.get_relation_with(faction_id)
    if rel not in ("peace", "nap", "alliance"):
        return False
    if faction_id in game_state.trade_partners:
        return False
    if random.random() < 0.03:
        game_state.trade_proposals_pending.append((faction_id,))
        return True
    return False


def process_faction_turn(game_state, faction_id: str) -> list[str]:
    messages = []
    owned = _get_faction_owned(game_state, faction_id)
    if not owned:
        return messages

    ai = game_state.ai_state.setdefault(faction_id, {})
    gold = ai.get("gold", AI_STARTING_GOLD)
    garrisons = dict(ai.get("garrisons", {}))
    field_army = ai.get("field_army", 0)
    sieges = dict(ai.get("sieges", {}))

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

    if gold >= HIRE_COST_PER_TROOP * 15 and random.random() < 0.5:
        forts = [fid for fid in owned if _get_faction_garrison(game_state, faction_id, fid) < 200]
        if forts:
            fid = random.choice(forts[:5])
            count = min(25, gold // HIRE_COST_PER_TROOP)
            cost = count * HIRE_COST_PER_TROOP
            if cost <= gold:
                gold -= cost
                cur = garrisons.get(fid, get_fortress_by_id(fid).base_garrison if get_fortress_by_id(fid) else 50)
                garrisons[fid] = cur + count
                ai["gold"] = gold
                ai["garrisons"] = garrisons

    capital = ai.get("capital") or (list(owned)[0] if owned else None)
    cap_garrison = garrisons.get(capital, get_fortress_by_id(capital).base_garrison if capital and get_fortress_by_id(capital) else 50)
    if cap_garrison > 80 and field_army < 100 and random.random() < 0.5:
        transfer = min(70, cap_garrison - 50)
        garrisons[capital] = cap_garrison - transfer
        field_army += transfer
        ai["field_army"] = field_army
        ai["garrisons"] = garrisons

    if _maybe_propose_trade(game_state, faction_id):
        messages.append(f"{FACTION_NAMES_RU.get(faction_id, faction_id)} предлагает торговать")

    enemy_forts = _get_enemy_fortresses(game_state, faction_id)
    if field_army > 50 and not sieges and enemy_forts and random.random() < 0.65:
        random.shuffle(enemy_forts)
        for target_id, owner in enemy_forts[:8]:
            defender = game_state._get_garrison(target_id)
            if field_army > defender and _get_adjacent_faction_fortresses(game_state, faction_id, target_id):
                troop_count = min(field_army, defender + 50)
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
    msgs = []
    for fid in AI_FACTION_IDS:
        msgs.extend(process_faction_turn(game_state, fid))
    return msgs
