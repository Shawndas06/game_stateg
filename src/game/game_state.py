"""
Состояние игры — центральный хранилище данных кампании
Золото, гарнизоны, армии, осады
"""

from dataclasses import dataclass, field
from typing import Optional

from src.data.fortresses import Fortress, FORTESSES_DATA, get_fortress_by_id
from src.data.campaign_stages import (
    get_stage_by_fortress,
    STAGES,
)
from src.utils.constants import STAGE_BEYLIK

# Максимальная дистанция (px) до своей крепости для возможности осады
SIEGE_ADJACENCY_DISTANCE = 280
# Ходов на осаду до капитуляции (когда атакующие сильнее)
SIEGE_TURNS_CAPITULATION = 3
# Стоимость найма одного война (золото)
HIRE_COST_PER_TROOP = 5
# Золото за ход с каждой своей крепости
GOLD_PER_FORTRESS_PER_TURN = 15
# Начальное золото
STARTING_GOLD = 100
# Множитель для штурма — нужна армия в 1.5x больше гарнизона
ASSAULT_RATIO = 1.5
# ID столицы по умолчанию
DEFAULT_CAPITAL_ID = "sogut"


@dataclass
class SiegeInfo:
    """Информация об осаде"""
    target_fortress_id: str
    source_fortress_id: str  # Откуда отправлены войска
    attacker_troops: int
    turns_remaining: int


