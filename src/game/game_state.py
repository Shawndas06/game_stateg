"""
Состояние игры — центральный хранилище данных кампании
Золото, гарнизоны, армии, осады, владение крепостями
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from src.data.fortresses import Fortress, FORTESSES_DATA, get_fortress_by_id
from src.data.factions_data import AI_FACTION_IDS, FACTION_IDS
from src.data.campaign_stages import get_stage_by_fortress, STAGES
from src.data.laws_data import LAW_EFFECTS
from src.utils.constants import STAGE_BEYLIK

SIEGE_ADJACENCY_DISTANCE = 720
SIEGE_TURNS_CAPITULATION = 3
HIRE_COST_PER_TROOP = 5
GOLD_PER_FORTRESS_PER_TURN = 15
UPKEEP_PER_TROOP = 1
ASSAULT_RATIO = 1.5
STARTING_GOLD = 100
DEFAULT_CAPITAL_ID = "sogut"
AI_STARTING_GOLD = 120
TRIBUTE_GOLD_PER_TURN = 25
TRADE_GOLD_PER_TURN = 12
DEFENDER_SUPPLIES_START = 3


@dataclass
class SiegeInfo:
    """Информация об осаде (снабжение защитника)"""
    target_fortress_id: str
    source_fortress_id: str
    attacker_troops: int
    turns_remaining: int
    defender_supplies: int = DEFENDER_SUPPLIES_START


def _init_fortress_owners() -> dict[str, str]:
    return {f.id: f.faction for f in FORTESSES_DATA}


def _init_ai_state() -> dict:
    """Начальное состояние AI-фракций."""
    state = {}
    for fid in AI_FACTION_IDS:
        forts = [f for f in FORTESSES_DATA if f.faction == fid]
        capital = forts[0].id if forts else None
        state[fid] = {
            "gold": AI_STARTING_GOLD,
            "garrisons": {},
            "sieges": {},
            "field_army": 0,
            "capital": capital,
            "relation": "war" if fid == "byzantine" else "peace",
        }
    return state


@dataclass
class GameState:
    """Текущее состояние кампании."""
    stage: str = STAGE_BEYLIK
    year: int = 1299
    turn: int = 0
    gold: int = STARTING_GOLD
    fortress_owners: dict[str, str] = field(default_factory=_init_fortress_owners)
    fortress_garrisons: dict[str, int] = field(default_factory=dict)
    capital_id: str = DEFAULT_CAPITAL_ID
    field_army: int = 0
    fortress_renames: dict[str, str] = field(default_factory=dict)
    sieges_in_progress: dict[str, SiegeInfo] = field(default_factory=dict)
    shown_events: set[str] = field(default_factory=set)
    enacted_laws: set[str] = field(default_factory=set)
    ai_state: dict = field(default_factory=_init_ai_state)
    trade_partners: set[str] = field(default_factory=set)  # Фракции с торговым соглашением
    nap_violations: int = 0  # Количество нарушений НПП (влияет на дипломатию)

    byzantine_relation: str = "war"

    @property
    def owned_fortresses(self) -> set[str]:
        return {fid for fid, o in self.fortress_owners.items() if o == "ottoman"}

    @property
    def byzantine_owned(self) -> set[str]:
        return {fid for fid, o in self.fortress_owners.items() if o == "byzantine"}

    def get_fortress_owner(self, fortress_id: str) -> str:
        return self.fortress_owners.get(fortress_id) or get_fortress_by_id(fortress_id).faction if get_fortress_by_id(fortress_id) else ""

    def get_relation_with(self, faction_id: str) -> str:
        """Отношения с фракцией: war, peace, tribute, alliance, nap."""
        if faction_id == "ottoman":
            return "peace"
        ai = self.ai_state.get(faction_id, {})
        return ai.get("relation", "war")

    def _get_law_modifiers(self) -> dict:
        """Модификаторы из принятых законов."""
        mods = {"income": 1.0, "hire_cost": 1.0, "upkeep": 1.0, "assault_morale": 0.0, "trade_income": 1.0}
        for law_id in self.enacted_laws:
            eff = LAW_EFFECTS.get(law_id, {})
            for k, v in eff.items():
                if k in mods:
                    if k in ("income", "hire_cost", "upkeep", "trade_income"):
                        mods[k] *= v
                    else:
                        mods[k] += v
        return mods

    def _get_garrison(self, fortress_id: str) -> int:
        fortress = get_fortress_by_id(fortress_id)
        if not fortress:
            return 0
        owner = self.get_fortress_owner(fortress_id)
        if owner == "ottoman":
            return self.fortress_garrisons.get(fortress_id, fortress.base_garrison)
        if owner in AI_FACTION_IDS:
            ai = self.ai_state.get(owner, {})
            g = ai.get("garrisons", {})
            return g.get(fortress_id, fortress.base_garrison)
        return fortress.base_garrison

    def _distance(self, fid1: str, fid2: str) -> float:
        f1 = get_fortress_by_id(fid1)
        f2 = get_fortress_by_id(fid2)
        if not f1 or not f2:
            return float("inf")
        return ((f1.x - f2.x) ** 2 + (f1.y - f2.y) ** 2) ** 0.5

    def set_capital(self, fortress_id: str) -> tuple[bool, str]:
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        if fortress_id == self.capital_id:
            return False, "Уже столица"
        self.capital_id = fortress_id
        return True, "Столица перенесена"

    def rename_fortress(self, fortress_id: str, new_name: str) -> tuple[bool, str]:
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        name = new_name.strip()
        if not name or len(name) > 30:
            return False, "Имя: 1–30 символов"
        self.fortress_renames[fortress_id] = name
        return True, f"Переименовано в «{name}»"

    def get_fortress_display_name(self, fortress_id: str) -> str:
        if fortress_id in self.fortress_renames:
            return self.fortress_renames[fortress_id]
        f = get_fortress_by_id(fortress_id)
        return f.name_ru if f else fortress_id

    def is_capital(self, fortress_id: str) -> bool:
        return fortress_id == self.capital_id

    def get_other_owned_fortresses(self, exclude_id: str) -> list[tuple[str, int]]:
        return [
            (fid, self._get_garrison(fid))
            for fid in self.owned_fortresses
            if fid != exclude_id
        ]

    def get_adjacent_owned_fortresses(self, target_fortress_id: str) -> list[tuple[str, int]]:
        result = []
        for fid in self.owned_fortresses:
            if self._distance(fid, target_fortress_id) <= SIEGE_ADJACENCY_DISTANCE:
                result.append((fid, self._get_garrison(fid)))
        return result

    def get_defender_garrison(self, fortress_id: str) -> int:
        return self._get_garrison(fortress_id)

    def get_effective_defender(self, fortress_id: str) -> float:
        defender = self.get_defender_garrison(fortress_id)
        fortress = get_fortress_by_id(fortress_id)
        fortification = getattr(fortress, "fortification", 1.0) if fortress else 1.0
        return defender * fortification

    def transfer_to_field_army(self, source_fortress_id: str, amount: int) -> tuple[bool, str]:
        if source_fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        garrison = self._get_garrison(source_fortress_id)
        if amount <= 0 or amount > garrison:
            return False, "Недостаточно войск"
        if garrison - amount < 1:
            amount = garrison - 1
            if amount <= 0:
                return False, "Минимум 1 воин должен остаться в гарнизоне"
        self.fortress_garrisons[source_fortress_id] = garrison - amount
        if self.fortress_garrisons[source_fortress_id] < 1:
            self.fortress_garrisons[source_fortress_id] = 1
        self.field_army += amount
        return True, f"В армию переведено {amount} воинов"

    def can_besiege(self, fortress_id: str) -> bool:
        """Можно осаждать любую вражескую крепость (не свою)."""
        if fortress_id in self.owned_fortresses or fortress_id in self.sieges_in_progress:
            return False
        owner = self.get_fortress_owner(fortress_id)
        if owner == "ottoman":
            return False
        return (
            self.field_army > self.get_defender_garrison(fortress_id)
            and len(self.get_adjacent_owned_fortresses(fortress_id)) > 0
        )

    def _get_effective_defender(self, fortress_id: str) -> float:
        defender = self.get_defender_garrison(fortress_id)
        fortress = get_fortress_by_id(fortress_id)
        fortification = getattr(fortress, "fortification", 1.0) if fortress else 1.0
        return defender * fortification

    def can_assault(self, fortress_id: str, attacker_troops: int) -> bool:
        effective_defender = self._get_effective_defender(fortress_id)
        return attacker_troops >= int(effective_defender * ASSAULT_RATIO)

    def start_siege_from_field_army(
        self,
        target_fortress_id: str,
        troop_count: int,
    ) -> tuple[bool, str]:
        if target_fortress_id in self.owned_fortresses:
            return False, "Крепость уже ваша"
        if target_fortress_id in self.sieges_in_progress:
            return False, "Осада уже идёт"
        if troop_count <= 0 or troop_count > self.field_army:
            return False, "Недостаточно войск в армии"
        defender = self.get_defender_garrison(target_fortress_id)
        if troop_count <= defender:
            return False, f"Нужно больше войск! Гарнизон: {defender}"
        if len(self.get_adjacent_owned_fortresses(target_fortress_id)) == 0:
            return False, "Нет своих крепостей рядом с целью"
        self.field_army -= troop_count
        self.sieges_in_progress[target_fortress_id] = SiegeInfo(
            target_fortress_id=target_fortress_id,
            source_fortress_id="field_army",
            attacker_troops=troop_count,
            turns_remaining=SIEGE_TURNS_CAPITULATION,
            defender_supplies=DEFENDER_SUPPLIES_START,
        )
        return True, ""

    def assault_from_field_army(
        self,
        target_fortress_id: str,
        troop_count: int,
    ) -> tuple[bool, str]:
        if not self.can_assault(target_fortress_id, troop_count):
            effective = self._get_effective_defender(target_fortress_id)
            needed = int(effective * ASSAULT_RATIO)
            return False, f"Для штурма нужно минимум {needed} воинов (гарнизон с учётом укреплений)"
        if troop_count <= 0 or troop_count > self.field_army:
            return False, "Недостаточно войск в армии"
        if len(self.get_adjacent_owned_fortresses(target_fortress_id)) == 0:
            return False, "Нет своих крепостей рядом с целью"
        self.field_army -= troop_count
        effective_defender = self._get_effective_defender(target_fortress_id)
        ratio = troop_count / max(1, effective_defender)
        defeat_chance = max(0.05, 0.5 - (ratio - 1.5) * 0.15)
        mods = self._get_law_modifiers()
        defeat_chance -= mods["assault_morale"]  # Идеология газа снижает шанс поражения
        defeat_chance = max(0.02, defeat_chance)
        if random.random() < defeat_chance:
            return False, f"Штурм отбит! Потери: {troop_count} воинов. Укрепления оказались крепче."
        loss_factor = 0.5 - (ratio - 1.5) * 0.05
        survivors = max(1, int(troop_count * (1 - loss_factor)))
        self._capture_fortress(target_fortress_id, survivors)
        return True, f"Штурм успешен! Выжило: {survivors} воинов — стали гарнизоном."

    def _capture_fortress(self, fortress_id: str, garrison: int = 50) -> bool:
        fortress = get_fortress_by_id(fortress_id)
        if not fortress or fortress_id in self.owned_fortresses:
            return False
        prev_owner = self.fortress_owners.get(fortress_id, fortress.faction)
        self.fortress_owners[fortress_id] = "ottoman"
        self.fortress_garrisons[fortress_id] = garrison
        if prev_owner in AI_FACTION_IDS:
            ai = self.ai_state.get(prev_owner, {})
            g = ai.get("garrisons", {})
            g.pop(fortress_id, None)
        return True

    def capture_fortress(self, fortress_id: str) -> bool:
        return self._capture_fortress(fortress_id, garrison=50)

    def hire_troops(self, fortress_id: str, count: int) -> tuple[bool, str]:
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        if count <= 0:
            return False, "Укажите количество"
        mods = self._get_law_modifiers()
        cost_per = int(HIRE_COST_PER_TROOP * mods["hire_cost"])
        cost = count * cost_per
        if self.gold < cost:
            return False, f"Недостаточно золота. Нужно: {cost}"
        self.gold -= cost
        current = self._get_garrison(fortress_id)
        self.fortress_garrisons[fortress_id] = current + count
        return True, f"Нанято {count} воинов"

    def get_stage_info(self):
        return STAGES.get(self.stage, STAGES[STAGE_BEYLIK])

    def is_fortress_owned(self, fortress_id: str) -> bool:
        return fortress_id in self.owned_fortresses

    def is_fortress_byzantine(self, fortress_id: str) -> bool:
        return fortress_id in self.byzantine_owned

    def is_fortress_enemy(self, fortress_id: str) -> bool:
        """Любая крепость, не принадлежащая игроку."""
        return self.get_fortress_owner(fortress_id) != "ottoman"

    def next_turn(self) -> list[str]:
        self.turn += 1
        if self.turn % 3 == 0:
            self.year += 1
        mods = self._get_law_modifiers()

        # Расходы на армию (с учётом законов)
        troops_total = sum(self._get_garrison(fid) for fid in self.owned_fortresses) + self.field_army
        upkeep = int(troops_total * UPKEEP_PER_TROOP * mods["upkeep"])
        self.gold -= upkeep

        # Доход с крепостей
        base_income = len(self.owned_fortresses) * GOLD_PER_FORTRESS_PER_TURN
        self.gold += int(base_income * mods["income"])

        # Дань от вассалов
        for fid in AI_FACTION_IDS:
            if self.get_relation_with(fid) == "tribute":
                self.gold += TRIBUTE_GOLD_PER_TURN

        # Торговый доход (капитуляции увеличивают)
        for _ in self.trade_partners:
            self.gold += int(TRADE_GOLD_PER_TURN * mods["trade_income"])

        # Осады (снабжение защитника: при 0 — капитуляция быстрее)
        captured = []
        for fid in list(self.sieges_in_progress.keys()):
            siege = self.sieges_in_progress[fid]
            supplies = getattr(siege, "defender_supplies", DEFENDER_SUPPLIES_START)
            supplies = max(0, supplies - 1)
            siege.defender_supplies = supplies
            siege.turns_remaining -= 1
            if supplies <= 0:
                siege.turns_remaining -= 1  # Без снабжения — двойной прогресс капитуляции
            if siege.turns_remaining <= 0:
                del self.sieges_in_progress[fid]
                garrison_survivors = max(50, int(siege.attacker_troops * 0.9))
                self._capture_fortress(fid, garrison_survivors)
                captured.append(fid)

        from src.game.ai_controller import process_all_ai_turns
        process_all_ai_turns(self)
        return captured
