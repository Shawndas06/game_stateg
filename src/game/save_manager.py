"""
save_manager.py — сохранение и загрузка игры в JSON.

Реализует:
- Путь к файлу: saves/savegame.json (от корня проекта).
- Сериализация SiegeInfo в словарь и обратно (_siege_to_dict, _dict_to_siege).
- save_game(game_state): запись всех полей GameState в JSON (включая ai_state, постройки, дипломатию, уведомления и т.д.).
- load_game(): чтение JSON и восстановление GameState; приведение списков/множеств (fortress_buildings, trade_proposals_pending, ai_diplomacy_proposals).
- has_save(): проверка наличия файла сохранения.
"""

import json
from pathlib import Path

from src.game.game_state import GameState, SiegeInfo


SAVE_PATH = Path(__file__).resolve().parent.parent.parent / "saves"
SAVE_FILE = SAVE_PATH / "savegame.json"


def _siege_to_dict(siege: SiegeInfo) -> dict:
    """Преобразование SiegeInfo в словарь для JSON (включая defender_supplies и catapults при наличии)."""
    d = {
        "target_fortress_id": siege.target_fortress_id,
        "source_fortress_id": siege.source_fortress_id,
        "attacker_troops": siege.attacker_troops,
        "turns_remaining": siege.turns_remaining,
    }
    if hasattr(siege, "defender_supplies"):
        d["defender_supplies"] = siege.defender_supplies
    if hasattr(siege, "catapults"):
        d["catapults"] = siege.catapults
    return d


def _dict_to_siege(d: dict) -> SiegeInfo:
    """Восстановление SiegeInfo из словаря (с дефолтами для defender_supplies и catapults)."""
    return SiegeInfo(
        target_fortress_id=d["target_fortress_id"],
        source_fortress_id=d["source_fortress_id"],
        attacker_troops=d["attacker_troops"],
        turns_remaining=d["turns_remaining"],
        defender_supplies=d.get("defender_supplies", 3),
        catapults=d.get("catapults", 0),
    )


def save_game(game_state: GameState) -> bool:
    """Сохранить состояние игры в saves/savegame.json. Возвращает True при успехе."""
    try:
        SAVE_PATH.mkdir(parents=True, exist_ok=True)
        sieges_data = {k: _siege_to_dict(v) for k, v in game_state.sieges_in_progress.items()}
        data = {
            "stage": game_state.stage,
            "year": game_state.year,
            "turn": game_state.turn,
            "gold": game_state.gold,
            "capital_id": game_state.capital_id,
            "field_army": game_state.field_army,
            "fortress_renames": dict(game_state.fortress_renames),
            "fortress_owners": dict(game_state.fortress_owners),
            "fortress_garrisons": dict(game_state.fortress_garrisons),
            "shown_events": list(game_state.shown_events),
            "enacted_laws": list(game_state.enacted_laws),
            "trade_partners": list(game_state.trade_partners),
            "nap_violations": game_state.nap_violations,
            "ai_state": game_state.ai_state,
            "sieges_in_progress": sieges_data,
            "fortress_buildings": {k: list(v) for k, v in getattr(game_state, "fortress_buildings", {}).items()},
            "fortress_build_progress": dict(getattr(game_state, "fortress_build_progress", {})),
            "fortress_governors": dict(getattr(game_state, "fortress_governors", {})),
            "field_army_commander": getattr(game_state, "field_army_commander", None),
            "garrison_troops": dict(getattr(game_state, "garrison_troops", {})),
            "field_army_troops": dict(getattr(game_state, "field_army_troops", {})),
            "legitimacy": getattr(game_state, "legitimacy", 50),
            "trade_proposals_pending": list(getattr(game_state, "trade_proposals_pending", [])),
            "notifications": list(getattr(game_state, "notifications", [])),
            "fortress_unrest": dict(getattr(game_state, "fortress_unrest", {})),
            "sultan_health": getattr(game_state, "sultan_health", 80),
            "heir_name": getattr(game_state, "heir_name", "Орхан"),
            "ai_diplomacy_proposals": list(getattr(game_state, "ai_diplomacy_proposals", [])),
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_game() -> GameState | None:
    """Загрузить состояние из saves/savegame.json. Возвращает GameState или None при ошибке/отсутствии файла."""
    try:
        if not SAVE_FILE.exists():
            return None
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = GameState()
        state.stage = data.get("stage", state.stage)
        state.year = data.get("year", state.year)
        state.turn = data.get("turn", state.turn)
        state.gold = data.get("gold", state.gold)
        state.capital_id = data.get("capital_id", state.capital_id)
        state.field_army = data.get("field_army", 0)
        state.fortress_renames = dict(data.get("fortress_renames", {}))
        state.fortress_owners = dict(data.get("fortress_owners", state.fortress_owners))
        state.fortress_garrisons = dict(data.get("fortress_garrisons", {}))
        state.shown_events = set(data.get("shown_events", []))
        state.enacted_laws = set(data.get("enacted_laws", []))
        state.trade_partners = set(data.get("trade_partners", []))
        state.nap_violations = data.get("nap_violations", 0)
        state.ai_state = data.get("ai_state", state.ai_state)
        sieges_raw = data.get("sieges_in_progress", {})
        state.sieges_in_progress = {k: _dict_to_siege(v) for k, v in sieges_raw.items()}
        state.fortress_buildings = {k: set(v) for k, v in data.get("fortress_buildings", {}).items()}
        state.fortress_build_progress = dict(data.get("fortress_build_progress", {}))
        state.fortress_governors = dict(data.get("fortress_governors", {}))
        state.field_army_commander = data.get("field_army_commander")
        gt = data.get("garrison_troops", {})
        state.garrison_troops = {k: dict(v) if isinstance(v, dict) else v for k, v in gt.items()}
        state.field_army_troops = dict(data.get("field_army_troops", {}))
        state.legitimacy = data.get("legitimacy", 50)
        tpp = data.get("trade_proposals_pending", [])
        state.trade_proposals_pending = [tuple(p) if isinstance(p, list) else (p,) for p in tpp]
        state.notifications = list(data.get("notifications", []))
        state.fortress_unrest = dict(data.get("fortress_unrest", {}))
        state.sultan_health = data.get("sultan_health", 80)
        state.heir_name = data.get("heir_name", "Орхан")
        adp = data.get("ai_diplomacy_proposals", [])
        state.ai_diplomacy_proposals = [tuple(p) if isinstance(p, list) else (p,) for p in adp]
        for fid, ai in state.ai_state.items():
            if "fortress_buildings" not in ai:
                ai["fortress_buildings"] = {}
            if "fortress_build_progress" not in ai:
                ai["fortress_build_progress"] = {}
        return state
    except Exception:
        return None


def has_save() -> bool:
    """Проверить, существует ли файл сохранения."""
    return SAVE_FILE.exists()