@dataclass
class GameState:
    """
    Текущее состояние кампании.
    Османский беелик → Султанат (Бурса)
    """
    # Текущий этап кампании
    stage: str = STAGE_BEYLIK
    # Текущий год (начинаем 1299)
    year: int = 1299
    # Номер хода
    turn: int = 0
    # Золото казны
    gold: int = STARTING_GOLD
    # Захваченные крепости (id) — в начале только османские
    owned_fortresses: set[str] = field(default_factory=lambda: {
        f.id for f in FORTESSES_DATA if f.faction == "ottoman"
    })
    # Гарнизоны в своих крепостях: fortress_id -> количество войск (по умолчанию base_garrison)
    fortress_garrisons: dict[str, int] = field(default_factory=dict)
    # Текущая столица — здесь собирается походная армия
    capital_id: str = DEFAULT_CAPITAL_ID
    # Походная армия — собирается в столице, отправляется на осады
    field_army: int = 0
    # Переименования крепостей: fortress_id -> новое имя
    fortress_renames: dict[str, str] = field(default_factory=dict)
    # Осады в процессе: fortress_id -> SiegeInfo
    sieges_in_progress: dict[str, SiegeInfo] = field(default_factory=dict)
    # Показанные нарративные события (id)
    shown_events: set[str] = field(default_factory=set)

    def _get_garrison(self, fortress_id: str) -> int:
        """Гарнизон крепости (своей или вражеской)"""
        fortress = get_fortress_by_id(fortress_id)
        if not fortress:
            return 0
        if fortress_id in self.owned_fortresses:
            return self.fortress_garrisons.get(
                fortress_id,
                fortress.base_garrison
            )
        # Вражеская — всегда base_garrison
        return fortress.base_garrison

    def _distance(self, fid1: str, fid2: str) -> float:
        """Расстояние между двумя крепостями на карте (px)"""
        f1 = get_fortress_by_id(fid1)
        f2 = get_fortress_by_id(fid2)
        if not f1 or not f2:
            return float("inf")
        return ((f1.x - f2.x) ** 2 + (f1.y - f2.y) ** 2) ** 0.5

    def set_capital(self, fortress_id: str) -> tuple[bool, str]:
        """Перенести столицу в крепость. Возвращает (успех, сообщение)."""
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        if fortress_id == self.capital_id:
            return False, "Уже столица"
        self.capital_id = fortress_id
        return True, "Столица перенесена"

    def rename_fortress(self, fortress_id: str, new_name: str) -> tuple[bool, str]:
        """Переименовать крепость. Возвращает (успех, сообщение)."""
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        name = new_name.strip()
        if not name or len(name) > 30:
            return False, "Имя: 1–30 символов"
        self.fortress_renames[fortress_id] = name
        return True, f"Переименовано в «{name}»"

    def get_fortress_display_name(self, fortress_id: str) -> str:
        """Имя крепости для отображения (кастомное или из данных)."""
        if fortress_id in self.fortress_renames:
            return self.fortress_renames[fortress_id]
        f = get_fortress_by_id(fortress_id)
        return f.name_ru if f else fortress_id

    def is_capital(self, fortress_id: str) -> bool:
        return fortress_id == self.capital_id

    def get_other_owned_fortresses(self, exclude_id: str) -> list[tuple[str, int]]:
        """Свои крепости кроме указанной. (fortress_id, garrison)."""
        return [
            (fid, self._get_garrison(fid))
            for fid in self.owned_fortresses
            if fid != exclude_id
        ]

    def get_adjacent_owned_fortresses(self, target_fortress_id: str) -> list[tuple[str, int]]:
        """
        Свои крепости рядом с целью (в пределах SIEGE_ADJACENCY_DISTANCE).
        Возвращает список (fortress_id, garrison_count).
        """
        result = []
        for fid in self.owned_fortresses:
            if self._distance(fid, target_fortress_id) <= SIEGE_ADJACENCY_DISTANCE:
                garrison = self._get_garrison(fid)
                result.append((fid, garrison))
        return result

    def get_defender_garrison(self, fortress_id: str) -> int:
        """Гарнизон вражеской крепости (защитники)"""
        return self._get_garrison(fortress_id)

    def transfer_to_field_army(self, source_fortress_id: str, amount: int) -> tuple[bool, str]:
        """
        Перевести войска из крепости в походную армию (столица).
        Возвращает (успех, сообщение).
        """
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
        """Можно ли начать осаду (есть походная армия и своя крепость рядом)"""
        if fortress_id in self.owned_fortresses or fortress_id in self.sieges_in_progress:
            return False
        target = get_fortress_by_id(fortress_id)
        if not target or target.faction != "byzantine":
            return False
        return (
            self.field_army > self.get_defender_garrison(fortress_id)
            and len(self.get_adjacent_owned_fortresses(fortress_id)) > 0
        )

    def can_assault(self, fortress_id: str, attacker_troops: int) -> bool:
        """Можно ли штурмовать (армия >= гарнизон * ASSAULT_RATIO)"""
        defender = self.get_defender_garrison(fortress_id)
        return attacker_troops >= int(defender * ASSAULT_RATIO)

    def start_siege_from_field_army(
        self,
        target_fortress_id: str,
        troop_count: int,
    ) -> tuple[bool, str]:
        """
        Начать осаду походной армией. Списывает войска из field_army.
        """
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
        )
        return True, ""

    def assault_from_field_army(
        self,
        target_fortress_id: str,
        troop_count: int,
    ) -> tuple[bool, str]:
        """
        Штурм походной армией. Мгновенный захват, если армия сильнее.
        """
        if not self.can_assault(target_fortress_id, troop_count):
            defender = self.get_defender_garrison(target_fortress_id)
            needed = int(defender * ASSAULT_RATIO)
            return False, f"Для штурма нужно минимум {needed} воинов (гарнизон: {defender})"

        if troop_count <= 0 or troop_count > self.field_army:
            return False, "Недостаточно войск в армии"

        if len(self.get_adjacent_owned_fortresses(target_fortress_id)) == 0:
            return False, "Нет своих крепостей рядом с целью"

        self.field_army -= troop_count

        # Потери при штурме — ~40%
        survivors = max(1, int(troop_count * 0.6))
        self._capture_fortress(target_fortress_id, survivors)
        return True, f"Штурм успешен! Выжило: {survivors} воинов"

    def _capture_fortress(self, fortress_id: str, garrison: int = 50) -> bool:
        """Захватить крепость (внутренний метод)"""
        fortress = get_fortress_by_id(fortress_id)
        if not fortress or fortress_id in self.owned_fortresses:
            return False

        self.owned_fortresses.add(fortress_id)
        self.fortress_garrisons[fortress_id] = garrison

        new_stage = get_stage_by_fortress(fortress_id)
        if new_stage:
            self.stage = new_stage
        return True

    def capture_fortress(self, fortress_id: str) -> bool:
        """Захватить крепость (при капитуляции после осады)"""
        return self._capture_fortress(fortress_id, garrison=50)

    def hire_troops(self, fortress_id: str, count: int) -> tuple[bool, str]:
        """
        Нанять войска в крепости. Стоит gold.
        Возвращает (успех, сообщение).
        """
        if fortress_id not in self.owned_fortresses:
            return False, "Не ваша крепость"
        if count <= 0:
            return False, "Укажите количество"
        cost = count * HIRE_COST_PER_TROOP
        if self.gold < cost:
            return False, f"Недостаточно золота. Нужно: {cost}"

        self.gold -= cost
        current = self._get_garrison(fortress_id)
        self.fortress_garrisons[fortress_id] = current + count
        return True, f"Нанято {count} воинов"

    def get_stage_info(self):
        """Информация о текущем этапе"""
        return STAGES.get(self.stage, STAGES[STAGE_BEYLIK])

    def is_fortress_owned(self, fortress_id: str) -> bool:
        return fortress_id in self.owned_fortresses

    def next_turn(self) -> list[str]:
        """
        Следующий ход. Обрабатывает осады и доход.
        Возвращает список fortress_id, которые были захвачены.
        """
        self.turn += 1
        if self.turn % 3 == 0:
            self.year += 1

        # Доход с крепостей
        self.gold += len(self.owned_fortresses) * GOLD_PER_FORTRESS_PER_TURN

        captured = []
        for fid in list(self.sieges_in_progress.keys()):
            siege = self.sieges_in_progress[fid]
            siege.turns_remaining -= 1
            if siege.turns_remaining <= 0:
                del self.sieges_in_progress[fid]
                self.capture_fortress(fid)
                captured.append(fid)
        return captured
