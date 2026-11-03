from __future__ import annotations

from collections import deque
from copy import deepcopy
import hashlib
import math
import random
from typing import Any
from functools import lru_cache

from campaign.content import ADJACENCY, BUILDINGS, CAPITALS, DYNASTY, EVENTS, FACTIONS, FORTRESS_PROJECT, INITIAL_SEAFARERS, PLACES, PLACE_INDEX, PLACE_KINDS, REGIONS, REFORMS, ROADS, ROUTE_TYPES, TECHNOLOGIES, TROOPS
from campaign.models import Army, Faction, Province, Siege, State


class RuleError(ValueError):
    """Expected rejection; the command must leave the entire state unchanged."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuleError(message)


def neighbours(place: str) -> list[str]:
    return ADJACENCY.get(place, [])


def route_kind(a: str, b: str) -> str:
    return ROUTE_TYPES.get(tuple(sorted((a, b))), 'land')


def can_use_route(s: State, actor: str, a: str, b: str, supply: bool = False) -> bool:
    kind = route_kind(a, b)
    tech = s.factions[actor].technologies
    if kind == 'land': return True
    if kind == 'ferry': return 'ferries' in tech
    return 'convoys' in tech if supply else 'ferries' in tech


def administrative_weight(pid: str) -> float:
    return .25 if PLACE_KINDS[pid] == 'village' else 1


def faction_capital(s: State, actor: str) -> str | None:
    home = s.capital if actor == 'ottoman' else CAPITALS[actor]
    if s.provinces[home].controller == actor and s.provinces[home].owner == actor: return home
    return next((p.id for p in sorted(controlled(s, actor), key=lambda p: (-p.prosperity, p.id)) if p.owner == actor), None)


def relation_key(a: str, b: str) -> str:
    return ":".join(sorted((a, b)))


def relation(s: State, a: str, b: str) -> dict:
    if a == b:
        return {"status": "peace", "trade": False}
    return s.treaties[relation_key(a, b)]


def rng(s: State, context: str) -> random.Random:
    digest = hashlib.sha256(f"{s.seed}:{s.turn}:{context}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def note(s: State, text: str, kind: str = "world") -> None:
    s.log.append({"turn": s.turn, "text": text, "kind": kind})
    s.log[:] = s.log[-100:]


def new_campaign(seed: int) -> State:
    s = State(seed=seed)
    for fid in FACTIONS:
        s.factions[fid] = Faction(fid, technologies=["ferries", "convoys"] if fid in INITIAL_SEAFARERS else [])
    for i, a in enumerate(FACTIONS):
        for b in list(FACTIONS)[i + 1:]:
            s.treaties[relation_key(a, b)] = {"status": "war" if {a, b} == {"ottoman", "byzantine"} else "peace", "trade": False, "envoys": {}}
    for pid, _, _, _, owner, guards, walls, _ in PLACES:
        s.provinces[pid] = Province(pid, owner, owner, {"militia": guards}, walls, fortress_level=int(walls > 0), max_walls=walls)
    s.armies = {
        "ottoman-1": Army("ottoman-1", "ottoman", "sogut", {"militia": 60, "archers": 20}),
        "byzantine-1": Army("byzantine-1", "byzantine", "nicomedia", {"militia": 35, "archers": 15}),
        "germiyan-1": Army("germiyan-1", "germiyan", "kutahya", {"militia": 30, "cavalry": 10}),
    }
    for fid, f in s.factions.items():
        if fid != 'ottoman': f.administrative_base = max(3, math.ceil(sum(administrative_weight(p.id) for p in controlled(s, fid))))
        if f'{fid}-1' not in s.armies:
            s.armies[f'{fid}-1'] = Army(f'{fid}-1', fid, CAPITALS[fid], {'militia': 30, 'archers': 10})
    note(s, "Весна 1299 года. Сёгют и Караджахисар под вашей властью. Совет ждёт первого решения.")
    validate(s)
    return s


def power(s: State, troops: dict[str, int], faction: str) -> float:
    tech = s.factions[faction].technologies
    result = sum(count * TROOPS[tid]["power"] * (1.15 if tid != "cavalry" and "drill" in tech else 1) for tid, count in troops.items())
    if "combined_arms" in tech and sum(count > 0 for count in troops.values()) > 1:
        result *= 1.1
    return result


def army_power(s: State, a: Army) -> float:
    return power(s, a.troops, a.faction) * max(.3, a.supply / 100) * max(.3, a.morale / 100)


def cleanup(s: State) -> None:
    for pid, siege in list(s.sieges.items()):
        a = s.armies[siege.army_id]
        if not a.size or a.location != pid or s.provinces[pid].controller == a.faction or relation(s, a.faction, s.provinces[pid].controller)['status'] != 'war':
            del s.sieges[pid]
    for a in s.armies.values():
        if not a.size:
            a.order = None
            homes = [p for p in controlled(s, a.faction) if p.owner == a.faction and p.id not in s.sieges]
            if homes and s.provinces[a.location].controller != a.faction:
                a.location = min(homes, key=lambda p: (_distance(a.location, p.id), p.id)).id


def remove_troops(troops: dict[str, int], count: int) -> dict[str, int]:
    """Proportional losses, exact integer total; never turn survivors into other units."""
    total = sum(troops.values())
    count = max(0, min(count, total))
    losses = {tid: n * count // total if total else 0 for tid, n in troops.items()}
    remaining = count - sum(losses.values())
    for tid in sorted(troops, key=lambda t: (-(troops[t] * count % max(total, 1)), t)):
        if remaining and losses[tid] < troops[tid]:
            losses[tid] += 1
            remaining -= 1
    for tid, amount in losses.items():
        troops[tid] -= amount
    return {tid: amount for tid, amount in losses.items() if amount}


def controlled(s: State, actor: str) -> list[Province]:
    return [p for p in s.provinces.values() if p.controller == actor]


def supplied(s: State, army: Army) -> bool:
    # A chain of controlled corridors is required; nearby pixels confer no supply.
    capital = faction_capital(s, army.faction)
    starts = [capital] if capital else []
    seen = set(starts)
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        if current == army.location or (army.location in neighbours(current) and can_use_route(s, army.faction, current, army.location, supply=True)):
            return True
        for dest in neighbours(current):
            if dest not in seen and s.provinces[dest].controller == army.faction and can_use_route(s, army.faction, current, dest, supply=True):
                seen.add(dest)
                queue.append(dest)
    return False


def budget(s: State, actor: str, for_turn: int | None = None) -> dict[str, int | float]:
    f = s.factions[actor]
    places = controlled(s, actor)
    capacity = f.administrative_base + int("scribes" in f.technologies) + int(f.groups["administration"] >= 80) - int(f.groups["administration"] < 30) + (12 if 'provincial_offices' in f.reforms else 0)
    used_capacity = sum(administrative_weight(p.id) for p in places)
    overload = max(0, used_capacity - capacity)
    income = food = 0
    for p in places:
        tax = (8 if PLACE_KINDS[p.id] == 'village' else 22) + (8 if "market" in p.buildings else 0)
        tax += 4 if "land_register" in f.technologies else 0
        tax += 6 if "tax_register" in f.reforms else 0
        factor = max(.15, p.loyalty / 100) * p.prosperity / 70
        factor *= .55 if p.owner != actor else 1
        income += int(tax * factor / (1 + overload * .12))
        food += (18 if PLACE_KINDS[p.id] == 'village' else 30) + (12 if "granary" in p.buildings else 0) + (10 if "stores" in f.technologies else 0) + (15 if "irrigation" in f.technologies else 0)
    troops = sum(sum(p.garrison.values()) for p in places)
    weighted = sum(n * TROOPS[t]["upkeep"] for p in places for t, n in p.garrison.items())
    for a in s.armies.values():
        if a.faction == actor:
            troops += a.size
            weighted += sum(n * TROOPS[t]["upkeep"] for t, n in a.troops.items())
    upkeep = math.ceil(weighted / 12)
    trade = sum(12 for k, treaty in s.treaties.items() if actor in k.split(":") and treaty["status"] == "peace" and treaty["trade"] and f.groups["merchants"] >= 40 and controlled(s, next(x for x in k.split(":") if x != actor)))
    port = any(PLACE_INDEX[p.id][7] for p in places)
    income += 6 if port and "ferries" in f.technologies else 0
    privileges = (8 if actor == "ottoman" and s.flags.get("merchant_privileges") else 0) + (6 if actor == "ottoman" and s.flags.get("military_share") else 0)
    new_forts = sum('new_fortress' in p.buildings for p in places)
    expense = upkeep + math.ceil(used_capacity * 3) + privileges + new_forts * FORTRESS_PROJECT['upkeep'] + (8 if 'provincial_offices' in f.reforms else 0)
    forecast_turn = s.turn + 1 if for_turn is None else for_turn
    return {"income": income, "trade": trade, "expense": expense, "net": income + trade - expense, "food_income": int(food * (.65 if forecast_turn % 4 == 3 else 1)), "food_expense": math.ceil(troops / 5), "troops": troops, "capacity": capacity, "used_capacity": used_capacity}


def spend(f: Faction, gold: int) -> None:
    require(f.gold >= gold, f"Нужно {gold} золота. В казне {f.gold}.")
    f.gold -= gold


def owned_place(s: State, actor: str, pid: str) -> Province:
    require(pid in s.provinces, "Неизвестное владение")
    p = s.provinces[pid]
    require(p.controller == actor, "Владение не под вашим контролем")
    return p


def own_army(s: State, actor: str, aid: str) -> Army:
    require(aid in s.armies and s.armies[aid].faction == actor, "Армия не под вашим командованием")
    return s.armies[aid]


def integer(payload: dict, key: str, maximum: int = 500) -> int:
    n = payload.get(key)
    require(type(n) is int and 0 < n <= maximum, "Укажите допустимое целое количество")
    return n


def apply_command(state: State, kind: str, payload: dict, actor: str = "ottoman") -> State:
    """Copy-on-write: rejected commands cannot partially apply effects."""
    require(actor in state.factions, "Неизвестное государство")
    require(state.ending is None, "Глава завершена. Начните новую кампанию.")
    require(not state.pending_event or kind == "choose" or actor != "ottoman", "Сначала ответьте на решение совета")
    s = deepcopy(state)
    _execute(s, kind, payload, actor)
    s.revision += 1
    _schedule_event(s)
    validate(s)
    return s


def _execute(s: State, kind: str, data: dict, actor: str) -> None:
    f = s.factions[actor]
    if kind == "choose":
        require(actor == "ottoman" and s.pending_event in EVENTS, "Нет решения совета")
        _choose(s, str(data.get("choice", "")))
    elif kind == "recruit":
        p = owned_place(s, actor, str(data.get("province", "")))
        require(p.owner == actor, "Сначала заключите мир и закрепите владение")
        require(p.id not in s.sieges, "Осада прервала набор и снабжение гарнизона")
        count = integer(data, "count", 40)
        tid = str(data.get("troop", ""))
        require(tid in TROOPS, "Неизвестный тип войск")
        require(f.manpower >= count, "Недостаточно людского резерва")
        spend(f, count * TROOPS[tid]["cost"])
        f.manpower -= count
        p.garrison[tid] = p.garrison.get(tid, 0) + count
        p.prosperity = max(20, p.prosperity - count // 10)
        note(s, f"{FACTIONS[actor]}: набрано {count} воинов.")
    elif kind == "mobilize":
        a = own_army(s, actor, str(data.get("army", "")))
        p = owned_place(s, actor, a.location)
        require(a.location not in s.sieges, "Нельзя пополнять армию в осаде")
        tid = str(data.get("troop", "")); count = integer(data, "count")
        require(tid in TROOPS and p.garrison.get(tid, 0) >= count and sum(p.garrison.values()) - count >= 10, "В гарнизоне должны остаться хотя бы 10 воинов")
        p.garrison[tid] -= count
        a.troops[tid] = a.troops.get(tid, 0) + count
    elif kind in ("move", "retreat"):
        a = own_army(s, actor, str(data.get("army", "")))
        target = str(data.get("target", ""))
        require(target in neighbours(a.location), "Выберите соседнее владение по дороге")
        require(can_use_route(s, actor, a.location, target), "Для переправы и морского перехода нужно освоить организацию переправ")
        dest = s.provinces[target]
        active = next((x for x in s.sieges.values() if x.army_id == a.id), None)
        if active:
            require(kind == "retreat" and dest.controller == actor, "Из осады можно отступить только в своё владение")
        require(a.size > 0, "В армии нет воинов")
        require(dest.controller == actor or relation(s, actor, dest.controller)["status"] == "war", "Нет права входа. Сначала объявите войну.")
        require(dest.controller == actor or not any(x.province == target and s.armies[x.army_id].faction != actor for x in s.sieges.values()), "У цели уже действует чужая осада")
        fee = {'land': 0, 'ferry': 10, 'sea': 20}[route_kind(a.location, target)]
        require(f.gold >= fee, f"Для перехода нужно {fee} золота")
        a.order = {"kind": kind, "target": target}
    elif kind == "siege_mode":
        a = own_army(s, actor, str(data.get("army", "")))
        siege = s.sieges.get(a.location)
        require(siege is not None and siege.army_id == a.id, "Армия не ведёт осаду")
        mode = data.get("mode")
        require(mode in ("blockade", "works", "assault", "negotiate"), "Неизвестный план осады")
        if mode == "negotiate":
            require(siege.supplies <= 25 or siege.morale <= 35, "Защитники пока рассчитывают удержать город")
            spend(f, 50)
        siege.mode = str(mode)
    elif kind == "build":
        p = owned_place(s, actor, str(data.get("province", "")))
        bid = str(data.get("building", ""))
        require(p.owner == actor and p.id not in s.sieges, "Строительство доступно в закреплённом безопасном владении")
        require(bid in BUILDINGS, "Неизвестная постройка")
        require(p.construction is None and bid not in p.buildings, "Постройка уже есть или очередь занята")
        b = BUILDINGS[bid]
        require(bid != 'walls' or p.fortress_level > 0, "Сначала возведите новую крепость; возможность открывается при Мураде I")
        require(not b.get("requires") or b["requires"] in f.technologies, "Сначала освойте нужное знание")
        spend(f, b["cost"])
        p.construction = {"building": bid, "left": b["turns"]}
    elif kind == 'found_fortress':
        p = owned_place(s, actor, str(data.get('province', '')))
        require(actor == 'ottoman' and s.ruler_rank >= 3, "Возведение новых крепостей открывается после вступления Мурада I")
        require(p.owner == actor and p.id not in s.sieges, "Нужен закреплённый город или поселение без осады")
        require(p.fortress_level == 0, "В этом месте уже есть крепость")
        require(p.construction is None, "Очередь строительства занята")
        require(f.manpower >= FORTRESS_PROJECT['workers'], "Нужны 20 свободных людей для строительных работ")
        spend(f, FORTRESS_PROJECT['cost']); f.manpower -= FORTRESS_PROJECT['workers']
        p.construction = {'building': 'new_fortress', 'left': FORTRESS_PROJECT['turns']}
        note(s, f"{place_name(p.id)}: заложена новая крепость, завершение через 4 сезона.", 'building')
    elif kind == 'repair_walls':
        p = owned_place(s, actor, str(data.get('province', '')))
        require(p.owner == actor and p.id not in s.sieges and p.construction is None, "Нужно безопасное владение со свободной строительной очередью")
        require(p.fortress_level > 0 and p.walls < p.max_walls, "Стены не нуждаются в ремонте")
        spend(f, (p.max_walls - p.walls) * 2)
        p.construction = {'building': 'repair_walls', 'left': 2}
    elif kind == "equip":
        a = own_army(s, actor, str(data.get("army", "")))
        p = owned_place(s, actor, a.location)
        require("workshop" in p.buildings and a.location not in s.sieges, "Нужна безопасная осадная мастерская в месте армии")
        require(a.engines < 3, "Армия уже оснащена тремя орудиями")
        spend(f, 45); a.engines += 1
    elif kind == "research":
        tid = str(data.get("technology", ""))
        require(tid in TECHNOLOGIES and tid not in f.technologies, "Знание неизвестно или уже освоено")
        require(all(t in f.technologies for t in TECHNOLOGIES[tid]["requires"]), "Сначала освойте предшествующие знания")
        require(f.research is None, "Приостановите текущий приоритет перед сменой")
        f.research = {"id": tid, "progress": int(s.flags.get(f"research:{actor}:{tid}", 0))}
    elif kind == "pause_research":
        require(f.research is not None, "Нет активного исследования")
        s.flags[f"research:{actor}:{f.research['id']}"] = f.research["progress"]
        f.research = None
    elif kind == "reform":
        rid = str(data.get("reform", ""))
        require(rid in REFORMS and rid not in f.reforms, "Реформа неизвестна или уже принята")
        r = REFORMS[rid]
        require(not r.get("requires") or r["requires"] in f.technologies, "Недостаточно знаний для реформы")
        spend(f, r["cost"]); f.reforms.append(rid)
        if rid == "tolerance":
            f.groups["military"] -= 10
        elif rid == 'tax_register':
            for p in controlled(s, actor): p.loyalty = max(0, p.loyalty - 10)
    elif kind == "diplomacy":
        _diplomacy(s, actor, str(data.get("target", "")), str(data.get("proposal", "")))
    elif kind == "integrate":
        p = owned_place(s, actor, str(data.get("province", "")))
        require(p.owner == actor and p.loyalty < 100, "Сначала закрепите город мирным договором")
        spend(f, 25); p.loyalty = min(100, p.loyalty + 15); p.prosperity = min(100, p.prosperity + 5)
    elif kind == "end_turn":
        require(actor == "ottoman", "Только игрок завершает общий сезон")
        _next_turn(s)
    else:
        raise RuleError("Неизвестная команда")


def _diplomacy(s: State, actor: str, target: str, proposal: str) -> None:
    require(target in s.factions and target != actor, "Неизвестное государство")
    require(controlled(s, actor) and controlled(s, target), "Государство утратило все владения")
    treaty = relation(s, actor, target)
    require(proposal in ("war", "peace", "trade"), "Неизвестное предложение")
    require(treaty.get("envoys", {}).get(actor) != s.turn, "Посол уже действовал в этом сезоне")
    if proposal == "war":
        require(treaty["status"] != "war", "Война уже идёт")
        require(s.turn >= treaty.get("truce_until", 0), "Срок перемирия ещё не истёк")
        treaty.update(status="war", trade=False)
    elif proposal == "trade":
        require(treaty["status"] == "peace" and not treaty["trade"], "Нужен мир и отсутствие действующего торгового договора")
        require(s.factions[actor].groups["merchants"] >= 40, "Купцы не доверяют правителю: для торговли нужна поддержка хотя бы 40")
        spend(s.factions[actor], 20); treaty["trade"] = True
    else:
        require(treaty["status"] == "war", "Война не идёт")
        occupied = [p for p in s.provinces.values() if p.owner == target and p.controller == actor]
        require(occupied or len(controlled(s, actor)) >= len(controlled(s, target)), "Противник не готов уступить. Нужны военные результаты.")
        treaty.update(status="peace", trade=False, truce_until=s.turn + 4)
        for p in s.provinces.values():
            if {p.owner, p.controller} == {actor, target}: p.owner = p.controller
        for pid, siege in list(s.sieges.items()):
            if {s.armies[siege.army_id].faction, s.provinces[pid].controller} == {actor, target}:
                del s.sieges[pid]
        for a in s.armies.values():
            if a.faction in (actor, target):
                a.order = None
                if s.provinces[a.location].controller != a.faction:
                    homes = controlled(s, a.faction)
                    if homes: a.location = sorted(homes, key=lambda p: (_distance(a.location, p.id), p.id))[0].id
    treaty.setdefault("envoys", {})[actor] = s.turn
    note(s, f"{FACTIONS[actor]} / {FACTIONS[target]}: {dict(war='объявлена война', peace='заключён мир с признанием занятых владений', trade='торговый договор')[proposal]}", "diplomacy")


@lru_cache(maxsize=30000)
def _distance(a: str, b: str) -> int:
    queue = deque([(a, 0)]); seen = {a}
    while queue:
        current, distance = queue.popleft()
        if current == b: return distance
        for n in neighbours(current):
            if n not in seen: seen.add(n); queue.append((n, distance + 1))
    return 10000


def _occupy(s: State, siege: Siege) -> None:
    a = s.armies[siege.army_id]; p = s.provinces[siege.province]
    old = p.controller
    p.controller = a.faction
    # Defenders surrender. Occupying troops are explicitly detached from the army.
    p.garrison = {t: 0 for t in TROOPS}
    target = min(15, max(1, a.size // 5))
    for tid in sorted(a.troops):
        take = min(target, a.troops[tid]); a.troops[tid] -= take
        p.garrison[tid] += take; target -= take
    p.loyalty = 35
    if p.construction: p.construction = None  # interrupted work is not secretly finished by the old owner
    s.sieges.pop(p.id, None)
    a.order = None
    if old == "ottoman" and s.capital == p.id:
        homes = controlled(s, "ottoman")
        if homes: s.capital = sorted(homes, key=lambda home: home.id)[0].id
    s.factions[a.faction].legitimacy = min(100, s.factions[a.faction].legitimacy + 5)
    note(s, f"{place_name(p.id)}: {FACTIONS[a.faction]} установили военный контроль. Нужен мирный договор для закрепления.", "capture")
    if a.faction == "ottoman":
        s.flags.setdefault("first_capture_turn", s.turn)
        if p.id == "bursa": s.flags["bursa_captured"] = True
    if not controlled(s, old):
        for province in s.provinces.values():
            if province.owner == old: province.owner = province.controller
        note(s, f"{FACTIONS[old]} утратили все владения; занятые земли закреплены за державами, которые их удерживают.", 'diplomacy')
        for treaty_key, treaty in s.treaties.items():
            if old in treaty_key.split(":"): treaty.update(status="peace", trade=False)
        for pid, active in list(s.sieges.items()):
            if s.armies[active.army_id].faction == old: del s.sieges[pid]
        for army in s.armies.values():
            if army.faction == old:
                remove_troops(army.troops, army.size); army.order = None


def _assault(s: State, siege: Siege) -> None:
    a = s.armies[siege.army_id]; p = s.provinces[siege.province]
    attack = army_power(s, a)
    defense = power(s, p.garrison, p.controller) * (1 + p.walls / 50) * max(.35, siege.morale / 100)
    chance = max(.08, min(.92, attack / max(1, attack + defense)))
    success = rng(s, f"assault:{a.id}:{p.id}").random() < chance
    losses = math.ceil(a.size * (.20 if success else .32))
    remove_troops(a.troops, losses)
    remove_troops(p.garrison, math.ceil(sum(p.garrison.values()) * (.7 if success else .15)))
    a.morale = max(10, a.morale - (5 if success else 20))
    note(s, f"{place_name(p.id)}: {'штурм успешен' if success else 'штурм отбит'}, потери атакующих {losses}. Выжившие сохранили свои отряды.", "battle")
    siege.mode = "blockade"
    if success and a.size: _occupy(s, siege)
    elif not a.size:
        s.sieges.pop(p.id, None)
        homes = controlled(s, a.faction)
        if homes: a.location = min(homes, key=lambda p: (_distance(a.location, p.id), p.id)).id


def _ai(s: State) -> None:
    for fid in sorted(set(FACTIONS) - {"ottoman"}):
        if not controlled(s, fid): continue
        for a in sorted(s.armies.values(), key=lambda x: x.id):
            if a.faction != fid or a.size == 0: continue
            active = s.sieges.get(a.location)
            if active and active.army_id == a.id:
                _execute(s, "siege_mode", {"army": a.id, "mode": "works"}, fid)
                continue
            home = s.provinces[a.location]
            if home.controller == fid and home.owner == fid and home.id not in s.sieges and a.size < 120 and sum(home.garrison.values()) >= 10:
                try:
                    _execute(s, "recruit", {"province": home.id, "troop": "militia", "count": 10}, fid)
                    _execute(s, "mobilize", {"army": a.id, "troop": "militia", "count": 10}, fid)
                except RuleError: pass
            targets = [s.provinces[n] for n in neighbours(a.location) if can_use_route(s, fid, a.location, n) and s.provinces[n].controller != fid and relation(s, fid, s.provinces[n].controller)["status"] == "war"]
            targets.sort(key=lambda p: (p.owner != fid, sum(p.garrison.values()), p.id))
            for target in targets:
                # Defensive faction first tries to recover its occupied land.
                if s.turn < 8 and target.owner != fid: continue
                if army_power(s, a) > power(s, target.garrison, target.controller) * 1.4:
                    try: _execute(s, "move", {"army": a.id, "target": target.id}, fid)
                    except RuleError: continue
                    break


def _next_turn(s: State) -> None:
    _ai(s)
    s.turn += 1
    # Stable seeded initiative avoids a permanent player-first movement advantage.
    ordered = sorted(s.armies.values(), key=lambda a: rng(s, f"initiative:{a.id}").random())
    for a in ordered:
        if not a.order or not a.size: continue
        dest = s.provinces[a.order["target"]]
        if dest.controller != a.faction and relation(s, a.faction, dest.controller)["status"] != "war":
            a.order = None; continue
        old_siege = s.sieges.get(a.location)
        target = dest.id
        fee = {'land': 0, 'ferry': 10, 'sea': 20}[route_kind(a.location, target)]
        if not can_use_route(s, a.faction, a.location, target) or s.factions[a.faction].gold < fee:
            a.order = None
            note(s, f"Переход к {place_name(target)} отменён: нет средств или необходимых знаний.", 'supply')
            continue
        # Meet enemy field armies before occupying the same location.
        defenders = [other for other in s.armies.values() if other.faction != a.faction and other.location == target and other.size and relation(s, a.faction, other.faction)["status"] == "war"]
        for other in defenders:
            if army_power(s, a) >= army_power(s, other):
                remove_troops(a.troops, math.ceil(a.size * .15)); remove_troops(other.troops, math.ceil(other.size * .35))
                home = [p for p in controlled(s, other.faction) if p.id != target]
                if home:
                    other.location = min(home, key=lambda p: (_distance(target, p.id), p.id)).id
                    other.order = None
                    for pid, siege in list(s.sieges.items()):
                        if siege.army_id == other.id: del s.sieges[pid]
                else:
                    remove_troops(other.troops, other.size)
                note(s, f"Полевое сражение у {place_name(target)}: армия {FACTIONS[other.faction]} отступила.", "battle")
            else:
                remove_troops(a.troops, math.ceil(a.size * .3)); remove_troops(other.troops, math.ceil(other.size * .12))
                note(s, f"Поход к {place_name(target)} остановлен полевой армией.", "battle")
                a.order = None; break
        cleanup(s)
        if a.order is None: continue
        # Another army cannot replace an existing siege and discard its soldiers.
        if target in s.sieges and s.sieges[target].army_id != a.id:
            a.order = None; continue
        if not a.size:
            a.order = None; continue
        if old_siege and old_siege.army_id == a.id: s.sieges.pop(a.location, None)
        s.factions[a.faction].gold -= fee
        a.location = target; a.order = None
        if dest.controller != a.faction and not dest.walls and army_power(s, a) > power(s, dest.garrison, dest.controller) * 1.5:
            remove_troops(a.troops, min(a.size, math.ceil(sum(dest.garrison.values()) * .15)))
            if a.size: _occupy(s, Siege(target, a.id))
        elif dest.controller != a.faction:
            s.sieges[target] = Siege(target, a.id, supplies=120 if "granary" in dest.buildings else 100)
            note(s, f"{FACTIONS[a.faction]} начали осаду {place_name(target)}.", "siege")
    for a in s.armies.values():
        if not a.size: continue
        if supplied(s, a) and s.factions[a.faction].food > 0:
            convoy = "convoys" in s.factions[a.faction].technologies and s.provinces[a.location].controller == a.faction and PLACE_INDEX[a.location][7]
            a.supply = min(100, a.supply + 15 + (15 if convoy else 0)); a.morale = min(100, a.morale + 5)
        else:
            a.supply = max(0, a.supply - 25)
            if a.supply == 0:
                losses = max(1, math.ceil(a.size * .08)); remove_troops(a.troops, losses)
                note(s, f"Армия {FACTIONS[a.faction]} теряет {losses} воинов без снабжения.", "supply")
    for pid, siege in list(s.sieges.items()):
        a = s.armies[siege.army_id]; p = s.provinces[pid]
        if not a.size or relation(s, a.faction, p.controller)["status"] != "war":
            del s.sieges[pid]; continue
        if siege.mode == "assault": _assault(s, siege); continue
        if siege.mode == "negotiate": _occupy(s, siege); continue
        cover = min(1, a.size / max(1, sum(p.garrison.values()) * 1.5))
        port = PLACE_INDEX[pid][7]
        # Land-only blockade cannot fully starve a port supplied by sea in this chapter.
        replenishment = 20 if port else round((1 - cover) * 10)
        siege.supplies = max(0, min(120, siege.supplies - round(20 * cover) + replenishment))
        if siege.mode == "works" and a.supply > 20:
            tech = s.factions[a.faction].technologies
            damage = 3 + (4 if "siege_camp" in tech else 0) + a.engines * (10 if "trebuchets" in tech else 6)
            p.walls = max(0, p.walls - damage); siege.breached = p.walls <= 20
        siege.morale = max(0, siege.morale - (15 if siege.supplies <= 20 else 2))
        if siege.supplies == 0 and siege.morale <= 30: _occupy(s, siege)
    s.report = {}
    for fid, f in s.factions.items():
        b = budget(s, fid, for_turn=s.turn); s.report[fid] = b
        available = f.gold + b["income"] + b["trade"]
        f.arrears += max(0, b["expense"] - available)
        f.gold = max(0, available - b["expense"])
        if f.arrears:
            paid = min(f.gold, f.arrears); f.gold -= paid; f.arrears -= paid
        f.food = max(0, min(2000, f.food + b["food_income"] - b["food_expense"]))
        f.manpower = min(250, f.manpower + len(controlled(s, fid)) * 4)
        if f.arrears or f.food == 0:
            f.legitimacy = max(0, f.legitimacy - 3)
            for a in s.armies.values():
                if a.faction == fid:
                    a.morale = max(10, a.morale - 10)
                    remove_troops(a.troops, math.ceil(a.size * .04))
        if f.groups["military"] < 30:
            for a in s.armies.values():
                if a.faction == fid and a.size:
                    losses = math.ceil(a.size * .02)
                    remove_troops(a.troops, losses); a.morale = max(10, a.morale - 5)
                    note(s, f"{FACTIONS[fid]}: беи отзывают {losses} воинов из-за низкой поддержки власти.", "politics")
        if controlled(s, fid):
            f.knowledge += 6 + f.groups["administration"] // 20 + (2 if "scribes" in f.technologies else 0)
        if f.research:
            amount = min(f.knowledge, 15)
            f.knowledge -= amount; f.research["progress"] += amount
            if f.research["progress"] >= TECHNOLOGIES[f.research["id"]]["cost"]:
                f.technologies.append(f.research["id"])
                note(s, f"{FACTIONS[fid]}: освоено «{TECHNOLOGIES[f.research['id']]['name']}».", "research")
                f.research = None
    for p in s.provinces.values():
        if p.id not in s.sieges:
            p.loyalty = min(100, p.loyalty + (4 if "tolerance" in s.factions[p.controller].reforms else 1))
            p.prosperity = min(100, p.prosperity + 1)
            if p.construction and p.owner == p.controller:
                p.construction["left"] -= 1
                if p.construction["left"] == 0:
                    bid = p.construction['building']; p.construction = None
                    if bid == 'repair_walls':
                        p.walls = p.max_walls; name = 'Ремонт стен'
                    elif bid == 'new_fortress':
                        p.buildings.append(bid); p.fortress_level = 1
                        p.walls = p.max_walls = FORTRESS_PROJECT['walls']; name = FORTRESS_PROJECT['name']
                    else:
                        p.buildings.append(bid); name = BUILDINGS[bid]['name']
                        if bid == 'walls':
                            p.max_walls = min(150, p.max_walls + 25); p.walls = min(p.max_walls, p.walls + 25)
                    note(s, f"{place_name(p.id)}: завершена постройка «{name}».", 'building')
    cleanup(s)
    if not controlled(s, "ottoman"):
        s.ending = "Все владения потеряны. Государство распалось."
        s.pending_event = None
    note(s, "Сезон завершён. Проверьте отчёт казны, снабжение и решения совета.", "turn")


def _schedule_event(s: State) -> None:
    if s.pending_event or s.ending: return
    candidates = [
        ("merchant_debt", s.flags.get("founding") == "merchants" and s.turn >= 8),
        ("first_city", "first_capture_turn" in s.flags),
        ("local_petition", s.flags.get("first_city") == "charter" and s.turn >= s.flags.get("charter_turn", 0) + 3),
        ("military_claim", s.flags.get("founding") == "frontier" and "first_capture_turn" in s.flags and s.turn >= 4),
        ("succession", s.turn >= 100 and s.ruler_rank < 2),
        ("bursa", s.flags.get("bursa_captured") is True),
    ]
    candidates = [(f"accession_{r['id']}", s.turn >= (r['year'] - 1299) * 4 and s.ruler_rank < r['rank']) for r in DYNASTY[2:]] + candidates
    for event, eligible in candidates:
        if eligible and event not in s.shown_events:
            s.pending_event = event; return
    if s.turn >= 619:
        s.ending = f"Зима 1453 года. Летопись завершена: под вашей властью {len(controlled(s, 'ottoman'))} владений. Решения этой кампании определили судьбу державы."


def _choose(s: State, choice: str) -> None:
    event = s.pending_event
    require(event in EVENTS and choice in {c["id"] for c in EVENTS[event]["choices"]}, "Неизвестный ответ")
    f = s.factions["ottoman"]
    if event == "founding":
        if choice == "frontier":
            require(f.manpower >= 15, "Нужно 15 людей в резерве"); spend(f, 30); f.manpower -= 15; s.armies["ottoman-1"].troops["militia"] += 15
            f.groups["military"] += 10; f.groups["merchants"] -= 5
        elif choice == "merchants": f.gold += 60; f.groups["merchants"] += 10
        else: spend(f, 25); f.food += 80; f.knowledge += 15
    elif event == "merchant_debt":
        if choice == "repay": spend(f, 90); f.groups["merchants"] += 15
        elif choice == "privileges": s.flags["merchant_privileges"] = True; f.groups["merchants"] += 5; f.groups["military"] -= 5
        else: f.groups["merchants"] -= 25; f.legitimacy -= 10; s.flags["broken_promise"] = True
    elif event == "first_city":
        occupied = [p for p in controlled(s, "ottoman") if p.owner != "ottoman"]
        if choice == "charter":
            spend(f, 25); f.groups["military"] -= 5; s.flags["charter_turn"] = s.turn
            for p in occupied: p.loyalty = min(100, p.loyalty + 25)
        else:
            f.gold += 65; f.groups["military"] += 10
            for p in occupied: p.loyalty = max(0, p.loyalty - 20); p.prosperity = max(20, p.prosperity - 20)
    elif event == "local_petition":
        for p in controlled(s, "ottoman"):
            if p.id not in ("sogut", "karacahisar"): p.loyalty = max(0, min(100, p.loyalty + (15 if choice == "honour" else -25)))
        f.groups["military"] += -10 if choice == "honour" else 10
        f.legitimacy += 5 if choice == "honour" else -5
    elif event == "military_claim":
        if choice == "grant": s.flags["military_share"] = True; f.groups["military"] += 15; f.legitimacy += 5
        else: f.groups["military"] -= 20; f.groups["administration"] += 10
    elif event == "succession":
        if choice == "oath": spend(f, 40); f.groups["military"] += 10
        else: f.legitimacy -= 10; f.groups["military"] -= 15
        s.ruler = "Орхан"; s.ruler_id = "orhan"; s.ruler_rank = 2; s.flags["succession_done"] = True
    elif event.startswith('accession_'):
        ruler = next(r for r in DYNASTY if event == f"accession_{r['id']}")
        if choice == 'oath': spend(f, 40); f.groups['military'] += 10
        else: f.legitimacy -= 10; f.groups['military'] -= 15
        s.ruler = ruler['name']; s.ruler_id = ruler['id']; s.ruler_rank = ruler['rank']
        note(s, f"Власть принял {s.ruler}.", 'dynasty')
    elif event == "bursa":
        require(s.provinces["bursa"].controller == "ottoman", "Бурса больше не под вашим контролем")
        if choice == "capital":
            spend(f, 60); s.capital = "bursa"; s.provinces["bursa"].loyalty = min(100, s.provinces["bursa"].loyalty + 20); f.legitimacy += 15
        else: f.groups["military"] += 10; f.legitimacy += 10
        s.flags["chapter_complete"] = True
        note(s, "Первая глава пройдена. Государство продолжает жить; можно заключить мир и изучить последствия.", "chapter")
    s.flags[event] = choice
    f.legitimacy = max(0, min(100, f.legitimacy))
    f.groups = {k: max(0, min(100, v)) for k, v in f.groups.items()}
    s.shown_events.append(event); s.pending_event = None
    note(s, f"{EVENTS[event]['title']}: {next(c['text'] for c in EVENTS[event]['choices'] if c['id'] == choice)}", "decision")


def place_name(pid: str) -> str:
    return PLACE_INDEX[pid][1]


def validate(s: State) -> None:
    for p in s.provinces.values():
        assert p.owner in s.factions and p.controller in s.factions
        assert 0 <= p.loyalty <= 100 and 0 <= p.walls <= 150
        assert all(t in TROOPS and type(n) is int and n >= 0 for t, n in p.garrison.items())
    for a in s.armies.values():
        assert a.location in s.provinces and a.faction in s.factions
        assert all(t in TROOPS and type(n) is int and n >= 0 for t, n in a.troops.items())
        assert 0 <= a.supply <= 100 and 0 <= a.morale <= 100
    for pid, siege in s.sieges.items():
        a = s.armies[siege.army_id]
        assert siege.province == pid and a.location == pid and a.size > 0
        assert s.provinces[pid].controller != a.faction
        assert relation(s, a.faction, s.provinces[pid].controller)["status"] == "war"
    for f in s.factions.values():
        assert f.gold >= 0 and f.food >= 0 and f.manpower >= 0


def view(s: State) -> dict:
    data = s.to_dict()
    data["calendar"] = {"year": 1299 + s.turn // 4, "season": ["Весна", "Лето", "Осень", "Зима"][s.turn % 4]}
    data["budget"] = budget(s, "ottoman")
    data['fortress_construction'] = dict(FORTRESS_PROJECT, unlocked=s.ruler_rank >= 3, unlock_year=1362)
    data['dynasty'] = {'current': s.ruler_id, 'rank': s.ruler_rank, 'next': next((r for r in DYNASTY if r['rank'] > s.ruler_rank), None)}
    data["event"] = EVENTS.get(s.pending_event)
    data["chapter"] = {"name": "Рождение государства", "goal": "Установить контроль над Бурсой и определить её будущее", "complete": bool(s.flags.get("chapter_complete"))}
    if s.ruler_rank >= 3 or s.flags.get('chapter_complete'):
        data['chapter'] = {'name': 'Держава на перекрёстке', 'goal': 'Развивать государство, удерживать земли и определять отношения с соседями', 'complete': False}
    return data


def catalog() -> dict:
    return {"places": [{"id": x[0], "name": x[1], "lon": x[2], "lat": x[3], "port": x[7], "kind": PLACE_KINDS[x[0]]} for x in PLACES], "roads": ROADS, "troops": TROOPS, "buildings": BUILDINGS, "technologies": TECHNOLOGIES, "reforms": REFORMS, "factions": FACTIONS, "regions": REGIONS, "dynasty": DYNASTY, "fortress_project": FORTRESS_PROJECT, "route_details": [{"from": a, "to": b, "kind": route_kind(a, b), "cost": {"land": 0, "ferry": 10, "sea": 20}[route_kind(a,b)]} for a,b in ROADS]}
