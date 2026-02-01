"""
Менеджер сохранения/загрузки игры
"""

import json
from pathlib import Path

from src.game.game_state import GameState, SiegeInfo


SAVE_PATH = Path(__file__).resolve().parent.parent.parent / "saves"
SAVE_FILE = SAVE_PATH / "savegame.json"


def _siege_to_dict(siege: SiegeInfo) -> dict:
    return {
        "target_fortress_id": siege.target_fortress_id,
        "source_fortress_id": siege.source_fortress_id,
        "attacker_troops": siege.attacker_troops,
        "turns_remaining": siege.turns_remaining,
    }


def _dict_to_siege(d: dict) -> SiegeInfo:
    return SiegeInfo(
        target_fortress_id=d["target_fortress_id"],
        source_fortress_id=d["source_fortress_id"],
        attacker_troops=d["attacker_troops"],
        turns_remaining=d["turns_remaining"],
    )


def save_game(game_state: GameState) -> bool:
    """
    Сохранить текущее состояние игры в файл.
    Возвращает True при успехе.
    """
    try:
        SAVE_PATH.mkdir(parents=True, exist_ok=True)
        sieges_data = {
            k: _siege_to_dict(v)
            for k, v in game_state.sieges_in_progress.items()
        }
        data = {
            "stage": game_state.stage,
            "year": game_state.year,
            "turn": game_state.turn,
            "gold": game_state.gold,
            "capital_id": game_state.capital_id,
            "field_army": game_state.field_army,
            "fortress_renames": dict(game_state.fortress_renames),
            "owned_fortresses": list(game_state.owned_fortresses),
            "fortress_garrisons": dict(game_state.fortress_garrisons),
            "shown_events": list(game_state.shown_events),
            "sieges_in_progress": sieges_data,
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_game() -> GameState | None:
    """
    Загрузить сохранение. Возвращает GameState или None при ошибке.
    """
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
        state.owned_fortresses = set(data.get("owned_fortresses", []))
        state.fortress_garrisons = dict(data.get("fortress_garrisons", {}))
        state.shown_events = set(data.get("shown_events", []))
        sieges_raw = data.get("sieges_in_progress", {})
        state.sieges_in_progress = {
            k: _dict_to_siege(v) for k, v in sieges_raw.items()
        }
        return state
    except Exception:
        return None


def has_save() -> bool:
    """Проверить наличие сохранения"""
    return SAVE_FILE.exists()
