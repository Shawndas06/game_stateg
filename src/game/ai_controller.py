"""
Контроллер ИИ для других государств (Византия).
Найм войск, осада, штурм. Возможность подключения полноценной AI-модели в будущем.
"""

import random
from typing import Optional

from src.data.fortresses import FORTESSES_DATA, get_fortress_by_id


BYZANTINE_ID = "byzantine"
OTTOMAN_ID = "ottoman"

SIEGE_ADJACENCY_DISTANCE = 450
SIEGE_TURNS_CAPITULATION = 3
HIRE_COST_PER_TROOP = 5
GOLD_PER_FORTRESS_PER_TURN = 15
UPKEEP_PER_TROOP = 1
ASSAULT_RATIO = 1.5
BYZANTINE_STARTING_GOLD = 200


def get_byzantine_owned(game_state) -> set[str]:
    """Крепости, принадлежащие Византии."""
    return getattr(game_state, "byzantine_owned", set())


def _get_byzantine_garrison(game_state, fortress_id: str) -> int:
    """Гарнизон византийской крепости."""
    byz_garrisons = getattr(game_state, "byzantine_fortress_garrisons", {})
    if fortress_id in byz_garrisons:
        return byz_garrisons[fortress_id]
    f = get_fortress_by_id(fortress_id)
    return f.base_garrison if f else 50


def _distance(game_state, fid1: str, fid2: str) -> float:
    f1 = get_fortress_by_id(fid1)
    f2 = get_fortress_by_id(fid2)
    if not f1 or not f2:
        return float("inf")
    return ((f1.x - f2.x) ** 2 + (f1.y - f2.y) ** 2) ** 0.5


def _get_adjacent_byzantine_fortresses(game_state, target_id: str) -> list[str]:
    """Византийские крепости рядом с целью."""
    byz_owned = get_byzantine_owned(game_state)
    return [
        fid for fid in byz_owned
        if _distance(game_state, fid, target_id) <= SIEGE_ADJACENCY_DISTANCE
    ]


def process_byzantine_turn(game_state) -> list[str]:
    """
    Ход Византии: доход, содержание, найм, осада/штурм османских крепостей.
    Возвращает список сообщений о действиях.
    """
    messages = []
    if getattr(game_state, "byzantine_relation", "war") != "war":
        return messages

    byz_owned = get_byzantine_owned(game_state)
    if not byz_owned:
        return messages

    byz_gold = getattr(game_state, "byzantine_gold", BYZANTINE_STARTING_GOLD)
    byz_garrisons = getattr(game_state, "byzantine_fortress_garrisons", {})
    byz_field_army = getattr(game_state, "byzantine_field_army", 0)
    byz_sieges = getattr(game_state, "byzantine_sieges", {})

    # Доход
    income = len(byz_owned) * GOLD_PER_FORTRESS_PER_TURN
    byz_gold += income

    # Содержание войск
    troops = sum(byz_garrisons.get(fid, get_fortress_by_id(fid).base_garrison if get_fortress_by_id(fid) else 50)
                 for fid in byz_owned) + byz_field_army
    upkeep = troops * UPKEEP_PER_TROOP
    byz_gold -= upkeep
    if byz_gold < 0:
        byz_gold = 0

    game_state.byzantine_gold = byz_gold
    game_state.byzantine_fortress_garrisons = byz_garrisons
    game_state.byzantine_field_army = byz_field_army
    game_state.byzantine_sieges = byz_sieges

    # Обработка осад
    for fid in list(byz_sieges.keys()):
        siege = byz_sieges[fid]
        siege["turns_remaining"] -= 1
        if siege["turns_remaining"] <= 0:
            del byz_sieges[fid]
            game_state.owned_fortresses.discard(fid)
            game_state.byzantine_owned.add(fid)
            survivors = max(50, int(siege["attacker_troops"] * 0.9))
            byz_garrisons[fid] = survivors
            messages.append(f"Византия захватила {fid} (капитуляция)")

    # Простой ИИ: нанять в одной крепости, если есть золото; начать осаду, если возможно
    if byz_gold >= HIRE_COST_PER_TROOP * 10:
        hire_forts = [fid for fid in byz_owned if _get_byzantine_garrison(game_state, fid) < 200]
        if hire_forts and random.random() < 0.4:
            fid = random.choice(hire_forts[:3])
            count = min(25, byz_gold // HIRE_COST_PER_TROOP)
            cost = count * HIRE_COST_PER_TROOP
            if cost <= byz_gold:
                byz_gold -= cost
                current = byz_garrisons.get(fid, get_fortress_by_id(fid).base_garrison if get_fortress_by_id(fid) else 50)
                byz_garrisons[fid] = current + count
                game_state.byzantine_gold = byz_gold
                game_state.byzantine_fortress_garrisons = byz_garrisons
                messages.append(f"Византия наняла {count} воинов в {fid}")

    # Собрать армию из столицы (Константинополь или первая византийская)
    byz_capital = getattr(game_state, "byzantine_capital_id", "constantinople")
    if byz_capital not in byz_owned:
        byz_capital = next((fid for fid in ["constantinople", "nicaea", "bursa", "nicomedia"] if fid in byz_owned),
                           list(byz_owned)[0] if byz_owned else None)
    if not byz_capital:
        return messages
    f_cap = get_fortress_by_id(byz_capital)
    garrison_at_capital = byz_garrisons.get(byz_capital, f_cap.base_garrison if f_cap else 50)
    if garrison_at_capital > 100 and byz_field_army < 50 and random.random() < 0.3:
        transfer = min(75, garrison_at_capital - 50)
        byz_garrisons[byz_capital] = garrison_at_capital - transfer
        byz_field_army += transfer
        game_state.byzantine_field_army = byz_field_army
        game_state.byzantine_fortress_garrisons = byz_garrisons

    # Найти османскую крепость для атаки
    ottoman_forts = list(game_state.owned_fortresses)
    if byz_field_army > 80 and ottoman_forts and not byz_sieges and random.random() < 0.35:
        for target_id in random.sample(ottoman_forts, min(5, len(ottoman_forts))):
            defender = game_state._get_garrison(target_id)
            if byz_field_army > defender and _get_adjacent_byzantine_fortresses(game_state, target_id):
                troop_count = min(byz_field_army, defender + 50)
                byz_field_army -= troop_count
                byz_sieges[target_id] = {
                    "target_fortress_id": target_id,
                    "attacker_troops": troop_count,
                    "turns_remaining": SIEGE_TURNS_CAPITULATION,
                }
                game_state.byzantine_field_army = byz_field_army
                game_state.byzantine_sieges = byz_sieges
                f = get_fortress_by_id(target_id)
                messages.append(f"Византия осадила {f.name_ru if f else target_id}")
                break

    return messages
